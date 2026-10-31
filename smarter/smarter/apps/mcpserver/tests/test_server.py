"""Tests for smarter.apps.mcpserver.protocol.server: the MCP protocol, without HTTP."""

from unittest import mock

import mcp_types
from mcp_types.version import HANDSHAKE_PROTOCOL_VERSIONS, LATEST_HANDSHAKE_VERSION
from pydantic import SecretStr

from smarter.apps.mcpserver.github.issues import GitHubIssue
from smarter.apps.mcpserver.protocol.server import (
    ISSUE_INSTRUCTIONS,
    SmarterProjectMCPServer,
)
from smarter.apps.mcpserver.signals import mcpserver_tool_called

from .base_classes import TOKEN, MCPServerTestBase

CREATE_ISSUE = "smarter.apps.mcpserver.github.issues.create_issue"

INITIALIZE_PARAMS = {
    "protocolVersion": "2025-06-18",
    "capabilities": {},
    "clientInfo": {"name": "test-client", "version": "1.0.0"},
}


def request(method: str, params=None, request_id=1) -> dict:
    """Return a JSON-RPC request."""
    message = {"jsonrpc": "2.0", "id": request_id, "method": method}
    if params is not None:
        message["params"] = params
    return message


class TestSmarterProjectMCPServer(MCPServerTestBase):
    """Test SmarterProjectMCPServer.handle()."""

    def setUp(self):
        super().setUp()
        self.server = SmarterProjectMCPServer(self.docs_repository)
        self.all_server = SmarterProjectMCPServer()

    def test_names(self):
        """The server of one repository is named after it."""
        self.assertEqual(self.server.name, f"smarter-project-{self.docs_repository.name}")
        self.assertEqual(self.all_server.name, "smarter-project")
        self.assertIn(self.server.name, repr(self.server))

    def test_initialize(self):
        """The handshake returns the client's protocol version, the tools capability, and instructions."""
        response = self.server.handle(request("initialize", INITIALIZE_PARAMS))
        result = mcp_types.InitializeResult.model_validate(response["result"])
        self.assertEqual(response["id"], 1)
        self.assertEqual(result.protocol_version, "2025-06-18")
        self.assertIsNotNone(result.capabilities.tools)
        self.assertIsNone(result.capabilities.resources)
        self.assertEqual(result.server_info.name, self.server.name)
        self.assertIn(self.docs_repository.full_name, result.instructions)
        self.assertIn("search_documentation", result.instructions)
        self.assertIn("get_manifest_schema", result.instructions)

    def test_initialize_negotiates_the_protocol_version(self):
        """Every handshake version is accepted, and an unknown one is answered with the latest."""
        for version in HANDSHAKE_PROTOCOL_VERSIONS:
            with self.subTest(version=version):
                params = {**INITIALIZE_PARAMS, "protocolVersion": version}
                self.assertEqual(
                    self.server.handle(request("initialize", params))["result"]["protocolVersion"], version
                )
        params = {**INITIALIZE_PARAMS, "protocolVersion": "1999-01-01"}
        self.assertEqual(
            self.server.handle(request("initialize", params))["result"]["protocolVersion"], LATEST_HANDSHAKE_VERSION
        )

    def test_instructions_of_all_repositories(self):
        """The server of all of the repositories lists them in its instructions."""
        instructions = self.all_server.instructions()
        for repository in self.repositories:
            self.assertIn(f"- {repository.name}: {repository.title}", instructions)
        self.assertIn(f"search_blog finds the posts of the blog, {self.blog.url}", instructions)
        self.assertIn("include its Markdown image in your answer", instructions)
        self.assertNotIn("search_blog", self.server.instructions())

    def test_ping(self):
        """Ping returns an empty result."""
        self.assertEqual(self.server.handle(request("ping")), {"jsonrpc": "2.0", "id": 1, "result": {}})

    def test_tools_list(self):
        """The read-only tools are listed, and the blog's only by the server of all of the repositories."""
        response = self.server.handle(request("tools/list", {}))
        result = mcp_types.ListToolsResult.model_validate(response["result"])
        self.assertEqual(
            [tool.name for tool in result.tools],
            [
                "get_repository_overview",
                "search_documentation",
                "search_code",
                "read_file",
                "list_files",
                "get_manifest_schema",
                "validate_manifest",
                "search_issues",
            ],
        )
        self.assertNotIn("repository", result.tools[3].input_schema["properties"])
        all_tools = mcp_types.ListToolsResult.model_validate(self.all_server.handle(request("tools/list"))["result"])
        self.assertIn("repository", all_tools.tools[3].input_schema["required"])
        self.assertEqual(
            [tool.name for tool in all_tools.tools[5:]],
            ["get_manifest_schema", "validate_manifest", "search_blog", "read_blog_post", "search_issues"],
        )

    def test_tools_call(self):
        """A tool call returns text, and sends a signal."""
        received = []

        def receiver(sender, **kwargs):
            received.append(kwargs)

        mcpserver_tool_called.connect(receiver)
        self.addCleanup(mcpserver_tool_called.disconnect, receiver)
        params = {"name": "search_code", "arguments": {"query": "verify_custom_domain"}}
        response = self.server.handle(request("tools/call", params))
        result = mcp_types.CallToolResult.model_validate(response["result"])
        self.assertFalse(result.is_error)
        self.assertIn("verification.py", result.content[0].text)
        self.assertEqual(received[0]["tool_name"], "search_code")
        self.assertFalse(received[0]["is_error"])

    def test_tool_error_is_a_result(self):
        """A tool's own error is a result with isError, so that the LLM can correct its call."""
        params = {"name": "read_file", "arguments": {"path": "no/such/file.py"}}
        response = self.server.handle(request("tools/call", params))
        self.assertTrue(response["result"]["isError"])
        self.assertIn("is not a file of", response["result"]["content"][0]["text"])

    def test_unknown_tool_and_method(self):
        """An unknown tool or method is a JSON-RPC error."""
        response = self.server.handle(request("tools/call", {"name": "write_file", "arguments": {}}))
        self.assertEqual(response["error"]["code"], mcp_types.METHOD_NOT_FOUND)
        response = self.server.handle(request("resources/list"))
        self.assertEqual(response["error"]["code"], mcp_types.METHOD_NOT_FOUND)

    def test_invalid_params(self):
        """Params that do not validate are a JSON-RPC error."""
        response = self.server.handle(request("initialize", {"protocolVersion": "2025-06-18"}))
        self.assertEqual(response["error"]["code"], mcp_types.INVALID_PARAMS)
        response = self.server.handle(request("tools/call", {"arguments": {}}))
        self.assertEqual(response["error"]["code"], mcp_types.INVALID_PARAMS)

    def test_internal_error(self):
        """An unexpected failure is a JSON-RPC internal error, without its details."""
        with mock.patch.object(SmarterProjectMCPServer, "call_tool", side_effect=RuntimeError("database is down")):
            response = self.server.handle(request("tools/call", {"name": "search_code", "arguments": {}}))
        self.assertEqual(response["error"]["code"], mcp_types.INTERNAL_ERROR)
        self.assertNotIn("database", response["error"]["message"])

    def test_notifications_and_client_responses(self):
        """Notifications, and responses from the client, are not answered."""
        self.assertIsNone(self.server.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}))
        self.assertIsNone(self.server.handle({"jsonrpc": "2.0", "method": "notifications/cancelled", "params": "bad"}))
        self.assertIsNone(self.server.handle({"jsonrpc": "2.0", "id": 7, "result": {}}))

    def test_invalid_messages(self):
        """A message that is not JSON-RPC 2.0, or not a valid request, is an invalid request."""
        for message in (1, "text", {"jsonrpc": "1.0", "id": 1, "method": "ping"}):
            with self.subTest(message=message):
                response = self.server.handle(message)
                self.assertEqual(response["error"]["code"], mcp_types.INVALID_REQUEST)
                self.assertIsNone(response["id"])
        response = self.server.handle({"jsonrpc": "2.0", "id": 5, "method": 42})
        self.assertEqual(response["error"]["code"], mcp_types.INVALID_REQUEST)
        self.assertEqual(response["id"], 5)
        response = self.server.handle({"jsonrpc": "2.0", "id": [1], "method": "ping"})
        self.assertIsNone(response["id"])

    def test_batch(self):
        """A batch is answered with the responses of its requests, in order, without its notifications."""
        batch = [
            request("ping", request_id=1),
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            request("tools/list", request_id=2),
        ]
        responses = self.server.handle(batch)
        self.assertEqual([response["id"] for response in responses], [1, 2])
        self.assertIsNone(self.server.handle([{"jsonrpc": "2.0", "method": "notifications/initialized"}]))
        for batch in ([], [request("ping")] * 21):
            with self.subTest(size=len(batch)):
                self.assertEqual(self.server.handle(batch)["error"]["code"], mcp_types.INVALID_REQUEST)

    def test_create_issue_with_a_github_token(self):
        """With the caller's GitHub token, create_issue is listed, explained and called, and the token is not sent in the signal."""
        server = SmarterProjectMCPServer(github_token=SecretStr(TOKEN))
        names = [tool["name"] for tool in server.handle(request("tools/list"))["result"]["tools"]]
        self.assertEqual(names[-2:], ["create_issue", "comment_on_issue"])
        self.assertNotIn(
            "create_issue", [tool["name"] for tool in self.all_server.handle(request("tools/list"))["result"]["tools"]]
        )
        self.assertTrue(server.instructions().endswith(ISSUE_INSTRUCTIONS))
        self.assertNotIn("create_issue", self.all_server.instructions())

        received = []

        def receiver(sender, **kwargs):
            received.append(kwargs)

        mcpserver_tool_called.connect(receiver)
        self.addCleanup(mcpserver_tool_called.disconnect, receiver)
        issue = GitHubIssue(number=7, title="t", html_url="https://github.com/smarter-sh/x/issues/7")
        params = {
            "name": "create_issue",
            "arguments": {"repository": self.docs_repository.name, "title": "t", "body": "b"},
        }
        with mock.patch(CREATE_ISSUE, return_value=issue):
            response = server.handle(request("tools/call", params))
        self.assertFalse(response["result"]["isError"])
        self.assertIn(issue.html_url, response["result"]["content"][0]["text"])
        self.assertEqual(received[0]["tool_name"], "create_issue")
        self.assertNotIn(TOKEN, str(received))

    def test_create_issue_without_a_github_token(self):
        """Without a token, create_issue is not a tool."""
        params = {"name": "create_issue", "arguments": {"title": "t", "body": "b"}}
        response = self.server.handle(request("tools/call", params))
        self.assertEqual(response["error"]["code"], mcp_types.METHOD_NOT_FOUND)
