"""
The Model Context Protocol, over Streamable HTTP, in Django: what every MCP server of the app shares.

:class:`MCPServerBase` answers the JSON-RPC messages of one POST request, and :class:`MCPToolBase`
is the base class of a tool. A server names itself, describes itself, gives its instructions, and
holds its tools. Everything else, the ``initialize`` handshake, ``ping``, ``tools/list`` and
``tools/call``, JSON-RPC batches and errors, is here. The app's servers:

- :class:`~smarter.apps.mcpserver.protocol.server.SmarterProjectMCPServer`: the public server of The
  Smarter Project's repositories, documentation and blog.
- :class:`~smarter.apps.mcpserver.protocol.operations_server.SmarterOperationsMCPServer`: the
  staff-only server of this platform's operations: its logs, its health and its users.

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

**Signals.** Every notification and request that a server accepts sends
:data:`~smarter.apps.mcpserver.signals.mcpserver_called`, and every tool call sends
:data:`~smarter.apps.mcpserver.signals.mcpserver_tool_called`. The app's receivers log them.

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
"""
Every server's version: the platform's, e.g. ``0.41.0``.

It is the ``version`` of the server's identity in the ``initialize`` result, so that a client can
tell which release of the platform answered it.
"""

MAX_BATCH_SIZE = 20
"""
The maximum number of messages in a JSON-RPC batch, which protocol 2025-03-26 allows.

A larger batch, or an empty one, is refused with one ``INVALID_REQUEST`` error, so that one POST
cannot make a server run an unbounded number of tool calls.
"""

JsonRpcResponse = Union[mcp_types.JSONRPCResponse, mcp_types.JSONRPCError]
"""The answer to one JSON-RPC request: a response with a result, or an error."""

NULL_TYPE = {"type": "null"}
"""The JSON schema of ``None``, which Pydantic adds to an optional field's ``anyOf``."""


def simplify_schema(schema: SmarterDictType) -> SmarterDictType:
    """
    Simplify a Pydantic JSON schema for an LLM.

    Pydantic's schema carries what helps a form, not an LLM: a title for the model and for each
    field, the model's docstring as its description, and ``"default": null`` for each optional
    field. They cost tokens in every ``tools/list`` result, and the docstring is written for
    developers, so they are removed. An optional field's ``anyOf: [<type>, {"type": "null"}]``
    becomes its type, which every MCP client understands.

    :param schema: The schema, from ``model_json_schema()``. It is not changed: the function works
        on a deep copy.
    :returns: The simplified schema.
    """
    schema = copy.deepcopy(schema)
    schema.pop("title", None)
    schema.pop("description", None)
    properties = schema.get("properties", {})
    for prop in properties.values():
        prop.pop("title", None)
        if "default" in prop and prop["default"] is None:
            prop.pop("default")
        variants = prop.get("anyOf")
        if not variants:
            continue
        if len(variants) != 2:
            continue
        if NULL_TYPE not in variants:
            continue
        prop.pop("anyOf")
        for variant in variants:
            if variant != NULL_TYPE:
                prop.update(variant)
                break
    return schema


def invalid_arguments(tool_name: str, error: ValidationError) -> SmarterMCPServerToolError:
    """
    Return the tool error for arguments that are not valid, naming each problem, for the LLM to correct.

    The error is returned to the LLM as a tool result with ``isError`` set, rather than as a
    JSON-RPC error, so that it can read what was wrong and call the tool again. Each problem is
    the argument's dotted path, or ``arguments`` for the arguments as a whole, then Pydantic's
    message, e.g. ``invalid arguments for search_logs: limit: Input should be less than or equal
    to 200``.

    :param tool_name: The tool's name, e.g. ``search_logs``.
    :param error: Pydantic's validation error of the arguments.
    :returns: The error, for the caller to raise.
    """
    problems = []
    for problem in error.errors():
        location_parts = [str(part) for part in problem["loc"]]
        location = ".".join(location_parts)
        if not location:
            location = "arguments"
        problems.append(f"{location}: {problem['msg']}")
    description = "; ".join(problems)
    return SmarterMCPServerToolError(f"invalid arguments for {tool_name}: {description}")


class MCPToolBase(ABC):
    """
    A tool of an MCP server: a name, a description, and a Pydantic model of its arguments.

    The tool's MCP ``inputSchema`` is generated from :attr:`arguments_model`, and :meth:`call`
    returns its result as Markdown text for the LLM. A subclass sets the class attributes, and
    implements :meth:`call`. The two families of tools are
    :class:`~smarter.apps.mcpserver.protocol.tools.SmarterProjectTool`, of the public Smarter
    Project MCP server, and
    :class:`~smarter.apps.mcpserver.protocol.operations_tools.SmarterOperationsTool`, of the
    staff-only Smarter Operations MCP server.
    """

    name: ClassVar[str]
    """The tool's name, which the LLM calls it by, e.g. ``search_logs``."""

    title: ClassVar[str]
    """The tool's human-readable name, which an MCP client may show, e.g. ``Search pod logs``."""

    description: ClassVar[str]
    """What the tool does, and when to call it.

    The LLM reads it to decide which tool to call.
    """

    arguments_model: ClassVar[type[BaseModel]]
    """The Pydantic model of the tool's arguments, which validates them and generates the ``inputSchema``."""

    read_only: ClassVar[bool] = True
    """
    Whether the tool only reads.

    A tool that writes is annotated so, with ``readOnlyHint`` false, so that an MCP client can ask
    its user before it calls it.
    """

    open_world: ClassVar[bool] = False
    """Whether the tool reaches beyond the platform's own data, e.g. to GitHub."""

    def input_schema(self) -> SmarterDictType:
        """
        Return the tool's MCP ``inputSchema``.

        The schema is generated from :attr:`arguments_model`, and simplified with
        :func:`simplify_schema`. MCP requires a schema of type ``object``, and
        ``additionalProperties: false`` tells the LLM that it may not invent arguments.

        :returns: A JSON schema of type object, without additional properties.
        """
        model_schema = self.arguments_model.model_json_schema()
        schema = simplify_schema(model_schema)
        schema.setdefault("properties", {})
        schema["type"] = "object"
        schema["additionalProperties"] = False
        return schema

    def definition(self) -> mcp_types.Tool:
        """
        Return the tool, as ``tools/list`` lists it.

        Its annotations are hints for the MCP client: a read-only tool is also idempotent, and no
        tool of this app destroys anything.

        :returns: The tool's name, title, description, ``inputSchema`` and annotations.
        """
        annotations = mcp_types.ToolAnnotations(
            title=self.title,
            read_only_hint=self.read_only,
            destructive_hint=False,
            idempotent_hint=self.read_only,
            open_world_hint=self.open_world,
        )
        tool = mcp_types.Tool(
            name=self.name,
            title=self.title,
            description=self.description,
            input_schema=self.input_schema(),
            annotations=annotations,
        )
        return tool

    @abstractmethod
    def call(self, arguments: Optional[SmarterDictType]) -> str:
        """
        Validate a tool call's arguments, and run the tool.

        :param arguments: The tool call's arguments, as the client sent them, or None.
        :returns: The result, as Markdown.
        :raises SmarterMCPServerToolError: If the arguments are not valid, or the tool fails. The
            server returns the error's message to the LLM as a result with ``isError`` set.
        """


class MCPServerBase(ABC):
    """
    An MCP server: answers the JSON-RPC messages of one POST request with its :attr:`tools`.

    A server lives for one request: the view creates it, calls :meth:`handle` with the request's
    body, and returns what it answers. A subclass sets :attr:`tools` in its constructor, and
    implements :attr:`name`, :meth:`server_info` and :meth:`instructions`.

    **Methods:**

    - :meth:`handle`: answers a request's body, one message or a batch.
    - :meth:`handle_message`: answers one message, with a JSON-RPC response or error.
    - :meth:`dispatch`: runs one JSON-RPC method: ``initialize``, ``ping``, ``tools/list`` or
      ``tools/call``.
    - :meth:`error` and :meth:`dump`: build a JSON-RPC error, and serialize a response. The views
      also use them, for errors that they answer before a server is created.
    """

    tools: dict[str, MCPToolBase]
    """The server's tools, by their name, in the order that ``tools/list`` lists them."""

    def __repr__(self) -> str:
        """Return the server's class and name, e.g. ``<SmarterProjectMCPServer name=smarter-project>``."""
        return f"<{self.__class__.__name__} name={self.name}>"

    @property
    def formatted_class_name(self) -> str:
        """The module, class and server name, formatted for the start of a log message."""
        module_name = logging.SmarterFormattedText.text(__name__)
        return f"{module_name}.{self.__class__.__name__}[{self.name}]"

    @property
    @abstractmethod
    def name(self) -> str:
        """The server's name, e.g. ``smarter-project``."""

    @abstractmethod
    def server_info(self) -> mcp_types.Implementation:
        """
        Return the server's identity, for the initialize result.

        :returns: The server's name, title, version, description and website.
        """

    @abstractmethod
    def instructions(self) -> str:
        """
        Return the server's instructions, which MCP clients add to the LLM's system prompt.

        :returns: Plain text that tells the LLM what the server is for, and when to call each tool.
        """

    # -------------------------------------------------------------------------
    # JSON-RPC
    # -------------------------------------------------------------------------
    def handle(self, payload: JsonValue) -> Optional[JsonValue]:
        """
        Answer the JSON-RPC message, or batch of messages, of one POST request.

        A batch is a list of 1 to :data:`MAX_BATCH_SIZE` messages, and is answered with a list of
        the responses of the messages that need one, in their order. A batch of notifications only
        needs no response.

        :param payload: The request body, parsed from JSON.
        :returns: The response body, or None if no message needs a response, e.g. a notification.
        """
        if not isinstance(payload, list):
            response = self.handle_message(payload)
            if response is None:
                return None
            return self.dump(response)

        if not payload or len(payload) > MAX_BATCH_SIZE:
            message = f"a batch must have from 1 to {MAX_BATCH_SIZE} messages."
            error = self.error(None, mcp_types.INVALID_REQUEST, message)
            return self.dump(error)

        answers = []
        for message in payload:
            response = self.handle_message(message)
            if response is not None:
                answer = self.dump(response)
                answers.append(answer)
        if not answers:
            return None
        return answers

    def handle_message(self, message: JsonValue) -> Optional[JsonRpcResponse]:
        """
        Answer one JSON-RPC message.

        Sends :data:`~smarter.apps.mcpserver.signals.mcpserver_called` for each valid notification
        and request. An exception that a method raises is answered with a JSON-RPC error: invalid
        params with ``INVALID_PARAMS``, an unknown method or tool with ``METHOD_NOT_FOUND``, and any
        other exception with ``INTERNAL_ERROR``, which is logged with its traceback, but whose
        message is not returned, so that internal details never reach the client.

        :param message: The message.
        :returns: The response, or None for a notification, or for a response from the client.
        """
        if not isinstance(message, dict):
            return self.error(None, mcp_types.INVALID_REQUEST, "not a JSON-RPC 2.0 message.")
        if message.get("jsonrpc") != mcp_types.JSONRPC_VERSION:
            return self.error(None, mcp_types.INVALID_REQUEST, "not a JSON-RPC 2.0 message.")
        if "method" not in message:
            # a response, or an error, from the client: this server sends no requests to answer.
            return None
        if "id" not in message:
            return self.handle_notification(message)

        try:
            request = mcp_types.JSONRPCRequest.model_validate(message)
        except ValidationError:
            request_id = message.get("id")
            if not isinstance(request_id, (int, str)):
                request_id = None
            return self.error(request_id, mcp_types.INVALID_REQUEST, "not a valid JSON-RPC request.")

        mcpserver_called.send(sender=self.__class__, server=self.name, method=request.method)
        params = request.params or {}
        try:
            result = self.dispatch(request.method, params)
        except ValidationError as e:
            error_message = f"invalid params for {request.method}: {e.error_count()} errors."
            return self.error(request.id, mcp_types.INVALID_PARAMS, error_message)
        except LookupError as e:
            return self.error(request.id, mcp_types.METHOD_NOT_FOUND, str(e))
        # pylint: disable=broad-exception-caught
        except Exception as e:
            logger.error("%s %s failed: %s", self.formatted_class_name, request.method, e, exc_info=True)
            return self.error(request.id, mcp_types.INTERNAL_ERROR, f"{request.method} failed.")

        result_json = result.model_dump(mode="json", by_alias=True, exclude_none=True)
        response = mcp_types.JSONRPCResponse(
            jsonrpc=mcp_types.JSONRPC_VERSION,
            id=request.id,
            result=result_json,
        )
        return response

    def handle_notification(self, message: SmarterDictType) -> None:
        """
        Accept a JSON-RPC notification, a message without an ``id``, and ignore it.

        The server keeps no state between requests, so a notification, e.g.
        ``notifications/initialized``, changes nothing. A valid notification sends
        :data:`~smarter.apps.mcpserver.signals.mcpserver_called`, so that it is logged, and one that
        is not valid is dropped, because JSON-RPC never answers a notification, not even with an
        error.

        :param message: The notification, a dict with a ``method`` and no ``id``.
        :returns: None: a notification has no response.
        """
        try:
            notification = mcp_types.JSONRPCNotification.model_validate(message)
        except ValidationError:
            return None
        mcpserver_called.send(sender=self.__class__, server=self.name, method=notification.method)
        return None

    def dispatch(self, method: str, params: SmarterDictType) -> mcp_types.Result:
        """
        Run one JSON-RPC method.

        :param method: The method, e.g. ``tools/call``.
        :param params: Its params, or an empty dict.
        :returns: Its result.
        :raises LookupError: If the server does not implement the method, or the tool does not exist.
        :raises ValidationError: If the params are not valid.
        """
        if method == "initialize":
            initialize_params = mcp_types.InitializeRequestParams.model_validate(params)
            return self.initialize(initialize_params)
        if method == "ping":
            return mcp_types.EmptyResult()
        if method == "tools/list":
            definitions = [tool.definition() for tool in self.tools.values()]
            return mcp_types.ListToolsResult(tools=definitions)
        if method == "tools/call":
            call_params = mcp_types.CallToolRequestParams.model_validate(params)
            return self.call_tool(call_params)
        raise LookupError(f"method not found: {method}")

    def initialize(self, params: mcp_types.InitializeRequestParams) -> mcp_types.InitializeResult:
        """
        Answer the initialize handshake.

        The server offers only the tools capability, and its list of tools never changes during a
        session, so ``listChanged`` is false.

        :param params: The client's offer: its protocol version, capabilities and identity.
        :returns: The client's protocol version, if this server speaks it, and otherwise the
            latest that it speaks, which the client may refuse.
        """
        requested_version = params.protocol_version
        if requested_version in HANDSHAKE_PROTOCOL_VERSIONS:
            version = requested_version
        else:
            version = LATEST_HANDSHAKE_VERSION
        tools_capability = mcp_types.ToolsCapability(list_changed=False)
        capabilities = mcp_types.ServerCapabilities(tools=tools_capability)
        result = mcp_types.InitializeResult(
            protocol_version=version,
            capabilities=capabilities,
            server_info=self.server_info(),
            instructions=self.instructions(),
        )
        return result

    def call_tool(self, params: mcp_types.CallToolRequestParams) -> mcp_types.CallToolResult:
        """
        Run a tool.

        A :class:`~smarter.apps.mcpserver.exceptions.SmarterMCPServerToolError` that the tool raises
        is returned as the result's text, with ``is_error`` set, so that the LLM can read it and
        correct its call. Sends :data:`~smarter.apps.mcpserver.signals.mcpserver_tool_called`
        after every call, whether or not it failed.

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
        content: list[mcp_types.ContentBlock] = [mcp_types.TextContent(text=text)]
        result = mcp_types.CallToolResult(content=content, is_error=is_error)
        return result

    @staticmethod
    def error(request_id: Optional[Union[int, str]], code: int, message: str) -> mcp_types.JSONRPCError:
        """
        Return a JSON-RPC error response.

        :param request_id: The id of the request that failed, or None if it could not be read.
        :param code: The JSON-RPC error code, e.g. ``mcp_types.INVALID_REQUEST``.
        :param message: What went wrong, for the client.
        :returns: The error response. Serialize it with :meth:`dump`.
        """
        error_data = mcp_types.ErrorData(code=code, message=message)
        response = mcp_types.JSONRPCError(jsonrpc=mcp_types.JSONRPC_VERSION, id=request_id, error=error_data)
        return response

    @staticmethod
    def dump(response: JsonRpcResponse) -> JsonValue:
        """
        Return a response as JSON.

        Fields that are None are left out of a result, but an error keeps its ``id``, which JSON-RPC
        requires, even when it is null.

        :param response: The response or error.
        :returns: The response as a JSON-serializable dict, with the protocol's camelCase names.
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
