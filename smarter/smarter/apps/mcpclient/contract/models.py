"""
Pydantic models of the MCPClients' REST api responses (``/api/v1/mcpclients/``).

The REST api's views build their responses from these models, and the Smarter api's OpenAPI
document (:mod:`smarter.apps.api.v1.contract.openapi`) publishes their JSON Schemas.

:class:`MCPClientApiMCPClient` is an MCPClient, as :class:`smarter.apps.mcpclient.serializers.MCPClientSerializer`
returned it before the api was modeled, which clients already read. One value changed: its
``canDelete`` is computed for the requesting user. The other models replace the dicts that the
views built by hand, with the same keys. ``lastConnected`` is now an ISO 8601 date-time ending in
``Z``, where it ended in ``+00:00``: the same instant.

The models forbid extra fields: the api returns exactly what they declare.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Literal, Optional

from pydantic import Field, JsonValue

from smarter.apps.account.contract.models import (
    AccountApiModel,
    AccountApiUserProfile,
    MetaDataApiAnnotations,
)
from smarter.apps.account.serializers import user_can_delete

if TYPE_CHECKING:
    from smarter.apps.mcpclient.connection import (
        MCPServerCatalog,
        MCPToolInfo,
        MCPToolResult,
    )
    from smarter.apps.mcpclient.models import MCPClient


MCPClientApiTransport = Literal["stdio", "sse", "http"]
"""The choices of ``MCPClient.transport``.

A test fails if the two differ.
"""

MCPClientApiAuthType = Literal["none", "api_key", "oauth2", "bearer_token"]
"""The choices of ``MCPClient.auth_type``.

A test fails if the two differ.
"""

MCPClientApiConnectionStatus = Literal["unconfigured", "connected", "disconnected", "error"]
"""The choices of ``MCPClient.status``: the result of the last connection.

A test fails if the two differ.
"""


class MCPClientApiMCPClient(AccountApiModel):
    """An MCPClient: a :class:`smarter.apps.mcpclient.models.MCPClient`.

    Its credentials are their Secret's name.
    """

    id: int = Field(..., description="The row's primary key.")
    hashed_id: str = Field(..., description="The MCPClient's hashed id, which its urls use.")
    created_at: Optional[datetime] = Field(None, description="TimestampedModel.created_at.")
    updated_at: Optional[datetime] = Field(None, description="TimestampedModel.updated_at.")
    name: str = Field(..., description="MetaDataModel.name, in snake_case.")
    description: Optional[str] = Field(None, description="MetaDataModel.description.")
    version: Optional[str] = Field(None, description="MetaDataModel.version, e.g. 1.0.0.")
    tags: list[str] = Field(default_factory=list, description="MetaDataModel.tags, by name.")
    annotations: MetaDataApiAnnotations = Field(None, description="MetaDataModel.annotations.")
    user_profile: AccountApiUserProfile = Field(..., description="The MCPClient's owner.")
    can_delete: bool = Field(
        ...,
        description="Whether the requesting user may delete the MCPClient now: they own it, and nothing uses it.",
    )
    credentials: Optional[str] = Field(
        None, description="The name of the Secret that holds the credential, never its value."
    )
    manifest_url: str = Field(..., description="The url of the MCPClient's manifest in the web console.")
    ready: bool = Field(..., description="Whether the MCPClient is configured completely.")
    rfc1034_compliant_name: Optional[str] = Field(None, description="The name, as a DNS label.")
    transport: Optional[MCPClientApiTransport] = Field(None, description="The MCP transport.")
    endpoint_url: Optional[str] = Field(None, description="The url of the MCP server's endpoint.")
    command: Optional[str] = Field(None, description="The command of a stdio server.")
    headers: Optional[dict[str, JsonValue]] = Field(None, description="Non-secret http headers to send to the server.")
    timeout: int = Field(..., ge=0, description="Seconds to wait for the server.")
    auth_type: MCPClientApiAuthType = Field(..., description="How to authenticate with the server.")
    api_key_header: str = Field(..., description="The http header that carries an api_key credential.")
    allowed_tools: Optional[list[str]] = Field(None, description="Glob patterns of the tools to offer the LLM.")
    allowed_resources: Optional[list[str]] = Field(None, description="Glob patterns of the resources the LLM may read.")
    include_instructions: bool = Field(..., description="Whether the server's instructions join the system prompt.")
    cache_ttl: int = Field(..., ge=0, description="Seconds to cache the server's catalog.")
    is_active: bool = Field(..., description="Whether LLMClients use the MCPClient.")
    status: MCPClientApiConnectionStatus = Field(..., description="The result of the last connection.")
    priority: int = Field(..., ge=0, description="The order of an LLMClient's MCPClients. Lower runs first.")
    protocol_version: Optional[str] = Field(None, description="The MCP protocol version that the server negotiated.")
    server_name: Optional[str] = Field(None, description="The name that the server reported.")
    server_version: Optional[str] = Field(None, description="The version that the server reported.")
    tools: Optional[list[str]] = Field(None, description="The names of the tools offered, as of the last connection.")
    last_connected_at: Optional[datetime] = Field(None, description="When the platform last connected.")
    last_error: Optional[str] = Field(None, description="The error of the last failed connection.")

    @classmethod
    def from_model(cls, mcpclient: "MCPClient", user: object = None) -> "MCPClientApiMCPClient":
        """
        The contract's model of an MCPClient.

        :param mcpclient: The row, whose ``user_profile`` and ``credentials`` should be fetched with it.
        :type mcpclient: smarter.apps.mcpclient.models.MCPClient
        :param user: The requesting user, for ``can_delete``. None may delete nothing.
        :type user: object
        :returns: The model.
        :rtype: MCPClientApiMCPClient
        """
        # pylint: disable=import-outside-toplevel
        from django.urls import reverse

        from smarter.apps.mcpclient.manifest.models.mcpclient.const import (
            MANIFEST_KIND as MCPCLIENT_KIND,
        )
        from smarter.apps.mcpclient.urls import MCPClientReverseNames

        return cls(
            id=mcpclient.pk,
            hashed_id=mcpclient.hashed_id,
            created_at=mcpclient.created_at,
            updated_at=mcpclient.updated_at,
            name=mcpclient.name,
            description=mcpclient.description,
            version=mcpclient.version,
            tags=[tag.name for tag in mcpclient.tags.all()],
            annotations=mcpclient.annotations,
            user_profile=AccountApiUserProfile.from_model(mcpclient.user_profile),
            can_delete=user_can_delete(mcpclient, MCPCLIENT_KIND, user),
            credentials=mcpclient.credentials.name if mcpclient.credentials else None,
            manifest_url=reverse(
                f"{MCPClientReverseNames.namespace}:{MCPClientReverseNames.detailview}",
                kwargs={"hashed_id": mcpclient.hashed_id},
            ),
            ready=mcpclient.ready,
            rfc1034_compliant_name=mcpclient.rfc1034_compliant_name,
            transport=mcpclient.transport,  # type: ignore[arg-type]
            endpoint_url=mcpclient.endpoint_url,
            command=mcpclient.command,
            headers=mcpclient.headers,
            timeout=mcpclient.timeout,
            auth_type=mcpclient.auth_type,  # type: ignore[arg-type]
            api_key_header=mcpclient.api_key_header,
            allowed_tools=mcpclient.allowed_tools,
            allowed_resources=mcpclient.allowed_resources,
            include_instructions=mcpclient.include_instructions,
            cache_ttl=mcpclient.cache_ttl,
            is_active=mcpclient.is_active,
            status=mcpclient.status,  # type: ignore[arg-type]
            priority=mcpclient.priority,
            protocol_version=mcpclient.protocol_version,
            server_name=mcpclient.server_name,
            server_version=mcpclient.server_version,
            tools=mcpclient.tools,
            last_connected_at=mcpclient.last_connected_at,
            last_error=mcpclient.last_error,
        )


class MCPClientApiStatus(AccountApiModel):
    """An MCPClient's connection to its MCP server: the result of the last connection, and what the server reported."""

    name: str = Field(..., description="The MCPClient's name.")
    status: MCPClientApiConnectionStatus = Field(..., description="The result of the last connection.")
    protocol_version: Optional[str] = Field(None, description="The MCP protocol version that the server negotiated.")
    server_name: Optional[str] = Field(None, description="The name that the server reported.")
    server_version: Optional[str] = Field(None, description="The version that the server reported.")
    last_connected: Optional[datetime] = Field(None, description="When the platform last connected.")
    last_error: Optional[str] = Field(None, description="The error of the last failed connection.")
    tools: list[str] = Field(..., description="The names of the tools offered, as of the last connection.")

    @classmethod
    def from_model(cls, mcpclient: "MCPClient") -> "MCPClientApiStatus":
        """
        The connection status of an MCPClient.

        :param mcpclient: The row.
        :type mcpclient: smarter.apps.mcpclient.models.MCPClient
        :returns: The model.
        :rtype: MCPClientApiStatus
        """
        return cls(
            name=mcpclient.name,
            status=mcpclient.status,  # type: ignore[arg-type]
            protocol_version=mcpclient.protocol_version,
            server_name=mcpclient.server_name,
            server_version=mcpclient.server_version,
            last_connected=mcpclient.last_connected_at,
            last_error=mcpclient.last_error,
            tools=mcpclient.tools or [],
        )


class MCPClientApiStatusError(MCPClientApiStatus):
    """A failed connection to an MCP server: the error, beside the MCPClient's connection status."""

    detail: str = Field(..., description="The error, for a person.")


class MCPClientApiTool(AccountApiModel):
    """A tool that an MCP server offers, and that the MCPClient allows."""

    name: str = Field(..., description="The tool's name, which an LLM calls it by.")
    title: Optional[str] = Field(None, description="The tool's title, for a person.")
    description: str = Field("", description="What the tool does, for the LLM.")
    input_schema: dict[str, JsonValue] = Field(..., description="The JSON Schema of the tool's arguments.")
    read_only: Optional[bool] = Field(None, description="Whether the server says the tool changes nothing.")
    destructive: Optional[bool] = Field(None, description="Whether the server says the tool may destroy data.")

    @classmethod
    def from_tool(cls, tool: "MCPToolInfo") -> "MCPClientApiTool":
        """
        The contract's model of a tool from an MCP server's catalog.

        :param tool: The tool.
        :type tool: smarter.apps.mcpclient.connection.MCPToolInfo
        :returns: The model.
        :rtype: MCPClientApiTool
        """
        return cls(
            name=tool.name,
            title=tool.title,
            description=tool.description,
            input_schema=tool.input_schema,
            read_only=tool.read_only,
            destructive=tool.destructive,
        )


class MCPClientApiTools(AccountApiModel):
    """An MCPClient's connection status, its server's instructions, and the tools that it offers the LLM."""

    name: str = Field(..., description="The MCPClient's name.")
    status: MCPClientApiConnectionStatus = Field(..., description="The result of the last connection.")
    protocol_version: Optional[str] = Field(None, description="The MCP protocol version that the server negotiated.")
    server_name: Optional[str] = Field(None, description="The name that the server reported.")
    server_version: Optional[str] = Field(None, description="The version that the server reported.")
    last_connected: Optional[datetime] = Field(None, description="When the platform last connected.")
    last_error: Optional[str] = Field(None, description="The error of the last failed connection.")
    instructions: Optional[str] = Field(None, description="The server's instructions for the LLM.")
    tools: list[MCPClientApiTool] = Field(..., description="The tools that the MCPClient allows.")

    @classmethod
    def from_catalog(
        cls, mcpclient: "MCPClient", catalog: "MCPServerCatalog", tools: list["MCPToolInfo"]
    ) -> "MCPClientApiTools":
        """
        The tools of an MCPClient, from its server's catalog.

        :param mcpclient: The row.
        :type mcpclient: smarter.apps.mcpclient.models.MCPClient
        :param catalog: The server's catalog.
        :type catalog: smarter.apps.mcpclient.connection.MCPServerCatalog
        :param tools: The catalog's tools that the MCPClient allows.
        :type tools: list[smarter.apps.mcpclient.connection.MCPToolInfo]
        :returns: The model.
        :rtype: MCPClientApiTools
        """
        status = MCPClientApiStatus.from_model(mcpclient)
        return cls(
            **status.model_dump(exclude={"tools"}),
            instructions=catalog.instructions,
            tools=[MCPClientApiTool.from_tool(tool) for tool in tools],
        )


class MCPClientApiToolResult(AccountApiModel):
    """The result of a call of an MCPClient's tool, as text for an LLM."""

    name: str = Field(..., description="The MCPClient's name.")
    tool: str = Field(..., description="The tool's name.")
    is_error: bool = Field(..., description="Whether the tool reported an error.")
    content: str = Field(..., description="The tool's result, as text. Binary content is described, not included.")

    @classmethod
    def from_result(cls, mcpclient: "MCPClient", tool: str, result: "MCPToolResult") -> "MCPClientApiToolResult":
        """
        The contract's model of a tool call's result.

        :param mcpclient: The row.
        :type mcpclient: smarter.apps.mcpclient.models.MCPClient
        :param tool: The tool's name.
        :type tool: str
        :param result: The result.
        :type result: smarter.apps.mcpclient.connection.MCPToolResult
        :returns: The model.
        :rtype: MCPClientApiToolResult
        """
        return cls(name=mcpclient.name, tool=tool, is_error=result.is_error, content=result.text)


MCPCLIENT_API_MODELS = (
    MCPClientApiMCPClient,
    MCPClientApiStatus,
    MCPClientApiStatusError,
    MCPClientApiTools,
    MCPClientApiToolResult,
)
"""The models whose JSON Schemas the Smarter api's OpenAPI document includes.

Their dependencies are included with them.
"""

__all__ = [
    "MCPCLIENT_API_MODELS",
    "MCPClientApiAuthType",
    "MCPClientApiConnectionStatus",
    "MCPClientApiMCPClient",
    "MCPClientApiStatus",
    "MCPClientApiStatusError",
    "MCPClientApiTool",
    "MCPClientApiToolResult",
    "MCPClientApiTools",
    "MCPClientApiTransport",
]
