"""
The Smarter Project MCP server: the Model Context Protocol, over Streamable HTTP, in Django.

:class:`SmarterProjectMCPServer` answers the JSON-RPC messages of one POST request, and
:class:`~smarter.apps.mcpserver.views.SmarterProjectMCPServerView` serves it. It speaks the
``initialize`` handshake of every protocol version that the MCP Python SDK negotiates
(:data:`mcp_types.version.HANDSHAKE_PROTOCOL_VERSIONS`), and implements these methods:

- ``initialize``: the server's identity, its tools capability and its instructions.
- ``notifications/initialized`` and every other notification: accepted, and ignored.
- ``ping``: an empty result.
- ``tools/list``: the tools of :mod:`smarter.apps.mcpserver.tools`.
- ``tools/call``: runs a tool. A tool's own errors, e.g. a file that does not exist, are
  returned as a result with ``isError`` set, so that the LLM can correct its call.

**Why not the MCP SDK's server.** The SDK's server runs as an ASGI application, with an
anyio task group for its lifetime, and calls its tools as coroutines. Smarter's views and
ORM are synchronous, and the platform runs under both the Django development server and
uvicorn. Every message of this server is answered from the database, with no state between
requests, so the server is a plain Django view that uses the SDK's own Pydantic models,
:mod:`mcp_types`, to validate the requests and to build the responses.

**Stateless.** The server answers every POST with ``application/json``, and does not issue
an ``Mcp-Session-Id``. Clients therefore open no GET stream, and send no DELETE, and any
of the platform's pods can answer any request.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from typing import Optional, Union

import mcp_types
from mcp_types.version import HANDSHAKE_PROTOCOL_VERSIONS, LATEST_HANDSHAKE_VERSION
from pydantic import JsonValue, ValidationError

from smarter.common.const import SMARTER_PROJECT_WEBSITE_URL, VERSION
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.typing import SmarterDictType

from .exceptions import SmarterMCPServerToolError
from .repositories import (
    SMARTER_PROJECT_DOCS_LATEST_URL,
    ProjectRepository,
    project_repositories,
)
from .signals import mcpserver_called, mcpserver_tool_called
from .tools import TOOL_CLASSES, SmarterProjectScope, SmarterProjectTool

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.MCPSERVER_LOGGING])

SERVER_NAME = "smarter-project"
SERVER_VERSION = str(VERSION.get("__version__", "0.0.0"))
MAX_BATCH_SIZE = 20
"""The maximum number of messages in a JSON-RPC batch, which protocol 2025-03-26 allows."""

JsonRpcResponse = Union[mcp_types.JSONRPCResponse, mcp_types.JSONRPCError]

INSTRUCTIONS = """\
This server reads {subject}, from GitHub: its documentation and its source code. Answer questions \
about The Smarter Project from what its tools return, rather than from memory, which may be outdated \
or about another product named Smarter.

- search_documentation finds concepts, features, configuration and how-to guides, in the Sphinx \
documentation that is published at {docs_url}, and in READMEs.
- search_code finds how something is implemented, and a class, function, setting or manifest field by name.
- read_file reads a file that a search returned, to confirm the details before you answer.
- get_repository_overview and list_files describe a repository's layout.

Search with specific keywords and identifiers. Some clients allow only one round of tool calls \
per answer, so make every search that you need at once, in parallel, e.g. search_documentation and \
search_code together, rather than one after another. Their results include the matching lines, which \
are usually enough to answer. Cite your sources: link to the published documentation page when a result has one, and \
otherwise to the GitHub url of the file.{repositories}"""


class SmarterProjectMCPServer:
    """
    The MCP server of one repository of The Smarter Project, or of all of them.

    :param repository: The repository, or None for all of them.

    **Example usage**::

        server = SmarterProjectMCPServer(get_repository("smarter-cli"))
        response = server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    """

    def __init__(self, repository: Optional[ProjectRepository] = None):
        self.scope = SmarterProjectScope(
            repository=repository,
            repositories=(repository,) if repository else project_repositories(),
        )
        self.tools: dict[str, SmarterProjectTool] = {
            tool_class.name: tool_class(self.scope) for tool_class in TOOL_CLASSES
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name}>"

    @property
    def formatted_class_name(self) -> str:
        """The class name, for logging."""
        return f"{logging.SmarterFormattedText.text(__name__)}.{self.__class__.__name__}[{self.name}]"

    @property
    def name(self) -> str:
        """The server's name, e.g. ``smarter-project`` or ``smarter-project-smarter-cli``."""
        repository = self.scope.repository
        return f"{SERVER_NAME}-{repository.name}" if repository else SERVER_NAME

    def server_info(self) -> mcp_types.Implementation:
        """Return the server's identity, for the initialize result."""
        repository = self.scope.repository
        return mcp_types.Implementation(
            name=self.name,
            title=f"The Smarter Project: {repository.title}" if repository else "The Smarter Project",
            version=SERVER_VERSION,
            description=(
                repository.description
                if repository
                else "The documentation and source code of every repository of The Smarter Project."
            ),
            website_url=SMARTER_PROJECT_WEBSITE_URL,
        )

    def instructions(self) -> str:
        """Return the server's instructions, which MCP clients add to the LLM's system prompt."""
        repository = self.scope.repository
        if repository:
            subject = f"the {repository.full_name} GitHub repository, {repository.title}"
            repositories = ""
        else:
            subject = "every GitHub repository of The Smarter Project"
            repositories = "\n\nThe repositories:\n" + "\n".join(
                f"- {r.name}: {r.title}" for r in self.scope.repositories
            )
        return INSTRUCTIONS.format(subject=subject, docs_url=SMARTER_PROJECT_DOCS_LATEST_URL, repositories=repositories)

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


__all__ = ["SmarterProjectMCPServer"]
