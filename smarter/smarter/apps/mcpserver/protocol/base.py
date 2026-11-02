"""
The Model Context Protocol, over Streamable HTTP, in Django: what every MCP server of the app shares.

:class:`MCPServerBase` answers the JSON-RPC messages of one POST request, and :class:`MCPToolBase`
is the base class of a tool. A server names itself, describes itself, gives its instructions, and
holds its tools. Everything else, the ``initialize`` handshake, ``ping``, ``tools/list`` and
``tools/call``, JSON-RPC batches and errors, is here. The app's servers:

- :class:`~smarter.apps.mcpserver.protocol.server.SmarterProjectMCPServer`: the public server of The
  Smarter Project's repositories, documentation and blog.
- :class:`~smarter.apps.mcpserver.protocol.operations.SmarterOperationsMCPServer`: the staff-only
  server of this platform's operations: its logs, its health and its users.

The server speaks the ``initialize`` handshake of every protocol version that the MCP Python SDK
negotiates (:data:`mcp_types.version.HANDSHAKE_PROTOCOL_VERSIONS`):

- ``initialize``: the server's identity, its tools capability and its instructions.
- ``notifications/initialized`` and every other notification: accepted, and ignored.
- ``ping``: an empty result.
- ``tools/list``: the server's tools.
- ``tools/call``: runs a tool. A tool's own errors, e.g. a file that does not exist, are
  returned as a result with ``isError`` set, so that the LLM can correct its call.

**Why not the MCP SDK's server.** The SDK's server runs as an ASGI application, with an
anyio task group for its lifetime, and calls its tools as coroutines. Smarter's views and
ORM are synchronous, and the platform runs under both the Django development server and
uvicorn. Every message is answered from the platform's own data, with no state between
requests, so a server is a plain Django view that uses the SDK's own Pydantic models,
:mod:`mcp_types`, to validate the requests and to build the responses.

**Stateless.** A server answers every POST with ``application/json``, and does not issue an
``Mcp-Session-Id``. Clients therefore open no GET stream, and send no DELETE, and any of the
platform's pods can answer any request.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

import copy
from abc import ABC, abstractmethod
from typing import ClassVar, Optional, Union

import mcp_types
from mcp_types.version import HANDSHAKE_PROTOCOL_VERSIONS, LATEST_HANDSHAKE_VERSION
from pydantic import BaseModel, JsonValue, ValidationError

from smarter.apps.mcpserver.exceptions import SmarterMCPServerToolError
from smarter.apps.mcpserver.signals import mcpserver_called, mcpserver_tool_called
from smarter.common.const import VERSION
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.typing import SmarterDictType

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.MCPSERVER_LOGGING])

SERVER_VERSION = str(VERSION.get("__version__", "0.0.0"))
"""Every server's version: the platform's."""

MAX_BATCH_SIZE = 20
"""The maximum number of messages in a JSON-RPC batch, which protocol 2025-03-26 allows."""

JsonRpcResponse = Union[mcp_types.JSONRPCResponse, mcp_types.JSONRPCError]


def simplify_schema(schema: SmarterDictType) -> SmarterDictType:
    """
    Simplify a Pydantic JSON schema for an LLM.

    Titles, the model's docstring and null defaults are removed, and an optional field's
    ``anyOf: [<type>, null]`` becomes its type.

    :param schema: The schema, from ``model_json_schema()``.
    :returns: The simplified schema.
    """
    schema = copy.deepcopy(schema)
    schema.pop("title", None)
    schema.pop("description", None)
    for name, prop in list(schema.get("properties", {}).items()):
        prop.pop("title", None)
        if "default" in prop and prop["default"] is None:
            prop.pop("default")
        variants = prop.get("anyOf")
        if variants and len(variants) == 2 and {"type": "null"} in variants:
            prop.pop("anyOf")
            prop.update(next(variant for variant in variants if variant != {"type": "null"}))
        schema["properties"][name] = prop
    return schema


def invalid_arguments(tool_name: str, error: ValidationError) -> SmarterMCPServerToolError:
    """
    Return the tool error for arguments that are not valid, naming each problem, for the LLM to correct.

    :param tool_name: The tool.
    :param error: Pydantic's validation error.
    """
    problems = "; ".join(
        f"{'.'.join(str(part) for part in problem['loc']) or 'arguments'}: {problem['msg']}"
        for problem in error.errors()
    )
    return SmarterMCPServerToolError(f"invalid arguments for {tool_name}: {problems}")


class MCPToolBase(ABC):
    """
    A tool of an MCP server: a name, a description, and a Pydantic model of its arguments.

    The tool's MCP ``inputSchema`` is generated from :attr:`arguments_model`, and :meth:`call`
    returns its result as Markdown text for the LLM.
    """

    name: ClassVar[str]
    title: ClassVar[str]
    description: ClassVar[str]
    arguments_model: ClassVar[type[BaseModel]]
    read_only: ClassVar[bool] = True
    """Whether the tool only reads.

    A tool that writes is annotated so.
    """
    open_world: ClassVar[bool] = False
    """Whether the tool reaches beyond the platform's own data, e.g. to GitHub."""

    def input_schema(self) -> SmarterDictType:
        """
        Return the tool's MCP ``inputSchema``.

        :returns: A JSON schema of type object, without additional properties.
        """
        schema = simplify_schema(self.arguments_model.model_json_schema())
        schema.setdefault("properties", {})
        schema["type"] = "object"
        schema["additionalProperties"] = False
        return schema

    def definition(self) -> mcp_types.Tool:
        """Return the tool, as tools/list lists it."""
        return mcp_types.Tool(
            name=self.name,
            title=self.title,
            description=self.description,
            input_schema=self.input_schema(),
            annotations=mcp_types.ToolAnnotations(
                title=self.title,
                read_only_hint=self.read_only,
                destructive_hint=False,
                idempotent_hint=self.read_only,
                open_world_hint=self.open_world,
            ),
        )

    @abstractmethod
    def call(self, arguments: Optional[SmarterDictType]) -> str:
        """
        Validate a tool call's arguments, and run the tool.

        :param arguments: The tool call's arguments.
        :returns: The result, as Markdown.
        :raises SmarterMCPServerToolError: If the arguments are not valid, or the tool fails.
        """


class MCPServerBase(ABC):
    """
    An MCP server: answers the JSON-RPC messages of one POST request with its :attr:`tools`.

    A subclass sets :attr:`tools` in its constructor, and implements :attr:`name`,
    :meth:`server_info` and :meth:`instructions`.
    """

    tools: dict[str, MCPToolBase]

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name}>"

    @property
    def formatted_class_name(self) -> str:
        """The class name, for logging."""
        return f"{logging.SmarterFormattedText.text(__name__)}.{self.__class__.__name__}[{self.name}]"

    @property
    @abstractmethod
    def name(self) -> str:
        """The server's name, e.g. ``smarter-project``."""

    @abstractmethod
    def server_info(self) -> mcp_types.Implementation:
        """Return the server's identity, for the initialize result."""

    @abstractmethod
    def instructions(self) -> str:
        """Return the server's instructions, which MCP clients add to the LLM's system prompt."""

    # -------------------------------------------------------------------------
    # JSON-RPC
    # -------------------------------------------------------------------------
    def handle(self, payload: JsonValue) -> Optional[JsonValue]:
        """
        Answer the JSON-RPC message, or batch of messages, of one POST request.

        :param payload: The request body, parsed.
        :returns: The response body, or None if no message needs a response, e.g. a notification.
        """
        if isinstance(payload, list):
            if not payload or len(payload) > MAX_BATCH_SIZE:
                return self.dump(
                    self.error(
                        None, mcp_types.INVALID_REQUEST, f"a batch must have from 1 to {MAX_BATCH_SIZE} messages."
                    )
                )
            responses = [self.handle_message(message) for message in payload]
            answered = [response for response in responses if response is not None]
            return [self.dump(response) for response in answered] if answered else None
        response = self.handle_message(payload)
        return self.dump(response) if response is not None else None

    def handle_message(self, message: JsonValue) -> Optional[JsonRpcResponse]:
        """
        Answer one JSON-RPC message.

        :param message: The message.
        :returns: The response, or None for a notification, or for a response from the client.
        """
        if not isinstance(message, dict) or message.get("jsonrpc") != mcp_types.JSONRPC_VERSION:
            return self.error(None, mcp_types.INVALID_REQUEST, "not a JSON-RPC 2.0 message.")
        if "method" not in message:
            # a response, or an error, from the client: this server sends no requests to answer.
            return None
        if "id" not in message:
            try:
                notification = mcp_types.JSONRPCNotification.model_validate(message)
            except ValidationError:
                return None
            mcpserver_called.send(sender=self.__class__, server=self.name, method=notification.method)
            return None
        try:
            request = mcp_types.JSONRPCRequest.model_validate(message)
        except ValidationError:
            request_id = message.get("id")
            return self.error(
                request_id if isinstance(request_id, (int, str)) else None,
                mcp_types.INVALID_REQUEST,
                "not a valid JSON-RPC request.",
            )
        mcpserver_called.send(sender=self.__class__, server=self.name, method=request.method)
        try:
            result = self.dispatch(request.method, request.params or {})
        except ValidationError as e:
            return self.error(
                request.id, mcp_types.INVALID_PARAMS, f"invalid params for {request.method}: {e.error_count()} errors."
            )
        except LookupError as e:
            return self.error(request.id, mcp_types.METHOD_NOT_FOUND, str(e))
        # pylint: disable=broad-exception-caught
        except Exception as e:
            logger.error("%s %s failed: %s", self.formatted_class_name, request.method, e, exc_info=True)
            return self.error(request.id, mcp_types.INTERNAL_ERROR, f"{request.method} failed.")
        return mcp_types.JSONRPCResponse(
            jsonrpc=mcp_types.JSONRPC_VERSION,
            id=request.id,
            result=result.model_dump(mode="json", by_alias=True, exclude_none=True),
        )

    def dispatch(self, method: str, params: SmarterDictType) -> mcp_types.Result:
        """
        Run one JSON-RPC method.

        :param method: The method.
        :param params: Its params.
        :returns: Its result.
        :raises LookupError: If the server does not implement the method, or the tool does not exist.
        :raises ValidationError: If the params are not valid.
        """
        if method == "initialize":
            return self.initialize(mcp_types.InitializeRequestParams.model_validate(params))
        if method == "ping":
            return mcp_types.EmptyResult()
        if method == "tools/list":
            return mcp_types.ListToolsResult(tools=[tool.definition() for tool in self.tools.values()])
        if method == "tools/call":
            return self.call_tool(mcp_types.CallToolRequestParams.model_validate(params))
        raise LookupError(f"method not found: {method}")

    def initialize(self, params: mcp_types.InitializeRequestParams) -> mcp_types.InitializeResult:
        """
        Answer the initialize handshake.

        :param params: The client's offer.
        :returns: The client's protocol version, if this server speaks it, and otherwise the
            latest that it speaks, which the client may refuse.
        """
        requested = params.protocol_version
        version = requested if requested in HANDSHAKE_PROTOCOL_VERSIONS else LATEST_HANDSHAKE_VERSION
        return mcp_types.InitializeResult(
            protocol_version=version,
            capabilities=mcp_types.ServerCapabilities(tools=mcp_types.ToolsCapability(list_changed=False)),
            server_info=self.server_info(),
            instructions=self.instructions(),
        )

    def call_tool(self, params: mcp_types.CallToolRequestParams) -> mcp_types.CallToolResult:
        """
        Run a tool.

        :param params: The tool's name and arguments.
        :returns: The tool's result, as text. A tool error is a result with ``is_error`` set.
        :raises LookupError: If there is no such tool.
        """
        tool = self.tools.get(params.name)
        if tool is None:
            raise LookupError(f"tool not found: {params.name}")
        try:
            text = tool.call(params.arguments)
            is_error = False
        except SmarterMCPServerToolError as e:
            text = e.message
            is_error = True
        mcpserver_tool_called.send(
            sender=self.__class__,
            server=self.name,
            tool_name=tool.name,
            arguments=params.arguments or {},
            is_error=is_error,
            characters=len(text),
        )
        return mcp_types.CallToolResult(content=[mcp_types.TextContent(text=text)], is_error=is_error)

    @staticmethod
    def error(request_id: Optional[Union[int, str]], code: int, message: str) -> mcp_types.JSONRPCError:
        """Return a JSON-RPC error response."""
        return mcp_types.JSONRPCError(
            jsonrpc=mcp_types.JSONRPC_VERSION, id=request_id, error=mcp_types.ErrorData(code=code, message=message)
        )

    @staticmethod
    def dump(response: JsonRpcResponse) -> JsonValue:
        """Return a response as JSON.

        An error keeps its ``id``, which JSON-RPC requires, even when it is null.
        """
        if isinstance(response, mcp_types.JSONRPCError):
            return response.model_dump(mode="json", by_alias=True)
        return response.model_dump(mode="json", by_alias=True, exclude_none=True)


__all__ = [
    "MAX_BATCH_SIZE",
    "SERVER_VERSION",
    "JsonRpcResponse",
    "MCPServerBase",
    "MCPToolBase",
    "invalid_arguments",
    "simplify_schema",
]
