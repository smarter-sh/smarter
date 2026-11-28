"""
The execution of an MCP call, from its resolved :class:`MCPToolCall`, through the tool runner.

Every connection to an MCPClient's server goes through the tool runner (:mod:`smarter.apps.llmtool.runner`), so that it
can run in a worker without credentials (ADR-038): a tool call, a resource read, and the catalog's listing of the
server's tools. :func:`run_mcp_call` resolves the call in the app, into an :class:`MCPToolCall` that carries the
MCPClient's :class:`~smarter.apps.mcpclient.connection.MCPEndpoint`, credential included, and the runner executes it
with :func:`execute_mcp_call`, which reads nothing from the database. :func:`discover_catalog` and :func:`call_tool`
are its two common uses.

The executor checks ``allowed_tools`` and ``allowed_resources`` again, from the endpoint, so a worker doesn't trust its
caller to have checked them.
"""

import json
from typing import Final, Literal, Optional

from pydantic import Field, JsonValue

from smarter.apps.llmtool.runner import ToolCall, ToolCallResult, get_tool_runner

from .connection import (
    MCPEndpoint,
    MCPServerCatalog,
    MCPServerConnection,
    MCPToolResult,
)
from .exceptions import SmarterMCPClientConnectionError, SmarterMCPClientException

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

DISCOVER: Final = "discover"
"""The operation that lists the server's identity, instructions, capabilities and tools: the MCPClient's catalog."""

MCPOperation = Literal["tool", "read_resource", "discover"]
"""The operations of an :class:`MCPToolCall`."""


class MCPToolCall(ToolCall):
    """
    An MCP call, resolved for execution.

    :ivar endpoint: The MCPClient's resolved endpoint, credential included.
    :ivar operation: ``tool`` to call a tool, ``read_resource`` to read a resource, or ``discover`` to list the
        server's catalog.
    :ivar tool_name: The tool's name, as the server reports it, for ``tool``.
    :ivar uri: The resource's URI, for ``read_resource``.
    :ivar arguments: The tool's arguments, from the LLM.
    """

    kind: Literal["mcp"] = MCP_TOOL_CALL_KIND
    endpoint: MCPEndpoint
    operation: MCPOperation
    tool_name: str = ""
    uri: str = ""
    arguments: dict[str, JsonValue] = Field(default_factory=dict)


def execute_mcp_call(call: ToolCall) -> ToolCallResult:
    """
    Execute a resolved MCP call: connect, perform the handshake, call the tool, read the resource or list the catalog, and disconnect.

    :param call: The call, an :class:`MCPToolCall`.
    :returns: The tool's or the resource's text, with ``is_error`` when the tool reports an error; for ``discover``,
        the catalog, from :meth:`~smarter.apps.mcpclient.connection.MCPServerCatalog.to_dict`; or a result with a
        ``failure`` when the call couldn't be made: refused, unreachable, timed out, or not allowed.
    :raises TypeError: If the call isn't an :class:`MCPToolCall`.
    """
    if not isinstance(call, MCPToolCall):
        raise TypeError(f"execute_mcp_call() needs an MCPToolCall, not a {type(call).__name__}.")
    connection = MCPServerConnection(endpoint=call.endpoint)
    try:
        if call.operation == DISCOVER:
            catalog = connection.discover()
            return ToolCallResult(value=catalog.to_dict())
        if call.operation == READ_RESOURCE:
            text = connection.read_resource(call.uri)
            return ToolCallResult(value=text)
        tool_result = connection.call_tool(call.tool_name, call.arguments)
    except SmarterMCPClientException as e:
        return ToolCallResult(failure=e.message)
    result = ToolCallResult(value=tool_result.text, is_error=tool_result.is_error)
    return result


def result_text(value: JsonValue) -> str:
    """
    Return a tool runner's result as text for the LLM.

    :param value: The result's ``value``: an MCP tool's text, or None.
    :returns: The text, or JSON for any other value.
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    text = json.dumps(value)
    return text


def run_mcp_call(
    connection: MCPServerConnection,
    operation: MCPOperation,
    *,
    tool_name: str = "",
    uri: str = "",
    arguments: Optional[dict[str, JsonValue]] = None,
) -> ToolCallResult:
    """
    Resolve an MCP call in the app, and execute it through the tool runner.

    Resolving it reads the MCPClient's credential from its Smarter Secret, here, where the database is. The caller
    checks ``allowed_tools`` or ``allowed_resources`` first, if it wants the permission error rather than the
    executor's failure.

    :param connection: The MCPClient's connection, built from the MCPClient.
    :param operation: ``tool``, ``read_resource`` or ``discover``.
    :param tool_name: The tool's name, for ``tool``.
    :param uri: The resource's URI, for ``read_resource``.
    :param arguments: The tool's arguments, for ``tool``.
    :returns: The runner's result, which made the call.
    :raises SmarterMCPClientConnectionError: If the call couldn't be made: refused, unreachable, timed out, or not
        allowed. The message is the runner's.
    :raises SmarterMCPClientConfigurationError: If the MCPClient has no endpoint URL, or its credential is missing.
    """
    call = MCPToolCall(
        endpoint=connection.endpoint(),
        operation=operation,
        tool_name=tool_name,
        uri=uri,
        arguments=arguments or {},
    )
    result = get_tool_runner().run(call)
    if result.failure is not None:
        raise SmarterMCPClientConnectionError(result.failure)
    return result


def discover_catalog(connection: MCPServerConnection) -> MCPServerCatalog:
    """
    Return an MCPClient's catalog, listed through the tool runner: its server's identity, instructions, capabilities and tools.

    :param connection: The MCPClient's connection, built from the MCPClient.
    :returns: The catalog. All of the server's tools, whether or not ``allowed_tools`` allows them.
    :raises SmarterMCPClientConnectionError: If the server couldn't be reached, or answered with something that isn't
        a catalog.
    :raises SmarterMCPClientConfigurationError: If the MCPClient is misconfigured.
    """
    result = run_mcp_call(connection, DISCOVER)
    if not isinstance(result.value, dict):
        raise SmarterMCPClientConnectionError(f"MCPClient {connection.name}: the tool runner returned no catalog.")
    catalog = MCPServerCatalog.from_dict(result.value)
    return catalog


def call_tool(
    connection: MCPServerConnection, tool_name: str, arguments: Optional[dict[str, JsonValue]] = None
) -> MCPToolResult:
    """
    Call one of an MCPClient's tools through the tool runner.

    :param connection: The MCPClient's connection, built from the MCPClient.
    :param tool_name: The tool's name, as the server reports it.
    :param arguments: The tool's arguments.
    :returns: The result, as text, with ``is_error`` when the tool reports an error of its own.
    :raises SmarterMCPClientPermissionError: If ``allowed_tools`` doesn't allow the tool.
    :raises SmarterMCPClientConnectionError: If the call couldn't be made.
    """
    connection.require_allowed_tool(tool_name)
    result = run_mcp_call(connection, TOOL, tool_name=tool_name, arguments=arguments)
    tool_result = MCPToolResult(text=result_text(result.value), is_error=result.is_error)
    return tool_result


__all__ = [
    "DISCOVER",
    "MCP_TOOL_CALL_KIND",
    "READ_RESOURCE",
    "TOOL",
    "MCPOperation",
    "MCPToolCall",
    "call_tool",
    "discover_catalog",
    "execute_mcp_call",
    "result_text",
    "run_mcp_call",
]
