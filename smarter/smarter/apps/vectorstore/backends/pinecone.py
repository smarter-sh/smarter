"""
The Pinecone backend: a managed service.

See https://www.pinecone.io/. A vectorstore is one serverless Pinecone index. Its API key is
the Secret of the vectorstore's ApiConnection. The backend embeds the chunks itself and calls the
Pinecone index directly. The chunks' text is in the metadata's ``text``, where LangChain's
PineconeVectorStore stores it, so indexes that it wrote stay searchable. Dumps are Pinecone backups, which Pinecone keeps,
and which require a paid Pinecone plan.
"""

from typing import TYPE_CHECKING, Optional

import numpy as np
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores.utils import maximal_marginal_relevance
from pinecone import Pinecone
from pinecone.db_control.models import ServerlessSpec
from pinecone.exceptions import (
    ForbiddenException,
    PineconeApiException,
    UnauthorizedException,
)

from smarter.apps.vectorstore.models import VectorstoreMeta
from smarter.common.conf import smarter_settings
from smarter.lib.typing import SmarterDictType

from .base import (
    SearchResult,
    SmarterVectorstoreBackend,
    SnapshotInfo,
    VectorStoreBackendConnectionError,
    VectorStoreBackendCredentialsError,
    VectorStoreBackendError,
    VectorStoreBackendRejectedError,
)

TEXT_KEY = "text"
DONT_WAIT = -1
"""The ``timeout`` that makes Pinecone's create_index and delete_index return at once, rather than wait."""
REJECTED_STATUSES = (400, 403, 422)
"""Pinecone's http statuses for a request that it would refuse again, e.g. an invalid dimension or a full quota."""


def pinecone_error(action: str, error: Exception) -> VectorStoreBackendError:
    """
    Return the backend error of an exception from Pinecone, by whether retrying could help.

    :param action: What failed, e.g. ``create the index``.
    :param error: Pinecone's exception.
    :returns: A :class:`~.base.VectorStoreBackendCredentialsError` for a refused api key, a
        :class:`~.base.VectorStoreBackendRejectedError` for another request that Pinecone would refuse
        again, and a :class:`~.base.VectorStoreBackendConnectionError` for anything else, e.g. a
        timeout or a 5xx, which may pass.
    """
    message = f"Pinecone could not {action}: {error}"
    if isinstance(error, UnauthorizedException):
        return VectorStoreBackendCredentialsError(f"Pinecone refused the api key: {error}")
    if isinstance(error, ForbiddenException):
        return VectorStoreBackendRejectedError(message)
    if isinstance(error, PineconeApiException) and error.status_code in REJECTED_STATUSES:
        return VectorStoreBackendRejectedError(message)
    return VectorStoreBackendConnectionError(message)


if TYPE_CHECKING:
    # Pinecone.Index()'s return type, which pinecone imports only for type checkers, as here.
    from pinecone import GrpcIndex, Index


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
        self._index: Optional["Index | GrpcIndex"] = None

    @property
    def client(self) -> Pinecone:
        """
        The Pinecone client, created when it is first used, with the API key of the vectorstore's ApiConnection.

        :raises VectorStoreBackendCredentialsError: If the vectorstore has no ApiConnection with an API key.
        """
        if self._client is None:
            connection = self.vectorstore.connection
            api_key = None
            if connection and connection.api_key:
                api_key = connection.api_key.get_secret()
            if not api_key:
                raise VectorStoreBackendCredentialsError(
                    f"Vectorstore {self.vectorstore.name} has no ApiConnection with a Pinecone API key."
                )
            self._client = Pinecone(api_key=api_key)
        return self._client

    @property
    def index(self) -> "Index | GrpcIndex":
        """The Pinecone index, created when it is first used."""
        if self._index is None:
            self._index = self.client.Index(name=self.index_name)
        return self._index

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
        try:
            status = self.client.describe_index(self.index_name).status
        except Exception as e:
            raise pinecone_error("describe the index", e) from e
        if isinstance(status, dict):
            ready = status.get("ready")
        else:
            ready = getattr(status, "ready", True)
        if ready:
            return True, ""
        return False, "Pinecone is initializing the index."

    def exists(self) -> bool:
        """
        Whether the Pinecone index exists.

        :raises VectorStoreBackendCredentialsError: If Pinecone refuses the api key.
        :raises VectorStoreBackendConnectionError: If Pinecone is unreachable.
        """
        try:
            return self.client.has_index(self.index_name)
        except Exception as e:
            raise pinecone_error("find the index", e) from e

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
        try:
            self.client.create_index(
                name=self.index_name,
                spec=ServerlessSpec(cloud=config.get("cloud", "aws"), region=config.get("region", "us-east-1")),
                dimension=self.vectorstore.dimension,
                metric=self.vectorstore.metric,
                deletion_protection="enabled" if self.vectorstore.deletion_protection else "disabled",
                tags={"created_by": smarter_settings.platform_name, "vectorstore": str(self.vectorstore.pk)},
                timeout=DONT_WAIT,
            )
        except Exception as e:
            raise pinecone_error("create the index", e) from e

    def drop(self) -> None:
        """Delete the Pinecone index, if it exists, and its data.

        It returns at once, while Pinecone deletes the index.
        """
        if self.exists():
            self.client.delete_index(self.index_name, timeout=DONT_WAIT)
        self._index = None

    def stats(self) -> SmarterDictType:
        """The index's vector count, dimension and fullness, from Pinecone."""
        response = self.index.describe_index_stats()
        stats: SmarterDictType
        if isinstance(response, dict):
            stats = response
        else:
            stats = response.to_dict()
        retval: SmarterDictType = {
            "vector_count": stats.get("total_vector_count", 0),
            "dimension": stats.get("dimension"),
            "index_fullness": stats.get("index_fullness"),
        }
        return retval

    # --- data -------------------------------------------------------------------
    def upsert(self, ids: list[str], texts: list[str], metadatas: list[SmarterDictType], batch_size: int = 64) -> None:
        """
        Embed the texts, and upsert them in batches, with each text in its metadata's ``text``.

        :param ids: The chunks' ids.
        :param texts: The chunks' texts.
        :param metadatas: The chunks' metadata.
        :param batch_size: How many chunks to embed and upsert at a time.
        """
        for start in range(0, len(texts), batch_size):
            end = start + batch_size
            batch_ids = ids[start:end]
            batch_texts = texts[start:end]
            batch_metadatas = metadatas[start:end]
            vectors = self.embeddings.embed_documents(batch_texts)
            records = []
            for chunk_id, vector, metadata, text in zip(batch_ids, vectors, batch_metadatas, batch_texts):
                record_metadata = {**metadata, TEXT_KEY: text}
                records.append({"id": chunk_id, "values": vector, "metadata": record_metadata})
            self.index.upsert(vectors=records)

    def delete(self, ids: list[str]) -> None:
        """
        Delete chunks by id.

        Ids that do not exist are ignored.

        :param ids: The chunks' ids.
        """
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
        metadata_filter: Optional[SmarterDictType] = None,
    ) -> list[SearchResult]:
        """
        Search the index with the query's embedding.

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
        if search_type == "mmr":
            if not fetch_k:
                fetch_k = max(20, k * 4)
            if not lambda_mult:
                lambda_mult = 0.5
            response = self.index.query(
                vector=vector,
                top_k=fetch_k,
                include_values=True,
                include_metadata=True,
                filter=metadata_filter,
            )
            matches = self._matches(response)
            if not matches:
                return []
            query_vectors = np.array([vector], dtype=np.float32)
            match_vectors = [match["values"] for match in matches]
            selected = maximal_marginal_relevance(query_vectors, match_vectors, k=k, lambda_mult=lambda_mult)
            mmr_results: list[SearchResult] = []
            for i in selected:
                result = self._result(matches[i], score=None)
                if result:
                    mmr_results.append(result)
            return mmr_results
        response = self.index.query(vector=vector, top_k=k, include_metadata=True, filter=metadata_filter)
        threshold: Optional[float] = None
        if search_type == "similarity_score_threshold":
            threshold = score_threshold
        results: list[SearchResult] = []
        for match in self._matches(response):
            result = self._result(match, score=match.get("score"))
            if not result:
                continue
            if threshold is not None:
                if result.score is None:
                    continue
                if result.score < threshold:
                    continue
            results.append(result)
        return results

    @staticmethod
    def _matches(response) -> list[SmarterDictType]:
        response = response.to_dict() if hasattr(response, "to_dict") else response
        return list(response.get("matches") or [])

    @staticmethod
    def _result(match: SmarterDictType, score: Optional[float]) -> Optional[SearchResult]:
        """The match as a SearchResult, or None if its metadata has no text, e.g. a vector that.

        something other than Smarter wrote.
        """
        metadata = dict(match.get("metadata") or {})
        if TEXT_KEY not in metadata:
            return None
        text = metadata.pop(TEXT_KEY)
        return SearchResult(id=match.get("id"), text=text, metadata=metadata, score=score)

    # --- dumps ------------------------------------------------------------------
    def create_snapshot(self, name: str) -> SnapshotInfo:
        """
        Back up the index, with Pinecone's backups.

        :param name: The backup's name.
        :returns: The backup's id, size, and whether it is ready.
        :raises VectorStoreBackendError: If Pinecone did not back it up.
        """
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
        """
        Delete a Pinecone backup.

        :param name: The backup's id.
        """
        self.client.delete_backup(backup_id=name)

    def restore_snapshot(self, name: str) -> None:
        """Replace the index with a new one from the backup.

        Pinecone requires that the index is deleted first, so this waits until it is.
        """
        if self.exists():
            self.client.delete_index(self.index_name)
        self._index = None
        self.client.create_index_from_backup(
            name=self.index_name,
            backup_id=name,
            deletion_protection="enabled" if self.vectorstore.deletion_protection else "disabled",
        )


__all__ = ["PineconeBackend"]
