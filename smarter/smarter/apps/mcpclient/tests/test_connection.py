"""
Test :mod:`smarter.apps.mcpclient.connection`.

The MCP server is the in-process test server of :func:`.base_classes.build_test_server`.

.. note::

    **Experimental.** The MCPClient was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

import asyncio
import time
from unittest import mock

import httpx2
import mcp_types
from mcp.server import MCPServer

from smarter.apps.mcpclient.connection import (
    MAX_RESULT_CHARACTERS,
    TRUNCATION_MARKER,
    USER_AGENT,
    MCPServerCatalog,
    MCPServerConnection,
    content_to_text,
    guard_request,
    guarded_http_client,
    is_resource_allowed,
    is_tool_allowed,
    matches_any,
    run_sync,
    truncate,
)
from smarter.apps.mcpclient.exceptions import (
    SmarterMCPClientConfigurationError,
    SmarterMCPClientConnectionError,
    SmarterMCPClientPermissionError,
)
from smarter.apps.mcpclient.models import MCPAuthType, MCPClient, MCPTransport
from smarter.apps.plugin.plugin.safe_http import SafeHttpError

from .base_classes import (
    GUARD_PATCH,
    README_TEXT,
    README_URI,
    TEST_SERVER_INSTRUCTIONS,
    TEST_SERVER_NAME,
    TEST_SERVER_VERSION,
    TOKEN_VALUE,
    MCPClientTestBase,
    mock_mcp_server,
)


# pylint: disable=too-many-public-methods
class TestMCPServerConnection(MCPClientTestBase):
    """Test MCPServerConnection, and the connection helpers."""

    def connection(self, **fields) -> MCPServerConnection:
        """Return a connection for an unsaved copy of the test MCPClient, with fields overridden."""
        mcpclient = MCPClient.objects.get(pk=self.mcpclient.pk)
        for key, value in fields.items():
            setattr(mcpclient, key, value)
        return MCPServerConnection(mcpclient)

    # -------------------------------------------------------------------------
    # discover()
    # -------------------------------------------------------------------------
    def test_discover(self):
        """Test that discover() returns the server's identity, instructions, capabilities and tools."""
        with mock_mcp_server() as guard:
            catalog = self.connection().discover()
        self.assertIsInstance(catalog, MCPServerCatalog)
        self.assertEqual(catalog.server_name, TEST_SERVER_NAME)
        self.assertEqual(catalog.server_version, TEST_SERVER_VERSION)
        self.assertEqual(catalog.instructions, TEST_SERVER_INSTRUCTIONS)
        self.assertTrue(catalog.protocol_version)
        self.assertTrue(catalog.has_tools)
        self.assertTrue(catalog.has_resources)
        names = [tool.name for tool in catalog.tools]
        self.assertEqual(sorted(names), ["add_numbers", "echo", "fail", "secret_admin_tool"])
        echo = next(tool for tool in catalog.tools if tool.name == "echo")
        self.assertEqual(echo.description, "Repeat the text.")
        self.assertEqual(echo.input_schema["properties"]["text"]["type"], "string")
        guard.assert_called_once_with(self.mcpclient.endpoint_url)

    def test_catalog_round_trip(self):
        """Test that a catalog survives to_dict() and from_dict(), as it does in the cache."""
        with mock_mcp_server():
            catalog = self.connection().discover()
        self.assertEqual(MCPServerCatalog.from_dict(catalog.to_dict()), catalog)

    def test_server_without_instructions(self):
        """Test a server without instructions, whose only tool is ping."""
        server = MCPServer(name="bare")

        @server.tool()
        def ping() -> str:
            """Reply pong."""
            return "pong"

        with mock_mcp_server(server):
            catalog = self.connection().discover()
        self.assertIsNone(catalog.instructions)
        self.assertEqual([tool.name for tool in catalog.tools], ["ping"])
        self.assertEqual(ping(), "pong")

    # -------------------------------------------------------------------------
    # call_tool()
    # -------------------------------------------------------------------------
    def test_call_tool(self):
        """Test that call_tool() returns the tool's result as text."""
        with mock_mcp_server():
            connection = self.connection()
            echo = connection.call_tool("echo", {"text": "hello"})
            added = connection.call_tool("add_numbers", {"a": 2, "b": 3})
        self.assertEqual(echo.text, "hello")
        self.assertFalse(echo.is_error)
        self.assertEqual(added.text, "5")

    def test_call_tool_error(self):
        """Test that a tool's error is returned as an error result, not raised."""
        with mock_mcp_server():
            result = self.connection().call_tool("fail", {})
        self.assertTrue(result.is_error)
        self.assertIn("fail", result.text)

    def test_call_tool_not_allowed(self):
        """Test that a tool that allowedTools does not allow is refused, without connecting."""
        with mock_mcp_server() as guard:
            with self.assertRaises(SmarterMCPClientPermissionError):
                self.connection().call_tool("secret_admin_tool", {})
        guard.assert_not_called()

    def test_call_tool_all_allowed(self):
        """Test that every tool is allowed when allowedTools is empty."""
        with mock_mcp_server():
            result = self.connection(allowed_tools=[]).call_tool("secret_admin_tool", {})
        self.assertEqual(result.text, "should never be called")

    def test_call_tool_truncates(self):
        """Test that a long result is truncated."""
        with mock_mcp_server():
            result = self.connection().call_tool("echo", {"text": "x" * (MAX_RESULT_CHARACTERS + 100)})
        self.assertEqual(len(result.text), MAX_RESULT_CHARACTERS)
        self.assertTrue(result.text.endswith(TRUNCATION_MARKER))

    # -------------------------------------------------------------------------
    # read_resource()
    # -------------------------------------------------------------------------
    def test_read_resource(self):
        """Test that read_resource() returns the resource's text."""
        with mock_mcp_server():
            self.assertEqual(self.connection().read_resource(README_URI), README_TEXT)

    def test_read_resource_not_allowed(self):
        """Test that a resource that allowedResources does not allow is refused."""
        with mock_mcp_server():
            with self.assertRaises(SmarterMCPClientPermissionError):
                self.connection().read_resource("file:///etc/passwd")
            with self.assertRaises(SmarterMCPClientPermissionError):
                self.connection(allowed_resources=[]).read_resource(README_URI)

    # -------------------------------------------------------------------------
    # errors
    # -------------------------------------------------------------------------
    def test_non_public_host(self):
        """Test that a host without a public address is refused, before connecting."""
        with mock.patch(GUARD_PATCH, side_effect=SafeHttpError("host must have a public address: 10.0.0.1")):
            with self.assertRaises(SmarterMCPClientConnectionError) as cm:
                self.connection().discover()
        self.assertIn("public address", cm.exception.message)

    def test_no_endpoint_url(self):
        """Test that an MCPClient without an endpoint URL is a configuration error."""
        with self.assertRaises(SmarterMCPClientConfigurationError):
            self.connection(endpoint_url=None).discover()

    def test_stdio_is_not_supported(self):
        """Test that the stdio transport is refused, even if it is somehow stored."""
        with mock.patch(GUARD_PATCH):
            with self.assertRaises(SmarterMCPClientConfigurationError):
                self.connection(transport=MCPTransport.STDIO).discover()

    def test_server_error(self):
        """Test that a failure during the connection is reported as a connection error."""

        def broken_target(self, http_client):
            raise httpx2.ConnectError("connection refused")

        with mock.patch(GUARD_PATCH), mock.patch.object(MCPServerConnection, "server_target", broken_target):
            with self.assertRaises(SmarterMCPClientConnectionError) as cm:
                self.connection().discover()
        self.assertIn("connection refused", cm.exception.message)

    def test_timeout(self):
        """Test that a server that does not respond in time is reported as a connection error."""
        server = MCPServer(name="slow")

        @server.tool()
        async def slow() -> str:
            """Take too long."""
            await asyncio.sleep(5)
            return "late"

        with mock_mcp_server(server):
            started = time.monotonic()
            with self.assertRaises(SmarterMCPClientConnectionError) as cm:
                self.connection(timeout=1, allowed_tools=[]).call_tool("slow", {})
        self.assertLess(time.monotonic() - started, 4)
        self.assertIn("timed out", cm.exception.message)

    # -------------------------------------------------------------------------
    # authentication
    # -------------------------------------------------------------------------
    def test_headers_without_auth(self):
        """Test the request headers of an MCPClient without authentication."""
        headers = self.connection().request_headers()
        self.assertEqual(headers["X-Client-Id"], "smarter-tests")
        self.assertEqual(headers["User-Agent"], USER_AGENT)
        self.assertNotIn("Authorization", headers)

    def test_headers_bearer_token(self):
        """Test that bearer_token and oauth2 send the Secret as a bearer token."""
        for auth_type in (MCPAuthType.BEARER_TOKEN, MCPAuthType.OAUTH2):
            with self.subTest(auth_type=auth_type):
                headers = self.connection(auth_type=auth_type, credentials=self.token_secret).request_headers()
                self.assertEqual(headers["Authorization"], f"Bearer {TOKEN_VALUE}")

    def test_headers_api_key(self):
        """Test that api_key sends the Secret in the apiKeyHeader header."""
        connection = self.connection(
            auth_type=MCPAuthType.API_KEY, credentials=self.token_secret, api_key_header="CONTEXT7_API_KEY"
        )
        headers = connection.request_headers()
        self.assertEqual(headers["CONTEXT7_API_KEY"], TOKEN_VALUE)
        self.assertNotIn("Authorization", headers)

    def test_headers_missing_credentials(self):
        """Test that authentication without a Secret is a configuration error."""
        with self.assertRaises(SmarterMCPClientConfigurationError):
            self.connection(auth_type=MCPAuthType.BEARER_TOKEN, credentials=None).request_headers()

    # -------------------------------------------------------------------------
    # helpers
    # -------------------------------------------------------------------------
    def test_guarded_http_client(self):
        """Test that the http client checks every request with the public-URL guard, and does not follow redirects."""
        client = guarded_http_client(headers={"X-Test": "1"})
        self.assertIn(guard_request, client.event_hooks["request"])
        self.assertFalse(client.follow_redirects)
        with mock.patch(GUARD_PATCH, side_effect=SafeHttpError("blocked")) as guard:
            with self.assertRaises(SafeHttpError):
                run_sync(lambda: guard_request(httpx2.Request("GET", "https://169.254.169.254/latest/")))
        guard.assert_called_once_with("https://169.254.169.254/latest/")
        run_sync(client.aclose)

    def test_run_sync_in_event_loop(self):
        """Test that run_sync() also works from a thread that runs an event loop."""

        async def inner() -> int:
            return 42

        async def outer() -> int:
            return run_sync(inner)

        self.assertEqual(asyncio.run(outer()), 42)

    def test_matching(self):
        """Test the glob matching of allowedTools and allowedResources."""
        self.assertTrue(matches_any("search_code", ["get_*", "search_*"]))
        self.assertFalse(matches_any("delete_repo", ["get_*", "search_*"]))
        self.assertFalse(matches_any("Search_code", ["search_*"]))
        self.assertTrue(is_tool_allowed(MCPClient(allowed_tools=[]), "anything"))
        self.assertFalse(is_resource_allowed(MCPClient(allowed_resources=[]), README_URI))
        self.assertTrue(is_resource_allowed(MCPClient(allowed_resources=["docs://test/*"]), README_URI))

    def test_truncate(self):
        """Test truncate()."""
        self.assertEqual(truncate("short", 100), "short")
        self.assertEqual(len(truncate("x" * 200, 100)), 100)

    def test_content_to_text(self):
        """Test that text is returned, and binary content is described rather than included."""
        self.assertEqual(content_to_text(mcp_types.TextContent(type="text", text="hi")), "hi")
        image = mcp_types.ImageContent(type="image", data="aGk=", mime_type="image/png")
        self.assertEqual(content_to_text(image), "[image content (image/png) omitted]")
        link = mcp_types.ResourceLink(type="resource_link", name="readme", uri=README_URI)
        self.assertIn(README_URI, content_to_text(link))
        embedded = mcp_types.EmbeddedResource(
            type="resource", resource=mcp_types.TextResourceContents(uri=README_URI, text=README_TEXT)
        )
        self.assertEqual(content_to_text(embedded), README_TEXT)
