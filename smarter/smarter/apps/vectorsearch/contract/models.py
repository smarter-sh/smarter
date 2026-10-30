"""
Pydantic models of the Vectorsearches' REST api responses (``/api/v1/vectorsearches/``).

:class:`VectorsearchApiVectorsearch` is a Vectorsearch, as :class:`smarter.apps.vectorsearch.serializers.VectorsearchSerializer` returned it
before the api was modeled, which clients already read. One value changed: its ``canDelete`` is
computed for the requesting user. The serializer was called without a request, so it was always
false.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Literal, Optional

from pydantic import Field, JsonValue

from smarter.apps.account.contract.models import (
    AccountApiModel,
    AccountApiUserProfile,
    MetaDataApiAnnotations,
)
from smarter.apps.account.serializers import user_can_delete

if TYPE_CHECKING:
    from smarter.apps.vectorsearch.models import Vectorsearch

VectorsearchApiSearchType = Literal["similarity", "similarity_score_threshold", "mmr"]
"""A Vectorsearch's ``searchType``: the choices of ``Vectorsearch.search_type``."""


class VectorsearchApiVectorsearch(AccountApiModel):
    """A Vectorsearch, a retrieval pipeline over a vectorstore: a :class:`smarter.apps.vectorsearch.models.Vectorsearch`."""

    id: int = Field(..., description="The row's primary key.")
    hashed_id: str = Field(..., description="The Vectorsearch's hashed id, e.g. rMTAwMDAwMQx, which its urls use.")
    created_at: Optional[datetime] = Field(None, description="TimestampedModel.created_at.")
    updated_at: Optional[datetime] = Field(None, description="TimestampedModel.updated_at.")
    name: str = Field(..., description="MetaDataModel.name, in snake_case.")
    description: Optional[str] = Field(None, description="MetaDataModel.description.")
    version: Optional[str] = Field(None, description="MetaDataModel.version, e.g. 1.0.0.")
    tags: list[str] = Field(default_factory=list, description="MetaDataModel.tags, by name.")
    annotations: MetaDataApiAnnotations = Field(None, description="MetaDataModel.annotations.")
    user_profile: AccountApiUserProfile = Field(..., description="The Vectorsearch's owner.")
    can_delete: bool = Field(
        ...,
        description="Whether the requesting user may delete the Vectorsearch now: they own it, and nothing uses it.",
    )
    manifest_url: str = Field(..., description="The url of the Vectorsearch's manifest in the web console.")
    detail_url: Optional[str] = Field(
        None,
        description="The url of the Vectorsearch's detail in the web console: its manifest, the resources that it "
        "uses, and those that use it.",
    )
    search_type: VectorsearchApiSearchType = Field(..., description="Vectorsearch.search_type.")
    k: int = Field(..., ge=0, description="Vectorsearch.k: the number of chunks to return.")
    score_threshold: Optional[float] = Field(None, description="Vectorsearch.score_threshold.")
    fetch_k: Optional[int] = Field(None, ge=0, description="Vectorsearch.fetch_k: the candidates of an mmr search.")
    lambda_mult: Optional[float] = Field(None, description="Vectorsearch.lambda_mult: an mmr search's diversity.")
    metadata_filter: Optional[JsonValue] = Field(None, description="Vectorsearch.metadata_filter.")
    is_enabled: bool = Field(..., description="Vectorsearch.is_enabled.")
    vectorstore: int = Field(..., description="Vectorsearch.vectorstore: the vectorstore's id.")
    auth_secret: Optional[int] = Field(None, description="Vectorsearch.auth_secret: the Secret's id, if any.")

    @classmethod
    def from_model(cls, row: "Vectorsearch", user: object = None) -> "VectorsearchApiVectorsearch":
        """
        The contract's model of a Vectorsearch.

        :param row: The row, whose ``user_profile`` should be fetched with it.
        :type row: smarter.apps.vectorsearch.models.Vectorsearch
        :param user: The requesting user, for ``can_delete``. None may delete nothing.
        :type user: object
        :returns: The model.
        :rtype: VectorsearchApiVectorsearch
        """
        # pylint: disable=import-outside-toplevel
        from smarter.apps.dashboard.resource_detail import resource_detail_url
        from smarter.apps.vectorsearch.manifest.models.vectorsearch.const import (
            MANIFEST_KIND,
        )
        from smarter.apps.vectorsearch.serializers import VectorsearchSerializer

        return cls(
            id=row.pk,
            hashed_id=row.hashed_id,
            created_at=row.created_at,
            updated_at=row.updated_at,
            name=row.name,
            description=row.description,
            version=row.version,
            tags=[tag.name for tag in row.tags.all()],
            annotations=row.annotations,
            user_profile=AccountApiUserProfile.from_model(row.user_profile),
            can_delete=user_can_delete(row, MANIFEST_KIND, user),
            manifest_url=VectorsearchSerializer().get_manifest_url(row),
            detail_url=resource_detail_url(MANIFEST_KIND, row.record_locator),
            search_type=row.search_type,  # type: ignore[arg-type]
            k=row.k,
            score_threshold=row.score_threshold,
            fetch_k=row.fetch_k,
            lambda_mult=row.lambda_mult,
            metadata_filter=row.metadata_filter,
            is_enabled=row.is_enabled,
            vectorstore=row.vectorstore_id,  # type: ignore[attr-defined]
            auth_secret=row.auth_secret_id,  # type: ignore[attr-defined]
        )


VECTORSEARCH_API_MODELS = (VectorsearchApiVectorsearch,)
"""The models whose JSON Schemas the Smarter api's OpenAPI document includes."""

__all__ = ["VECTORSEARCH_API_MODELS", "VectorsearchApiSearchType", "VectorsearchApiVectorsearch"]
