"""All models for the Orchestrator app."""

from django.db import models

from smarter.lib import logging
from smarter.lib.django.models import TimestampedModel
from smarter.lib.django.waffle.switches import SmarterWaffleSwitches

from .orchestrator import Orchestrator

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.ORCHESTRATOR])


class OrchestrationRunStatus(models.TextChoices):
    """Lifecycle status of an OrchestrationRun."""

    PENDING = "pending", "Pending"
    RUNNING = "running", "Running"
    SUCCEEDED = "succeeded", "Succeeded"
    FAILED = "failed", "Failed"
    CANCELLED = "cancelled", "Cancelled"
    MAX_ITERATIONS_EXCEEDED = "max_iterations_exceeded", "Max Iterations Exceeded"


class OrchestrationRun(TimestampedModel):
    """A single execution of an Orchestrator against a concrete objective.

    The audit/trace root: one row per attempt to achieve an objective,
    independent of how many LLMClient invocations (OrchestrationSteps) it
    took to get there.
    """

    orchestrator = models.ForeignKey(
        Orchestrator,
        on_delete=models.CASCADE,
        related_name="runs",
    )
    objective = models.TextField(
        help_text="Natural-language statement of the agentic objective for this run.",
    )
    status = models.CharField(
        max_length=32,
        choices=OrchestrationRunStatus.choices,
        default=OrchestrationRunStatus.PENDING,
    )
    result = models.JSONField(
        null=True,
        blank=True,
        help_text="Final output/artifact produced by the run, if any.",
    )
    error_message = models.TextField(null=True, blank=True)
    iteration_count = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Orchestration Run"
        verbose_name_plural = "Orchestration Runs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["orchestrator", "status"]),
        ]

    def __str__(self) -> str:
        return f"Run {self.pk} · {self.orchestrator.name} · {self.status}"


__all__ = ["OrchestrationRun"]
