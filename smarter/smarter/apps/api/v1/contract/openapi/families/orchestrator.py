"""The Orchestrators' REST reads, under ``/api/v1/orchestrators/``.

For superusers.
"""

from smarter_types import SAMKinds

from smarter.apps.api.v1.contract.models import OpenApiPathItem
from smarter.apps.api.v1.contract.openapi.builders import (
    ApiFamily,
    superuser_list_and_retrieve,
)
from smarter.apps.orchestrator.const import namespace
from smarter.apps.orchestrator.contract.models import OrchestratorApiOrchestrator

ORCHESTRATORS = ApiFamily(
    name=namespace,
    resource=SAMKinds.ORCHESTRATOR.value,
    urlconf="smarter.apps.orchestrator.api.v1.urls",
    description="The {plural}' REST reads. For superusers.",
)
"""The Orchestrators' family."""


def orchestrator_paths() -> dict[str, OpenApiPathItem]:
    """
    The Orchestrators' REST reads, relative to the server's ``/api/v1``.

    Only superusers may call them.

    :returns: The paths, e.g. ``{"/orchestrators/": ...}``.
    :rtype: dict[str, OpenApiPathItem]
    """
    return superuser_list_and_retrieve(ORCHESTRATORS, OrchestratorApiOrchestrator.__name__)


__all__ = ["ORCHESTRATORS", "orchestrator_paths"]
