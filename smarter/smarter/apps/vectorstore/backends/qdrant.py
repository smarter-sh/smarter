"""
The Qdrant backend: self-hosted on Kubernetes, or Qdrant Cloud.

See https://qdrant.tech/. A vectorstore is one Qdrant collection, with one dense vector per
chunk. Its text is in the payload's ``page_content``, and its metadata in ``metadata``,
as LangChain's QdrantVectorStore stores them, so that its collections stay readable.

Every operation is one of :mod:`smarter.apps.vectorstore.execution`'s. The texts are embedded here, in the app. A Qdrant
Cloud collection, at its ApiConnection's url, is reached through the tool runner, in the tool worker (ADR-038); a
self-hosted server, which Smarter runs in the cluster, in process.
"""

from typing import Optional

from langchain_core.embeddings import Embeddings
from qdrant_client import QdrantClient

from smarter.apps.vectorstore.deployment import FALSE, SERVER, TRUE, VOLUME
from smarter.apps.vectorstore.execution import (
    QDRANT,
    QDRANT_TIMEOUT,
    qdrant_filter,
    run_vectorstore_operation,
)
from smarter.apps.vectorstore.kubernetes import (
    SNAPSHOTS_PATH,
    QdrantKubernetes,
    QdrantObservation,
)
from smarter.apps.vectorstore.manifest.models.vectorstore.status import (
    SAMVectorstoreCondition,
)
from smarter.apps.vectorstore.models import VectorstoreMeta
from smarter.lib.typing import SmarterDictType

from .base import (
    SearchResult,
    SmarterVectorstoreBackend,
    SnapshotInfo,
    VectorStoreBackendConnectionError,
    VectorStoreBackendError,
    json_dict,
    json_dicts,
    json_int,
    mmr_fetch_k,
    result_of,
    select_mmr,
)

RESTORE_TIMEOUT_SECONDS = 600.0
"""How long recovering a snapshot may take."""


def condition_of(condition_type, observation: QdrantObservation) -> SAMVectorstoreCondition:
    """
    Return the condition of an observation of a self-hosted server's volume or pod.

    :param condition_type: ``Volume`` or ``Server``.
    :param observation: What Kubernetes reported.
    :returns: The condition, which is met if the observation is ready.
    """
    status = TRUE if observation.ready else FALSE
    condition = SAMVectorstoreCondition(
        type=condition_type, status=status, reason=observation.reason, message=observation.message
    )
    return condition


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
        """The Kubernetes resources of the self-hosted Qdrant server, created when it is first used."""
        if self._kubernetes is None:
            self._kubernetes = QdrantKubernetes(self.vectorstore)
        return self._kubernetes

    @property
    def client(self) -> QdrantClient:
        """
        The Qdrant client of a self-hosted server, created when it is first used, or the one a test injected.

        A self-hosted server is reached at its in-cluster endpoint, with its generated API key. A Qdrant Cloud
        collection has no client here: its operations go to the tool runner (:meth:`operation`).

        :raises VectorStoreBackendError: For a Qdrant Cloud vectorstore without an injected client.
        """
        if self._client is None:
            if not self.vectorstore.is_self_hosted:
                raise VectorStoreBackendError(
                    f"Vectorstore {self.vectorstore.name} is Qdrant Cloud, which the tool runner reaches, not the app."
                )
            api_key: Optional[str] = None
            secret = self.vectorstore.api_key_secret
            if secret:
                api_key = secret.get_secret()
            self._client = QdrantClient(url=self.kubernetes.endpoint, api_key=api_key, timeout=QDRANT_TIMEOUT)
        return self._client

    def managed_url_and_api_key(self) -> tuple[str, str]:
        """
        The url and the api key of a Qdrant Cloud vectorstore's ApiConnection, read here, in the app.

        :raises VectorStoreBackendConnectionError: If the vectorstore has no ApiConnection url.
        """
        connection = self.vectorstore.connection
        if connection is None or not connection.base_url:
            raise VectorStoreBackendConnectionError(f"Vectorstore {self.vectorstore.name} has no ApiConnection URL.")
        api_key = ""
        if connection.api_key:
            api_key = connection.api_key.get_secret() or ""
        return connection.base_url, api_key

    def operation(self, name: str, params: Optional[SmarterDictType] = None, timeout: float = QDRANT_TIMEOUT):
        """
        Run one of the collection's operations: in process on a self-hosted server, or through the tool runner for Qdrant Cloud.

        :param name: The operation, e.g. ``exists``.
        :param params: Its parameters, as JSON.
        :param timeout: Seconds that it may take.
        :returns: Its result.
        :raises VectorStoreBackendError: If it fails, classified as credentials, rejected or connection.
        """
        if self._client is not None or self.vectorstore.is_self_hosted:
            return run_vectorstore_operation(
                QDRANT, name, params, index_name=self.index_name, client=self.client, timeout=timeout
            )
        url, api_key = self.managed_url_and_api_key()
        return run_vectorstore_operation(
            QDRANT, name, params, index_name=self.index_name, url=url, api_key=api_key, timeout=timeout
        )

    # --- lifecycle --------------------------------------------------------------
    def check_credentials(self) -> str:
        """
        Check that Qdrant accepts the vectorstore's credentials.

        A self-hosted server's api key is generated by Smarter, and the server doesn't exist yet, so
        only Qdrant Cloud is asked.

        :returns: What was found, for a person.
        :raises VectorStoreBackendCredentialsError: If Qdrant Cloud refuses the api key.
        :raises VectorStoreBackendConnectionError: If Qdrant Cloud can't be reached.
        """
        if self.vectorstore.is_self_hosted:
            return "Smarter generated the server's api key."
        self.exists()
        return "Qdrant accepted the api key."

    def provision(self) -> None:
        """
        Create, or update, the Kubernetes resources of a self-hosted Qdrant server, without waiting for it.

        Nothing is done for Qdrant Cloud.

        :raises VectorStoreBackendError: If a self-hosted vectorstore has no API key Secret.
        """
        if self.vectorstore.is_self_hosted:
            secret = self.vectorstore.api_key_secret
            if secret is None:
                raise VectorStoreBackendError(f"Vectorstore {self.vectorstore.name} has no API key Secret.")
            self.kubernetes.apply(secret.get_secret() or "")

    def infrastructure_conditions(self) -> list[SAMVectorstoreCondition]:
        """
        The conditions of a self-hosted Qdrant server: its volume, then its pod.

        Qdrant Cloud has none.

        :returns: The ``Volume`` and ``Server`` conditions, or an empty list.
        """
        if not self.vectorstore.is_self_hosted:
            return []
        volume = condition_of(VOLUME, self.kubernetes.observe_volume())
        server = condition_of(SERVER, self.kubernetes.observe())
        return [volume, server]

    def stop(self) -> None:
        """Stop a self-hosted Qdrant server, keeping its volume and data."""
        if self.vectorstore.is_self_hosted:
            self.kubernetes.stop()

    def exists(self) -> bool:
        """
        Whether the Qdrant collection exists.

        :raises VectorStoreBackendCredentialsError: If Qdrant refuses the api key.
        :raises VectorStoreBackendConnectionError: If Qdrant is unreachable.
        """
        return bool(self.operation("exists"))

    def create(self) -> None:
        """Create the Qdrant collection, with a payload index on each chunk's document id."""
        self.operation("create", {"dimension": self.vectorstore.dimension, "metric": self.vectorstore.metric})

    def drop(self) -> None:
        """Delete the Qdrant collection, if it exists, and its data."""
        self.operation("drop")

    def destroy(self) -> None:
        """
        Delete the collection, or, if self-hosted, the whole Qdrant server and its volume.

        The collection goes with the server's volume.
        """
        if self.vectorstore.is_self_hosted:
            # the collection goes with the server's volume.
            self.kubernetes.destroy()
            return
        self.drop()

    def stats(self) -> SmarterDictType:
        """The collection's exact vector count, status, segments count and indexed vectors count."""
        stats = json_dict(self.operation("stats"))
        return stats

    # --- data -------------------------------------------------------------------
    def upsert(self, ids: list[str], texts: list[str], metadatas: list[SmarterDictType], batch_size: int = 64) -> None:
        """
        Embed, here, and insert, or replace, chunks, a batch at a time.

        :param ids: The chunks' ids.
        :param texts: The chunks' texts.
        :param metadatas: The chunks' metadata.
        :param batch_size: How many chunks to embed and upsert at a time.
        """
        for start in range(0, len(texts), batch_size):
            end = start + batch_size
            batch_texts = texts[start:end]
            vectors = self.embeddings.embed_documents(batch_texts)
            params: SmarterDictType = {
                "ids": ids[start:end],
                "vectors": vectors,
                "texts": batch_texts,
                "metadatas": metadatas[start:end],
            }
            self.operation("upsert", params)

    def delete(self, ids: list[str]) -> None:
        """
        Delete chunks by id.

        Ids that do not exist are ignored.

        :param ids: The chunks' ids.
        """
        if ids:
            self.operation("delete", {"ids": ids})

    def delete_document(self, document_id: int) -> None:
        """Delete every chunk of a document, whatever their number."""
        self.operation("delete_document", {"document_id": document_id})

    def search(  # pylint: disable=too-many-positional-arguments,too-many-arguments
        self,
        query: str,
        k: int = 4,
        search_type: str = "similarity",
        score_threshold: Optional[float] = None,
        fetch_k: Optional[int] = None,
        lambda_mult: Optional[float] = None,
        metadata_filter: Optional[SmarterDictType] = None,
    ) -> list[SearchResult]:
        """
        Find the chunks that are closest in meaning to a query, embedded here.

        :param query: The query.
        :param k: How many results.
        :param search_type: ``similarity``, ``similarity_score_threshold``, or ``mmr`` (maximal marginal relevance).
        :param score_threshold: The lowest score of a result, for ``similarity_score_threshold``.
        :param fetch_k: How many candidates MMR re-ranks. By default, four times ``k``, and at least 20.
        :param lambda_mult: MMR's balance of relevance, 1, and diversity, 0. By default 0.5.
        :param metadata_filter: Chunks whose metadata has these values, e.g. ``{"source": "faq"}``.
        :returns: The results. MMR's have no score.
        """
        vector = self.embeddings.embed_query(query)
        params: SmarterDictType = {"vector": vector, "filter": metadata_filter}
        if search_type == "mmr":
            params.update({"limit": mmr_fetch_k(k, fetch_k), "with_vectors": True})
            matches = json_dicts(self.operation("query", params))
            return select_mmr(vector, matches, k, lambda_mult)
        params["limit"] = k
        if search_type == "similarity_score_threshold":
            params["score_threshold"] = score_threshold
        matches = json_dicts(self.operation("query", params))
        results = [result_of(match, score=match.get("score")) for match in matches]
        return results

    # --- dumps ------------------------------------------------------------------
    def create_snapshot(self, name: str) -> SnapshotInfo:
        """
        Take a snapshot of the collection, and wait for it.

        :param name: Unused: Qdrant names the snapshot.
        :returns: The snapshot's name and size.
        :raises VectorStoreBackendError: If Qdrant did not create it.
        """
        description = json_dict(self.operation("create_snapshot", timeout=RESTORE_TIMEOUT_SECONDS))
        if not description.get("name"):
            raise VectorStoreBackendError(f"Qdrant did not create a snapshot of {self.index_name}.")
        return SnapshotInfo(name=str(description["name"]), size_bytes=json_int(description.get("size_bytes")))

    def delete_snapshot(self, name: str) -> None:
        """
        Delete a snapshot of the collection, and wait for it.

        :param name: The snapshot's name.
        """
        self.operation("delete_snapshot", {"name": name})

    def restore_snapshot(self, name: str) -> None:
        """
        Recover the collection from a snapshot on the self-hosted server's volume, and wait for it.

        :param name: The snapshot's name.
        :raises VectorStoreBackendError: For Qdrant Cloud, whose snapshots are restored in its console.
        """
        if not self.vectorstore.is_self_hosted:
            raise VectorStoreBackendError(
                "Restoring a Qdrant Cloud snapshot is done in the Qdrant Cloud console, where its snapshots are kept."
            )
        location = f"file://{SNAPSHOTS_PATH}/{self.index_name}/{name}"
        self.operation("restore_snapshot", {"location": location}, timeout=RESTORE_TIMEOUT_SECONDS)

    def logs(self, tail: int = 200) -> Optional[str]:
        """
        Return the self-hosted Qdrant server's recent logs.

        :param tail: How many lines of each pod.
        :returns: The logs, or None for Qdrant Cloud.
        """
        return self.kubernetes.logs(tail) if self.vectorstore.is_self_hosted else None


__all__ = ["QdrantBackend", "qdrant_filter"]
