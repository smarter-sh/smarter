"""Smarter API Manifest - Guardrail.spec."""

import os
from typing import ClassVar, Optional

from pydantic import Field, field_validator, model_validator

from smarter.apps.guardrail.manifest.models.guardrail.const import MANIFEST_KIND
from smarter.apps.guardrail.models.guardail import (
    GuardrailAction,
    GuardrailCategory,
    GuardrailType,
    MatchStrategy,
)

# from smarter.common.conf import settings_defaults
from smarter.lib.manifest.models import AbstractSAMSpecBase

filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"
SMARTER_PLUGIN_MAX_SYSTEM_ROLE_LENGTH = 2048


class SAMGuardrailSpecConfig(AbstractSAMSpecBase):
    """Smarter API Guardrail Manifest Guardrail.spec.config."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER + ".configuration"
    # --- classification ---
    guardrail_type: GuardrailType = Field(
        ...,
        description="Whether this guardrail evaluates input, output, or both.",
    )
    category: GuardrailCategory = Field(
        ...,
        description="The risk category this guardrail addresses.",
    )

    # --- detection logic ---
    match_strategy: MatchStrategy = Field(
        ...,
        description="Detection mechanism used to evaluate content against this guardrail.",
    )
    pattern: Optional[str] = Field(
        default="",
        description=("Regex, keyword list (newline/comma), or judge prompt template, " "depending on match_strategy."),
    )
    config: Optional[dict] = Field(
        default_factory=dict,
        description=(
            "Strategy-specific parameters: similarity_threshold, model_id, " "temperature, few-shot examples, etc."
        ),
    )

    # --- response behavior ---
    action: GuardrailAction = Field(
        ...,
        description="Action taken when this guardrail triggers.",
    )
    severity: int = Field(
        default=1,
        ge=1,
        le=5,
        description="1=low ... 5=critical; drives alerting/escalation thresholds.",
    )
    confidence_threshold: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Minimum confidence score to trigger action, for model/semantic strategies.",
    )

    # --- lifecycle ---
    is_active: bool = Field(
        default=True,
        description="Whether this guardrail is currently in effect.",
    )
    is_blocking: bool = Field(
        default=False,
        description="If False, action runs in shadow/log-only mode regardless of `action`.",
    )
    priority: int = Field(
        default=100,
        ge=0,
        description="Execution order when multiple guardrails match; lower runs first.",
    )

    # --- versioning / provenance ---
    fallback_message: Optional[str] = Field(
        default="",
        description="User-facing message returned when action=BLOCK.",
    )

    # --- cross-field validation, mirrors the Django model's intended clean() logic ---
    @field_validator("config")
    @classmethod
    def validate_config_shape(cls, v: dict, info) -> dict:
        strategy = info.data.get("match_strategy")
        if strategy == MatchStrategy.SEMANTIC and "similarity_threshold" not in v:
            raise ValueError("config.similarity_threshold is required when match_strategy=semantic")
        if strategy == MatchStrategy.MODEL and "model_id" not in v:
            raise ValueError("config.model_id is required when match_strategy=model")
        if strategy == MatchStrategy.LLM_JUDGE and "judge_prompt" not in v:
            raise ValueError("config.judge_prompt is required when match_strategy=llm_judge")
        return v

    @model_validator(mode="after")
    def validate_confidence_threshold_applicability(self) -> "SAMGuardrailSpecConfig":
        needs_threshold = self.match_strategy in (
            MatchStrategy.SEMANTIC,
            MatchStrategy.MODEL,
            MatchStrategy.LLM_JUDGE,
        )
        if needs_threshold and self.confidence_threshold is None:
            raise ValueError(f"confidence_threshold is required when match_strategy={self.match_strategy}")
        return self

    @model_validator(mode="after")
    def validate_fallback_message_on_block(self) -> "SAMGuardrailSpecConfig":
        if self.action == GuardrailAction.BLOCK and not self.fallback_message:
            raise ValueError("fallback_message is required when action=block")
        return self


class SAMGuardrailSpec(AbstractSAMSpecBase):
    """Smarter API Guardrail Manifest Guardrail.spec."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    config: SAMGuardrailSpecConfig = Field(
        ..., description=f"{class_identifier}.config[object]. The configuration for the {MANIFEST_KIND}."
    )
