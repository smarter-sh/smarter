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
        """
        Moderate the segment, and compare the scores of the Guardrail's categories with its threshold.

        Calls the Guardrail's LLM provider. A category triggers when its score reaches the threshold,
        or when the moderation model flagged it. With no ``categories``, every category counts.

        :param segment: The text segment.
        :param guardrail: The Guardrail, which supplies the strategy's configuration.
        :param context: Ambient evaluation context. Unused.
        :returns: A match whose confidence is the highest score among the categories.
        :raises GuardrailProviderError: when the moderation call fails.
        """
        model = guardrail.settings.get("model") or DEFAULT_MODERATION_MODEL
        result = get_client(guardrail).moderate(segment.text, model=model)
        categories = set(guardrail.settings.get("categories") or result.scores.keys())
        threshold = self.threshold(guardrail)
        scores = {name: score for name, score in result.scores.items() if name in categories}
        triggered_names = []
        for name in categories:
            score = scores.get(name, 0.0)
            if score >= threshold or name in result.flagged:
                triggered_names.append(name)
        triggered = sorted(triggered_names)
        confidence = max(scores.values(), default=0.0)
        if not triggered:
            return StrategyMatch(triggered=False, confidence=confidence)
        details = ", ".join(f"{name} {scores.get(name, 0.0):.2f}" for name in triggered)
        return StrategyMatch(triggered=True, confidence=confidence, rationale=f"Moderation categories: {details}.")


__all__ = ["ModerationStrategy"]
