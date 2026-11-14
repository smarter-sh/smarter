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
    from smarter.apps.orchestrator.models import (
        OrchestrationRun,
        OrchestrationStep,
        Orchestrator,
    )

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
    detail_url: Optional[str] = Field(
        None,
        description="The url of the Orchestrator's detail in the web console: its manifest, the resources that it "
        "uses, and those that use it.",
    )
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
        from smarter.apps.dashboard.resource_detail import resource_detail_url
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
            detail_url=resource_detail_url(MANIFEST_KIND, row.record_locator),
            strategy=row.strategy,  # type: ignore[arg-type]
            max_iterations=row.max_iterations,
            is_active=row.is_active,
            llmclients=[llmclient.pk for llmclient in row.llmclients.all()],
        )


OrchestratorApiRunStatus = Literal["pending", "running", "succeeded", "failed", "cancelled", "max_iterations_exceeded"]
"""An OrchestrationRun's ``status``: the choices of ``OrchestrationRunStatus``."""

OrchestratorApiStepStatus = Literal["succeeded", "failed", "skipped"]
"""An OrchestrationStep's ``status``: the choices of ``OrchestrationStep.StepStatus``."""

OrchestratorApiHarnessRole = Literal["planner", "executor", "critic", "router", "summarizer", "tool_caller"]
"""A harness's ``role``: the choices of ``OrchestratorHarness.Role``."""


class OrchestratorApiRunRequest(AccountApiModel):
    """The body of a request that starts a run: what the run is to achieve."""

    objective: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="What the run is to achieve, e.g. Prepare the board pack for Q4 2025. Every step receives it.",
    )


class OrchestratorApiStep(AccountApiModel):
    """
    One step of a run: one call of a harness LLMClient, as its owner.

    Its messages, tokens and charges are those of its Prompt session, which the LLMClient's owner may read.
    """

    sequence: int = Field(..., ge=1, description="OrchestrationStep.sequence: the step's position in the run.")
    llmclient: str = Field(..., description="The harness LLMClient's name.")
    account_number: str = Field(..., description="The account that the LLMClient belongs to.")
    role: OrchestratorApiHarnessRole = Field(..., description="The harness's role.")
    status: OrchestratorApiStepStatus = Field(..., description="OrchestrationStep.status.")
    error_message: Optional[str] = Field(None, description="Why the step failed, if it did.")
    created_at: Optional[datetime] = Field(None, description="When the step ended.")

    @classmethod
    def from_model(cls, row: "OrchestrationStep") -> "OrchestratorApiStep":
        """
        The contract's model of a step.

        :param row: The row, whose harness, LLMClient and LLMClient's account should be fetched with it.
        :returns: The model.
        """
        llmclient = row.harness.llmclient
        return cls(
            sequence=row.sequence,
            llmclient=llmclient.name,
            account_number=llmclient.user_profile.account.account_number,  # type: ignore[union-attr]
            role=row.harness.role,  # type: ignore[arg-type]
            status=row.status,  # type: ignore[arg-type]
            error_message=row.error_message,
            created_at=row.created_at,
        )


class OrchestratorApiRun(AccountApiModel):
    """
    A run of an Orchestrator: an attempt at an objective, its status, its steps and its result (ADR-037).

    A run starts ``pending``, and a Celery task executes it, so a client polls it until its status is final:
    ``succeeded``, ``failed``, ``cancelled`` or ``max_iterations_exceeded``.
    """

    id: int = Field(..., description="The run's primary key.")
    orchestrator: int = Field(..., description="The Orchestrator's id.")
    objective: str = Field(..., description="OrchestrationRun.objective.")
    status: OrchestratorApiRunStatus = Field(..., description="OrchestrationRun.status.")
    result: Optional[str] = Field(None, description="The run's result: its last step's text, once it succeeded.")
    error_message: Optional[str] = Field(None, description="Why the run failed, or stopped, if it did.")
    iteration_count: int = Field(..., ge=0, description="How many steps the run has taken.")
    started_by: Optional[AccountApiUserProfile] = Field(None, description="Who started the run.")
    created_at: Optional[datetime] = Field(None, description="When the run was requested.")
    started_at: Optional[datetime] = Field(None, description="When its execution began.")
    completed_at: Optional[datetime] = Field(None, description="When it ended.")
    steps: list[OrchestratorApiStep] = Field(default_factory=list, description="Its steps, in order.")

    @classmethod
    def from_model(cls, row: "OrchestrationRun") -> "OrchestratorApiRun":
        """
        The contract's model of a run, with its steps.

        :param row: The row.
        :returns: The model.
        """
        result_text = None
        if isinstance(row.result, dict):
            result_text = row.result.get("text")
        started_by = None
        if row.started_by is not None:
            started_by = AccountApiUserProfile.from_model(row.started_by)
        steps = row.steps.select_related("harness__llmclient__user_profile__account").order_by("sequence")  # type: ignore[attr-defined]
        return cls(
            id=row.pk,
            orchestrator=row.orchestrator_id,  # type: ignore[attr-defined]
            objective=row.objective,
            status=row.status,  # type: ignore[arg-type]
            result=result_text,
            error_message=row.error_message,
            iteration_count=row.iteration_count,
            started_by=started_by,
            created_at=row.created_at,
            started_at=row.started_at,
            completed_at=row.completed_at,
            steps=[OrchestratorApiStep.from_model(step) for step in steps],
        )


ORCHESTRATOR_API_MODELS = (
    OrchestratorApiOrchestrator,
    OrchestratorApiRunRequest,
    OrchestratorApiRun,
    OrchestratorApiStep,
)
"""The models whose JSON Schemas the Smarter api's OpenAPI document includes."""

__all__ = [
    "ORCHESTRATOR_API_MODELS",
    "OrchestratorApiHarnessRole",
    "OrchestratorApiOrchestrator",
    "OrchestratorApiRun",
    "OrchestratorApiRunRequest",
    "OrchestratorApiRunStatus",
    "OrchestratorApiStep",
    "OrchestratorApiStepStatus",
    "OrchestratorApiStrategy",
]
