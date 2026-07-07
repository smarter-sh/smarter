"""All models for the Orchestrator app."""

from django.db import models

from smarter.apps.prompt.models import Prompt
from smarter.lib import logging
from smarter.lib.django.models import TimestampedModel
from smarter.lib.django.waffle.switches import SmarterWaffleSwitches

from .orchestration_harness import OrchestratorHarness
from .orchestration_run import OrchestrationRun

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.ORCHESTRATOR])


class OrchestrationStep(TimestampedModel):
    """A single LLMClient invocation within an OrchestrationRun.

    One row per turn/hop in the orchestration loop: which Harness ran, and
    where in the run's sequence. Input/output, token counts, and latency
    live on LLMClient's own execution-tracking model (`execution`) —
    this model just adds the run/sequence/orchestration-status context
    on top, so that data isn't duplicated in two places.
    """

    class StepStatus(models.TextChoices):
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        SKIPPED = "skipped", "Skipped"

    run = models.ForeignKey(
        OrchestrationRun,
        on_delete=models.CASCADE,
        related_name="steps",
    )
    harness = models.ForeignKey(
        OrchestratorHarness,
        on_delete=models.CASCADE,
        related_name="steps",
        help_text="Which Orchestrator/LLMClient membership executed this step.",
    )
    prompt = models.ForeignKey(
        Prompt,  # adjust to match LLMClient's actual execution-tracking model
        on_delete=models.CASCADE,
        related_name="orchestration_steps",
        help_text=(
            "The underlying LLMClient execution record (input/output, tokens, latency). "
            "OrchestrationStep only adds the run/sequence context on top of it."
        ),
    )
    sequence = models.PositiveIntegerField(
        help_text="Ordinal position of this step within the run.",
    )
    status = models.CharField(max_length=16, choices=StepStatus.choices, default=StepStatus.SUCCEEDED)
    error_message = models.TextField(
        null=True,
        blank=True,
        help_text="Orchestration-level failure reason (e.g. bad handoff), distinct from any error on the execution record itself.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Orchestration Step"
        verbose_name_plural = "Orchestration Steps"
        unique_together = ("run", "sequence")
        ordering = ["run", "sequence"]

    def __str__(self) -> str:
        return f"{self.id} · step {self.sequence} · {self.harness}"  # type: ignore


__all__ = ["OrchestrationStep"]
