"""
Test :mod:`smarter.apps.mcpclient.toolkit`.

.. note::

    **Experimental.** The MCPClient was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from unittest import mock

from smarter.apps.llmtool.plugin.tests.base_classes import capture_signal
from smarter.apps.mcpclient.connection import (
    MCPServerConnection,
    MCPToolInfo,
    MCPToolResult,
)
from smarter.apps.mcpclient.exceptions import SmarterMCPClientConnectionError
from smarter.apps.mcpclient.signals import (
    mcpclient_resource_read,
    mcpclient_tool_called,
    mcpclient_tool_failed,
    mcpclient_tool_responded,
)
from smarter.apps.mcpclient.toolkit import (
    MAX_DESCRIPTION_LENGTH,
    MAX_FUNCTION_NAME_LENGTH,
    MCPToolkit,
    input_schema,
)

from .base_classes import (
    README_TEXT,
    README_URI,
    TEST_SERVER_INSTRUCTIONS,
    MCPClientTestBase,
    mock_mcp_server,
)


class TestMCPToolkit(MCPClientTestBase):
    """Test MCPToolkit."""

    def load(self, *mcpclients) -> MCPToolkit:
        """Return a toolkit loaded from the test server."""
        with mock_mcp_server():
            return MCPToolkit(list(mcpclients) or [self.mcpclient]).load()

    def function_name(self, toolkit: MCPToolkit, tool_name: str) -> str:
        """Return the function name of one of the test MCPClient's tools."""
        return next(
            name
            for name, function in toolkit.functions.items()
            if function.mcpclient.pk == self.mcpclient.pk and function.tool_name == tool_name
        )

    def test_tools(self):
        """Test that the allowed tools become OpenAI function tools."""
        toolkit = self.load()
        tool_names = sorted(function.tool_name for function in toolkit.functions.values() if function.tool_name)
        self.assertEqual(tool_names, ["add_numbers", "echo", "fail"])
        echo = next(tool for tool in toolkit.tools if tool["function"]["name"] == f"mcp{self.mcpclient.id}_echo")
        self.assertEqual(echo["type"], "function")
        self.assertIn("Repeat the text.", echo["function"]["description"])
        self.assertIn(self.mcpclient.name, echo["function"]["description"])
        self.assertEqual(echo["function"]["parameters"]["type"], "object")
        self.assertIn("text", echo["function"]["parameters"]["properties"])
        self.assertEqual(toolkit.connected, [self.mcpclient])
        self.assertEqual(toolkit.errors, {})

    def test_read_resource_tool(self):
        """Test that a read_resource tool is added when the MCPClient allows resources."""
        toolkit = self.load()
        name = f"mcp{self.mcpclient.id}_read_resource"
        self.assertTrue(toolkit.is_mcp_function(name))
        tool = next(tool for tool in toolkit.tools if tool["function"]["name"] == name)
        self.assertIn("docs://test/*", tool["function"]["description"])
        self.assertEqual(tool["function"]["parameters"]["required"], ["uri"])

    def test_no_read_resource_tool(self):
        """Test that no read_resource tool is added when the MCPClient allows no resources."""
        mcpclient = self.new_mcpclient("test_mcpclient_no_resources", allowed_resources=[])
        toolkit = self.load(mcpclient)
        self.assertFalse(any(function.kind == "read_resource" for function in toolkit.functions.values()))

    def test_instructions(self):
        """Test that the servers' instructions are returned for the system prompt."""
        toolkit = self.load()
        system_prompt = toolkit.system_prompt()
        self.assertIn(TEST_SERVER_INSTRUCTIONS, system_prompt)
        self.assertIn(self.mcpclient.name, system_prompt)

    def test_no_instructions(self):
        """Test that includeInstructions false omits the server's instructions."""
        mcpclient = self.new_mcpclient("test_mcpclient_no_instructions", include_instructions=False)
        self.assertIsNone(self.load(mcpclient).system_prompt())

    def test_call(self):
        """Test that a tool call runs on the MCP server, and sends signals."""
        toolkit = self.load()
        with (
            mock_mcp_server(),
            capture_signal(mcpclient_tool_called) as called,
            capture_signal(mcpclient_tool_responded) as responded,
        ):
            result = toolkit.call(self.function_name(toolkit, "add_numbers"), {"a": 40, "b": 2})
        self.assertEqual(result, "42")
        self.assertEqual(called[0]["tool_name"], "add_numbers")
        self.assertEqual(called[0]["arguments"], {"a": 40, "b": 2})
        self.assertFalse(responded[0]["is_error"])
        self.assertEqual(responded[0]["characters"], 2)

    def test_call_tool_error(self):
        """Test that a tool's error is returned to the LLM as text."""
        toolkit = self.load()
        with mock_mcp_server():
            result = toolkit.call(self.function_name(toolkit, "fail"), {})
        self.assertTrue(result.startswith("Error:"))

    def test_call_read_resource(self):
        """Test that the read_resource tool reads an allowed resource, and refuses others."""
        toolkit = self.load()
        name = f"mcp{self.mcpclient.id}_read_resource"
        with mock_mcp_server(), capture_signal(mcpclient_resource_read) as read:
            self.assertEqual(toolkit.call(name, {"uri": README_URI}), README_TEXT)
            refused = toolkit.call(name, {"uri": "file:///etc/passwd"})
        self.assertEqual(read[0]["uri"], README_URI)
        self.assertTrue(refused.startswith("Error:"))
        self.assertIn("does not allow", refused)

    def test_call_unreachable(self):
        """Test that an unreachable server is reported to the LLM as text, and sends mcpclient_tool_failed."""
        toolkit = self.load()
        with (
            mock.patch.object(
                MCPServerConnection, "call_tool", side_effect=SmarterMCPClientConnectionError("server is down")
            ),
            capture_signal(mcpclient_tool_failed) as failed,
        ):
            result = toolkit.call(self.function_name(toolkit, "echo"), {"text": "hi"})
        self.assertIn("server is down", result)
        self.assertEqual(failed[0]["tool_name"], "echo")

    def test_read_only(self):
        """Test that a tool is read-only when the server marks it readOnlyHint, and the read_resource tool always is."""
        toolkit = self.load()
        self.assertTrue(toolkit.functions[self.function_name(toolkit, "echo")].read_only)
        self.assertFalse(toolkit.functions[self.function_name(toolkit, "add_numbers")].read_only)
        self.assertTrue(toolkit.functions[f"mcp{self.mcpclient.id}_read_resource"].read_only)

    def test_read_only_tool_is_cached(self):
        """Test that a read-only tool's result is cached, by its arguments, and reported as cached."""
        toolkit = self.load()
        name = self.function_name(toolkit, "echo")
        with (
            mock_mcp_server(),
            mock.patch.object(
                MCPServerConnection, "call_tool", autospec=True, side_effect=MCPServerConnection.call_tool
            ) as call_tool,
            capture_signal(mcpclient_tool_called) as called,
            capture_signal(mcpclient_tool_responded) as responded,
        ):
            first = toolkit.call(name, {"text": "cached once"})
            second = toolkit.call(name, {"text": "cached once"})
            other = toolkit.call(name, {"text": "other arguments"})
        self.assertEqual((first, second, other), ("cached once", "cached once", "other arguments"))
        self.assertEqual(call_tool.call_count, 2)
        self.assertEqual(len(called), 3)
        self.assertEqual([signal["cached"] for signal in responded], [False, True, False])

    def test_tool_that_is_not_read_only_is_not_cached(self):
        """Test that a tool that may change something is called every time."""
        toolkit = self.load()
        name = self.function_name(toolkit, "add_numbers")
        with (
            mock_mcp_server(),
            mock.patch.object(
                MCPServerConnection, "call_tool", autospec=True, side_effect=MCPServerConnection.call_tool
            ) as call_tool,
        ):
            self.assertEqual(toolkit.call(name, {"a": 1, "b": 2}), "3")
            self.assertEqual(toolkit.call(name, {"a": 1, "b": 2}), "3")
        self.assertEqual(call_tool.call_count, 2)

    def test_read_only_tool_error_is_not_cached(self):
        """Test that an error reported by a read-only tool is returned to the LLM, and not cached."""
        toolkit = self.load()
        name = self.function_name(toolkit, "echo")
        with (
            mock.patch.object(
                MCPServerConnection, "call_tool", return_value=MCPToolResult(text="no such text", is_error=True)
            ) as call_tool,
            capture_signal(mcpclient_tool_responded) as responded,
        ):
            first = toolkit.call(name, {"text": "an error"})
            second = toolkit.call(name, {"text": "an error"})
        self.assertEqual(first, "Error: no such text")
        self.assertEqual(second, first)
        self.assertEqual(call_tool.call_count, 2)
        self.assertTrue(all(signal["is_error"] and not signal["cached"] for signal in responded))

    def test_cache_ttl_zero_disables_the_cache(self):
        """Test that an MCPClient with cacheTtl 0 calls even its read-only tools every time."""
        mcpclient = self.new_mcpclient("test_mcpclient_no_cache", cache_ttl=0)
        toolkit = self.load(mcpclient)
        name = next(name for name, function in toolkit.functions.items() if function.tool_name == "echo")
        with (
            mock_mcp_server(),
            mock.patch.object(
                MCPServerConnection, "call_tool", autospec=True, side_effect=MCPServerConnection.call_tool
            ) as call_tool,
        ):
            toolkit.call(name, {"text": "uncached"})
            toolkit.call(name, {"text": "uncached"})
        self.assertEqual(call_tool.call_count, 2)

    def test_read_resource_is_cached(self):
        """Test that a resource read is cached, and reported as cached."""
        toolkit = self.load()
        name = f"mcp{self.mcpclient.id}_read_resource"
        with (
            mock_mcp_server(),
            mock.patch.object(
                MCPServerConnection, "read_resource", autospec=True, side_effect=MCPServerConnection.read_resource
            ) as read_resource,
            capture_signal(mcpclient_resource_read) as read,
        ):
            self.assertEqual(toolkit.call(name, {"uri": README_URI, "x": 1}), README_TEXT)
            self.assertEqual(toolkit.call(name, {"x": 1, "uri": README_URI}), README_TEXT)
        self.assertEqual(read_resource.call_count, 1)
        self.assertEqual([signal["cached"] for signal in read], [False, True])

    def test_call_unknown_function(self):
        """Test that an unknown function name is reported to the LLM as text."""
        self.assertTrue(self.load().call("mcp0_nothing", {}).startswith("Error:"))

    def test_unreachable_server_is_skipped(self):
        """Test that an MCPClient whose server cannot be reached is skipped, and reported."""
        down = self.new_mcpclient("test_mcpclient_down", endpoint_url="https://down.example.com/mcp")

        real_discover = MCPServerConnection.discover

        def discover(connection):
            if connection.mcpclient.pk == down.pk:
                raise SmarterMCPClientConnectionError("server is down")
            return real_discover(connection)

        with mock_mcp_server(), mock.patch.object(MCPServerConnection, "discover", discover):
            toolkit = MCPToolkit([down, self.mcpclient]).load()
        self.assertEqual(toolkit.connected, [self.mcpclient])
        self.assertIn("server is down", toolkit.errors[down.name])
        self.assertTrue(toolkit.tools)
        self.assertFalse(any(function.mcpclient.pk == down.pk for function in toolkit.functions.values()))

    def test_function_names(self):
        """Test that function names are sanitized, limited to 64 characters, and unique."""
        toolkit = MCPToolkit([self.mcpclient])
        name = toolkit.function_name(self.mcpclient, "resolve-library-id")
        self.assertEqual(name, f"mcp{self.mcpclient.id}_resolve-library-id")
        self.assertEqual(toolkit.function_name(self.mcpclient, "a.b/c d"), f"mcp{self.mcpclient.id}_a_b_c_d")
        long_name = toolkit.function_name(self.mcpclient, "x" * 100)
        self.assertEqual(len(long_name), MAX_FUNCTION_NAME_LENGTH)
        # two tools whose sanitized names collide get distinct function names
        toolkit.functions[toolkit.function_name(self.mcpclient, "a.b")] = mock.MagicMock()
        self.assertNotEqual(toolkit.function_name(self.mcpclient, "a_b"), f"mcp{self.mcpclient.id}_a_b")

    def test_long_description(self):
        """Test that a long tool description is truncated."""
        toolkit = MCPToolkit([self.mcpclient])
        tool = MCPToolInfo(name="long", description="x" * 5000)
        with mock.patch("smarter.apps.mcpclient.toolkit.get_cached_catalog") as catalog:
            catalog.return_value.tools = [tool]
            catalog.return_value.has_resources = False
            catalog.return_value.instructions = None
            toolkit.mcpclients = [self.new_mcpclient("test_mcpclient_long", allowed_tools=[])]
            toolkit.load()
        self.assertEqual(len(toolkit.tools[0]["function"]["description"]), MAX_DESCRIPTION_LENGTH)

    def test_input_schema(self):
        """Test that a tool's input schema becomes an object schema, without $schema."""
        schema = input_schema(MCPToolInfo(name="t", input_schema={"$schema": "x", "properties": {"a": {}}}))
        self.assertEqual(schema, {"type": "object", "properties": {"a": {}}})
        self.assertEqual(input_schema(MCPToolInfo(name="t")), {"type": "object", "properties": {}})
