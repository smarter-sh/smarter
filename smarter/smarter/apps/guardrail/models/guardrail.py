"""
Guardrail models.

- :class:`Guardrail`: a protection of LLM prompts, configured by a Guardrail manifest.
- :class:`GuardrailEvent`: a record of a guardrail that triggered, or failed to run, for
  review and reporting.

.. note::

    **Experimental.** The Guardrail was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from typing import Any

from django.db import models

from smarter.apps.account.models import (
    MetaDataWithOwnershipModel,
)
from smarter.apps.guardrail.manifest.models.guardrail.const import (
    DEFAULT_MESSAGE,
    DEFAULT_PRIORITY,
    DEFAULT_REPLACEMENT,
    DEFAULT_SEVERITY,
)
from smarter.lib import logging
from smarter.lib.django.models import TimestampedModel
from smarter.lib.django.waffle.switches import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.GUARDRAIL_LOGGING])


class GuardrailStage(models.TextChoices):
    """When a guardrail runs."""

    INPUT = "input", "Input (the user's message)"
    OUTPUT = "output", "Output (the LLM's reply)"
    BOTH = "both", "Input & Output"


class GuardrailCategory(models.TextChoices):
    """The risk that a guardrail addresses."""

    PII = "pii", "PII / Personal Data"
    SECRETS = "secrets", "Secrets / Credentials"
    PROMPT_INJECTION = "prompt_injection", "Prompt Injection"
    JAILBREAK = "jailbreak", "Jailbreak"
    TOXICITY = "toxicity", "Toxicity / Harassment"
    SELF_HARM = "self_harm", "Self-harm"
    HALLUCINATION = "hallucination", "Hallucination / Factuality"
    OFF_TOPIC = "off_topic", "Off-topic / Scope"
    COMPLIANCE = "compliance", "Regulatory / Compliance"
    FORMATTING = "formatting", "Formatting"
    CUSTOM = "custom", "Custom"


class GuardrailStrategy(models.TextChoices):
    """How a guardrail detects what it guards against."""

    REGEX = "regex", "Regular Expression"
    KEYWORD = "keyword", "Keyword List"
    DETECTOR = "detector", "Built-in Detectors"
    SEMANTIC = "semantic", "Semantic Similarity"
    MODERATION = "moderation", "Moderation Model"
    LLM_JUDGE = "llm_judge", "LLM-as-Judge"


class GuardrailAction(models.TextChoices):
    """What a guardrail does when it triggers."""

    LOG = "log", "Log"
    FLAG = "flag", "Flag for Review"
    REDACT = "redact", "Redact & Continue"
    TRANSFORM = "transform", "Transform & Continue"
    BLOCK = "block", "Block"
    ESCALATE = "escalate", "Escalate to Human Review"


class GuardrailMode(models.TextChoices):
    """Whether a guardrail acts, or only records what it would do."""

    ENFORCE = "enforce", "Enforce"
    MONITOR = "monitor", "Monitor"


class GuardrailDisposition(models.TextChoices):
    """What a guardrail did, as recorded in a :class:`GuardrailEvent`."""

    LOGGED = "logged", "Logged"
    FLAGGED = "flagged", "Flagged"
    REDACTED = "redacted", "Redacted"
    TRANSFORMED = "transformed", "Transformed"
    BLOCKED = "blocked", "Blocked"
    ESCALATED = "escalated", "Escalated"
    MONITORED = "monitored", "Monitored (would have acted)"
    ERROR = "error", "Error"


class Guardrail(MetaDataWithOwnershipModel):
    """
    A guardrail: a protection of LLM prompts.

    The fields are set by the Guardrail manifest's ``spec.config``. ``config`` holds the
    fields of the guardrail's strategy, with their manifest names, e.g. ``keywords``,
    ``detectors`` and ``judgePrompt``.
    """

    # pylint: disable=C0115
    class Meta:
        verbose_name_plural = "Guardrails"
        unique_together = ("user_profile", "name")

    # --- when and what ---
    stage = models.CharField(max_length=16, choices=GuardrailStage.choices)
    category = models.CharField(max_length=32, choices=GuardrailCategory.choices, default=GuardrailCategory.CUSTOM)

    # --- detection ---
    strategy = models.CharField(max_length=16, choices=GuardrailStrategy.choices)
    pattern = models.TextField(blank=True, null=True, help_text="The regex strategy's regular expression.")
    config = models.JSONField(
        default=dict,
        blank=True,
        null=True,
        help_text="The strategy's other fields: flags, keywords, detectors, referenceTexts, categories, judgePrompt, etc.",
    )
    threshold = models.FloatField(
        null=True,
        blank=True,
        help_text="The minimum confidence at which the semantic, moderation and llm_judge strategies trigger.",
    )

    # --- response ---
    action = models.CharField(max_length=16, choices=GuardrailAction.choices)
    replacement = models.TextField(
        blank=True, null=True, help_text="What redact and transform replace each match with."
    )
    message = models.TextField(blank=True, null=True, help_text="What block returns to the user.")
    severity = models.PositiveSmallIntegerField(default=DEFAULT_SEVERITY, help_text="1 (low) to 5 (critical).")

    # --- lifecycle ---
    mode = models.CharField(max_length=16, choices=GuardrailMode.choices, default=GuardrailMode.ENFORCE)
    fail_closed = models.BooleanField(
        default=False, help_text="Block if the check itself fails, e.g. because the LLM provider is unavailable."
    )
    priority = models.PositiveSmallIntegerField(
        default=DEFAULT_PRIORITY, help_text="The order in which guardrails run; lower runs first."
    )
    is_active = models.BooleanField(default=True)

    @property
    def settings(self) -> dict[str, Any]:
        """The strategy's fields, from ``config``."""
        return self.config if isinstance(self.config, dict) else {}

    @property
    def effective_replacement(self) -> str:
        """What redact and transform replace each match with."""
        return DEFAULT_REPLACEMENT if self.replacement is None else self.replacement

    @property
    def effective_message(self) -> str:
        """What block returns to the user."""
        return self.message or DEFAULT_MESSAGE

    def runs_on(self, stage: str) -> bool:
        """Return whether the guardrail runs on ``stage``, input or output."""
        return self.stage in (stage, GuardrailStage.BOTH)


class GuardrailEvent(TimestampedModel):
    """
    A guardrail that triggered, or failed to run, on a prompt.

    Events are the audit trail of guardrails: flagged and escalated events await review in the
    Smarter admin. For the pii and secrets categories, ``excerpt`` is masked, so that the
    event does not store the personal data or secret that the guardrail detected.
    """

    # pylint: disable=C0115
    class Meta:
        verbose_name_plural = "Guardrail Events"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["disposition", "reviewed"])]

    guardrail = models.ForeignKey(Guardrail, on_delete=models.SET_NULL, null=True, blank=True, related_name="events")
    guardrail_name = models.CharField(max_length=255, help_text="The guardrail's name, in case it is deleted.")
    llmclient = models.ForeignKey(
        "llmclient.LLMClient",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="guardrail_events",
    )
    session_key = models.CharField(max_length=255, blank=True, null=True, help_text="The prompt's session key.")
    stage = models.CharField(max_length=16, choices=GuardrailStage.choices)
    category = models.CharField(max_length=32, choices=GuardrailCategory.choices)
    strategy = models.CharField(max_length=16, choices=GuardrailStrategy.choices)
    action = models.CharField(max_length=16, choices=GuardrailAction.choices)
    mode = models.CharField(max_length=16, choices=GuardrailMode.choices)
    disposition = models.CharField(max_length=16, choices=GuardrailDisposition.choices)
    severity = models.PositiveSmallIntegerField(default=DEFAULT_SEVERITY)
    confidence = models.FloatField(null=True, blank=True)
    excerpt = models.TextField(
        blank=True, null=True, help_text="What triggered the guardrail, masked for pii and secrets."
    )
    rationale = models.TextField(blank=True, null=True)
    error = models.TextField(blank=True, null=True, help_text="Why the guardrail failed to run, if it did.")
    reviewed = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"{self.guardrail_name} {self.stage} {self.disposition}"


__all__ = [
    "Guardrail",
    "GuardrailAction",
    "GuardrailCategory",
    "GuardrailDisposition",
    "GuardrailEvent",
    "GuardrailMode",
    "GuardrailStage",
    "GuardrailStrategy",
]
