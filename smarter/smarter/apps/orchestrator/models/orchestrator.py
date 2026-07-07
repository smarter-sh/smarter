"""All models for the Orchestrator app."""

from django.core.validators import MinValueValidator
from django.db import models

from smarter.apps.account.models import (
    MetaDataWithOwnershipModel,
)
from smarter.apps.llm_client.models import LLMClient
from smarter.lib import logging
from smarter.lib.django.waffle.switches import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.ORCHESTRATOR])


class OrchestrationStrategy(models.TextChoices):
    """Coordination pattern the Orchestrator applies across its member LLMClients."""

    SEQUENTIAL = "sequential", "Sequential"
    PARALLEL = "parallel", "Parallel"
    SUPERVISOR = "supervisor", "Supervisor / Worker"
    ROUTER = "router", "Router"
    VOTING = "voting", "Voting / Consensus"
    DEBATE = "debate", "Debate"


class Orchestrator(MetaDataWithOwnershipModel):
    """Implements the Orchestrator API model.

    Coordinates a collection of LLMClients (Harnesses) toward a shared
    agentic objective. An Orchestrator is a reusable configuration: which
    LLMClients participate, in what role, and in what order is tracked via
    OrchestratorHarness (the through model). Each concrete attempt at an
    objective is tracked as an OrchestrationRun, with per-invocation detail
    in OrchestrationStep.
    """

    strategy = models.CharField(
        max_length=32,
        choices=OrchestrationStrategy.choices,
        default=OrchestrationStrategy.SEQUENTIAL,
        help_text="Coordination pattern used to sequence/parallelize member LLMClients.",
    )
    llm_clients = models.ManyToManyField(
        LLMClient,
        through="OrchestratorHarness",
        related_name="orchestrators",
        help_text="LLMClients (Harnesses) available to this Orchestrator.",
    )
    max_iterations = models.PositiveIntegerField(
        default=10,
        validators=[MinValueValidator(1)],
        help_text="Upper bound on orchestration loop iterations; a runaway guard.",
    )
    is_active = models.BooleanField(default=True)

    # pylint: disable=C0115
    class Meta:
        verbose_name_plural = "Orchestrators"
        unique_together = ("user_profile", "name")

    def __str__(self) -> str:
        return f"{self.name}"


__all__ = [
    "OrchestrationStrategy",
    "Orchestrator",
]
