"""``MatchStrategy.MODEL`` — routes the segment through a hosted/local.

classifier (e.g. a moderation model, PII detector, or ``LLMHost``-served
model) and triggers based on the returned label/confidence.

Recognized ``guardrail.config`` keys:

* ``model_id`` (``str``, required) — passed through to the client.
* ``positive_labels`` (``list[str]``, required) — labels that count as
  a trigger, e.g. ``["TOXIC", "HARASSMENT"]``.

``guardrail.confidence_threshold`` gates the trigger; defaults to
:data:`_DEFAULT_THRESHOLD` if unset.
"""

from __future__ import annotations

from smarter.apps.guardrail.services.exceptions import GuardrailConfigError
from smarter.apps.guardrail.services.strategies.base import (
    BaseGuardrailStrategy,
    StrategyContext,
    StrategyMatch,
)
from smarter.apps.guardrail.services.strategies.clients import ClassifierClient

_DEFAULT_THRESHOLD = 0.5


class ModelStrategy(BaseGuardrailStrategy):
    """Match a text segment via a hosted/local classifier model.

    :param classifier_client: The client used to classify the segment.
    :type classifier_client: ~smarter.apps.guardrail.services.strategies.clients.ClassifierClient
    """

    def __init__(self, classifier_client: ClassifierClient):
        self._client = classifier_client

    def evaluate(self, *, segment, guardrail, context: StrategyContext) -> StrategyMatch:
        """Classify ``segment.text`` and check the result against ``guardrail``.

        :param segment: The text segment to evaluate.
        :type segment: ~smarter.apps.guardrail.services.contracts.TextSegment
        :param guardrail: The guardrail row; requires
            ``config["model_id"]`` and ``config["positive_labels"]`` to
            be set.
        :type guardrail: ~smarter.apps.guardrail.models.Guardrail
        :param context: Ambient evaluation context (unused by this
            strategy).
        :type context: ~smarter.apps.guardrail.services.strategies.base.StrategyContext
        :returns: A match with the classifier's confidence, ``triggered``
            when the predicted label is in
            ``guardrail.config["positive_labels"]`` and the confidence
            meets ``guardrail.confidence_threshold``.
        :rtype: ~smarter.apps.guardrail.services.strategies.base.StrategyMatch
        :raises smarter.apps.guardrail.services.exceptions.GuardrailConfigError:
            If ``guardrail.config["model_id"]`` or
            ``guardrail.config["positive_labels"]`` is missing.
        """
        model_id = guardrail.config.get("model_id")
        positive_labels = set(guardrail.config.get("positive_labels") or [])
        if not model_id or not positive_labels:
            raise GuardrailConfigError(
                f"Guardrail '{guardrail.name}' uses match_strategy=model but is missing "
                "config.model_id and/or config.positive_labels."
            )

        verdict = self._client.classify(segment.text, model_id=model_id)
        threshold = guardrail.confidence_threshold or _DEFAULT_THRESHOLD

        triggered = verdict.label in positive_labels and verdict.confidence >= threshold
        return StrategyMatch(
            triggered=triggered,
            confidence=verdict.confidence,
            matched_text=segment.text if triggered else None,
            rationale=f"Classifier returned label='{verdict.label}' confidence={verdict.confidence:.3f}",
        )


__all__ = ["ModelStrategy"]
