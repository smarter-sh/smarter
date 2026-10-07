"""Smarter API Manifest - Vectorsearch.spec."""

import os
from typing import ClassVar, Optional

from pydantic import Field, field_validator, model_validator

from smarter.apps.vectorsearch.manifest.models.vectorsearch.const import MANIFEST_KIND
from smarter.apps.vectorsearch.models import VectorsearchSearchType

# from smarter.common.conf import settings_defaults
from smarter.lib.manifest.models import AbstractSAMSpecBase

filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"


class SAMVectorsearchSpecConfig(AbstractSAMSpecBase):
    """Smarter API Vectorsearch Manifest Vectorsearch.spec.config."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER + ".configuration"

    # --- target ---
    vectorstore_name: str = Field(
        ...,
        description="The name of the locally-hosted Vectorstore this search queries against.",
    )
    auth_secret_name: Optional[str] = Field(
        default=None,
        description="Optional name of the Secret used to authenticate against the Vectorstore, if required.",
    )

    # --- retrieval strategy ---
    search_type: VectorsearchSearchType = Field(
        default=VectorsearchSearchType.SIMILARITY,
        description="The retrieval strategy to use when querying the Vectorstore.",
    )
    k: int = Field(
        default=4,
        gt=0,
        description="Number of top results to return from the search.",
    )
    score_threshold: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description=(
            "Minimum relevance score a result must meet to be included. "
            f"Only valid when search_type='{VectorsearchSearchType.SIMILARITY_SCORE_THRESHOLD}'."
        ),
    )
    fetch_k: Optional[int] = Field(
        default=None,
        gt=0,
        description=(
            "Number of candidate documents to fetch before MMR re-ranking. "
            f"Only valid when search_type='{VectorsearchSearchType.MMR}'."
        ),
    )
    lambda_mult: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description=(
            "Diversity vs. relevance trade-off for MMR (0.0=max diversity, 1.0=max relevance). "
            f"Only valid when search_type='{VectorsearchSearchType.MMR}'."
        ),
    )

    # --- scoping ---
    metadata_filter: Optional[dict] = Field(
        default=None,
        description="Optional metadata filter applied to the Vectorstore query, e.g. {'source': 'faq'}.",
    )
    is_enabled: bool = Field(
        default=True,
        description="Whether this Vectorsearch is active and eligible to be queried.",
    )

    @field_validator("vectorstore_name", "auth_secret_name")
    @classmethod
    def strip_and_validate_name(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("name fields must not be blank.")
        return value

    @model_validator(mode="after")
    def validate_search_type_constraints(self) -> "SAMVectorsearchSpecConfig":
        if self.search_type == VectorsearchSearchType.SIMILARITY_SCORE_THRESHOLD:
            if self.score_threshold is None:
                raise ValueError("score_threshold is required when search_type is similarity_score_threshold.")
        elif self.score_threshold is not None:
            raise ValueError("score_threshold is only valid when search_type is similarity_score_threshold.")

        if self.search_type == VectorsearchSearchType.MMR:
            if self.fetch_k is not None and self.fetch_k < self.k:
                raise ValueError("fetch_k must be greater than or equal to k.")
        else:
            if self.fetch_k is not None:
                raise ValueError("fetch_k is only valid when search_type is mmr.")
            if self.lambda_mult is not None:
                raise ValueError("lambda_mult is only valid when search_type is mmr.")

        return self


class SAMVectorsearchSpec(AbstractSAMSpecBase):
    """Smarter API Vectorsearch Manifest Vectorsearch.spec."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    config: SAMVectorsearchSpecConfig = Field(
        ..., description=f"{class_identifier}.config[object]. The configuration for the {MANIFEST_KIND}."
    )
