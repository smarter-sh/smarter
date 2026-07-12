"""MatchStrategy.SEMANTIC — embedding cosine-similarity against a set of.

reference texts.

config keys recognized:
    reference_texts: list[str]   (required) -- exemplar strings the segment
                                   is compared against
    embedding_model: str          (optional) -- passed through to the client
guardrail.confidence_threshold is the minimum cosine similarity (0-1) to
trigger; defaults to 0.85 if unset.
"""

from __future__ import annotations

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
    if len(a) != len(b):
        raise GuardrailConfigError("Embedding dimension mismatch between segment and reference text.")
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class SemanticStrategy(BaseGuardrailStrategy):
    def __init__(self, embedding_client: EmbeddingClient):
        self._client = embedding_client

    def evaluate(self, *, segment, guardrail, context: StrategyContext) -> StrategyMatch:
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
