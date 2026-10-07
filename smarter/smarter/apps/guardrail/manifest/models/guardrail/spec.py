"""
Smarter API Manifest - Guardrail.spec.

A Guardrail protects the prompts of the LLMClients that list it in their ``spec.guardrails``.
It checks the user's message before it is sent to the LLM (``stage: input``), and/or the
LLM's reply before it is returned to the user (``stage: output``), with one detection
``strategy``, and takes an ``action`` when it triggers.

.. code-block:: yaml

    spec:
      config:
        stage: input               # input, output or both
        category: pii              # the risk it addresses, for reporting
        strategy: detector         # regex, keyword, detector, semantic, moderation or llm_judge
        detectors:                 # the detector strategy's built-in detectors
          - credit_card
          - us_ssn
        action: redact             # log, flag, redact, transform, block or escalate
        replacement: "[REDACTED]"  # what redact and transform replace matches with
        message: null              # what block returns to the user
        severity: 4                # 1 (low) to 5 (critical)
        mode: enforce              # enforce, or monitor to only record what it would do
        failClosed: false          # block if the check itself fails, e.g. an LLM provider error
        priority: 10               # lower runs first
        isActive: true

Each strategy has its own fields:

- ``regex``: ``pattern``, and optional ``flags``.
- ``keyword``: ``keywords``, and optional ``caseSensitive`` and ``wholeWord``.
- ``detector``: ``detectors``.
- ``semantic``: ``referenceTexts``, and optional ``threshold``, ``model`` and ``provider``.
- ``moderation``: optional ``categories``, ``threshold``, ``model`` and ``provider``.
- ``llm_judge``: ``judgePrompt``, with a ``{text}`` placeholder, and optional ``threshold``,
  ``model`` and ``provider``.

.. note::

    **Experimental.** The Guardrail was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

import os
import re
from typing import ClassVar, Optional

from pydantic import Field, field_validator, model_validator

from smarter.apps.guardrail.manifest.enum import (
    SAMGuardrailAction,
    SAMGuardrailCategory,
    SAMGuardrailDetector,
    SAMGuardrailMode,
    SAMGuardrailModerationCategory,
    SAMGuardrailStage,
    SAMGuardrailStrategy,
)
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.manifest.models import AbstractSAMSpecBase

from .const import (
    DEFAULT_PRIORITY,
    DEFAULT_SEVERITY,
    MANIFEST_KIND,
    MAX_JUDGE_PROMPT_LENGTH,
    MAX_KEYWORDS,
    MAX_MESSAGE_LENGTH,
    MAX_PATTERN_LENGTH,
    MAX_REFERENCE_TEXTS,
)

filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"

REGEX_FLAGS = ("IGNORECASE", "MULTILINE", "DOTALL")
"""The regex flags that ``flags`` may contain."""


def choice(value: Optional[str], choices: list[str], field: str) -> str:
    """Return a lower cased value, if it is one of ``choices``."""
    value = (value or "").strip().lower()
    if value not in choices:
        raise SAMValidationError(f"{field}: must be one of {choices}, not '{value}'.")
    return value


def compile_flags(flags: list[str]) -> int:
    """Return the combined ``re`` flags for a list of flag names."""
    combined = 0
    for flag in flags:
        combined |= getattr(re, flag)
    return combined


class SAMGuardrailSpecConfig(AbstractSAMSpecBase):
    """Smarter API Guardrail Manifest Guardrail.spec.config."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER + ".config"

    # --- when and what ---
    stage: str = Field(
        ...,
        description=f"{class_identifier}.stage[str]: when the guardrail runs. One of: {SAMGuardrailStage.all()}.",
    )
    category: str = Field(
        default=SAMGuardrailCategory.CUSTOM.value,
        description=f"{class_identifier}.category[str]: the risk the guardrail addresses. One of: {SAMGuardrailCategory.all()}.",
    )

    # --- detection ---
    strategy: str = Field(
        ...,
        description=f"{class_identifier}.strategy[str]: how the guardrail detects. One of: {SAMGuardrailStrategy.all()}.",
    )
    pattern: Optional[str] = Field(
        default=None,
        description=f"{class_identifier}.pattern[str]: the regex strategy's regular expression.",
    )
    flags: Optional[list[str]] = Field(
        default_factory=lambda: ["IGNORECASE"],
        description=f"{class_identifier}.flags[list]: the regex strategy's flags. Any of: {list(REGEX_FLAGS)}.",
    )
    keywords: Optional[list[str]] = Field(
        default_factory=list,
        description=f"{class_identifier}.keywords[list]: the keyword strategy's words and phrases.",
    )
    caseSensitive: bool = Field(
        default=False,
        description=f"{class_identifier}.caseSensitive[bool]: whether the keyword strategy is case sensitive.",
    )
    wholeWord: bool = Field(
        default=True,
        description=f"{class_identifier}.wholeWord[bool]: whether the keyword strategy matches whole words only.",
    )
    detectors: Optional[list[str]] = Field(
        default_factory=list,
        description=f"{class_identifier}.detectors[list]: the detector strategy's detectors. Any of: {SAMGuardrailDetector.all()}.",
    )
    referenceTexts: Optional[list[str]] = Field(
        default_factory=list,
        description=f"{class_identifier}.referenceTexts[list]: the semantic strategy's examples of what to detect.",
    )
    categories: Optional[list[str]] = Field(
        default_factory=list,
        description=(
            f"{class_identifier}.categories[list]: the moderation strategy's categories. Empty means all. "
            f"Any of: {SAMGuardrailModerationCategory.all()}."
        ),
    )
    judgePrompt: Optional[str] = Field(
        default=None,
        description=(
            f"{class_identifier}.judgePrompt[str]: the llm_judge strategy's prompt, with a {{text}} placeholder "
            "for the text to judge. Any other braces must be doubled, e.g. {{ and }}."
        ),
    )
    threshold: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description=(
            f"{class_identifier}.threshold[float]: the minimum confidence, from 0 to 1, at which the semantic, "
            "moderation and llm_judge strategies trigger. Defaults to 0.8."
        ),
    )
    model: Optional[str] = Field(
        default=None,
        description=f"{class_identifier}.model[str]: the model of the semantic, moderation and llm_judge strategies.",
    )
    provider: Optional[str] = Field(
        default=None,
        description=(
            f"{class_identifier}.provider[str]: the name of the Smarter LLM Provider that the semantic, moderation "
            "and llm_judge strategies call. Defaults to openai."
        ),
    )

    # --- response ---
    action: str = Field(
        ...,
        description=f"{class_identifier}.action[str]: what the guardrail does when it triggers. One of: {SAMGuardrailAction.all()}.",
    )
    replacement: Optional[str] = Field(
        default=None,
        description=(
            f"{class_identifier}.replacement[str]: what redact and transform replace each match with. Defaults to "
            "[REDACTED], which an empty replacement also means. {label} is replaced with what matched, e.g. "
            "credit_card. For the regex strategy, transform may refer to groups, e.g. \\1."
        ),
    )
    message: Optional[str] = Field(
        default=None,
        description=f"{class_identifier}.message[str]: what block returns to the user, instead of the LLM's reply.",
    )
    severity: int = Field(
        default=DEFAULT_SEVERITY,
        ge=1,
        le=5,
        description=f"{class_identifier}.severity[int]: from 1 (low) to 5 (critical), for reporting and review.",
    )

    # --- lifecycle ---
    mode: str = Field(
        default=SAMGuardrailMode.ENFORCE.value,
        description=(
            f"{class_identifier}.mode[str]: enforce, to take the action, or monitor, to only record what the action "
            "would have been."
        ),
    )
    failClosed: bool = Field(
        default=False,
        description=(
            f"{class_identifier}.failClosed[bool]: if true, block when the check itself fails, e.g. because the LLM "
            "provider is unavailable. If false, the failure is recorded, and the prompt continues."
        ),
    )
    priority: int = Field(
        default=DEFAULT_PRIORITY,
        ge=0,
        description=f"{class_identifier}.priority[int]: the order in which guardrails run. Lower runs first.",
    )
    isActive: bool = Field(
        default=True,
        description=f"{class_identifier}.isActive[bool]: whether the guardrail runs.",
    )

    @field_validator("stage")
    @classmethod
    def validate_stage(cls, v: str) -> str:
        return choice(v, SAMGuardrailStage.all(), "stage")

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        return choice(v, SAMGuardrailCategory.all(), "category")

    @field_validator("strategy")
    @classmethod
    def validate_strategy(cls, v: str) -> str:
        return choice(v, SAMGuardrailStrategy.all(), "strategy")

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        return choice(v, SAMGuardrailAction.all(), "action")

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        return choice(v, SAMGuardrailMode.all(), "mode")

    @field_validator("flags")
    @classmethod
    def validate_flags(cls, v: Optional[list[str]]) -> list[str]:
        flags = [str(flag).upper() for flag in (v or [])]
        for flag in flags:
            if flag not in REGEX_FLAGS:
                raise SAMValidationError(f"flags: must be any of {list(REGEX_FLAGS)}, not '{flag}'.")
        return flags

    @field_validator("keywords", "referenceTexts")
    @classmethod
    def validate_texts(cls, v: Optional[list[str]]) -> list[str]:
        texts = []
        for text in v or []:
            text = str(text).strip()
            if text and text not in texts:
                texts.append(text)
        return texts

    @field_validator("detectors")
    @classmethod
    def validate_detectors(cls, v: Optional[list[str]]) -> list[str]:
        return [choice(detector, SAMGuardrailDetector.all(), "detectors") for detector in v or []]

    @field_validator("categories")
    @classmethod
    def validate_categories(cls, v: Optional[list[str]]) -> list[str]:
        return [choice(category, SAMGuardrailModerationCategory.all(), "categories") for category in v or []]

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: Optional[str]) -> Optional[str]:
        if v and len(v) > MAX_MESSAGE_LENGTH:
            raise SAMValidationError(f"message: must be at most {MAX_MESSAGE_LENGTH} characters.")
        return v or None

    @model_validator(mode="after")
    def validate_strategy_fields(self) -> "SAMGuardrailSpecConfig":  # pylint: disable=too-many-branches
        """Validate the fields of the guardrail's strategy."""
        strategy = self.strategy
        if strategy == SAMGuardrailStrategy.REGEX.value:
            if not self.pattern:
                raise SAMValidationError("pattern: is required when strategy is regex.")
            if len(self.pattern) > MAX_PATTERN_LENGTH:
                raise SAMValidationError(f"pattern: must be at most {MAX_PATTERN_LENGTH} characters.")
            try:
                compiled = re.compile(self.pattern, compile_flags(self.flags or []))
            except re.error as e:
                raise SAMValidationError(f"pattern: is not a valid regular expression: {e}") from e
            if compiled.match(""):
                raise SAMValidationError("pattern: must not match empty text.")
        elif strategy == SAMGuardrailStrategy.KEYWORD.value:
            if not self.keywords:
                raise SAMValidationError("keywords: at least one is required when strategy is keyword.")
            if len(self.keywords) > MAX_KEYWORDS:
                raise SAMValidationError(f"keywords: at most {MAX_KEYWORDS} are permitted.")
        elif strategy == SAMGuardrailStrategy.DETECTOR.value:
            if not self.detectors:
                raise SAMValidationError("detectors: at least one is required when strategy is detector.")
        elif strategy == SAMGuardrailStrategy.SEMANTIC.value:
            if not self.referenceTexts:
                raise SAMValidationError("referenceTexts: at least one is required when strategy is semantic.")
            if len(self.referenceTexts) > MAX_REFERENCE_TEXTS:
                raise SAMValidationError(f"referenceTexts: at most {MAX_REFERENCE_TEXTS} are permitted.")
        elif strategy == SAMGuardrailStrategy.LLM_JUDGE.value:
            prompt = self.judgePrompt or ""
            if "{text}" not in prompt:
                raise SAMValidationError(
                    "judgePrompt: is required, with a {text} placeholder, when strategy is llm_judge."
                )
            if len(prompt) > MAX_JUDGE_PROMPT_LENGTH:
                raise SAMValidationError(f"judgePrompt: must be at most {MAX_JUDGE_PROMPT_LENGTH} characters.")
            try:
                prompt.format(text="")
            except (KeyError, IndexError, ValueError) as e:
                raise SAMValidationError(
                    f"judgePrompt: its only placeholder may be {{text}}. Double any other braces: {e}"
                ) from e
        if self.threshold is not None and strategy not in SAMGuardrailStrategy.scored():
            raise SAMValidationError(f"threshold: applies only to the {SAMGuardrailStrategy.scored()} strategies.")
        return self

    @model_validator(mode="after")
    def validate_action_fields(self) -> "SAMGuardrailSpecConfig":
        """Validate that the action is possible with the strategy."""
        if self.action in (SAMGuardrailAction.REDACT.value, SAMGuardrailAction.TRANSFORM.value):
            if self.strategy not in SAMGuardrailStrategy.locating():
                raise SAMValidationError(
                    f"action: {self.action} requires a strategy that locates what it matches: "
                    f"{SAMGuardrailStrategy.locating()}. Use flag or block with {self.strategy}."
                )
        if self.action == SAMGuardrailAction.TRANSFORM.value and self.replacement is None:
            raise SAMValidationError("replacement: is required when action is transform.")
        return self


class SAMGuardrailSpec(AbstractSAMSpecBase):
    """Smarter API Guardrail Manifest Guardrail.spec."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    config: SAMGuardrailSpecConfig = Field(
        ..., description=f"{class_identifier}.config[object]. The configuration for the {MANIFEST_KIND}."
    )
