"""MatchStrategy.LLM_JUDGE — guardrail.pattern is a judge prompt template.

containing a `{text}` placeholder; it's sent to an LLM which is expected
to return a structured triggered/confidence/rationale verdict.

config keys recognized:
    model_id: str      (required) -- judge model to call
    temperature: float (optional, default 0.0) -- keep judges deterministic
guardrail.confidence_threshold gates the trigger; defaults to 0.7 if unset.
"""

from __future__ import annotations

from smarter.apps.guardrail.services.exceptions import GuardrailConfigError
from smarter.apps.guardrail.services.strategies.base import (
    BaseGuardrailStrategy,
    StrategyContext,
    StrategyMatch,
)
from smarter.apps.guardrail.services.strategies.clients import LLMJudgeClient

_DEFAULT_THRESHOLD = 0.7


class LLMJudgeStrategy(BaseGuardrailStrategy):
    def __init__(self, judge_client: LLMJudgeClient):
        self._client = judge_client

    def evaluate(self, *, segment, guardrail, context: StrategyContext) -> StrategyMatch:
        if not guardrail.pattern or "{text}" not in guardrail.pattern:
            raise GuardrailConfigError(
                f"Guardrail '{guardrail.name}' uses match_strategy=llm_judge but `pattern` "
                "is empty or missing a {text} placeholder."
            )

        model_id = guardrail.config.get("model_id")
        if not model_id:
            raise GuardrailConfigError(
                f"Guardrail '{guardrail.name}' uses match_strategy=llm_judge but config.model_id is unset."
            )

        temperature = float(guardrail.config.get("temperature", 0.0))
        prompt = guardrail.pattern.format(text=segment.text)

        verdict = self._client.judge(prompt, model_id=model_id, temperature=temperature)
        threshold = guardrail.confidence_threshold or _DEFAULT_THRESHOLD

        triggered = verdict.triggered and verdict.confidence >= threshold
        return StrategyMatch(
            triggered=triggered,
            confidence=verdict.confidence,
            matched_text=segment.text if triggered else None,
            rationale=verdict.rationale or "LLM judge did not provide a rationale.",
        )


__all__ = ["LLMJudgeStrategy"]
