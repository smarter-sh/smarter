"""The Orchestrators' REST reads, under ``/api/v1/orchestrators/``, and their runs.

The reads are for superusers. Any user may start a run of an Orchestrator that they may read, and read the runs that
they started (ADR-037).
"""

from smarter_types import SAMKinds

from smarter.apps.api.v1.contract.models import OpenApiPathItem
from smarter.apps.api.v1.contract.openapi.builders import (
    API_KEY_ONLY,
    ApiFamily,
    id_or_hashed_id,
    integer_id,
    json_body,
    merge_paths,
    rest_operation,
    rest_read,
    superuser_list_and_retrieve,
)
from smarter.apps.orchestrator.const import namespace
from smarter.apps.orchestrator.contract.models import (
    OrchestratorApiOrchestrator,
    OrchestratorApiRun,
    OrchestratorApiRunRequest,
)

ORCHESTRATORS = ApiFamily(
    name=namespace,
    resource=SAMKinds.ORCHESTRATOR.value,
    urlconf="smarter.apps.orchestrator.api.v1.urls",
    description="The {plural}' REST reads, for superusers, and their runs, for any user who may read them.",
)
"""The Orchestrators' family."""


def orchestrator_paths() -> dict[str, OpenApiPathItem]:
    """
    The Orchestrators' REST reads, relative to the server's ``/api/v1``.

    Only superusers may call them.

    :returns: The paths, e.g. ``{"/orchestrators/": ...}``.
    :rtype: dict[str, OpenApiPathItem]
    """
    family = ORCHESTRATORS
    orchestrator_id = id_or_hashed_id(family.resource)
    run_paths = {
        family.path("{id}/runs/"): OpenApiPathItem(
            post=rest_operation(
                family.operation_id("run"),
                f"Start a run of {family.a}",
                f"Start a run of {family.a} that the user may read, toward an objective. It answers 202 with the run, "
                "pending, which the platform then executes, one step at a time: poll the run until its status is "
                "succeeded, failed or max_iterations_exceeded. Each step calls a harness LLMClient as its owner, and "
                "is charged to it. The user must be able to read every harness LLMClient, or the run is refused "
                f"with 403. A strategy that can't run yet is refused with 400. {API_KEY_ONLY}",
                family.tag,
                OrchestratorApiRun.__name__,
                parameters=[orchestrator_id],
                status="202",
                request_body=json_body(OrchestratorApiRunRequest.__name__),
            )
        ),
        family.path("{id}/runs/{run_id}/"): OpenApiPathItem(
            get=rest_read(
                family.operation_id("run_retrieve"),
                f"A run of {family.a}",
                f"A run of {family.a}, with its steps and, once it succeeded, its result. Only the user who started "
                "it, or a superuser, may read it: anyone else gets 404.",
                family.tag,
                OrchestratorApiRun.__name__,
                many=False,
                parameters=[orchestrator_id, integer_id("run_id", "The run's id.")],
                note=API_KEY_ONLY,
            )
        ),
    }
    return merge_paths(superuser_list_and_retrieve(family, OrchestratorApiOrchestrator.__name__), run_paths)


__all__ = ["ORCHESTRATORS", "orchestrator_paths"]
