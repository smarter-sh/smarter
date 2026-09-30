"""All models for the Vectorsearch API app."""

from django.core.exceptions import ValidationError
from django.db import models

from smarter.apps.account.models import (
    MetaDataWithOwnershipModel,
)
from smarter.apps.secret.models import Secret
from smarter.apps.vectorstore.models import VectorstoreMeta
from smarter.lib import logging
from smarter.lib.django.waffle.switches import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.VECTORSEARCH_LOGGING])


class VectorsearchSearchType(models.TextChoices):
    """Supported retrieval strategies for a Vectorsearch query."""

    SIMILARITY = "similarity", "Similarity"
    SIMILARITY_SCORE_THRESHOLD = "similarity_score_threshold", "Similarity w/ Score Threshold"
    MMR = "mmr", "Maximal Marginal Relevance"


class Vectorsearch(MetaDataWithOwnershipModel):
    """
    Implements the Vectorsearch API model.

    A Vectorsearch is a named, ownable configuration describing how to
    execute a semantic search against a single VectorstoreMeta. It does not
    itself hold embeddings/documents -- it references a VectorstoreMeta for
    that -- and it does not generate text. Combine a Vectorsearch with a
    Smarter LLMClient to build a RAG pipeline: the top-k results returned
    by the Vectorsearch are injected into the LLMClient's system prompt
    at inference time.
    """

    vectorstore = models.ForeignKey(
        VectorstoreMeta,
        on_delete=models.PROTECT,
        related_name="vectorsearches",
        help_text="The locally-hosted VectorstoreMeta this search queries against.",
    )
    auth_secret = models.ForeignKey(
        Secret,
        on_delete=models.PROTECT,
        related_name="vectorsearches",
        null=True,
        blank=True,
        help_text="Optional credential used to authenticate against the VectorstoreMeta, if required.",
    )

    search_type = models.CharField(
        max_length=32,
        choices=VectorsearchSearchType.choices,
        default=VectorsearchSearchType.SIMILARITY,
        help_text="The retrieval strategy to use when querying the VectorstoreMeta.",
    )
    k = models.PositiveSmallIntegerField(
        default=4,
        help_text="Number of top results to return from the search.",
    )
    score_threshold = models.FloatField(
        null=True,
        blank=True,
        help_text=(
            "Minimum relevance score (0.0-1.0) a result must meet to be included. "
            f"Only applicable when search_type='{VectorsearchSearchType.SIMILARITY_SCORE_THRESHOLD}'."
        ),
    )
    fetch_k = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text=(
            "Number of candidate documents to fetch before applying MMR re-ranking. "
            f"Only applicable when search_type='{VectorsearchSearchType.MMR}'."
        ),
    )
    lambda_mult = models.FloatField(
        null=True,
        blank=True,
        help_text=(
            "Diversity vs. relevance trade-off for MMR, between 0.0 (max diversity) and 1.0 (max relevance). "
            f"Only applicable when search_type='{VectorsearchSearchType.MMR}'."
        ),
    )
    metadata_filter = models.JSONField(
        null=True,
        blank=True,
        help_text="Optional metadata filter applied to the VectorstoreMeta query, e.g. {'source': 'faq'}.",
    )
    is_enabled = models.BooleanField(
        default=True,
        help_text="Whether this Vectorsearch is active and eligible to be queried.",
    )

    # pylint: disable=C0115
    class Meta:
        verbose_name_plural = "Vectorsearches"
        unique_together = ("user_profile", "name")

    def clean(self):
        super().clean()

        if self.k is not None and self.k < 1:
            raise ValidationError({"k": "k must be a positive integer."})

        if self.search_type == VectorsearchSearchType.SIMILARITY_SCORE_THRESHOLD:
            if self.score_threshold is None:
                raise ValidationError(
                    {"score_threshold": "score_threshold is required when search_type is similarity_score_threshold."}
                )
        elif self.score_threshold is not None:
            raise ValidationError(
                {"score_threshold": "score_threshold is only valid when search_type is similarity_score_threshold."}
            )

        if self.search_type == VectorsearchSearchType.MMR:
            if self.fetch_k is not None and self.fetch_k < self.k:
                raise ValidationError({"fetch_k": "fetch_k must be greater than or equal to k."})
            if self.lambda_mult is not None and not 0.0 <= self.lambda_mult <= 1.0:
                raise ValidationError({"lambda_mult": "lambda_mult must be between 0.0 and 1.0."})
        else:
            if self.fetch_k is not None:
                raise ValidationError({"fetch_k": "fetch_k is only valid when search_type is mmr."})
            if self.lambda_mult is not None:
                raise ValidationError({"lambda_mult": "lambda_mult is only valid when search_type is mmr."})

    def __str__(self) -> str:
        return f"{self.name} -> {self.vectorstore} ({self.search_type})"


__all__ = ["Vectorsearch", "VectorsearchSearchType"]
