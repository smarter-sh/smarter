"""
The building blocks of the OpenAPI document: references, responses, operations, parameters, and families of routes.

Each family of the REST api is an :class:`ApiFamily`, named after its Django app, from which its tag, its
operations' ids, its paths, and the words that its descriptions use for its resource are derived, so that
each is written once.
"""

from dataclasses import dataclass
from typing import Optional, cast

import inflect

from smarter.apps.api.v1.contract.models import (
    OpenApiMediaType,
    OpenApiOperation,
    OpenApiParameter,
    OpenApiPathItem,
    OpenApiRequestBody,
    OpenApiResponse,
    OpenApiSchema,
    OpenApiTag,
    RestApiErrorResponse,
)
from smarter.lib.journal.contract.models import SAMJournalApiEnvelope

REF_TEMPLATE = "#/components/schemas/{model}"
"""Where the document's schemas refer to each other's definitions."""

API_KEY_AUTH = "ApiKeyAuth"
"""The name of the document's security scheme."""

PUBLIC: list[dict[str, list[str]]] = []
"""The ``security`` of an operation that needs no api key."""

SUPERUSER_ONLY = (
    "Requires an api key of a superuser: the REST api's views refuse other users with a 403. Other users read "
    "their resources with the cli api's get and describe."
)
"""The note of the REST reads whose views are SmarterAdminAPIView and SmarterAdminListAPIView."""

READ_PERMISSION = (
    "Requires an api key. The response includes only what the user may read: their account's resources, and "
    "the platform's built-in ones."
)
"""The note of the REST reads whose views are SmarterAuthenticatedAPIView and SmarterAuthenticatedListAPIView."""

API_KEY_ONLY = "Requires an api key."
"""The note of the REST reads that any api key may call, and whose views filter nothing more."""

SUPERUSER_READ_ERROR = "An error, e.g. 404 for a row that does not exist, or 403 for a user who is not a superuser."
"""The error of a read that only superusers may call: :data:`SUPERUSER_ONLY`."""

READ_ERROR = "An error, e.g. 404 for a row that does not exist, or that the user may not read."
"""The error of a read that every user may call, for what they may read."""

OPERATION_ERROR = "An error, e.g. 400 for an invalid request, or 404 for a row that the user may not read or own."
"""The error of an action that every user may call, on what they may read or own."""

SUPERUSER_OPERATION_ERROR = (
    "An error, e.g. 400 for an invalid request, 403 for a user who is not a superuser, or 404 for a row that does "
    "not exist."
)
"""The error of an action that only superusers may call."""

inflect_engine = inflect.engine()


def inflect_word(word: str) -> inflect.Word:
    """
    A word, as inflect's functions take it: a string of at least one character.

    inflect declares ``Word`` as ``Annotated[str, ...]`` for mypy, but as a class at run time, behind a flag
    that other type checkers, e.g. Pylance, can't follow, so they refuse a ``str``. inflect checks the
    length at run time; this checks it first, with a clearer message.

    :param word: The word, e.g. guardrail.
    :type word: str
    :returns: The word, as an ``inflect.Word``.
    :rtype: inflect.Word
    :raises ValueError: If the word is empty.
    """
    if not word:
        raise ValueError("inflect needs a word of at least one character.")
    return cast(inflect.Word, word)


def plural(word: str) -> str:
    """
    The plural of a word or a phrase, e.g. guardrails, LLMClients, account contacts.

    :param word: The word, e.g. guardrail.
    :type word: str
    :returns: Its plural.
    :rtype: str
    """
    return inflect_engine.plural(inflect_word(word))


def with_article(word: str, capitalize: bool = False) -> str:
    """
    A word or a phrase with its indefinite article, e.g. a Guardrail, an LLMClient.

    :param word: The word, e.g. LLMClient.
    :type word: str
    :param capitalize: Whether to capitalize the article, for a sentence's or a summary's first words.
    :type capitalize: bool
    :returns: e.g. an LLMClient, or An LLMClient.
    :rtype: str
    """
    phrase = inflect_engine.a(inflect_word(word))
    if capitalize:
        phrase = phrase[0].upper() + phrase[1:]
    return phrase


@dataclass(frozen=True)
class ApiFamily:
    """
    A family of the REST api's routes: one Django app's, or one feature's of an app.

    Everything that the document says about the family is derived from a few names, so that each is written
    once: e.g. ``ApiFamily(name="guardrail", resource="Guardrail", ...)`` has the tag ``guardrails``, the
    routes ``/guardrails/...``, the operation ids ``guardrail_list`` and ``guardrail_retrieve``, the plural
    ``Guardrails`` and the article ``a Guardrail``.
    """

    name: str
    """The family's name, its Django app's (the app's ``const.namespace``), e.g. guardrail.

    Its operations' ids start with it, and its tag is its plural.
    """
    resource: str
    """The family's resource, as its descriptions name it: its SAM kind, e.g. Guardrail, or a word, e.g. vectorstore."""
    urlconf: str
    """The module of the family's url patterns."""
    description: str
    """The description of the family's tag, in which ``{plural}`` is :attr:`plural`, e.g. The {plural}' REST reads."""
    resources: Optional[str] = None
    """The plural of :attr:`resource`, if inflect gets it wrong, e.g. Proxies: it adds only an s to a capitalized Proxy."""
    tag_name: Optional[str] = None
    """The family's tag, if it isn't the plural of :attr:`name`, e.g. journal."""
    mount: Optional[str] = None
    """Where ``smarter.apps.api.v1.urls`` mounts the family's routes, if not at its tag, e.g. llm-clients."""

    @property
    def tag(self) -> str:
        """The tag of the family's operations: :attr:`tag_name`, or the plural of :attr:`name`, e.g. guardrails."""
        if self.tag_name is not None:
            return self.tag_name
        return plural(self.name)

    @property
    def prefix(self) -> str:
        """The path of the family's routes, relative to ``/api/v1``: :attr:`mount` or :attr:`tag`, e.g. /guardrails/."""
        if self.mount is not None:
            return f"/{self.mount}/"
        return f"/{self.tag}/"

    @property
    def plural(self) -> str:
        """The plural of :attr:`resource`, e.g. Guardrails."""
        if self.resources is not None:
            return self.resources
        return plural(self.resource)

    @property
    def a(self) -> str:
        """The resource with its article, as a sentence names it: e.g. an LLMClient, or a Guardrail."""
        return with_article(self.resource)

    @property
    def a_capitalized(self) -> str:
        """The resource with its article, as a sentence's or a summary's first words: e.g. An LLMClient."""
        return with_article(self.resource, capitalize=True)

    def operation_id(self, action: str) -> str:
        """
        The id of one of the family's operations.

        :param action: What the operation does, e.g. list.
        :type action: str
        :returns: e.g. ``guardrail_list``.
        :rtype: str
        """
        return f"{self.name}_{action}"

    def path(self, suffix: str = "") -> str:
        """
        The path of one of the family's routes, relative to the server's ``/api/v1``.

        :param suffix: The route's path, relative to :attr:`prefix`, e.g. ``{id}/events/``.
        :type suffix: str
        :returns: e.g. ``/guardrails/{id}/events/``.
        :rtype: str
        """
        return f"{self.prefix}{suffix}"

    def openapi_tag(self) -> OpenApiTag:
        """
        The document's tag of the family's operations.

        :returns: The tag.
        :rtype: OpenApiTag
        """
        return OpenApiTag(name=self.tag, description=self.description.format(plural=self.plural))


def ref(name: str) -> OpenApiSchema:
    """
    A reference to one of the document's schemas.

    :param name: The schema's name in ``components.schemas``.
    :type name: str
    :returns: e.g. ``{"$ref": "#/components/schemas/SAMGuardrail"}``.
    :rtype: OpenApiSchema
    """
    return {"$ref": REF_TEMPLATE.format(model=name)}


def json_response(description: str, schema_name: str) -> OpenApiResponse:
    """
    A JSON response whose body is one of the document's schemas.

    :param description: The response's description.
    :type description: str
    :param schema_name: The body's schema, in ``components.schemas``.
    :type schema_name: str
    :returns: The response.
    :rtype: OpenApiResponse
    """
    return OpenApiResponse(
        description=description, content={"application/json": OpenApiMediaType(schema_=ref(schema_name))}
    )


def envelope(data: Optional[OpenApiSchema], description: str) -> OpenApiSchema:
    """
    The schema of a journaled response: the journal's envelope, beside the command's ``data`` and ``message``.

    :param data: The schema of the response's ``data``, or None for a response that has only a message.
    :type data: Optional[OpenApiSchema]
    :param description: The schema's description.
    :type description: str
    :returns: The schema.
    :rtype: OpenApiSchema
    """
    properties: dict[str, OpenApiSchema] = {
        "message": {"type": "string", "description": "A human-readable summary of the result."}
    }
    required: list[OpenApiSchema] = []
    if data is not None:
        properties["data"] = data
        required.append("data")
    else:
        required.append("message")
    return {
        "description": description,
        "allOf": [
            ref(SAMJournalApiEnvelope.__name__),
            {"type": "object", "properties": properties, "required": required},
        ],
    }


def rest_read(
    operation_id: str,
    summary: str,
    description: str,
    tag: str,
    item: str,
    *,
    many: bool,
    parameters: list[OpenApiParameter],
    note: str = SUPERUSER_ONLY,
    success: Optional[str] = None,
) -> OpenApiOperation:
    """
    A read of the REST api: a ``GET`` whose response is a row, or a list of rows, of one of the document's schemas.

    :param operation_id: The operation's id, e.g. llmclient_list.
    :type operation_id: str
    :param summary: A one-line summary.
    :type summary: str
    :param description: A description, to which ``note`` is added.
    :type description: str
    :param tag: The operation's tag.
    :type tag: str
    :param item: The schema of a row, in ``components.schemas``.
    :type item: str
    :param many: Whether the response is a list of rows.
    :type many: bool
    :param parameters: The operation's parameters.
    :type parameters: list[OpenApiParameter]
    :param note: Who may read, e.g. :data:`SUPERUSER_ONLY` or :data:`READ_PERMISSION`. It also chooses the
        error's description: :data:`SUPERUSER_READ_ERROR` for :data:`SUPERUSER_ONLY`, else :data:`READ_ERROR`.
    :type note: str
    :param success: The successful response's description, if the response is not a row or a list of rows, e.g.
        The window's points.
    :type success: Optional[str]
    :returns: The operation.
    :rtype: OpenApiOperation
    """
    if many:
        schema: OpenApiSchema = {"type": "array", "items": ref(item)}
        default_success = "The list."
    else:
        schema = ref(item)
        default_success = "The row."
    if success is None:
        success = default_success
    if note == SUPERUSER_ONLY:
        error = SUPERUSER_READ_ERROR
    else:
        error = READ_ERROR
    return OpenApiOperation(
        operationId=operation_id,
        summary=summary,
        description=f"{description} {note}",
        tags=[tag],
        parameters=parameters,
        responses={
            "200": OpenApiResponse(
                description=success,
                content={"application/json": OpenApiMediaType(schema_=schema)},
            ),
            "default": json_response(error, RestApiErrorResponse.__name__),
        },
    )


def rest_operation(  # pylint: disable=too-many-arguments
    operation_id: str,
    summary: str,
    description: str,
    tag: str,
    response: str,
    *,
    parameters: list[OpenApiParameter],
    status: str = "200",
    request_body: Optional[OpenApiRequestBody] = None,
    error: str = OPERATION_ERROR,
) -> OpenApiOperation:
    """
    An operation of the REST api, whose success is one of the document's schemas, and whose errors are DRF's.

    :param operation_id: The operation's id, e.g. vectorstore_search.
    :type operation_id: str
    :param summary: A one-line summary.
    :type summary: str
    :param description: A description, which says who may call it, and what it changes.
    :type description: str
    :param tag: The operation's tag.
    :type tag: str
    :param response: The successful response's schema, in ``components.schemas``.
    :type response: str
    :param parameters: The operation's parameters.
    :type parameters: list[OpenApiParameter]
    :param status: The successful response's http status, e.g. 202 for queued work.
    :type status: str
    :param request_body: The operation's request body.
    :type request_body: Optional[OpenApiRequestBody]
    :param error: The description of its errors, e.g. :data:`SUPERUSER_OPERATION_ERROR`.
    :type error: str
    :returns: The operation.
    :rtype: OpenApiOperation
    """
    return OpenApiOperation(
        operationId=operation_id,
        summary=summary,
        description=description,
        tags=[tag],
        parameters=parameters,
        requestBody=request_body,
        responses={
            status: json_response("Success.", response),
            "default": json_response(error, RestApiErrorResponse.__name__),
        },
    )


def json_body(schema_name: str, description: Optional[str] = None, required: bool = True) -> OpenApiRequestBody:
    """
    A JSON request body whose schema is one of the document's.

    :param schema_name: The body's schema, in ``components.schemas``.
    :type schema_name: str
    :param description: The body's description.
    :type description: Optional[str]
    :param required: Whether the body is required.
    :type required: bool
    :returns: The request body.
    :rtype: OpenApiRequestBody
    """
    return OpenApiRequestBody(
        required=required,
        description=description,
        content={"application/json": OpenApiMediaType(schema_=ref(schema_name))},
    )


def integer_id(name: str, description: str) -> OpenApiParameter:
    """
    A path parameter that is a row's numeric id.

    :param name: The parameter's name, e.g. plugin_id.
    :type name: str
    :param description: Its description.
    :type description: str
    :returns: The parameter.
    :rtype: OpenApiParameter
    """
    return OpenApiParameter(name=name, in_="path", required=True, description=description, schema_={"type": "integer"})


def id_or_hashed_id(resource: str) -> OpenApiParameter:
    """
    The ``{id}`` path parameter of a resource whose routes take its numeric id or its hashed id.

    :param resource: The resource's kind, e.g. Guardrail.
    :type resource: str
    :returns: The parameter.
    :rtype: OpenApiParameter
    """
    return OpenApiParameter(
        name="id",
        in_="path",
        required=True,
        description=f"The {resource}'s numeric id, e.g. 12, or its hashed id, e.g. rMTAwMDAxMgx.",
        schema_={"type": "string"},
    )


def path_string(name: str, description: str) -> OpenApiParameter:
    """
    A path parameter that is a string, e.g. a Provider's name.

    :param name: The parameter's name.
    :type name: str
    :param description: Its description.
    :type description: str
    :returns: The parameter.
    :rtype: OpenApiParameter
    """
    return OpenApiParameter(name=name, in_="path", required=True, description=description, schema_={"type": "string"})


def query(name: str, description: str, schema: OpenApiSchema, required: bool = False) -> OpenApiParameter:
    """
    A query parameter.

    :param name: The parameter's name.
    :type name: str
    :param description: Its description.
    :type description: str
    :param schema: Its JSON Schema.
    :type schema: OpenApiSchema
    :param required: Whether it is required.
    :type required: bool
    :returns: The parameter.
    :rtype: OpenApiParameter
    """
    return OpenApiParameter(name=name, in_="query", required=required, description=description, schema_=schema)


def superuser_list_and_retrieve(family: ApiFamily, item: str) -> dict[str, OpenApiPathItem]:
    """
    A family's REST list and retrieve, whose views only superusers may call.

    :param family: The family.
    :type family: ApiFamily
    :param item: The schema of a row, in ``components.schemas``.
    :type item: str
    :returns: The paths.
    :rtype: dict[str, OpenApiPathItem]
    """
    return {
        family.path(): OpenApiPathItem(
            get=rest_read(
                family.operation_id("list"),
                f"List {family.plural}",
                f"The {family.plural} that the user may read, by name.",
                family.tag,
                item,
                many=True,
                parameters=[],
            )
        ),
        family.path("{id}/"): OpenApiPathItem(
            get=rest_read(
                family.operation_id("retrieve"),
                family.a_capitalized,
                f"{family.a_capitalized}, by its id or hashed id.",
                family.tag,
                item,
                many=False,
                parameters=[id_or_hashed_id(family.resource)],
            )
        ),
    }


def merge_paths(*families: dict[str, OpenApiPathItem]) -> dict[str, OpenApiPathItem]:
    """
    The paths of several families, with the operations of a path that two families share in one path item.

    :param families: Each family's paths.
    :type families: dict[str, OpenApiPathItem]
    :returns: The paths.
    :rtype: dict[str, OpenApiPathItem]
    :raises ValueError: If two families define the same method of a path.
    """
    paths: dict[str, OpenApiPathItem] = {}
    for family in families:
        for path, item in family.items():
            merged = paths.get(path, OpenApiPathItem())
            for method in ("get", "post", "delete"):
                operation = getattr(item, method)
                if operation is not None:
                    if getattr(merged, method) is not None:
                        raise ValueError(f"{method.upper()} {path} is defined twice.")
                    setattr(merged, method, operation)
            paths[path] = merged
    return paths


__all__ = [
    "API_KEY_AUTH",
    "API_KEY_ONLY",
    "OPERATION_ERROR",
    "PUBLIC",
    "READ_ERROR",
    "READ_PERMISSION",
    "REF_TEMPLATE",
    "SUPERUSER_ONLY",
    "SUPERUSER_OPERATION_ERROR",
    "SUPERUSER_READ_ERROR",
    "ApiFamily",
    "envelope",
    "id_or_hashed_id",
    "inflect_engine",
    "inflect_word",
    "integer_id",
    "json_body",
    "json_response",
    "merge_paths",
    "path_string",
    "plural",
    "query",
    "ref",
    "rest_operation",
    "rest_read",
    "superuser_list_and_retrieve",
    "with_article",
]
