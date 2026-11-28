"""
The Pinecone backend: a managed service.

See https://www.pinecone.io/. A vectorstore is one serverless Pinecone index. Its API key is
the Secret of the vectorstore's ApiConnection. The backend embeds the chunks itself, here, in the app, and sends each
operation, one of :mod:`smarter.apps.vectorstore.execution`'s, through the tool runner, which calls Pinecone from the
tool worker (ADR-038). The chunks' text is in the metadata's ``text``, where LangChain's
PineconeVectorStore stores it, so indexes that it wrote stay searchable. Dumps are Pinecone backups, which Pinecone keeps,
and which require a paid Pinecone plan.
"""

from typing import Any, Optional

from langchain_core.embeddings import Embeddings

from smarter.apps.vectorstore.execution import (
    PINECONE,
    pinecone_error,
    run_vectorstore_operation,
)
from smarter.apps.vectorstore.execution import PINECONE_DONT_WAIT as DONT_WAIT
from smarter.apps.vectorstore.models import VectorstoreMeta
from smarter.common.conf import smarter_settings
from smarter.lib.typing import SmarterDictType

from .base import (
    SearchResult,
    SmarterVectorstoreBackend,
    SnapshotInfo,
    VectorStoreBackendCredentialsError,
    VectorStoreBackendError,
    json_dict,
    json_dicts,
    json_int,
    mmr_fetch_k,
    result_of,
    select_mmr,
)

RESTORE_TIMEOUT_SECONDS = 600.0
"""How long restoring a backup may take: Pinecone deletes the index, then creates it again."""


class PineconeBackend(SmarterVectorstoreBackend):
    """
    The Pinecone backend.

    :param client: A Pinecone client, e.g. a mock in tests, which the operations run on in this process. By default
        there is none, and each operation goes through the tool runner, with the API key of the vectorstore's
        ApiConnection.
    """

    def __init__(
        self,
        vectorstore: VectorstoreMeta,
        embeddings: Optional[Embeddings] = None,
        client: Any = None,
    ):
        super().__init__(vectorstore, embeddings)
        self._client = client

    def api_key(self) -> str:
        """
        The API key of the vectorstore's ApiConnection, read here, in the app.

        :raises VectorStoreBackendCredentialsError: If the vectorstore has no ApiConnection with an API key.
        """
        connection = self.vectorstore.connection
        api_key = None
        if connection and connection.api_key:
            api_key = connection.api_key.get_secret()
        if not api_key:
            raise VectorStoreBackendCredentialsError(
                f"Vectorstore {self.vectorstore.name} has no ApiConnection with a Pinecone API key."
            )
        return api_key

    def operation(self, name: str, params: Optional[SmarterDictType] = None, timeout: float = 30.0):
        """
        Run one of the index's operations: through the tool runner, or in process on an injected client.

        :param name: The operation, e.g. ``exists``.
        :param params: Its parameters, as JSON.
        :param timeout: Seconds that it may take.
        :returns: Its result.
        :raises VectorStoreBackendError: If it fails, classified as credentials, rejected or connection.
        """
        if self._client is not None:
            return run_vectorstore_operation(
                PINECONE, name, params, index_name=self.index_name, client=self._client, timeout=timeout
            )
        return run_vectorstore_operation(
            PINECONE, name, params, index_name=self.index_name, api_key=self.api_key(), timeout=timeout
        )

    def deletion_protection(self) -> str:
        """Pinecone's deletion protection of the index: ``enabled`` if the vectorstore has it."""
        return "enabled" if self.vectorstore.deletion_protection else "disabled"

    # --- lifecycle --------------------------------------------------------------
    def check_credentials(self) -> str:
        """
        Check that Pinecone accepts the api key, by asking whether the index exists.

        :returns: What was found, for a person.
        :raises VectorStoreBackendCredentialsError: If Pinecone refuses the api key.
        :raises VectorStoreBackendConnectionError: If Pinecone can't be reached.
        """
        self.exists()
        return "Pinecone accepted the api key."

    def index_ready(self) -> tuple[bool, str]:
        """Whether the index, which exists, is ready.

        Pinecone takes a minute or two to initialize a new one.
        """
        if self.operation("index_ready"):
            return True, ""
        return False, "Pinecone is initializing the index."

    def exists(self) -> bool:
        """
        Whether the Pinecone index exists.

        :raises VectorStoreBackendCredentialsError: If Pinecone refuses the api key.
        :raises VectorStoreBackendConnectionError: If Pinecone is unreachable.
        """
        return bool(self.operation("exists"))

    def create(self) -> None:
        """
        Create a serverless Pinecone index, in the cloud and region of the spec's ``pinecone``.

        It is tagged with the platform's name and the vectorstore's id, and has deletion protection if the
        vectorstore has. It returns at once: Pinecone initializes the index for a minute or two, which
        :meth:`index_ready` reports, rather than holding a request or a worker while it does.

        :raises VectorStoreBackendError: If Pinecone did not create it, as :func:`pinecone_error` classifies it.
        """
        spec = self.vectorstore.spec or {}
        config = spec.get("pinecone") or {}
        params: SmarterDictType = {
            "cloud": config.get("cloud", "aws"),
            "region": config.get("region", "us-east-1"),
            "dimension": self.vectorstore.dimension,
            "metric": self.vectorstore.metric,
            "deletion_protection": self.deletion_protection(),
            "tags": {"created_by": smarter_settings.platform_name, "vectorstore": str(self.vectorstore.pk)},
        }
        self.operation("create", params)

    def drop(self) -> None:
        """Delete the Pinecone index, if it exists, and its data.

        It returns at once, while Pinecone deletes the index.
        """
        self.operation("drop")

    def stats(self) -> SmarterDictType:
        """The index's vector count, dimension and fullness, from Pinecone."""
        stats = json_dict(self.operation("stats"))
        return stats

    # --- data -------------------------------------------------------------------
    def upsert(self, ids: list[str], texts: list[str], metadatas: list[SmarterDictType], batch_size: int = 64) -> None:
        """
        Embed the texts, here, and upsert them in batches, with each text in its metadata's ``text``.

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
        Search the index with the query's embedding, computed here.

        Scores are Pinecone's raw scores for the index's metric. MMR re-ranks ``fetch_k`` matches
        for diversity, and its results have no score.

        :param query: The text to search for.
        :param k: How many results to return.
        :param search_type: ``similarity``, ``similarity_score_threshold`` or ``mmr``.
        :param score_threshold: For ``similarity_score_threshold``, the lowest score to keep. A result
            without a score is dropped.
        :param fetch_k: For ``mmr``, how many matches to re-rank. Defaults to ``max(20, k * 4)``.
        :param lambda_mult: For ``mmr``, from 0 (most diverse) to 1 (most relevant). Defaults to 0.5.
        :param metadata_filter: A Pinecone metadata filter.
        :returns: The matching chunks, best first.
        """
        vector = self.embeddings.embed_query(query)
        params: SmarterDictType = {"vector": vector, "filter": metadata_filter}
        if search_type == "mmr":
            params.update({"limit": mmr_fetch_k(k, fetch_k), "with_vectors": True})
            matches = json_dicts(self.operation("query", params))
            return select_mmr(vector, matches, k, lambda_mult)
        params["limit"] = k
        threshold: Optional[float] = None
        if search_type == "similarity_score_threshold":
            threshold = score_threshold
        results: list[SearchResult] = []
        for match in json_dicts(self.operation("query", params)):
            result = result_of(match, score=match.get("score"))
            if threshold is not None:
                if result.score is None:
                    continue
                if result.score < threshold:
                    continue
            results.append(result)
        return results

    # --- dumps ------------------------------------------------------------------
    def create_snapshot(self, name: str) -> SnapshotInfo:
        """
        Back up the index, with Pinecone's backups.

        :param name: The backup's name.
        :returns: The backup's id, size, and whether it is ready.
        :raises VectorStoreBackendError: If Pinecone did not back it up.
        """
        params: SmarterDictType = {"name": name, "description": f"{smarter_settings.platform_name} backup"}
        try:
            backup = self.operation("create_snapshot", params)
        except VectorStoreBackendError as e:
            raise VectorStoreBackendError(f"Pinecone did not back up {self.index_name}: {e}") from e
        data = json_dict(backup)
        return SnapshotInfo(
            name=str(data.get("name") or name),
            size_bytes=json_int(data.get("size_bytes")),
            ready=str(data.get("status", "Ready")).lower() == "ready",
        )

    def delete_snapshot(self, name: str) -> None:
        """
        Delete a Pinecone backup.

        :param name: The backup's id.
        """
        self.operation("delete_snapshot", {"name": name})

    def restore_snapshot(self, name: str) -> None:
        """Replace the index with a new one from the backup.

        Pinecone requires that the index is deleted first, so this waits until it is.
        """
        params: SmarterDictType = {"name": name, "deletion_protection": self.deletion_protection()}
        self.operation("restore_snapshot", params, timeout=RESTORE_TIMEOUT_SECONDS)


__all__ = ["DONT_WAIT", "PineconeBackend", "pinecone_error"]
