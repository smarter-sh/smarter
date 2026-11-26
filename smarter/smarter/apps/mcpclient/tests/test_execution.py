"""
Test :mod:`smarter.apps.mcpclient.execution`, and the resolved :class:`~smarter.apps.mcpclient.connection.MCPEndpoint` that an MCP tool call carries.

.. note::

    **Experimental.** The MCPClient was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from unittest import mock

from smarter.apps.llmtool.runner import ToolCall, ToolCallResult, executor_for
from smarter.apps.mcpclient.connection import (
    MCPEndpoint,
    MCPServerConnection,
)
from smarter.apps.mcpclient.exceptions import (
    SmarterMCPClientConfigurationError,
    SmarterMCPClientConnectionError,
)
from smarter.apps.mcpclient.execution import (
    MCP_TOOL_CALL_KIND,
    READ_RESOURCE,
    TOOL,
    MCPToolCall,
    execute_mcp_call,
)
from smarter.apps.mcpclient.models import MCPAuthType

from .base_classes import (
    README_TEXT,
    README_URI,
    TOKEN_VALUE,
    MCPClientTestBase,
    mock_mcp_server,
)


class TestMCPExecution(MCPClientTestBase):
    """Test the resolution of an MCPClient's endpoint, and the execution of a resolved MCP tool call."""

    def endpoint(self, **fields) -> MCPEndpoint:
        """Return the test MCPClient's resolved endpoint, with some fields replaced."""
        resolved = MCPServerConnection(self.mcpclient).endpoint()
        endpoint = resolved.model_copy(update=fields)
        return endpoint

    def tool_call(self, tool_name: str, arguments=None, **endpoint_fields) -> MCPToolCall:
        """Return a resolved call of one of the test server's tools."""
        call = MCPToolCall(
            endpoint=self.endpoint(**endpoint_fields),
            operation=TOOL,
            tool_name=tool_name,
            arguments=arguments or {},
        )
        return call

    # =========================================================================
    # MCPEndpoint
    # =========================================================================
    def test_endpoint_is_resolved_from_the_mcpclient(self):
        """Test that the endpoint carries the MCPClient's connection, its headers and its permissions."""
        endpoint = MCPServerConnection(self.mcpclient).endpoint()
        self.assertEqual(endpoint.name, self.mcpclient.name)
        self.assertEqual(endpoint.endpoint_url, "https://mcp.example.com/mcp")
        self.assertEqual(endpoint.transport, "http")
        self.assertEqual(endpoint.timeout, 10)
        self.assertEqual(endpoint.headers["X-Client-Id"], "smarter-tests")
        self.assertIn("User-Agent", endpoint.headers)
        self.assertEqual(endpoint.allowed_tools, ["echo", "add_*", "fail"])
        self.assertEqual(endpoint.allowed_resources, ["docs://test/*"])

    def test_endpoint_carries_the_decrypted_credential_but_not_in_its_repr(self):
        """Test that the credential is resolved into the headers, and kept out of repr(), lest it be logged."""
        mcpclient = self.new_mcpclient(
            "test_mcpclient_bearer", auth_type=MCPAuthType.BEARER_TOKEN, credentials=self.token_secret
        )
        endpoint = MCPServerConnection(mcpclient).endpoint()
        self.assertEqual(endpoint.headers["Authorization"], f"Bearer {TOKEN_VALUE}")
        self.assertNotIn(TOKEN_VALUE, repr(endpoint))
        call = MCPToolCall(endpoint=endpoint, operation=TOOL, tool_name="echo")
        self.assertNotIn(TOKEN_VALUE, repr(call))

    def test_endpoint_is_resolved_once(self):
        """Test that the endpoint is resolved when it is first needed, and then kept."""
        connection = MCPServerConnection(self.mcpclient)
        with mock.patch.object(MCPServerConnection, "request_headers", return_value={}) as request_headers:
            first = connection.endpoint()
            second = connection.endpoint()
        self.assertIs(first, second)
        request_headers.assert_called_once()

    def test_endpoint_without_a_url(self):
        """Test that an MCPClient without an endpoint URL is a configuration error."""
        mcpclient = self.new_mcpclient("test_mcpclient_no_url", endpoint_url=None)
        with self.assertRaises(SmarterMCPClientConfigurationError):
            MCPServerConnection(mcpclient).endpoint()

    def test_connection_from_an_endpoint_has_no_mcpclient(self):
        """Test that a connection built from an endpoint works without the MCPClient, and refuses to read it."""
        endpoint = self.endpoint()
        connection = MCPServerConnection(endpoint=endpoint)
        self.assertIs(connection.endpoint(), endpoint)
        self.assertEqual(connection.name, self.mcpclient.name)
        self.assertEqual(connection.timeout, 10)
        with self.assertRaises(SmarterMCPClientConfigurationError):
            connection.require_mcpclient()
        with self.assertRaises(SmarterMCPClientConfigurationError):
            connection.credential()

    def test_connection_needs_an_mcpclient_or_an_endpoint(self):
        """Test that a connection needs one or the other."""
        with self.assertRaises(SmarterMCPClientConfigurationError):
            MCPServerConnection()

    # =========================================================================
    # MCPToolCall
    # =========================================================================
    def test_call_travels_as_json(self):
        """Test that a resolved call survives JSON, as it must to reach a worker."""
        call = self.tool_call("add_numbers", {"a": 40, "b": 2})
        self.assertEqual(call.kind, MCP_TOOL_CALL_KIND)
        self.assertEqual(MCPToolCall.model_validate_json(call.model_dump_json()), call)

    def test_mcp_kind_is_registered(self):
        """Test that the tool runner finds this executor for the mcp kind."""
        self.assertIs(executor_for(MCP_TOOL_CALL_KIND), execute_mcp_call)

    # =========================================================================
    # execute_mcp_call()
    # =========================================================================
    def test_execute_tool(self):
        """Test that a resolved call runs the tool on the server, without the MCPClient."""
        with mock_mcp_server():
            result = execute_mcp_call(self.tool_call("add_numbers", {"a": 40, "b": 2}))
        self.assertEqual(result, ToolCallResult(value="42"))

    def test_execute_tool_error(self):
        """Test that a tool's own error is a result with is_error, not a failure."""
        with mock_mcp_server():
            result = execute_mcp_call(self.tool_call("fail"))
        self.assertTrue(result.is_error)
        self.assertIsNone(result.failure)

    def test_execute_read_resource(self):
        """Test that a resolved call reads a resource."""
        call = MCPToolCall(endpoint=self.endpoint(), operation=READ_RESOURCE, uri=README_URI)
        with mock_mcp_server():
            result = execute_mcp_call(call)
        self.assertEqual(result.value, README_TEXT)

    def test_execute_checks_the_permissions_again(self):
        """Test that the executor refuses a tool or resource that the endpoint doesn't allow, before connecting."""
        refused_tool = self.tool_call("echo", {"text": "hi"}, allowed_tools=["add_*"])
        refused_resource = MCPToolCall(endpoint=self.endpoint(), operation=READ_RESOURCE, uri="file:///etc/passwd")
        with mock_mcp_server() as guard:
            for call in (refused_tool, refused_resource):
                result = execute_mcp_call(call)
                self.assertIsNotNone(result.failure)
                self.assertIn("does not allow", result.failure or "")
        guard.assert_not_called()

    def test_execute_connection_failure(self):
        """Test that a call that can't be made is a result with a failure, not an exception."""
        with mock.patch.object(
            MCPServerConnection, "call_tool", side_effect=SmarterMCPClientConnectionError("server is down")
        ):
            result = execute_mcp_call(self.tool_call("echo", {"text": "hi"}))
        self.assertEqual(result, ToolCallResult(failure="server is down"))

    def test_execute_needs_an_mcp_call(self):
        """Test that the executor refuses another kind of call."""
        with self.assertRaises(TypeError):
            execute_mcp_call(ToolCall(kind="other"))
