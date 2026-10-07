"""``detector``: ``guardrail.config["detectors"]`` names built-in detectors of personal data and secrets."""

from smarter.apps.guardrail.services.exceptions import GuardrailConfigError

from .base import BaseGuardrailStrategy, StrategyContext, StrategyMatch
from .detectors import DETECTORS, detect


class DetectorStrategy(BaseGuardrailStrategy):
    """Match a text segment with built-in, validated detectors.

    See :mod:`.detectors`.
    """

    def evaluate(self, *, segment, guardrail, context: StrategyContext) -> StrategyMatch:
        """Find everything that the Guardrail's detectors detect in the segment."""
        detectors = list(guardrail.settings.get("detectors") or [])
        if not detectors:
            raise GuardrailConfigError(f"Guardrail '{guardrail.name}' uses strategy detector but has no detectors.")
        unknown = [name for name in detectors if name not in DETECTORS]
        if unknown:
            raise GuardrailConfigError(f"Guardrail '{guardrail.name}' has unknown detectors: {unknown}")
        matches = detect(segment.text, detectors)
        if not matches:
            return StrategyMatch(triggered=False)
        found = sorted({match.label for match in matches if match.label})
        return StrategyMatch(
            triggered=True, confidence=1.0, matches=matches, rationale=f"Detected: {', '.join(found)}."
        )


__all__ = ["DetectorStrategy"]
