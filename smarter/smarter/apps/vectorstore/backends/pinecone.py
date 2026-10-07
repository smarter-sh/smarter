"""
The Pinecone backend: a managed service.

See https://www.pinecone.io/. A vectorstore is one serverless Pinecone index. Its API key is
the Secret of the vectorstore's ApiConnection. The chunks' text is in the metadata's ``text``,
as LangChain's PineconeVectorStore stores it. Dumps are Pinecone backups, which Pinecone keeps,
and which require a paid Pinecone plan.
"""

from typing import Any, Optional

from langchain_community.vectorstores.utils import DistanceStrategy
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone
from pinecone.db_control.models import ServerlessSpec

from smarter.apps.vectorstore.models import VectorstoreMeta
from smarter.common.conf import smarter_settings

from .base import (
    SearchResult,
    SmarterVectorstoreBackend,
    SnapshotInfo,
    VectorStoreBackendConnectionError,
    VectorStoreBackendError,
)

DISTANCE_STRATEGIES = {
    "cosine": DistanceStrategy.COSINE,
    "euclidean": DistanceStrategy.EUCLIDEAN_DISTANCE,
    "dotproduct": DistanceStrategy.DOT_PRODUCT,
}
TEXT_KEY = "text"


class PineconeBackend(SmarterVectorstoreBackend):
    """
    The Pinecone backend.

    :param client: A Pinecone client, e.g. a mock in tests. By default it is created with the API
        key of the vectorstore's ApiConnection.
    """

    def __init__(
        self,
        vectorstore: VectorstoreMeta,
        embeddings: Optional[Embeddings] = None,
        client: Optional[Pinecone] = None,
    ):
        super().__init__(vectorstore, embeddings)
        self._client = client
        self._index = None

    @property
    def client(self) -> Pinecone:
        if self._client is None:
            connection = self.vectorstore.connection
            api_key = connection.api_key.get_secret() if connection and connection.api_key else None
            if not api_key:
                raise VectorStoreBackendConnectionError(
                    f"Vectorstore {self.vectorstore.name} has no ApiConnection with a Pinecone API key."
                )
            self._client = Pinecone(api_key=api_key)
        return self._client

    @property
    def index(self):
        if self._index is None:
            self._index = self.client.Index(name=self.index_name)
        return self._index

    def vector_store(self) -> PineconeVectorStore:
        return PineconeVectorStore(
            index=self.index,
            embedding=self.embeddings,
            text_key=TEXT_KEY,
            distance_strategy=DISTANCE_STRATEGIES[self.vectorstore.metric],
        )

    # --- lifecycle --------------------------------------------------------------
    def infrastructure_ready(self) -> tuple[bool, str]:
        """Whether the index is ready.

        Pinecone takes a little while to initialize a new one.
        """
        if not self.exists():
            return True, ""
        status = self.client.describe_index(self.index_name).status
        ready = status.get("ready") if isinstance(status, dict) else getattr(status, "ready", True)
        return bool(ready), "" if ready else "Pinecone is initializing the index."

    def exists(self) -> bool:
        try:
            return self.client.has_index(self.index_name)
        except Exception as e:
            raise VectorStoreBackendConnectionError(f"Pinecone is unreachable: {e}") from e

    def create(self) -> None:
        config = (self.vectorstore.spec or {}).get("pinecone") or {}
        self.client.create_index(
            name=self.index_name,
            spec=ServerlessSpec(cloud=config.get("cloud", "aws"), region=config.get("region", "us-east-1")),
            dimension=self.vectorstore.dimension,
            metric=self.vectorstore.metric,
            deletion_protection="enabled" if self.vectorstore.deletion_protection else "disabled",
            tags={"created_by": smarter_settings.platform_name, "vectorstore": str(self.vectorstore.pk)},
        )

    def drop(self) -> None:
        if self.exists():
            self.client.delete_index(self.index_name)
        self._index = None

    def stats(self) -> dict[str, Any]:
        stats = self.index.describe_index_stats()
        stats = stats.to_dict() if hasattr(stats, "to_dict") else dict(stats)
        return {
            "vector_count": stats.get("total_vector_count", 0),
            "dimension": stats.get("dimension"),
            "index_fullness": stats.get("index_fullness"),
        }

    # --- data -------------------------------------------------------------------
    def upsert(self, ids: list[str], texts: list[str], metadatas: list[dict[str, Any]], batch_size: int = 64) -> None:
        self.vector_store().add_texts(
            texts=texts, metadatas=metadatas, ids=ids, batch_size=batch_size, embedding_chunk_size=batch_size
        )

    def delete(self, ids: list[str]) -> None:
        if ids:
            self.index.delete(ids=ids)

    def search(  # pylint: disable=too-many-positional-arguments,too-many-arguments
        self,
        query: str,
        k: int = 4,
        search_type: str = "similarity",
        score_threshold: Optional[float] = None,
        fetch_k: Optional[int] = None,
        lambda_mult: Optional[float] = None,
        metadata_filter: Optional[dict[str, Any]] = None,
    ) -> list[SearchResult]:
        store = self.vector_store()
        if search_type == "mmr":
            documents = store.max_marginal_relevance_search(
                query, k=k, fetch_k=fetch_k or max(20, k * 4), lambda_mult=lambda_mult or 0.5, filter=metadata_filter
            )
            return [self._result(document, None) for document in documents]
        pairs = store.similarity_search_with_score(query, k=k, filter=metadata_filter)
        if search_type == "similarity_score_threshold" and score_threshold is not None:
            pairs = [(document, score) for document, score in pairs if score >= score_threshold]
        return [self._result(document, score) for document, score in pairs]

    @staticmethod
    def _result(document: Document, score: Optional[float]) -> SearchResult:
        return SearchResult(
            id=document.id, text=document.page_content, metadata=dict(document.metadata or {}), score=score
        )

    # --- dumps ------------------------------------------------------------------
    def create_snapshot(self, name: str) -> SnapshotInfo:
        try:
            backup = self.client.create_backup(
                index_name=self.index_name, backup_name=name, description=f"{smarter_settings.platform_name} backup"
            )
        except Exception as e:
            raise VectorStoreBackendError(f"Pinecone did not back up {self.index_name}: {e}") from e
        data = backup.to_dict() if hasattr(backup, "to_dict") else {}
        return SnapshotInfo(
            name=data.get("backup_id") or name,
            size_bytes=data.get("size_bytes"),
            ready=str(data.get("status", "Ready")).lower() == "ready",
        )

    def delete_snapshot(self, name: str) -> None:
        self.client.delete_backup(backup_id=name)

    def restore_snapshot(self, name: str) -> None:
        """Replace the index with a new one from the backup.

        Pinecone requires that the index is deleted first.
        """
        self.drop()
        self.client.create_index_from_backup(
            name=self.index_name,
            backup_id=name,
            deletion_protection="enabled" if self.vectorstore.deletion_protection else "disabled",
        )


__all__ = ["PineconeBackend"]
