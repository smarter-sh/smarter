"""
Connections to remote MCP servers.

:class:`MCPServerConnection` connects an :class:`~smarter.apps.mcpclient.models.MCPClient`
to its MCP server with the official `MCP Python SDK <https://github.com/modelcontextprotocol/python-sdk>`_,
and exposes three synchronous operations, each of which opens a connection, performs the MCP
handshake, and closes the connection:

- :meth:`MCPServerConnection.discover` returns the server's :class:`MCPServerCatalog`: its
  protocol version, identity, instructions, capabilities and tools.
- :meth:`MCPServerConnection.call_tool` calls one of the server's tools.
- :meth:`MCPServerConnection.read_resource` reads one of the server's resources.

**Security.** The endpoint is user supplied, and the connection is made from the Smarter
server, so every HTTP request, including redirects and the message endpoint of the legacy
SSE transport, is checked with :func:`~smarter.apps.plugin.plugin.safe_http.validate_public_url`:
it must be https, on the standard port, and every address its host resolves to must be public.
Credentials are read from the MCPClient's Smarter Secret when a connection is made, and are
sent only as HTTP headers. The stdio transport, which would run a command on the Smarter
server, is not supported.

.. note::

    **Experimental.** The MCPClient was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

import asyncio
import fnmatch
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from typing import Any, Awaitable, Callable, Optional, TypeVar

import anyio
import httpx2
import mcp_types
from mcp import Client
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamable_http_client

from smarter.apps.plugin.plugin.safe_http import validate_public_url
from smarter.common.const import VERSION
from smarter.common.exceptions import SmarterValueError
from smarter.lib import json, logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .exceptions import (
    SmarterMCPClientConfigurationError,
    SmarterMCPClientConnectionError,
    SmarterMCPClientPermissionError,
)
from .models import MCPAuthType, MCPClient, MCPTransport

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.MCPCLIENT_LOGGING])

T = TypeVar("T")

CLIENT_NAME = "smarter"
CLIENT_VERSION = str(VERSION.get("__version__", "0.0.0"))
USER_AGENT = f"Smarter/{CLIENT_VERSION} MCPClient (+https://smarter.sh)"

MAX_TOOL_PAGES = 10
"""The maximum number of tools/list pages to fetch."""
MAX_TOOLS = 500
"""The maximum number of tools to accept from a server."""
MAX_RESULT_CHARACTERS = 20000
"""The maximum length of a tool result or resource returned to the LLM."""
MAX_INSTRUCTIONS_CHARACTERS = 4000
"""The maximum length of a server's instructions added to the system prompt."""
TRUNCATION_MARKER = "\n\n[content truncated]"


def truncate(text: str, max_characters: int) -> str:
    """
    Truncate text to at most ``max_characters``, marking the truncation.

    :param text: The text.
    :param max_characters: The maximum length.
    :returns: The text, truncated if necessary.
    """
    if len(text) <= max_characters:
        return text
    return text[: max_characters - len(TRUNCATION_MARKER)] + TRUNCATION_MARKER


def matches_any(value: str, patterns: Optional[list[str]]) -> bool:
    """
    Return whether a value matches any of a list of glob patterns.

    :param value: The value, e.g. a tool name or a resource URI.
    :param patterns: Glob patterns, e.g. ``search_*``.
    :returns: True if the value matches a pattern.
    """
    return any(fnmatch.fnmatchcase(value, pattern) for pattern in patterns or [])


def is_tool_allowed(mcpclient: MCPClient, tool_name: str) -> bool:
    """
    Return whether an MCPClient offers one of its server's tools to the LLM.

    :param mcpclient: The MCPClient.
    :param tool_name: The name of the tool, as the server reports it.
    :returns: True if ``allowed_tools`` is empty, or the name matches one of its patterns.
    """
    return not mcpclient.allowed_tools or matches_any(tool_name, mcpclient.allowed_tools)


def is_resource_allowed(mcpclient: MCPClient, uri: str) -> bool:
    """
    Return whether the LLM may read one of an MCPClient's server's resources.

    :param mcpclient: The MCPClient.
    :param uri: The URI of the resource.
    :returns: True if the URI matches one of the ``allowed_resources`` patterns. If there
        are none, no resource may be read.
    """
    return matches_any(uri, mcpclient.allowed_resources)


def run_sync(fn: Callable[[], Awaitable[T]]) -> T:
    """
    Run a coroutine function to completion, from synchronous code.

    The prompt pipeline, the Celery tasks and the views are synchronous. If this thread
    already runs an event loop, the coroutine is run in a new event loop in another thread.

    :param fn: A function that returns the coroutine to run.
    :returns: The coroutine's result.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(fn())  # type: ignore[arg-type]
    with ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(lambda: asyncio.run(fn())).result()  # type: ignore[arg-type]


def leaf_exception(e: BaseException) -> BaseException:
    """Return the first leaf of a (possibly nested) exception group, or the exception itself."""
    while isinstance(e, BaseExceptionGroup) and e.exceptions:
        e = e.exceptions[0]
    return e


async def guard_request(request: httpx2.Request) -> None:
    """
    An httpx2 request hook that refuses requests to non-public hosts.

    :param request: The request about to be sent.
    :raises SafeHttpError: If the URL is not https, not on the standard port, or its host
        resolves to an address that is not public.
    """
    await anyio.to_thread.run_sync(validate_public_url, str(request.url))


def guarded_http_client(
    headers: Optional[dict[str, str]] = None,
    timeout: Optional[httpx2.Timeout] = None,
    auth: Optional[httpx2.Auth] = None,
) -> httpx2.AsyncClient:
    """
    Create an httpx2 client whose every request is checked by :func:`guard_request`.

    Its signature matches the MCP SDK's ``McpHttpClientFactory``, so that it can also be
    passed to :func:`mcp.client.sse.sse_client`.
    """
    return httpx2.AsyncClient(
        headers=headers,
        timeout=timeout,
        auth=auth,
        follow_redirects=False,
        event_hooks={"request": [guard_request]},
    )


@dataclass(frozen=True)
class MCPToolInfo:
    """A tool that an MCP server advertises."""

    name: str
    description: str = ""
    title: Optional[str] = None
    input_schema: dict[str, Any] = field(default_factory=dict)
    read_only: Optional[bool] = None
    destructive: Optional[bool] = None


@dataclass(frozen=True)
class MCPServerCatalog:
    """What an MCP server reported during the handshake and tools/list."""

    protocol_version: Optional[str] = None
    server_name: Optional[str] = None
    server_version: Optional[str] = None
    instructions: Optional[str] = None
    has_tools: bool = False
    has_resources: bool = False
    tools: list[MCPToolInfo] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return the catalog as a JSON-serializable dict, e.g. for caching."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MCPServerCatalog":
        """Return a catalog from :meth:`to_dict`."""
        data = dict(data)
        data["tools"] = [MCPToolInfo(**tool) for tool in data.get("tools", [])]
        return cls(**data)


@dataclass(frozen=True)
class MCPToolResult:
    """The result of a tool call, as text for the LLM."""

    text: str
    is_error: bool = False


def content_to_text(block: Any) -> str:
    """
    Render one content block of a tool result as text for the LLM.

    Text is returned as is. Binary content, like images and audio, is described rather
    than included, because the chat completion's tool message can only carry text.

    :param block: An MCP content block.
    :returns: The block, as text.
    """
    if isinstance(block, mcp_types.TextContent):
        return block.text
    if isinstance(block, (mcp_types.ImageContent, mcp_types.AudioContent)):
        return f"[{block.type} content ({block.mime_type}) omitted]"
    if isinstance(block, mcp_types.EmbeddedResource):
        resource = block.resource
        if isinstance(resource, mcp_types.TextResourceContents):
            return resource.text
        return f"[binary resource {resource.uri} ({resource.mime_type}) omitted]"
    if isinstance(block, mcp_types.ResourceLink):
        return f"[resource: {block.name} {block.uri}]"
    return f"[{getattr(block, 'type', type(block).__name__)} content omitted]"


class MCPServerConnection:
    """
    A connection to an MCPClient's MCP server.

    :param mcpclient: The MCPClient.
    """

    def __init__(self, mcpclient: MCPClient):
        self.mcpclient = mcpclient

    @property
    def formatted_class_name(self) -> str:
        """The class name, for logging."""
        return logging.formatted_text(f"{__name__}.{self.__class__.__name__}[{self.mcpclient.name}]")

    @property
    def timeout(self) -> float:
        """Seconds to wait for the MCP server to connect and respond."""
        return float(self.mcpclient.timeout or 30)

    def credential(self) -> str:
        """
        Return the MCPClient's credential, from its Smarter Secret.

        :raises SmarterMCPClientConfigurationError: If the Secret is missing or empty.
        """
        secret = self.mcpclient.credentials
        value = secret.get_secret() if secret else None
        if not value:
            raise SmarterMCPClientConfigurationError(
                f"MCPClient {self.mcpclient.name} requires a credentials Secret for authType {self.mcpclient.auth_type}."
            )
        return value

    def request_headers(self) -> dict[str, str]:
        """
        Return the HTTP headers to send to the MCP server: its custom headers, and its credential.

        :raises SmarterMCPClientConfigurationError: If the credential is missing.
        """
        headers = {str(k): str(v) for k, v in (self.mcpclient.headers or {}).items()}
        headers["User-Agent"] = USER_AGENT
        auth_type = self.mcpclient.auth_type or MCPAuthType.NONE
        if auth_type == MCPAuthType.API_KEY:
            headers[self.mcpclient.api_key_header or "X-API-Key"] = self.credential()
        elif auth_type in (MCPAuthType.BEARER_TOKEN, MCPAuthType.OAUTH2):
            headers["Authorization"] = f"Bearer {self.credential()}"
        return headers

    def server_target(self, http_client: httpx2.AsyncClient) -> Any:
        """
        Return what the MCP SDK's :class:`mcp.Client` connects to: the MCPClient's transport.

        :param http_client: The guarded httpx2 client, for the Streamable HTTP transport.
        :raises SmarterMCPClientConfigurationError: If the transport is not supported.
        """
        url = self.mcpclient.endpoint_url or ""
        transport = self.mcpclient.transport or MCPTransport.HTTP
        if transport == MCPTransport.HTTP:
            return streamable_http_client(url, http_client=http_client)
        if transport == MCPTransport.SSE:
            return sse_client(
                url,
                headers=dict(http_client.headers),
                timeout=self.timeout,
                sse_read_timeout=self.timeout,
                httpx_client_factory=guarded_http_client,
            )
        raise SmarterMCPClientConfigurationError(
            f"MCPClient {self.mcpclient.name}: transport {transport} is not supported."
        )

    def run(self, operation: Callable[[Client], Awaitable[T]], description: str) -> T:
        """
        Connect to the MCP server, perform the handshake, run an operation, and disconnect.

        :param operation: An async function of the connected :class:`mcp.Client`.
        :param description: What the operation does, for error messages.
        :returns: The operation's result.
        :raises SmarterMCPClientConnectionError: If the server cannot be reached, fails the
            handshake, returns an error, or does not respond within the timeout.
        :raises SmarterMCPClientConfigurationError: If the MCPClient is misconfigured.
        """
        url = self.mcpclient.endpoint_url
        if not url:
            raise SmarterMCPClientConfigurationError(f"MCPClient {self.mcpclient.name} has no endpointUrl.")
        try:
            validate_public_url(url)
        except SmarterValueError as e:
            raise SmarterMCPClientConnectionError(f"MCPClient {self.mcpclient.name}: {e.message}") from e
        headers = self.request_headers()

        async def connect_and_run() -> T:
            timeout = httpx2.Timeout(self.timeout, read=self.timeout)
            with anyio.fail_after(self.timeout):
                async with guarded_http_client(headers=headers, timeout=timeout) as http_client:
                    client = Client(
                        self.server_target(http_client),
                        mode="legacy",
                        read_timeout_seconds=self.timeout,
                        client_info=mcp_types.Implementation(name=CLIENT_NAME, version=CLIENT_VERSION),
                    )
                    async with client:
                        return await operation(client)

        try:
            return run_sync(connect_and_run)
        except (SmarterMCPClientConfigurationError, SmarterMCPClientPermissionError):
            raise
        except BaseException as e:  # pylint: disable=broad-exception-caught
            if isinstance(e, (KeyboardInterrupt, SystemExit)):
                raise
            cause = leaf_exception(e)
            if isinstance(cause, TimeoutError):
                message = f"timed out after {self.timeout:g} seconds"
            elif isinstance(cause, SmarterValueError):
                message = cause.message
            elif isinstance(cause, httpx2.HTTPStatusError):
                message = f"HTTP {cause.response.status_code} from {cause.request.url}"
            else:
                message = str(cause) or type(cause).__name__
            logger.warning("%s %s failed: %s", self.formatted_class_name, description, message)
            raise SmarterMCPClientConnectionError(
                f"MCPClient {self.mcpclient.name} could not {description}: {message}"
            ) from cause

    # -------------------------------------------------------------------------
    # operations
    # -------------------------------------------------------------------------
    def discover(self) -> MCPServerCatalog:
        """
        Return the MCP server's catalog: its identity, instructions, capabilities and tools.

        All of the server's tools are returned, whether or not ``allowed_tools`` allows them.
        """

        async def operation(client: Client) -> MCPServerCatalog:
            capabilities = client.server_capabilities
            tools: list[MCPToolInfo] = []
            if capabilities.tools is not None:
                cursor = None
                for _ in range(MAX_TOOL_PAGES):
                    result = await client.list_tools(cursor=cursor)
                    for tool in result.tools:
                        annotations = tool.annotations
                        tools.append(
                            MCPToolInfo(
                                name=tool.name,
                                description=tool.description or "",
                                title=tool.title,
                                input_schema=dict(tool.input_schema or {}),
                                read_only=annotations.read_only_hint if annotations else None,
                                destructive=annotations.destructive_hint if annotations else None,
                            )
                        )
                    cursor = result.next_cursor
                    if not cursor or len(tools) >= MAX_TOOLS:
                        break
            server_info = client.server_info
            return MCPServerCatalog(
                protocol_version=client.protocol_version,
                server_name=server_info.name if server_info else None,
                server_version=server_info.version if server_info else None,
                instructions=client.instructions,
                has_tools=capabilities.tools is not None,
                has_resources=capabilities.resources is not None,
                tools=tools[:MAX_TOOLS],
            )

        return self.run(operation, "list its tools")

    def call_tool(self, tool_name: str, arguments: Optional[dict[str, Any]] = None) -> MCPToolResult:
        """
        Call one of the MCP server's tools.

        :param tool_name: The name of the tool, as the server reports it.
        :param arguments: The tool's arguments.
        :returns: The result, as text for the LLM. If the tool reports an error, the result's
            ``is_error`` is True, and its text describes the error.
        :raises SmarterMCPClientPermissionError: If ``allowed_tools`` does not allow the tool.
        """
        if not is_tool_allowed(self.mcpclient, tool_name):
            raise SmarterMCPClientPermissionError(
                f"MCPClient {self.mcpclient.name} does not allow the tool {tool_name}."
            )

        async def operation(client: Client) -> MCPToolResult:
            result = await client.call_tool(tool_name, arguments or {})
            parts = [content_to_text(block) for block in result.content or []]
            if result.structured_content and not any(
                isinstance(block, mcp_types.TextContent) for block in result.content or []
            ):
                parts.append(json.dumps(result.structured_content))
            text = truncate("\n\n".join(part for part in parts if part), MAX_RESULT_CHARACTERS)
            return MCPToolResult(text=text, is_error=bool(result.is_error))

        return self.run(operation, f"call the tool {tool_name}")

    def read_resource(self, uri: str) -> str:
        """
        Read one of the MCP server's resources.

        :param uri: The URI of the resource.
        :returns: The resource's text content, for the LLM.
        :raises SmarterMCPClientPermissionError: If ``allowed_resources`` does not allow the URI.
        """
        if not is_resource_allowed(self.mcpclient, uri):
            raise SmarterMCPClientPermissionError(
                f"MCPClient {self.mcpclient.name} does not allow reading the resource {uri}."
            )

        async def operation(client: Client) -> str:
            result = await client.read_resource(uri)
            parts = []
            for contents in result.contents or []:
                if isinstance(contents, mcp_types.TextResourceContents):
                    parts.append(contents.text)
                else:
                    parts.append(f"[binary resource {contents.uri} ({contents.mime_type}) omitted]")
            return truncate("\n\n".join(parts), MAX_RESULT_CHARACTERS)

        return self.run(operation, f"read the resource {uri}")


__all__ = [
    "MCPServerCatalog",
    "MCPServerConnection",
    "MCPToolInfo",
    "MCPToolResult",
    "is_resource_allowed",
    "is_tool_allowed",
    "matches_any",
    "run_sync",
    "truncate",
]
