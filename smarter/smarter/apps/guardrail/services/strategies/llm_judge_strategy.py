"""
``llm_judge``: an LLM judges the segment, with ``guardrail.config["judgePrompt"]``.

The prompt's ``{text}`` placeholder is replaced with the segment's text. The LLM must reply
with a JSON object: ``{"triggered": true or false, "confidence": 0.0 to 1.0, "rationale": "..."}``.
The guardrail triggers when the judge says so, with a confidence that reaches
``guardrail.threshold``. The judge runs at ``guardrail.config["temperature"]``, 0 by default,
so that its verdicts are as deterministic as possible.
"""

from smarter.apps.guardrail.manifest.models.guardrail.const import DEFAULT_JUDGE_MODEL
from smarter.apps.guardrail.services.exceptions import GuardrailConfigError

from .base import BaseGuardrailStrategy, StrategyContext, StrategyMatch
from .clients import get_client


class LLMJudgeStrategy(BaseGuardrailStrategy):
    """Match a text segment by asking an LLM to judge it."""

    def evaluate(self, *, segment, guardrail, context: StrategyContext) -> StrategyMatch:
        """Render the judge prompt for the segment, and run it."""
        template = guardrail.settings.get("judgePrompt") or ""
        if "{text}" not in template:
            raise GuardrailConfigError(
                f"Guardrail '{guardrail.name}' uses strategy llm_judge but its judgePrompt has no {{text}} placeholder."
            )
        try:
            prompt = template.format(text=segment.text)
        except (KeyError, IndexError, ValueError) as e:
            raise GuardrailConfigError(
                f"Guardrail '{guardrail.name}': its judgePrompt is not a valid template: {e}"
            ) from e
        model = guardrail.settings.get("model") or DEFAULT_JUDGE_MODEL
        temperature = float(guardrail.settings.get("temperature", 0.0))
        verdict = get_client(guardrail).judge(prompt, model=model, temperature=temperature)
        threshold = self.threshold(guardrail)
        return StrategyMatch(
            triggered=verdict.triggered and verdict.confidence >= threshold,
            confidence=verdict.confidence,
            rationale=verdict.rationale or "The LLM judge gave no rationale.",
        )


__all__ = ["LLMJudgeStrategy"]
