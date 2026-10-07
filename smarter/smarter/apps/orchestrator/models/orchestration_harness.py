"""All models for the Orchestrator app."""

from django.db import models

from smarter.apps.llmclient.models import LLMClient
from smarter.lib import logging
from smarter.lib.django.models import TimestampedModel
from smarter.lib.django.waffle.switches import SmarterWaffleSwitches

from .orchestrator import Orchestrator

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.ORCHESTRATOR])


class OrchestratorHarness(TimestampedModel):
    """Through model: membership of an LLMClient (Harness) within an Orchestrator.

    Carries metadata specific to *this* LLMClient's participation in *this*
    Orchestrator — role, execution order, active flag, per-membership config
    overrides — without polluting the LLMClient model itself, since a single
    LLMClient can belong to multiple Orchestrators with a different role in
    each.
    """

    class Role(models.TextChoices):
        PLANNER = "planner", "Planner"
        EXECUTOR = "executor", "Executor"
        CRITIC = "critic", "Critic"
        ROUTER = "router", "Router"
        SUMMARIZER = "summarizer", "Summarizer"
        TOOL_CALLER = "tool_caller", "Tool Caller"

    orchestrator = models.ForeignKey(
        Orchestrator,
        on_delete=models.CASCADE,
        related_name="harnesses",
    )
    llmclient = models.ForeignKey(
        LLMClient,
        on_delete=models.CASCADE,
        related_name="orchestrator_memberships",
    )
    role = models.CharField(max_length=32, choices=Role.choices, default=Role.EXECUTOR)
    execution_order = models.PositiveIntegerField(
        default=0,
        help_text="Relative ordering for sequential/supervisor strategies. Ignored for parallel/voting.",
    )
    is_active = models.BooleanField(default=True)
    config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Per-membership overrides (e.g. temperature, system prompt fragment, tool allowlist).",
    )

    class Meta:
        verbose_name = "Orchestrator Harness"
        verbose_name_plural = "Orchestrator Harnesses"
        unique_together = ("orchestrator", "llmclient")
        ordering = ["execution_order"]

    def __str__(self) -> str:
        return f"{self.orchestrator.name} · {self.llmclient} ({self.role})"
