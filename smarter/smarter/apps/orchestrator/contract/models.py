"""
Pydantic models of the Orchestrators' REST api responses (``/api/v1/orchestrators/``).

:class:`OrchestratorApiOrchestrator` is an Orchestrator, as :class:`smarter.apps.orchestrator.serializers.OrchestratorSerializer` returned it
before the api was modeled, which clients already read. One value changed: its ``canDelete`` is
computed for the requesting user. The serializer was called without a request, so it was always
false.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Literal, Optional

from pydantic import Field

from smarter.apps.account.contract.models import (
    AccountApiModel,
    AccountApiUserProfile,
    MetaDataApiAnnotations,
)
from smarter.apps.account.serializers import user_can_delete

if TYPE_CHECKING:
    from smarter.apps.orchestrator.models import Orchestrator

OrchestratorApiStrategy = Literal["sequential", "parallel", "supervisor", "router", "voting", "debate"]
"""An Orchestrator's ``strategy``: the choices of ``Orchestrator.strategy``."""


class OrchestratorApiOrchestrator(AccountApiModel):
    """An Orchestrator, a multi-agent workflow over LLMClients: a :class:`smarter.apps.orchestrator.models.Orchestrator`."""

    id: int = Field(..., description="The row's primary key.")
    hashed_id: str = Field(..., description="The Orchestrator's hashed id, e.g. rMTAwMDAwMQx, which its urls use.")
    created_at: Optional[datetime] = Field(None, description="TimestampedModel.created_at.")
    updated_at: Optional[datetime] = Field(None, description="TimestampedModel.updated_at.")
    name: str = Field(..., description="MetaDataModel.name, in snake_case.")
    description: Optional[str] = Field(None, description="MetaDataModel.description.")
    version: Optional[str] = Field(None, description="MetaDataModel.version, e.g. 1.0.0.")
    tags: list[str] = Field(default_factory=list, description="MetaDataModel.tags, by name.")
    annotations: MetaDataApiAnnotations = Field(None, description="MetaDataModel.annotations.")
    user_profile: AccountApiUserProfile = Field(..., description="The Orchestrator's owner.")
    can_delete: bool = Field(
        ...,
        description="Whether the requesting user may delete the Orchestrator now: they own it, and nothing uses it.",
    )
    manifest_url: str = Field(..., description="The url of the Orchestrator's manifest in the web console.")
    strategy: OrchestratorApiStrategy = Field(..., description="Orchestrator.strategy: how its LLMClients collaborate.")
    max_iterations: int = Field(..., ge=0, description="Orchestrator.max_iterations.")
    is_active: bool = Field(..., description="Orchestrator.is_active.")
    llmclients: list[int] = Field(default_factory=list, description="Orchestrator.llmclients: the LLMClients' ids.")

    @classmethod
    def from_model(cls, row: "Orchestrator", user: object = None) -> "OrchestratorApiOrchestrator":
        """
        The contract's model of an Orchestrator.

        :param row: The row, whose ``user_profile`` should be fetched with it.
        :type row: smarter.apps.orchestrator.models.Orchestrator
        :param user: The requesting user, for ``can_delete``. None may delete nothing.
        :type user: object
        :returns: The model.
        :rtype: OrchestratorApiOrchestrator
        """
        # pylint: disable=import-outside-toplevel
        from smarter.apps.orchestrator.manifest.models.orchestrator.const import (
            MANIFEST_KIND,
        )
        from smarter.apps.orchestrator.serializers import OrchestratorSerializer

        return cls(
            id=row.pk,
            hashed_id=row.hashed_id,
            created_at=row.created_at,
            updated_at=row.updated_at,
            name=row.name,
            description=row.description,
            version=row.version,
            tags=[tag.name for tag in row.tags.all()],
            annotations=row.annotations,
            user_profile=AccountApiUserProfile.from_model(row.user_profile),
            can_delete=user_can_delete(row, MANIFEST_KIND, user),
            manifest_url=OrchestratorSerializer().get_manifest_url(row),
            strategy=row.strategy,  # type: ignore[arg-type]
            max_iterations=row.max_iterations,
            is_active=row.is_active,
            llmclients=[llmclient.pk for llmclient in row.llmclients.all()],
        )


ORCHESTRATOR_API_MODELS = (OrchestratorApiOrchestrator,)
"""The models whose JSON Schemas the Smarter api's OpenAPI document includes."""

__all__ = ["ORCHESTRATOR_API_MODELS", "OrchestratorApiOrchestrator", "OrchestratorApiStrategy"]
