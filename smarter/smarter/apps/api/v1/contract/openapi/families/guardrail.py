"""The Guardrails' REST reads, and the dry run of a Guardrail, under ``/api/v1/guardrails/``."""

from typing import get_args

from smarter_types import SAMKinds

from smarter.apps.api.v1.contract.models import (
    OpenApiOperation,
    OpenApiParameter,
    OpenApiPathItem,
    RestApiErrorResponse,
)
from smarter.apps.api.v1.contract.openapi.builders import (
    READ_PERMISSION,
    ApiFamily,
    id_or_hashed_id,
    json_body,
    json_response,
    rest_read,
)
from smarter.apps.guardrail.const import namespace
from smarter.apps.guardrail.contract.models import (
    GuardrailApiEvaluateRequest,
    GuardrailApiEvaluation,
    GuardrailApiEventDisposition,
    GuardrailApiEvents,
    GuardrailApiGuardrail,
)

GUARDRAILS = ApiFamily(
    name=namespace,
    resource=SAMKinds.GUARDRAIL.value,
    urlconf="smarter.apps.guardrail.api.v1.urls",
    description="The {plural}' REST reads, and their dry run.",
)
"""The Guardrails' family."""


def guardrail_paths() -> dict[str, OpenApiPathItem]:
    """
    The Guardrails' REST reads, and the dry run of a Guardrail, relative to the server's ``/api/v1``.

    :returns: The paths, e.g. ``{"/guardrails/": ...}``.
    :rtype: dict[str, OpenApiPathItem]
    """
    family = GUARDRAILS
    guardrail_id = id_or_hashed_id(family.resource)
    events = rest_read(
        family.operation_id("events"),
        f"{family.a_capitalized}'s events",
        f"The latest 100 events of {family.a} that the user owns, newest first: what it did to prompts.",
        family.tag,
        GuardrailApiEvents.__name__,
        many=False,
        parameters=[
            guardrail_id,
            OpenApiParameter(
                name="reviewed",
                in_="query",
                description="Only the events that a person has reviewed (true), or has not (false).",
                schema_={"type": "string", "enum": ["true", "false"]},
            ),
            OpenApiParameter(
                name="disposition",
                in_="query",
                description="Only the events with this disposition, e.g. blocked.",
                schema_={"type": "string", "enum": list(get_args(GuardrailApiEventDisposition))},
            ),
        ],
        note=READ_PERMISSION,
    )
    evaluate = OpenApiOperation(
        operationId=family.operation_id("evaluate"),
        summary=f"Dry-run {family.a}",
        description=f"Run {family.a} on a text, as the user's message (input) or the LLM's reply (output), and "
        f"return what it would do. It records no events. {READ_PERMISSION}",
        tags=[family.tag],
        parameters=[guardrail_id],
        requestBody=json_body(GuardrailApiEvaluateRequest.__name__),
        responses={
            "200": json_response("The dry run's result.", GuardrailApiEvaluation.__name__),
            "default": json_response(
                f"An error, e.g. 400 for an invalid request, or 404 for {family.a} that the user may not read.",
                RestApiErrorResponse.__name__,
            ),
        },
    )
    return {
        family.path(): OpenApiPathItem(
            get=rest_read(
                family.operation_id("list"),
                f"List {family.plural}",
                f"The {family.plural} that the user may read, by priority and name.",
                family.tag,
                GuardrailApiGuardrail.__name__,
                many=True,
                parameters=[],
                note=READ_PERMISSION,
            )
        ),
        family.path("{id}/"): OpenApiPathItem(
            get=rest_read(
                family.operation_id("retrieve"),
                family.a_capitalized,
                f"{family.a_capitalized} that the user may read.",
                family.tag,
                GuardrailApiGuardrail.__name__,
                many=False,
                parameters=[guardrail_id],
                note=READ_PERMISSION,
            )
        ),
        family.path("{id}/evaluate/"): OpenApiPathItem(post=evaluate),
        family.path("{id}/events/"): OpenApiPathItem(get=events),
    }


__all__ = ["GUARDRAILS", "guardrail_paths"]
