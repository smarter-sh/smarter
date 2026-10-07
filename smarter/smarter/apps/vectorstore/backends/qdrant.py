"""
The Qdrant backend: self-hosted on Kubernetes, or Qdrant Cloud.

See https://qdrant.tech/. A vectorstore is one Qdrant collection, with one dense vector per
chunk. Its text is in the payload's ``page_content``, and its metadata in ``metadata``,
as LangChain's QdrantVectorStore stores them.
"""

from typing import Any, Optional

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient, models

from smarter.apps.vectorstore.kubernetes import SNAPSHOTS_PATH, QdrantKubernetes
from smarter.apps.vectorstore.models import VectorstoreMeta

from .base import (
    SearchResult,
    SmarterVectorstoreBackend,
    SnapshotInfo,
    VectorStoreBackendConnectionError,
    VectorStoreBackendError,
)

TIMEOUT = 30
DISTANCES = {
    "cosine": models.Distance.COSINE,
    "euclidean": models.Distance.EUCLID,
    "dotproduct": models.Distance.DOT,
}
DOCUMENT_ID_KEY = "metadata.document_id"


def qdrant_filter(metadata_filter: Optional[dict[str, Any]]) -> Optional[models.Filter]:
    """A Qdrant filter that matches chunks whose metadata has every value of metadata_filter."""
    if not metadata_filter:
        return None
    return models.Filter(
        must=[
            models.FieldCondition(key=f"metadata.{key}", match=models.MatchValue(value=value))
            for key, value in metadata_filter.items()
        ]
    )


class QdrantBackend(SmarterVectorstoreBackend):
    """
    The Qdrant backend.

    :param client: A QdrantClient, e.g. an in-memory one in tests. By default it connects to the
        self-hosted server, or to the managed service of the vectorstore's ApiConnection.
    :param kubernetes: The QdrantKubernetes of a self-hosted server. Created if needed.
    """

    def __init__(
        self,
        vectorstore: VectorstoreMeta,
        embeddings: Optional[Embeddings] = None,
        client: Optional[QdrantClient] = None,
        kubernetes: Optional[QdrantKubernetes] = None,
    ):
        super().__init__(vectorstore, embeddings)
        self._client = client
        self._kubernetes = kubernetes

    @property
    def kubernetes(self) -> QdrantKubernetes:
        if self._kubernetes is None:
            self._kubernetes = QdrantKubernetes(self.vectorstore)
        return self._kubernetes

    @property
    def client(self) -> QdrantClient:
        if self._client is None:
            url, api_key = self._url_and_api_key()
            self._client = QdrantClient(url=url, api_key=api_key, timeout=TIMEOUT)
        return self._client

    def _url_and_api_key(self) -> tuple[str, Optional[str]]:
        vectorstore = self.vectorstore
        if vectorstore.is_self_hosted:
            secret = vectorstore.api_key_secret
            return self.kubernetes.endpoint, secret.get_secret() if secret else None
        connection = vectorstore.connection
        if connection is None or not connection.base_url:
            raise VectorStoreBackendConnectionError(f"Vectorstore {vectorstore.name} has no ApiConnection URL.")
        return connection.base_url, connection.api_key.get_secret() if connection.api_key else None

    def vector_store(self) -> QdrantVectorStore:
        return QdrantVectorStore(
            client=self.client,
            collection_name=self.index_name,
            embedding=self.embeddings,
            distance=DISTANCES[self.vectorstore.metric],
        )

    # --- lifecycle --------------------------------------------------------------
    def provision(self) -> None:
        if self.vectorstore.is_self_hosted:
            secret = self.vectorstore.api_key_secret
            if secret is None:
                raise VectorStoreBackendError(f"Vectorstore {self.vectorstore.name} has no API key Secret.")
            self.kubernetes.apply(secret.get_secret() or "")

    def infrastructure_ready(self) -> tuple[bool, str]:
        if not self.vectorstore.is_self_hosted:
            return True, ""
        observation = self.kubernetes.observe()
        return observation.ready, observation.message

    def stop(self) -> None:
        if self.vectorstore.is_self_hosted:
            self.kubernetes.stop()

    def exists(self) -> bool:
        try:
            return self.client.collection_exists(self.index_name)
        except Exception as e:
            raise VectorStoreBackendConnectionError(f"Qdrant is unreachable: {e}") from e

    def create(self) -> None:
        self.client.create_collection(
            collection_name=self.index_name,
            vectors_config=models.VectorParams(
                size=self.vectorstore.dimension, distance=DISTANCES[self.vectorstore.metric]
            ),
        )
        # chunks are found by document when a document is deleted, or loaded again.
        self.client.create_payload_index(
            collection_name=self.index_name,
            field_name=DOCUMENT_ID_KEY,
            field_schema=models.PayloadSchemaType.INTEGER,
        )

    def drop(self) -> None:
        if self.exists():
            self.client.delete_collection(self.index_name)

    def destroy(self) -> None:
        if self.vectorstore.is_self_hosted:
            # the collection goes with the server's volume.
            self.kubernetes.destroy()
            return
        self.drop()

    def stats(self) -> dict[str, Any]:
        info = self.client.get_collection(self.index_name)
        return {
            "vector_count": self.client.count(self.index_name, exact=True).count,
            "status": str(getattr(info.status, "value", info.status)),
            "segments_count": info.segments_count,
            "indexed_vectors_count": info.indexed_vectors_count,
        }

    # --- data -------------------------------------------------------------------
    def upsert(self, ids: list[str], texts: list[str], metadatas: list[dict[str, Any]], batch_size: int = 64) -> None:
        self.vector_store().add_texts(texts=texts, metadatas=metadatas, ids=ids, batch_size=batch_size)

    def delete(self, ids: list[str]) -> None:
        if ids:
            self.client.delete(self.index_name, points_selector=models.PointIdsList(points=ids))

    def delete_document(self, document_id: int) -> None:
        """Delete every chunk of a document, whatever their number."""
        self.client.delete(
            self.index_name,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[models.FieldCondition(key=DOCUMENT_ID_KEY, match=models.MatchValue(value=document_id))]
                )
            ),
        )

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
        query_filter = qdrant_filter(metadata_filter)
        if search_type == "mmr":
            documents = store.max_marginal_relevance_search(
                query, k=k, fetch_k=fetch_k or max(20, k * 4), lambda_mult=lambda_mult or 0.5, filter=query_filter
            )
            return [self._result(document, None) for document in documents]
        threshold = score_threshold if search_type == "similarity_score_threshold" else None
        pairs = store.similarity_search_with_score(query, k=k, filter=query_filter, score_threshold=threshold)
        return [self._result(document, score) for document, score in pairs]

    @staticmethod
    def _result(document: Document, score: Optional[float]) -> SearchResult:
        metadata = dict(document.metadata or {})
        point_id = document.id or metadata.pop("_id", None)
        metadata.pop("_collection_name", None)
        return SearchResult(
            id=str(point_id) if point_id else None, text=document.page_content, metadata=metadata, score=score
        )

    # --- dumps ------------------------------------------------------------------
    def create_snapshot(self, name: str) -> SnapshotInfo:
        description = self.client.create_snapshot(self.index_name, wait=True)
        if description is None:
            raise VectorStoreBackendError(f"Qdrant did not create a snapshot of {self.index_name}.")
        return SnapshotInfo(name=description.name, size_bytes=description.size)

    def delete_snapshot(self, name: str) -> None:
        self.client.delete_snapshot(self.index_name, name, wait=True)

    def restore_snapshot(self, name: str) -> None:
        if not self.vectorstore.is_self_hosted:
            raise VectorStoreBackendError(
                "Restoring a Qdrant Cloud snapshot is done in the Qdrant Cloud console, where its snapshots are kept."
            )
        location = f"file://{SNAPSHOTS_PATH}/{self.index_name}/{name}"
        self.client.recover_snapshot(self.index_name, location=location, wait=True)

    def logs(self, tail: int = 200) -> Optional[str]:
        return self.kubernetes.logs(tail) if self.vectorstore.is_self_hosted else None


__all__ = ["QdrantBackend", "qdrant_filter"]
