"""``MatchStrategy.SEMANTIC`` — embedding cosine-similarity against a set.

of reference texts.

Recognized ``guardrail.config`` keys:

* ``reference_texts`` (``list[str]``, required) — exemplar strings the
  segment is compared against.
* ``embedding_model`` (``str``, optional) — passed through to the
  client.

``guardrail.confidence_threshold`` is the minimum cosine similarity
(``0``-``1``) required to trigger; defaults to :data:`_DEFAULT_THRESHOLD`
if unset.
"""

import math

from smarter.apps.guardrail.services.exceptions import GuardrailConfigError
from smarter.apps.guardrail.services.strategies.base import (
    BaseGuardrailStrategy,
    StrategyContext,
    StrategyMatch,
)
from smarter.apps.guardrail.services.strategies.clients import EmbeddingClient

_DEFAULT_THRESHOLD = 0.85


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute the cosine similarity between two equal-length vectors.

    :param a: The first vector.
    :type a: list[float]
    :param b: The second vector.
    :type b: list[float]
    :returns: The cosine similarity in ``[-1.0, 1.0]``, or ``0.0`` if
        either vector has zero magnitude.
    :rtype: float
    :raises smarter.apps.guardrail.services.exceptions.GuardrailConfigError:
        If ``a`` and ``b`` have different lengths.
    """
    if len(a) != len(b):
        raise GuardrailConfigError("Embedding dimension mismatch between segment and reference text.")
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class SemanticStrategy(BaseGuardrailStrategy):
    """Match a text segment by embedding similarity to reference texts.

    :param embedding_client: The client used to embed both the segment
        and each reference text.
    :type embedding_client: ~smarter.apps.guardrail.services.strategies.clients.EmbeddingClient
    """

    def __init__(self, embedding_client: EmbeddingClient):
        self._client = embedding_client

    def evaluate(self, *, segment, guardrail, context: StrategyContext) -> StrategyMatch:
        """Compare ``segment.text`` against each configured reference text.

        :param segment: The text segment to evaluate.
        :type segment: ~smarter.apps.guardrail.services.contracts.TextSegment
        :param guardrail: The guardrail row; requires
            ``config["reference_texts"]`` to be a non-empty list.
        :type guardrail: ~smarter.apps.guardrail.models.Guardrail
        :param context: Ambient evaluation context (unused by this
            strategy).
        :type context: ~smarter.apps.guardrail.services.strategies.base.StrategyContext
        :returns: A match whose ``confidence`` is the best cosine
            similarity found across all reference texts, ``triggered``
            when that score meets ``guardrail.confidence_threshold``.
        :rtype: ~smarter.apps.guardrail.services.strategies.base.StrategyMatch
        :raises smarter.apps.guardrail.services.exceptions.GuardrailConfigError:
            If ``guardrail.config["reference_texts"]`` is empty, or an
            embedding dimension mismatch occurs.
        """
        reference_texts: list[str] = guardrail.config.get("reference_texts") or []
        if not reference_texts:
            raise GuardrailConfigError(
                f"Guardrail '{guardrail.name}' uses match_strategy=semantic but config.reference_texts is empty."
            )

        threshold = guardrail.confidence_threshold or _DEFAULT_THRESHOLD
        segment_vector = self._client.embed(segment.text)

        best_score = 0.0
        best_reference = None
        for reference in reference_texts:
            reference_vector = self._client.embed(reference)
            score = _cosine_similarity(segment_vector, reference_vector)
            if score > best_score:
                best_score, best_reference = score, reference

        triggered = best_score >= threshold
        return StrategyMatch(
            triggered=triggered,
            confidence=best_score,
            matched_text=segment.text if triggered else None,
            rationale=(
                f"Best match similarity {best_score:.3f} against reference "
                f"'{best_reference}' (threshold {threshold:.3f})"
            ),
        )


__all__ = ["SemanticStrategy"]
