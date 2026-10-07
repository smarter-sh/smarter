"""
``moderation``: an LLM provider's moderation model, e.g. OpenAI's ``omni-moderation-latest``.

Triggers when the score of any of ``guardrail.config["categories"]``, or of any category if it
is empty, reaches ``guardrail.threshold``, or when the moderation model flags one of them.
"""

from smarter.apps.guardrail.manifest.models.guardrail.const import (
    DEFAULT_MODERATION_MODEL,
)

from .base import BaseGuardrailStrategy, StrategyContext, StrategyMatch
from .clients import get_client


class ModerationStrategy(BaseGuardrailStrategy):
    """Match a text segment with a moderation model."""

    def evaluate(self, *, segment, guardrail, context: StrategyContext) -> StrategyMatch:
        """Moderate the segment, and compare the scores of the Guardrail's categories with its threshold."""
        model = guardrail.settings.get("model") or DEFAULT_MODERATION_MODEL
        result = get_client(guardrail).moderate(segment.text, model=model)
        categories = set(guardrail.settings.get("categories") or result.scores.keys())
        threshold = self.threshold(guardrail)
        scores = {name: score for name, score in result.scores.items() if name in categories}
        triggered = sorted(name for name in categories if scores.get(name, 0.0) >= threshold or name in result.flagged)
        confidence = max(scores.values(), default=0.0)
        if not triggered:
            return StrategyMatch(triggered=False, confidence=confidence)
        details = ", ".join(f"{name} {scores.get(name, 0.0):.2f}" for name in triggered)
        return StrategyMatch(triggered=True, confidence=confidence, rationale=f"Moderation categories: {details}.")


__all__ = ["ModerationStrategy"]
