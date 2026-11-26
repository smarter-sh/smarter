"""
The execution of an MCP tool call, from its resolved :class:`MCPToolCall`.

:class:`~smarter.apps.mcpclient.toolkit.MCPToolkit` resolves each call in the app, into an
:class:`MCPToolCall`, and hands it to the tool runner (:mod:`smarter.apps.llmtool.runner`), which
executes it with :func:`execute_mcp_call`. The call carries the MCPClient's
:class:`~smarter.apps.mcpclient.connection.MCPEndpoint`, so nothing here reads the database, and the
same call can run in the app's process today, or in a worker without credentials (ADR-038).

The executor checks ``allowed_tools`` and ``allowed_resources`` again, from the endpoint, so a
worker doesn't trust its caller to have checked them.
"""

from typing import Final, Literal

from pydantic import Field, JsonValue

from smarter.apps.llmtool.runner import ToolCall, ToolCallResult

from .connection import MCPEndpoint, MCPServerConnection
from .exceptions import SmarterMCPClientException

MCP_TOOL_CALL_KIND: Final = "mcp"
"""The ``kind`` of an MCP tool call, which selects :func:`execute_mcp_call`."""

TOOL: Final = "tool"
"""The operation that calls one of the server's tools.

It matches ``MCPFunction.kind``.
"""

READ_RESOURCE: Final = "read_resource"
"""The operation that reads one of the server's resources.

It matches ``MCPFunction.kind``.
"""


class MCPToolCall(ToolCall):
    """
    An MCP tool call, resolved for execution.

    :ivar endpoint: The MCPClient's resolved endpoint, credential included.
    :ivar operation: ``tool`` to call a tool, or ``read_resource`` to read a resource.
    :ivar tool_name: The tool's name, as the server reports it, for ``tool``.
    :ivar uri: The resource's URI, for ``read_resource``.
    :ivar arguments: The tool's arguments, from the LLM.
    """

    kind: Literal["mcp"] = MCP_TOOL_CALL_KIND
    endpoint: MCPEndpoint
    operation: Literal["tool", "read_resource"]
    tool_name: str = ""
    uri: str = ""
    arguments: dict[str, JsonValue] = Field(default_factory=dict)


def execute_mcp_call(call: ToolCall) -> ToolCallResult:
    """
    Execute a resolved MCP tool call: connect, perform the handshake, call the tool or read the resource, and disconnect.

    :param call: The call, an :class:`MCPToolCall`.
    :returns: The tool's text, with ``is_error`` when the tool reports an error, or a result with
        a ``failure`` when the call couldn't be made: refused, unreachable, timed out, or not
        allowed.
    :raises TypeError: If the call isn't an :class:`MCPToolCall`.
    """
    if not isinstance(call, MCPToolCall):
        raise TypeError(f"execute_mcp_call() needs an MCPToolCall, not a {type(call).__name__}.")
    connection = MCPServerConnection(endpoint=call.endpoint)
    try:
        if call.operation == READ_RESOURCE:
            text = connection.read_resource(call.uri)
            return ToolCallResult(value=text)
        tool_result = connection.call_tool(call.tool_name, call.arguments)
    except SmarterMCPClientException as e:
        return ToolCallResult(failure=e.message)
    result = ToolCallResult(value=tool_result.text, is_error=tool_result.is_error)
    return result


__all__ = ["MCP_TOOL_CALL_KIND", "READ_RESOURCE", "TOOL", "MCPToolCall", "execute_mcp_call"]
