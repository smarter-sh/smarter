"""
Pydantic models of the vectorstores' REST api requests and responses (``/api/v1/vectorstores/``).

The REST api's views build their responses from these models, and the Smarter api's OpenAPI
document (:mod:`smarter.apps.api.v1.contract.openapi`) publishes their JSON Schemas.

:class:`VectorstoreApiVectorstore`, :class:`VectorstoreApiDocument` and
:class:`VectorstoreApiSnapshot` are the rows, as :mod:`smarter.apps.vectorstore.serializers`
returned them before the api was modeled, which clients already read. One value changed: a
vectorstore's ``canDelete`` is computed for the requesting user. The serializer was called without a
request, so it was always false. The other models replace the dicts that the views built by hand,
with the same keys.

The models forbid extra fields: the api returns exactly what they declare.
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
    from smarter.apps.vectorstore.backends.base import SearchResult
    from smarter.apps.vectorstore.models import (
        VectorstoreDocument,
        VectorstoreMeta,
        VectorstoreSnapshot,
    )


VectorstoreApiBackend = Literal["qdrant", "pinecone"]
"""The choices of ``VectorstoreMeta.backend``.

A test fails if the two differ.
"""

VectorstoreApiHosting = Literal["self_hosted", "managed"]
"""The choices of ``VectorstoreMeta.hosting``.

A test fails if the two differ.
"""

VectorstoreApiMetric = Literal["cosine", "euclidean", "dotproduct"]
"""The choices of ``VectorstoreMeta.metric``.

A test fails if the two differ.
"""

VectorstoreApiStatusValue = Literal["pending", "provisioning", "ready", "stopped", "failed", "deleting"]
"""The choices of ``VectorstoreMeta.status``.

A test fails if the two differ.
"""

VectorstoreApiDocumentSource = Literal["upload", "url", "text", "file"]
"""The choices of ``VectorstoreDocument.source``.

A test fails if the two differ.
"""

VectorstoreApiDocumentStatus = Literal["pending", "loading", "loaded", "failed", "deleting"]
"""The choices of ``VectorstoreDocument.status``.

A test fails if the two differ.
"""

VectorstoreApiSnapshotStatus = Literal["creating", "ready", "failed"]
"""The choices of ``VectorstoreSnapshot.status``.

A test fails if the two differ.
"""

VectorstoreApiSearchType = Literal["similarity", "similarity_score_threshold", "mmr"]
"""The search types: ``smarter.apps.vectorstore.backends.base.SEARCH_TYPES``.

A test fails if the two differ.
"""


class VectorstoreApiVectorstore(AccountApiModel):
    """A vectorstore: a :class:`smarter.apps.vectorstore.models.VectorstoreMeta`.

    Its related rows are their names.
    """

    id: int = Field(..., description="The row's primary key.")
    hashed_id: str = Field(..., description="The vectorstore's hashed id, which its urls use.")
    created_at: Optional[datetime] = Field(None, description="TimestampedModel.created_at.")
    updated_at: Optional[datetime] = Field(None, description="TimestampedModel.updated_at.")
    name: str = Field(..., description="MetaDataModel.name, in snake_case.")
    description: Optional[str] = Field(None, description="MetaDataModel.description.")
    version: Optional[str] = Field(None, description="MetaDataModel.version, e.g. 1.0.0.")
    tags: list[str] = Field(default_factory=list, description="MetaDataModel.tags, by name.")
    annotations: MetaDataApiAnnotations = Field(None, description="MetaDataModel.annotations.")
    user_profile: AccountApiUserProfile = Field(..., description="The vectorstore's owner.")
    can_delete: bool = Field(
        ...,
        description="Whether the requesting user may delete the vectorstore now: they own it, and nothing uses it.",
    )
    connection: Optional[str] = Field(None, description="The name of its ApiConnection, if any.")
    embeddings_provider: Optional[str] = Field(None, description="The name of its embeddings' Provider.")
    api_key_secret: Optional[str] = Field(None, description="The name of the Secret of its api key, never the key.")
    document_count: int = Field(..., ge=0, description="The number of its documents.")
    snapshot_count: int = Field(..., ge=0, description="The number of its snapshots.")
    manifest_url: str = Field(..., description="The url of the vectorstore's manifest in the web console.")
    spec: dict[str, JsonValue] = Field(..., description="The manifest's spec, as it was applied. See SAMVectorstore.")
    backend: VectorstoreApiBackend = Field(..., description="The vector database.")
    hosting: VectorstoreApiHosting = Field(..., description="Who runs the database: the platform, or the vendor.")
    is_active: bool = Field(..., description="Whether LLMClients use the vectorstore.")
    dimension: int = Field(..., ge=0, description="The dimension of its vectors.")
    metric: VectorstoreApiMetric = Field(..., description="The distance metric of its index.")
    deletion_protection: bool = Field(..., description="Whether its index refuses to be deleted.")
    embeddings_model: str = Field(..., description="The embeddings model.")
    status: VectorstoreApiStatusValue = Field(..., description="Its deployment's status.")
    status_message: str = Field(..., description="Its status, for a person.")
    index_name: str = Field(..., description="The name of its index or collection.")
    endpoint_url: str = Field(..., description="The url of its database, once deployed.")
    vector_count: int = Field(..., description="The number of its vectors, as of the last check.")
    stats: dict[str, JsonValue] = Field(..., description="The database's statistics, as of the last check.")
    deployed_at: Optional[datetime] = Field(None, description="When it was deployed.")
    last_checked_at: Optional[datetime] = Field(None, description="When its status was last checked.")
    last_snapshot_at: Optional[datetime] = Field(None, description="When its last snapshot was taken.")
    last_maintenance_at: Optional[datetime] = Field(None, description="When its maintenance last ran.")

    @classmethod
    def from_model(cls, vectorstore: "VectorstoreMeta", user: object = None) -> "VectorstoreApiVectorstore":
        """
        The contract's model of a vectorstore.

        :param vectorstore: The row, whose ``user_profile`` should be fetched with it.
        :type vectorstore: smarter.apps.vectorstore.models.VectorstoreMeta
        :param user: The requesting user, for ``can_delete``. None may delete nothing.
        :type user: object
        :returns: The model.
        :rtype: VectorstoreApiVectorstore
        """
        # pylint: disable=import-outside-toplevel
        from django.urls import reverse

        from smarter.apps.vectorstore.manifest.models.vectorstore.const import (
            MANIFEST_KIND as VECTORSTORE_KIND,
        )
        from smarter.apps.vectorstore.urls import VectorstoreReverseNames

        return cls(
            id=vectorstore.pk,
            hashed_id=vectorstore.hashed_id,
            created_at=vectorstore.created_at,
            updated_at=vectorstore.updated_at,
            name=vectorstore.name,
            description=vectorstore.description,
            version=vectorstore.version,
            tags=[tag.name for tag in vectorstore.tags.all()],
            annotations=vectorstore.annotations,
            user_profile=AccountApiUserProfile.from_model(vectorstore.user_profile),
            can_delete=user_can_delete(vectorstore, VECTORSTORE_KIND, user),
            connection=vectorstore.connection.name if vectorstore.connection else None,
            embeddings_provider=vectorstore.embeddings_provider.name if vectorstore.embeddings_provider else None,
            api_key_secret=vectorstore.api_key_secret.name if vectorstore.api_key_secret else None,
            document_count=vectorstore.documents.count(),  # type: ignore[attr-defined]
            snapshot_count=vectorstore.snapshots.count(),  # type: ignore[attr-defined]
            manifest_url=reverse(
                f"{VectorstoreReverseNames.namespace}:{VectorstoreReverseNames.detailview}",
                kwargs={"hashed_id": vectorstore.hashed_id},
            ),
            spec=vectorstore.spec,
            backend=vectorstore.backend,  # type: ignore[arg-type]
            hosting=vectorstore.hosting,  # type: ignore[arg-type]
            is_active=vectorstore.is_active,
            dimension=vectorstore.dimension,
            metric=vectorstore.metric,  # type: ignore[arg-type]
            deletion_protection=vectorstore.deletion_protection,
            embeddings_model=vectorstore.embeddings_model,
            status=vectorstore.status,  # type: ignore[arg-type]
            status_message=vectorstore.status_message,
            index_name=vectorstore.index_name,
            endpoint_url=vectorstore.endpoint_url,
            vector_count=vectorstore.vector_count,
            stats=vectorstore.stats,
            deployed_at=vectorstore.deployed_at,
            last_checked_at=vectorstore.last_checked_at,
            last_snapshot_at=vectorstore.last_snapshot_at,
            last_maintenance_at=vectorstore.last_maintenance_at,
        )


class VectorstoreApiStatus(AccountApiModel):
    """A vectorstore's status and statistics, checked now."""

    vectorstore: str = Field(..., description="The vectorstore's name.")
    status: VectorstoreApiStatusValue = Field(..., description="Its deployment's status.")
    message: str = Field(..., description="Its status, for a person.")
    vector_count: int = Field(..., description="The number of its vectors.")
    stats: dict[str, JsonValue] = Field(..., description="The database's statistics.")


class VectorstoreApiDocument(AccountApiModel):
    """A document of a vectorstore: a :class:`smarter.apps.vectorstore.models.VectorstoreDocument`, without its content."""

    id: int = Field(..., description="The row's primary key.")
    hashed_id: str = Field(..., description="The document's hashed id.")
    created_at: Optional[datetime] = Field(None, description="TimestampedModel.created_at.")
    updated_at: Optional[datetime] = Field(None, description="TimestampedModel.updated_at.")
    name: str = Field(..., description="The document's name, e.g. its file name or url.")
    source: VectorstoreApiDocumentSource = Field(..., description="Where the document came from.")
    content_type: str = Field(..., description="Its media type, e.g. application/pdf.")
    sha256: str = Field(..., description="The SHA-256 of its content, which finds duplicates.")
    size_bytes: int = Field(..., ge=0, description="Its size.")
    metadata: dict[str, JsonValue] = Field(..., description="The metadata stored with each of its chunks.")
    status: VectorstoreApiDocumentStatus = Field(..., description="Whether its chunks are loaded.")
    status_message: str = Field(..., description="Its status, for a person.")
    chunk_count: int = Field(..., ge=0, description="The number of its chunks.")
    loaded_at: Optional[datetime] = Field(None, description="When its chunks were loaded.")

    @classmethod
    def from_model(cls, document: "VectorstoreDocument") -> "VectorstoreApiDocument":
        """
        The contract's model of a vectorstore's document.

        :param document: The row.
        :type document: smarter.apps.vectorstore.models.VectorstoreDocument
        :returns: The model.
        :rtype: VectorstoreApiDocument
        """
        return cls(
            id=document.pk,
            hashed_id=document.hashed_id,
            created_at=document.created_at,
            updated_at=document.updated_at,
            name=document.name,
            source=document.source,  # type: ignore[arg-type]
            content_type=document.content_type,
            sha256=document.sha256,
            size_bytes=document.size_bytes,
            metadata=document.metadata,
            status=document.status,  # type: ignore[arg-type]
            status_message=document.status_message,
            chunk_count=document.chunk_count,
            loaded_at=document.loaded_at,
        )


class VectorstoreApiDocuments(AccountApiModel):
    """A vectorstore's documents, newest first."""

    documents: list[VectorstoreApiDocument]


class VectorstoreApiAddText(AccountApiModel):
    """The JSON request body that adds a text, or the document at a url, to a vectorstore.

    Files are multipart/form-data.
    """

    name: Optional[str] = Field(None, description="The text's name. Defaults to text.")
    text: Optional[str] = Field(None, description="The text.")
    url: Optional[str] = Field(None, description="A public url, whose document is fetched now.")
    metadata: Optional[dict[str, JsonValue]] = Field(None, description="Metadata to store with each chunk.")


class VectorstoreApiDocumentsAdded(AccountApiModel):
    """The documents that a request added, the ones that the vectorstore already had, and whether they're queued."""

    documents: list[VectorstoreApiDocument] = Field(..., description="The documents that were added.")
    duplicates: list[VectorstoreApiDocument] = Field(
        ..., description="The documents with the same content, already added."
    )
    queued: bool = Field(
        ..., description="Whether the new documents are queued to be loaded. Only a ready vectorstore loads them."
    )
    message: str = Field(..., description="Why the documents are not queued, if they aren't.")


class VectorstoreApiDocumentDeleted(AccountApiModel):
    """A document that is being removed, with its chunks."""

    document: str = Field(..., description="The document's name.")
    status: VectorstoreApiDocumentStatus = Field(..., description="deleting.")


class VectorstoreApiSearch(AccountApiModel):
    """The request body of a search of a vectorstore."""

    query: str = Field(..., description="The text to find similar chunks of.")
    k: int = Field(4, ge=1, description="The number of results, at most 50.")
    search_type: VectorstoreApiSearchType = Field("similarity", description="How to search.")
    score_threshold: Optional[float] = Field(None, description="The minimum score of similarity_score_threshold.")
    fetch_k: Optional[int] = Field(None, description="The number of candidates that mmr chooses among.")
    lambda_mult: Optional[float] = Field(None, description="mmr's balance of relevance and diversity.")
    filter: Optional[dict[str, JsonValue]] = Field(None, description="Metadata that every result must match.")


class VectorstoreApiSearchResult(AccountApiModel):
    """A chunk that a search found."""

    id: Optional[str] = Field(None, description="The chunk's id in the database.")
    text: str = Field(..., description="The chunk's text.")
    metadata: dict[str, JsonValue] = Field(..., description="The chunk's metadata.")
    score: Optional[float] = Field(None, description="Its similarity to the query.")

    @classmethod
    def from_result(cls, result: "SearchResult") -> "VectorstoreApiSearchResult":
        """
        The contract's model of a search result.

        :param result: The result.
        :type result: smarter.apps.vectorstore.backends.base.SearchResult
        :returns: The model.
        :rtype: VectorstoreApiSearchResult
        """
        return cls(id=result.id, text=result.text, metadata=result.metadata, score=result.score)


class VectorstoreApiSearchResults(AccountApiModel):
    """The results of a search of a vectorstore, most similar first."""

    vectorstore: str = Field(..., description="The vectorstore's name.")
    results: list[VectorstoreApiSearchResult]


class VectorstoreApiSnapshot(AccountApiModel):
    """A snapshot of a vectorstore: a :class:`smarter.apps.vectorstore.models.VectorstoreSnapshot`, a Qdrant snapshot or Pinecone backup."""

    id: int = Field(..., description="The row's primary key.")
    hashed_id: str = Field(..., description="The snapshot's hashed id.")
    created_at: Optional[datetime] = Field(None, description="When it was taken.")
    updated_at: Optional[datetime] = Field(None, description="TimestampedModel.updated_at.")
    name: str = Field(..., description="The snapshot's name in the database.")
    status: VectorstoreApiSnapshotStatus
    status_message: str = Field(..., description="Its status, for a person.")
    size_bytes: Optional[int] = Field(None, ge=0, description="Its size, if the database reports it.")
    vector_count: Optional[int] = Field(None, description="The number of vectors it holds.")
    scheduled: bool = Field(..., description="Whether maintenance took it, rather than a person.")

    @classmethod
    def from_model(cls, snapshot: "VectorstoreSnapshot") -> "VectorstoreApiSnapshot":
        """
        The contract's model of a vectorstore's snapshot.

        :param snapshot: The row.
        :type snapshot: smarter.apps.vectorstore.models.VectorstoreSnapshot
        :returns: The model.
        :rtype: VectorstoreApiSnapshot
        """
        return cls(
            id=snapshot.pk,
            hashed_id=snapshot.hashed_id,
            created_at=snapshot.created_at,
            updated_at=snapshot.updated_at,
            name=snapshot.name,
            status=snapshot.status,  # type: ignore[arg-type]
            status_message=snapshot.status_message,
            size_bytes=snapshot.size_bytes,
            vector_count=snapshot.vector_count,
            scheduled=snapshot.scheduled,
        )


class VectorstoreApiSnapshots(AccountApiModel):
    """A vectorstore's snapshots."""

    snapshots: list[VectorstoreApiSnapshot]


class VectorstoreApiRestored(AccountApiModel):
    """A vectorstore whose data was replaced with one of its snapshots."""

    vectorstore: str = Field(..., description="The vectorstore's name.")
    restored: str = Field(..., description="The snapshot's name.")
    vector_count: int = Field(..., description="The number of its vectors now.")


VECTORSTORE_API_MODELS = (
    VectorstoreApiVectorstore,
    VectorstoreApiStatus,
    VectorstoreApiDocuments,
    VectorstoreApiAddText,
    VectorstoreApiDocumentsAdded,
    VectorstoreApiDocumentDeleted,
    VectorstoreApiSearch,
    VectorstoreApiSearchResults,
    VectorstoreApiSnapshot,
    VectorstoreApiSnapshots,
    VectorstoreApiRestored,
)
"""The models whose JSON Schemas the Smarter api's OpenAPI document includes.

Their dependencies are included with them.
"""

__all__ = [
    "VECTORSTORE_API_MODELS",
    "VectorstoreApiAddText",
    "VectorstoreApiBackend",
    "VectorstoreApiDocument",
    "VectorstoreApiDocumentDeleted",
    "VectorstoreApiDocumentSource",
    "VectorstoreApiDocumentStatus",
    "VectorstoreApiDocuments",
    "VectorstoreApiDocumentsAdded",
    "VectorstoreApiHosting",
    "VectorstoreApiMetric",
    "VectorstoreApiRestored",
    "VectorstoreApiSearch",
    "VectorstoreApiSearchResult",
    "VectorstoreApiSearchResults",
    "VectorstoreApiSearchType",
    "VectorstoreApiSnapshot",
    "VectorstoreApiSnapshotStatus",
    "VectorstoreApiSnapshots",
    "VectorstoreApiStatus",
    "VectorstoreApiStatusValue",
    "VectorstoreApiVectorstore",
]
