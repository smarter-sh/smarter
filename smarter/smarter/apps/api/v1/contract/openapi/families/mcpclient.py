"""The MCPClients' REST reads, their reconnection, and the call of a tool, under ``/api/v1/mcpclients/``."""

from smarter_types import SAMKinds

from smarter.apps.api.v1.contract.models import (
    OpenApiMediaType,
    OpenApiOperation,
    OpenApiParameter,
    OpenApiPathItem,
    OpenApiRequestBody,
    RestApiErrorResponse,
)
from smarter.apps.api.v1.contract.openapi.builders import (
    READ_PERMISSION,
    ApiFamily,
    id_or_hashed_id,
    json_response,
    path_string,
    rest_read,
)
from smarter.apps.mcpclient.const import namespace
from smarter.apps.mcpclient.contract.models import (
    MCPClientApiMCPClient,
    MCPClientApiStatus,
    MCPClientApiToolResult,
    MCPClientApiTools,
)

MCPCLIENTS = ApiFamily(
    name=namespace,
    resource=SAMKinds.MCP_CLIENT.value,
    urlconf="smarter.apps.mcpclient.api.v1.urls",
    description="The {plural}' REST reads, their reconnection, and tool calls.",
)
"""The MCPClients' family."""


def mcpclient_paths() -> dict[str, OpenApiPathItem]:
    """
    The MCPClients' REST reads, their reconnection, and the call of a tool, relative to the server's ``/api/v1``.

    :returns: The paths, e.g. ``{"/mcpclients/": ...}``.
    :rtype: dict[str, OpenApiPathItem]
    """
    family = MCPCLIENTS
    resource = family.resource
    mcpclient_id = id_or_hashed_id(resource)
    connection_error = json_response(
        f"An error, e.g. 502 for an MCP server that failed, 403 for a user who does not own the {resource}, or 404 "
        f"for {family.a} that the user may not read.",
        "MCPClientApiErrorResponse",
    )
    tools = OpenApiOperation(
        operationId=family.operation_id("tools"),
        summary=f"{family.a_capitalized}'s tools",
        description=f"The tools that the {resource} offers the LLM, from its server's cached catalog, with its "
        f"connection status and the server's instructions. {READ_PERMISSION}",
        tags=[family.tag],
        parameters=[
            mcpclient_id,
            OpenApiParameter(
                name="refresh",
                in_="query",
                description="true reconnects to the MCP server first, rather than reading the cached catalog.",
                schema_={"type": "string", "enum": ["true", "false"], "default": "false"},
            ),
        ],
        responses={"200": json_response("The tools.", MCPClientApiTools.__name__), "default": connection_error},
    )
    refresh = OpenApiOperation(
        operationId=family.operation_id("refresh"),
        summary=f"Reconnect {family.a}",
        description=f"Reconnect to the {resource}'s server, refresh its catalog, and return its connection status. "
        f"Only the {resource}'s owner may reconnect it.",
        tags=[family.tag],
        parameters=[mcpclient_id],
        responses={
            "200": json_response("The connection status.", MCPClientApiStatus.__name__),
            "default": connection_error,
        },
    )
    tool_call = OpenApiOperation(
        operationId=family.operation_id("tool_call"),
        summary=f"Call {family.a}'s tool",
        description=f"Call one of the tools that the {resource} allows, with the request body as its arguments, and "
        "return its result as text. The tool runs on the MCP server, and may change what the server manages. Only "
        f"the {resource}'s owner may call its tools.",
        tags=[family.tag],
        parameters=[mcpclient_id, path_string("tool_name", "The tool's name.")],
        requestBody=OpenApiRequestBody(
            required=False,
            content={
                "application/json": OpenApiMediaType(
                    schema_={
                        "type": "object",
                        "additionalProperties": True,
                        "description": "The tool's arguments, as its input schema describes them.",
                    }
                )
            },
        ),
        responses={
            "200": json_response("The tool's result.", MCPClientApiToolResult.__name__),
            "default": json_response(
                f"An error, e.g. 403 for a tool that the {resource} does not allow, or 502 for a failed server.",
                RestApiErrorResponse.__name__,
            ),
        },
    )
    return {
        family.path(): OpenApiPathItem(
            get=rest_read(
                family.operation_id("list"),
                f"List {family.plural}",
                f"The {family.plural} that the user may read, by name.",
                family.tag,
                MCPClientApiMCPClient.__name__,
                many=True,
                parameters=[],
                note=READ_PERMISSION,
            )
        ),
        family.path("{id}/"): OpenApiPathItem(
            get=rest_read(
                family.operation_id("retrieve"),
                family.a_capitalized,
                f"{family.a_capitalized} that the user may read. Its credentials are their Secret's name, never its "
                "value.",
                family.tag,
                MCPClientApiMCPClient.__name__,
                many=False,
                parameters=[mcpclient_id],
                note=READ_PERMISSION,
            )
        ),
        family.path("{id}/tools/"): OpenApiPathItem(get=tools),
        family.path("{id}/refresh/"): OpenApiPathItem(post=refresh),
        family.path("{id}/tools/{tool_name}/"): OpenApiPathItem(post=tool_call),
    }


__all__ = ["MCPCLIENTS", "mcpclient_paths"]
