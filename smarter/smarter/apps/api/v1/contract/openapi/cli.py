"""
The cli api's operations, under ``/api/v1/cli/``: the commands of the ``smarter`` cli, as the SDKs send them.

Every command is a ``POST`` whose response is journaled: the journal's envelope, beside the command's ``data``
or ``message``, and whose errors are the journal's error response.
"""

from typing import Optional

from smarter.apps.api.v1.contract.models import (
    CliApiPromptBody,
    OpenApiMediaType,
    OpenApiOperation,
    OpenApiParameter,
    OpenApiPathItem,
    OpenApiRequestBody,
    OpenApiTag,
)
from smarter.apps.prompt.contract.models import PromptChatApiConfigResponse

from .builders import PUBLIC, json_response, ref
from .chat import TAG_CHAT

CLI_PREFIX = "/cli/"
"""The path of the cli api's routes, relative to ``/api/v1``."""

CLI_URLCONF = "smarter.apps.api.v1.cli.urls"
"""The module of the cli api's url patterns."""

TAG_MANIFESTS = "manifests"
TAG_DEPLOYMENT = "deployment"
TAG_PLATFORM = "platform"

CLI_TAGS = [
    OpenApiTag(name=TAG_MANIFESTS, description="Resources, and the manifests that declare them."),
    OpenApiTag(name=TAG_DEPLOYMENT, description="Deployable resources, e.g. LLMClients."),
    OpenApiTag(name=TAG_PLATFORM, description="The platform, and the api key's user."),
]
"""The tags of the cli api's commands, but its chat commands', which are the chat api's."""


def cli_path(command: str) -> str:
    """
    The path of a cli command, relative to the server's ``/api/v1``.

    :param command: The command's path, relative to :data:`CLI_PREFIX`, e.g. ``get/{kind}/``.
    :type command: str
    :returns: e.g. ``/cli/get/{kind}/``.
    :rtype: str
    """
    return f"{CLI_PREFIX}{command}"


KIND_PARAMETER = OpenApiParameter(
    name="kind",
    in_="path",
    required=True,
    description="The resource's kind, as it is written in a manifest, e.g. Guardrail. Case-insensitive.",
    schema_=ref("SAMKind"),
)


NAME_PARAMETER = OpenApiParameter(
    name="name",
    in_="query",
    required=True,
    description="The resource's name, its manifest's metadata.name.",
    schema_={"type": "string"},
)


NAME_FILTER_PARAMETER = OpenApiParameter(
    name="name",
    in_="query",
    required=False,
    description="Only the resource with this name. Other query parameters are passed to the kind's broker as criteria.",
    schema_={"type": "string"},
)


LLMCLIENT_PARAMETER = OpenApiParameter(
    name="name",
    in_="path",
    required=True,
    description="The LLMClient's name.",
    schema_={"type": "string"},
)


UID_PARAMETER = OpenApiParameter(
    name="uid",
    in_="query",
    required=True,
    description="A unique identifier of the client, e.g. a machine id. The platform caches the client's chat "
    "session under it, so that a later prompt continues the same chat.",
    schema_={"type": "string"},
)


NEW_SESSION_PARAMETER = OpenApiParameter(
    name="new_session",
    in_="query",
    required=False,
    description="true starts a new chat session, rather than continuing the client's last one.",
    schema_={"type": "string", "enum": ["true", "false"], "default": "false"},
)


PROMPT_BODY = OpenApiRequestBody(
    description="The user's message.",
    required=True,
    content={"application/json": OpenApiMediaType(schema_=ref(CliApiPromptBody.__name__))},
)


MANIFEST_BODY = OpenApiRequestBody(
    description="A SAM manifest, as YAML or as JSON.",
    required=True,
    content={
        "application/x-yaml": OpenApiMediaType(schema_={"type": "string", "description": "A SAM manifest, as YAML."}),
        "application/json": OpenApiMediaType(schema_=ref("SAMManifest")),
    },
)


def operation(
    operation_id: str,
    summary: str,
    description: str,
    tag: str,
    response: str,
    *,
    parameters: Optional[list[OpenApiParameter]] = None,
    request_body: Optional[OpenApiRequestBody] = None,
    security: Optional[list[dict[str, list[str]]]] = None,
) -> OpenApiOperation:
    """
    A cli command: an operation whose successful response is ``200``, and whose other responses are journaled errors.

    :param operation_id: The operation's id, e.g. apply.
    :type operation_id: str
    :param summary: A one-line summary.
    :type summary: str
    :param description: A description.
    :type description: str
    :param tag: The operation's tag.
    :type tag: str
    :param response: The successful response's schema, in ``components.schemas``.
    :type response: str
    :param parameters: The operation's parameters.
    :type parameters: Optional[list[OpenApiParameter]]
    :param request_body: The operation's request body.
    :type request_body: Optional[OpenApiRequestBody]
    :param security: The operation's security, e.g. :data:`PUBLIC`, or None for the document's.
    :type security: Optional[list[dict[str, list[str]]]]
    :returns: The operation.
    :rtype: OpenApiOperation
    """
    return OpenApiOperation(
        operationId=operation_id,
        summary=summary,
        description=description,
        tags=[tag],
        parameters=parameters or [],
        requestBody=request_body,
        responses={
            "200": json_response("Success.", response),
            "default": json_response(
                "An error, e.g. 400 for an invalid manifest, 401 or 403 without a valid api key, "
                "404 for a resource that does not exist.",
                "CliApiErrorResponse",
            ),
        },
        security=security,
    )


def cli_paths() -> dict[str, OpenApiPathItem]:
    """
    The cli api's paths, relative to the server's ``/api/v1``, by the url names of their routes.

    :returns: The paths, e.g. ``{"/cli/apply/": ...}``.
    :rtype: dict[str, OpenApiPathItem]
    """
    by_name = [KIND_PARAMETER, NAME_PARAMETER]
    commands = {
        cli_path("apply/"): operation(
            "apply",
            "Apply a manifest",
            "Create the resource that a manifest declares, or update it to match the manifest.",
            TAG_MANIFESTS,
            "CliApiApplyResponse",
            request_body=MANIFEST_BODY,
        ),
        cli_path("validate/"): operation(
            "validate",
            "Validate a manifest",
            "Validate a manifest against its kind's model, without saving it. An invalid manifest is a "
            "successful response, whose data lists the manifest's errors.",
            TAG_MANIFESTS,
            "CliApiValidateResponse",
            request_body=MANIFEST_BODY,
        ),
        cli_path("get/{kind}/"): operation(
            "get",
            "List resources",
            "List the resources of a kind that the api key's user may see.",
            TAG_MANIFESTS,
            "CliApiGetResponse",
            parameters=[KIND_PARAMETER, NAME_FILTER_PARAMETER],
        ),
        cli_path("describe/{kind}/"): operation(
            "describe",
            "Describe a resource",
            "A resource's manifest, with its read-only status.",
            TAG_MANIFESTS,
            "CliApiManifestResponse",
            parameters=by_name,
        ),
        cli_path("delete/{kind}/"): operation(
            "delete",
            "Delete a resource",
            "Delete a resource.",
            TAG_MANIFESTS,
            "CliApiMessageResponse",
            parameters=by_name,
        ),
        cli_path("example-manifest/{kind}/"): operation(
            "example_manifest",
            "An example manifest",
            "An example manifest of a kind.",
            TAG_MANIFESTS,
            "CliApiManifestResponse",
            parameters=[KIND_PARAMETER],
            security=PUBLIC,
        ),
        cli_path("json-schema/{kind}/"): operation(
            "json_schema",
            "A kind's JSON Schema",
            "The JSON Schema of a kind's manifests. The same schemas are published in the repository, as "
            "smarter/smarter/apps/api/v1/contract/sam/<Kind>.schema.json.",
            TAG_MANIFESTS,
            "CliApiJsonSchemaResponse",
            parameters=[KIND_PARAMETER],
            security=PUBLIC,
        ),
        cli_path("deploy/{kind}/"): operation(
            "deploy",
            "Deploy a resource",
            "Deploy a resource of a deployable kind, e.g. an LLMClient. Deployment may create cloud infrastructure.",
            TAG_DEPLOYMENT,
            "CliApiMessageResponse",
            parameters=by_name,
        ),
        cli_path("undeploy/{kind}/"): operation(
            "undeploy",
            "Undeploy a resource",
            "Undeploy a deployed resource.",
            TAG_DEPLOYMENT,
            "CliApiMessageResponse",
            parameters=by_name,
        ),
        cli_path("logs/{kind}/"): operation(
            "logs",
            "A resource's logs",
            "A resource's logs.",
            TAG_DEPLOYMENT,
            "CliApiMessageResponse",
            parameters=by_name,
        ),
        cli_path("status/"): operation(
            "status",
            "Platform status",
            "The status of the platform's infrastructure and compute.",
            TAG_PLATFORM,
            "CliApiStatusResponse",
        ),
        cli_path("version/"): operation(
            "version",
            "Versions",
            "The versions of the platform and its packages, and the smarter cli's latest version.",
            TAG_PLATFORM,
            "CliApiVersionResponse",
        ),
        cli_path("whoami/"): operation(
            "whoami", "Who am I", "The api key's user and account.", TAG_PLATFORM, "CliApiWhoamiResponse"
        ),
        cli_path("prompt/{name}/"): operation(
            "prompt",
            "Prompt an LLMClient",
            "Send a message to an LLMClient, and return its chat completion. The chat session is cached under the "
            "uid, so that the next prompt continues it. The completion is the Smarter Chat api contract's version 1 "
            "completion, decoded from the JSON string of its body.",
            TAG_CHAT,
            "CliApiPromptResponse",
            parameters=[LLMCLIENT_PARAMETER, UID_PARAMETER, NEW_SESSION_PARAMETER],
            request_body=PROMPT_BODY,
        ),
        cli_path("prompt/config/{name}/"): operation(
            "prompt_config",
            "An LLMClient's chat configuration",
            "The configuration of a chat with an LLMClient, and its session, as the Smarter Chat api contract's "
            "version 2 configuration response.",
            TAG_CHAT,
            PromptChatApiConfigResponse.__name__,
            parameters=[LLMCLIENT_PARAMETER, UID_PARAMETER, NEW_SESSION_PARAMETER],
        ),
        cli_path("resources/"): operation(
            "resources",
            "Resource kinds",
            "The kinds of resources that the cli api manages.",
            TAG_PLATFORM,
            "CliApiResourcesResponse",
        ),
    }
    return {path: OpenApiPathItem(post=command) for path, command in commands.items()}


__all__ = [
    "CLI_PREFIX",
    "CLI_TAGS",
    "CLI_URLCONF",
    "TAG_DEPLOYMENT",
    "TAG_MANIFESTS",
    "TAG_PLATFORM",
    "cli_path",
    "cli_paths",
    "operation",
]
