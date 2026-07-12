"""Guardrail model."""

from django.db import models

from smarter.apps.account.models import (
    MetaDataWithOwnershipModel,
)
from smarter.lib import logging
from smarter.lib.django.waffle.switches import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.GUARDRAIL_LOGGING])


class GuardrailType(models.TextChoices):
    INPUT = "input", "Input (pre-prompt)"
    OUTPUT = "output", "Output (post-completion)"
    BOTH = "both", "Input & Output"


class GuardrailCategory(models.TextChoices):
    PII = "pii", "PII / Sensitive Data"
    JAILBREAK = "jailbreak", "Jailbreak / Prompt Injection"
    TOXICITY = "toxicity", "Toxicity / Harassment"
    HALLUCINATION = "hallucination", "Hallucination / Factuality"
    OFF_TOPIC = "off_topic", "Off-topic / Scope Drift"
    COMPLIANCE = "compliance", "Regulatory / Compliance"
    CUSTOM = "custom", "Custom"


class MatchStrategy(models.TextChoices):
    REGEX = "regex", "Regex"
    KEYWORD = "keyword", "Keyword List"
    SEMANTIC = "semantic", "Semantic / Embedding Similarity"
    MODEL = "model", "Classifier Model Call"
    LLM_JUDGE = "llm_judge", "LLM-as-Judge"


class GuardrailAction(models.TextChoices):
    ALLOW = "allow", "Allow (log only)"
    FLAG = "flag", "Flag for Review"
    REDACT = "redact", "Redact & Continue"
    TRANSFORM = "transform", "Transform/Rewrite"
    BLOCK = "block", "Block Request"
    ESCALATE = "escalate", "Escalate to Human"


class Guardrail(MetaDataWithOwnershipModel):
    """Implements the Guardrail model."""

    # pylint: disable=C0115
    class Meta:
        verbose_name_plural = "Guardrails"
        unique_together = ("user_profile", "name")

    # --- classification ---
    guardrail_type = models.CharField(max_length=16, choices=GuardrailType.choices)
    category = models.CharField(max_length=32, choices=GuardrailCategory.choices)

    # --- detection logic ---
    match_strategy = models.CharField(max_length=16, choices=MatchStrategy.choices)
    pattern = models.TextField(
        blank=True,
        help_text="Regex, keyword list (newline/comma), or judge prompt template depending on match_strategy.",
    )
    config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Strategy-specific params: similarity_threshold, model_id, temperature, few-shot examples, etc.",
    )

    # --- response behavior ---
    action = models.CharField(max_length=16, choices=GuardrailAction.choices)
    severity = models.PositiveSmallIntegerField(
        default=1,
        help_text="1=low ... 5=critical; drives alerting/escalation thresholds.",
    )
    confidence_threshold = models.FloatField(
        null=True,
        blank=True,
        help_text="Minimum confidence score to trigger action, for model/semantic strategies.",
    )

    # --- lifecycle ---
    is_active = models.BooleanField(default=True)
    is_blocking = models.BooleanField(
        default=False,
        help_text="If False, action runs in shadow/log-only mode regardless of `action`.",
    )
    priority = models.PositiveSmallIntegerField(
        default=100,
        help_text="Execution order when multiple guardrails match; lower runs first.",
    )

    # --- versioning / provenance ---
    fallback_message = models.TextField(
        blank=True,
        help_text="User-facing message returned when action=BLOCK.",
    )


__all__ = ["Guardrail", "GuardrailType", "GuardrailCategory", "MatchStrategy", "GuardrailAction"]
