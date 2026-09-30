"""
``semantic``: triggers when the segment's embedding is similar to any of.

``guardrail.config["referenceTexts"]``.

The similarity is the cosine similarity of the embeddings, and the guardrail triggers when the
best similarity reaches ``guardrail.threshold``. The reference texts' embeddings are cached,
so that each prompt embeds only the segment.
"""

import hashlib
import math

from django.core.cache import cache

from smarter.apps.guardrail.manifest.models.guardrail.const import (
    DEFAULT_EMBEDDING_MODEL,
)
from smarter.apps.guardrail.services.exceptions import (
    GuardrailConfigError,
    GuardrailProviderError,
)

from .base import BaseGuardrailStrategy, StrategyContext, StrategyMatch
from .clients import get_client

EMBEDDING_CACHE_TTL = 60 * 60 * 24 * 7
"""Seconds to cache a reference text's embedding."""


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """
    Return the cosine similarity of two vectors, or 0.0 if either has no magnitude.

    :raises GuardrailProviderError: If the vectors have different lengths.
    """
    if len(a) != len(b):
        raise GuardrailProviderError("The embeddings of the segment and a reference text have different dimensions.")
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def embedding_cache_key(model: str, text: str) -> str:
    """Return the cache key of a text's embedding."""
    return f"smarter.apps.guardrail.embedding.{model}.{hashlib.sha256(text.encode()).hexdigest()}"


class SemanticStrategy(BaseGuardrailStrategy):
    """Match a text segment by its embedding's similarity to reference texts."""

    def evaluate(self, *, segment, guardrail, context: StrategyContext) -> StrategyMatch:  # pylint: disable=R0914
        """Compare the segment's embedding with each reference text's embedding."""
        references: list[str] = list(guardrail.settings.get("referenceTexts") or [])
        if not references:
            raise GuardrailConfigError(
                f"Guardrail '{guardrail.name}' uses strategy semantic but has no referenceTexts."
            )
        model = guardrail.settings.get("model") or DEFAULT_EMBEDDING_MODEL
        cached = cache.get_many([embedding_cache_key(model, text) for text in references])
        missing = [text for text in references if embedding_cache_key(model, text) not in cached]
        vectors = get_client(guardrail).embed([segment.text, *missing], model=model)
        if len(vectors) != len(missing) + 1:
            raise GuardrailProviderError("The embeddings call returned the wrong number of vectors.")
        segment_vector = vectors[0]
        new = {embedding_cache_key(model, text): vector for text, vector in zip(missing, vectors[1:])}
        if new:
            cache.set_many(new, EMBEDDING_CACHE_TTL)
        cached.update(new)
        scores = [
            (cosine_similarity(segment_vector, cached[embedding_cache_key(model, text)]), text) for text in references
        ]
        best_score, best_reference = max(scores)
        threshold = self.threshold(guardrail)
        return StrategyMatch(
            triggered=best_score >= threshold,
            confidence=best_score,
            rationale=f"The most similar reference text, with similarity {best_score:.3f} (threshold {threshold:.3f}): {best_reference[:120]}",
        )


__all__ = ["SemanticStrategy", "cosine_similarity"]
