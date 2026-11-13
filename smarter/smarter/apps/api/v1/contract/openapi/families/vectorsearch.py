"""The Vectorsearches' REST reads, for superusers, and the run of a Vectorsearch, under ``/api/v1/vectorsearches/``."""

from smarter_types import SAMKinds

from smarter.apps.api.v1.contract.models import OpenApiPathItem, RestApiErrorResponse
from smarter.apps.api.v1.contract.openapi.builders import (
    READ_PERMISSION,
    ApiFamily,
    id_or_hashed_id,
    json_body,
    json_response,
    rest_operation,
    superuser_list_and_retrieve,
)
from smarter.apps.vectorsearch.const import namespace
from smarter.apps.vectorsearch.contract.models import (
    VectorsearchApiResults,
    VectorsearchApiRun,
    VectorsearchApiVectorsearch,
)

VECTORSEARCHES = ApiFamily(
    name=namespace,
    resource=SAMKinds.VECTORSEARCH.value,
    urlconf="smarter.apps.vectorsearch.api.v1.urls",
    description="The {plural}' REST reads, for superusers, and their runs, for any user who may read them.",
)
"""The Vectorsearches' family."""


def vectorsearch_paths() -> dict[str, OpenApiPathItem]:
    """
    The Vectorsearches' REST reads, and the run of a Vectorsearch, relative to the server's ``/api/v1``.

    Only superusers may read them. Any user who may read a Vectorsearch may run it.

    :returns: The paths, e.g. ``{"/vectorsearches/": ...}``.
    :rtype: dict[str, OpenApiPathItem]
    """
    family = VECTORSEARCHES
    resource = family.resource
    paths = superuser_list_and_retrieve(family, VectorsearchApiVectorsearch.__name__)
    run = rest_operation(
        family.operation_id("run"),
        f"Run {family.a}",
        f"Search the {resource}'s vectorstore with a query, and the {resource}'s own configuration: its "
        "search type, k, score threshold, mmr settings and metadata filter. Answers 400 when the "
        f"{resource} is disabled, and 402 when a budget forbids it. {READ_PERMISSION}",
        family.tag,
        VectorsearchApiResults.__name__,
        parameters=[id_or_hashed_id(resource)],
        request_body=json_body(
            VectorsearchApiRun.__name__,
            "The query, and optionally more metadata that every result must match.",
        ),
    )
    run.responses["402"] = json_response(
        f"Refused: a budget locks the {resource}, the user's profile or their account.",
        RestApiErrorResponse.__name__,
    )
    paths[family.path(f"{{id}}/{family.name}/")] = OpenApiPathItem(post=run)
    return paths


__all__ = ["VECTORSEARCHES", "vectorsearch_paths"]
