"""
Pydantic models of the Smarter cli api contract, and of the OpenAPI document that publishes it.

The cli api (``/api/v1/cli/``) is the api of the ``smarter`` cli and of the SDKs: it applies, gets,
describes and deletes the resources that SAM manifests declare. Its requests and responses are
described by:

- the SAM models, one per kind, e.g. :class:`smarter.apps.guardrail.manifest.models.guardrail.model.SAMGuardrail`,
  for the manifests that it accepts and returns,
- the Smarter Journal api contract (:mod:`smarter.lib.journal.contract.models`), for the envelope
  of every response, and for its errors,
- the Smarter Chat api contract (:mod:`smarter.apps.prompt.contract.models`), for the chat
  configuration and the chat completion that the cli's prompt commands return,
- the models in this module, for the ``data`` of the commands whose data is not a manifest. The
  views build their responses from them.

:mod:`smarter.apps.api.v1.contract.openapi` assembles them into an OpenAPI document, which is
modeled here too (``OpenApi...``), so that it is built from models rather than from nested dicts.
A schema inside the document is JSON Schema, which is arbitrary JSON, so it is a ``JsonValue``.

The response models allow extra fields: adding a field is backward compatible. Removing or renaming
one that is declared here is not.
"""

from typing import Literal, Optional, Union

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    SerializerFunctionWrapHandler,
    model_serializer,
)

from smarter.apps.prompt.contract.models import (
    PromptChatApiCompletionV1,
    PromptChatApiJournalMetadata,
    PromptChatApiMessage,
)

# ------------------------------------------------------------------------------
# the data of cli responses
# ------------------------------------------------------------------------------


class CliApiModel(BaseModel):
    """Base class of the models of the cli api's response data, which allow extra fields."""

    model_config = ConfigDict(extra="allow")


class CliApiApplied(CliApiModel):
    """The ``data`` of an ``apply`` response: the resource that the manifest created or updated."""

    apiVersion: str = Field(..., description='The manifest\'s api version, e.g. "smarter.sh/v1".')
    kind: str = Field(..., description="The manifest's kind, e.g. Guardrail.")
    name: str = Field(..., description="The resource's name, the manifest's metadata.name.")


class CliApiValidationError(CliApiModel):
    """An error of a manifest that ``validate`` reports."""

    loc: list[Union[str, int]] = Field(
        ...,
        description="The path of the invalid value in the manifest, e.g. ['spec', 'config', 'severity']. "
        "Empty for an error that concerns the whole manifest.",
    )
    message: str = Field(..., description="A human-readable description of the error.")
    type: str = Field(..., description="The error's type, e.g. missing, or invalid_kind.")


class CliApiValidation(CliApiModel):
    """The ``data`` of a ``validate`` response."""

    valid: bool = Field(..., description="Whether the manifest is valid.")
    errors: list[CliApiValidationError] = Field(..., description="The manifest's errors. Empty when it is valid.")


class CliApiGetMetadata(CliApiModel):
    """The ``metadata`` of a ``get`` response's data."""

    count: int = Field(..., ge=0, description="The number of resources that matched.")


class CliApiGetTitle(CliApiModel):
    """A column of a ``get`` response's table: an item's field, and its serializer field's type."""

    name: str = Field(..., description="The field's name, e.g. createdAt.")
    type: str = Field(..., description="The serializer field's class, e.g. DateTimeField.")


class CliApiGetItems(CliApiModel):
    """The table of a ``get`` response: its columns, and one row per resource."""

    titles: list[CliApiGetTitle] = Field(..., description="The table's columns.")
    items: list[dict[str, JsonValue]] = Field(
        ..., description="The resources, one object per resource, with one key per title."
    )


class CliApiGet(CliApiModel):
    """The ``data`` of a ``get`` response: the resources of a kind that match the request's criteria."""

    apiVersion: str = Field(..., description='The api version, e.g. "smarter.sh/v1".')
    kind: str = Field(..., description="The resources' kind, e.g. Guardrail.")
    name: Optional[str] = Field(None, description="The name that the request asked for, if any.")
    metadata: CliApiGetMetadata
    kwargs: dict[str, JsonValue] = Field(..., description="The request's criteria, from its query parameters.")
    data: CliApiGetItems


class CliApiResource(CliApiModel):
    """A kind of resource that the cli api manages: an item of the ``resources`` response's data."""

    Singular: str = Field(..., description="The kind's singular name, e.g. Guardrail.")
    Plural: str = Field(..., description="The kind's plural name, e.g. Guardrails.")
    APIKind: str = Field(..., description="The kind, as it is written in a manifest and in the api's urls.")
    Display: str = Field(..., description="The kind's singular display name.")
    DisplayPlural: str = Field(..., description="The kind's plural display name.")
    Deployable: bool = Field(..., description="Whether the kind's resources can be deployed and undeployed.")


class CliApiStatusRedis(CliApiModel):
    """The Redis server of a ``status`` response, from Redis's INFO command."""

    gcc_version: Optional[str] = None
    os: Optional[str] = None
    redis_build_id: Optional[str] = None
    redis_version: Optional[str] = None


class CliApiStatusInfrastructures(CliApiModel):
    """The infrastructure of a ``status`` response."""

    kubernetes: dict[str, JsonValue] = Field(
        ...,
        description="The Kubernetes cluster, as the infrastructure provider describes it, e.g. its version and "
        "status, or an error if the provider is not ready. Its fields depend on the provider.",
    )
    redis: CliApiStatusRedis


class CliApiStatusCompute(CliApiModel):
    """The platform's compute, from Python's platform module."""

    machine: str
    release: str
    platform: str
    processor: str
    system: str
    version: str


class CliApiStatus(CliApiModel):
    """The ``data`` of a ``status`` response: the platform's infrastructure and compute."""

    infrastructures: CliApiStatusInfrastructures
    compute: CliApiStatusCompute


class CliApiVersionApi(CliApiModel):
    """The platform's version, and the versions of its main Python packages."""

    version: str = Field(..., description="The platform's version.")
    python: dict[str, Optional[str]] = Field(
        ..., description="The version of Python, and of each of the platform's main packages, by name. Null if unknown."
    )


class CliApiVersionCli(CliApiModel):
    """The smarter cli's latest version."""

    version: str


class CliApiVersion(CliApiModel):
    """The ``data`` of a ``version`` response."""

    api: CliApiVersionApi
    cli: CliApiVersionCli


class CliApiWhoamiUser(CliApiModel):
    """The api key's user."""

    id: int
    username: str
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    email: Optional[str] = None
    isStaff: bool
    isSuperuser: bool


class CliApiWhoamiAccount(CliApiModel):
    """The api key's account."""

    id: int
    hashedId: Optional[str] = None
    accountNumber: str
    name: Optional[str] = None
    description: Optional[str] = None
    companyName: Optional[str] = None
    isDefaultAccount: Optional[bool] = None
    isActive: Optional[bool] = None
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None
    phoneNumber: Optional[str] = None
    address1: Optional[str] = None
    address2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postalCode: Optional[str] = None
    country: Optional[str] = None
    language: Optional[str] = None
    timezone: Optional[str] = None
    currency: Optional[str] = None


class CliApiWhoami(CliApiModel):
    """The ``data`` of a ``whoami`` response: the api key's user and account, and the platform's environment."""

    user: CliApiWhoamiUser
    account: CliApiWhoamiAccount
    environment: str = Field(..., description="The platform's environment, e.g. prod, or local.")


class CliApiPromptBody(CliApiModel):
    """The request body of a ``prompt``."""

    prompt: str = Field(..., description="The user's message.")
    session_key: Optional[str] = Field(
        None, description="The chat session to continue. By default, the session that the uid used last."
    )
    messages: Optional[list[PromptChatApiMessage]] = Field(
        None, description="The chat's earlier messages, to which the prompt is added. By default, a new chat."
    )


class CliApiPromptRequest(CliApiModel):
    """The request that a ``prompt`` sent to the LLMClient."""

    session_key: str
    messages: list[PromptChatApiMessage]


class CliApiPromptLambdaResponse(CliApiModel):
    """The LLMClient's response to a ``prompt``: the version 1 prompt response, with its body decoded from a JSON string."""

    isBase64Encoded: bool = False
    statusCode: int
    headers: dict[str, str] = Field(default_factory=dict)
    body: PromptChatApiCompletionV1


class CliApiPromptChatResponse(CliApiModel):
    """The LLMClient's journaled response to a ``prompt``."""

    api: str
    metadata: PromptChatApiJournalMetadata
    data: CliApiPromptLambdaResponse


class CliApiPrompt(CliApiModel):
    """The ``data`` of a ``prompt`` response: the request that the cli api sent to the LLMClient, and its response."""

    request: CliApiPromptRequest
    response: CliApiPromptChatResponse


CLI_API_MODELS: tuple[type[BaseModel], ...] = (
    CliApiApplied,
    CliApiValidation,
    CliApiGet,
    CliApiResource,
    CliApiStatus,
    CliApiVersion,
    CliApiWhoami,
    CliApiPromptBody,
    CliApiPrompt,
)
"""The models of the cli api's response data whose JSON Schema the OpenAPI document includes.

Their dependencies are included with them.
"""


# ------------------------------------------------------------------------------
# the OpenAPI document
# ------------------------------------------------------------------------------


class OpenApiModel(BaseModel):
    """
    Base class of the models of an OpenAPI 3.1 document.

    They forbid extra fields, so a misspelled field fails rather than being published. Fields whose
    OpenAPI name is a Python keyword, or a ``BaseModel`` attribute, have an alias: e.g. ``in_`` is
    ``in``, and ``schema_`` is ``schema``. A field that is None is left out of the dump, because no
    OpenAPI field may be null. ``exclude_none`` would also drop the nulls inside the schemas, e.g. a
    field's ``"default": null``, so the models drop their own Nones instead.
    """

    model_config = ConfigDict(extra="forbid", validate_by_name=True, validate_by_alias=True, serialize_by_alias=True)

    @model_serializer(mode="wrap")
    def _drop_none(self, handler: SerializerFunctionWrapHandler) -> dict[str, JsonValue]:
        """The model's fields, without those that are None."""
        return {key: value for key, value in handler(self).items() if value is not None}


OpenApiSchema = JsonValue
"""A JSON Schema (2020-12), e.g. ``{"$ref": "#/components/schemas/SAMGuardrail"}``."""


class OpenApiContact(OpenApiModel):
    """The document's contact information."""

    name: str
    url: str


class OpenApiLicense(OpenApiModel):
    """The api's license."""

    name: str
    url: str


class OpenApiInfo(OpenApiModel):
    """The document's metadata."""

    title: str
    version: str
    summary: Optional[str] = None
    description: Optional[str] = None
    contact: Optional[OpenApiContact] = None
    license: Optional[OpenApiLicense] = None


class OpenApiServerVariable(OpenApiModel):
    """A variable of a server's url."""

    default: str
    description: Optional[str] = None


class OpenApiServer(OpenApiModel):
    """A server that hosts the api."""

    url: str
    description: Optional[str] = None
    variables: Optional[dict[str, OpenApiServerVariable]] = None


class OpenApiTag(OpenApiModel):
    """A tag, which groups operations."""

    name: str
    description: Optional[str] = None


class OpenApiParameter(OpenApiModel):
    """A path, query or header parameter of an operation."""

    name: str
    in_: Literal["path", "query", "header"] = Field(..., alias="in")
    description: Optional[str] = None
    required: bool = False
    schema_: OpenApiSchema = Field(..., alias="schema")


class OpenApiMediaType(OpenApiModel):
    """The schema of a request's or response's body, in one media type."""

    schema_: OpenApiSchema = Field(..., alias="schema")
    x_smarter_events: Optional[dict[str, OpenApiSchema]] = Field(
        None,
        alias="x-smarter-events",
        description="For text/event-stream: the schema of each event's data, by the event's name. OpenAPI 3.1 has "
        "no field for it, so it is an extension.",
    )


class OpenApiRequestBody(OpenApiModel):
    """An operation's request body."""

    description: Optional[str] = None
    required: bool = False
    content: dict[str, OpenApiMediaType]


class OpenApiResponse(OpenApiModel):
    """One of an operation's responses."""

    description: str
    content: Optional[dict[str, OpenApiMediaType]] = None


class OpenApiOperation(OpenApiModel):
    """An http method of a path."""

    operationId: str
    summary: str
    description: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    parameters: list[OpenApiParameter] = Field(default_factory=list)
    requestBody: Optional[OpenApiRequestBody] = None
    responses: dict[str, OpenApiResponse]
    security: Optional[list[dict[str, list[str]]]] = Field(
        None, description="Overrides the document's security. An empty list makes the operation public."
    )


class OpenApiPathItem(OpenApiModel):
    """A path, and its operations."""

    get: Optional[OpenApiOperation] = None
    post: Optional[OpenApiOperation] = None


class OpenApiSecurityScheme(OpenApiModel):
    """An api key scheme: the only one that the cli api accepts from programs."""

    type: Literal["apiKey"] = "apiKey"
    name: str
    in_: Literal["header"] = Field("header", alias="in")
    description: Optional[str] = None


class OpenApiComponents(OpenApiModel):
    """The document's reusable schemas and security schemes."""

    schemas: dict[str, OpenApiSchema]
    securitySchemes: dict[str, OpenApiSecurityScheme]


class OpenApiDocument(OpenApiModel):
    """An OpenAPI 3.1 document."""

    openapi: str
    info: OpenApiInfo
    jsonSchemaDialect: str
    servers: list[OpenApiServer]
    security: list[dict[str, list[str]]]
    tags: list[OpenApiTag]
    paths: dict[str, OpenApiPathItem]
    components: OpenApiComponents


__all__ = [
    "CLI_API_MODELS",
    "CliApiApplied",
    "CliApiGet",
    "CliApiGetItems",
    "CliApiGetMetadata",
    "CliApiGetTitle",
    "CliApiModel",
    "CliApiPrompt",
    "CliApiPromptBody",
    "CliApiPromptChatResponse",
    "CliApiPromptLambdaResponse",
    "CliApiPromptRequest",
    "CliApiResource",
    "CliApiStatus",
    "CliApiStatusCompute",
    "CliApiStatusInfrastructures",
    "CliApiStatusRedis",
    "CliApiValidation",
    "CliApiValidationError",
    "CliApiVersion",
    "CliApiVersionApi",
    "CliApiVersionCli",
    "CliApiWhoami",
    "CliApiWhoamiAccount",
    "CliApiWhoamiUser",
    "OpenApiComponents",
    "OpenApiContact",
    "OpenApiDocument",
    "OpenApiInfo",
    "OpenApiLicense",
    "OpenApiMediaType",
    "OpenApiModel",
    "OpenApiOperation",
    "OpenApiParameter",
    "OpenApiPathItem",
    "OpenApiRequestBody",
    "OpenApiResponse",
    "OpenApiSchema",
    "OpenApiSecurityScheme",
    "OpenApiServer",
    "OpenApiServerVariable",
    "OpenApiTag",
]
