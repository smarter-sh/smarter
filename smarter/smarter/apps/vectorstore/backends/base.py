"""
The interface of vector database backends.

A backend runs one vectorstore's database operations: its lifecycle, its data, and its dumps.
Lifecycle, status and scheduling are the job of
:class:`~smarter.apps.vectorstore.service.VectorstoreService`, which calls a backend.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

from langchain_core.embeddings import Embeddings

from smarter.apps.vectorstore.models import VectorstoreMeta
from smarter.common.exceptions import SmarterException

SEARCH_TYPES = ("similarity", "similarity_score_threshold", "mmr")


class VectorStoreBackendError(SmarterException):
    """A vector database operation failed."""


class VectorStoreBackendConnectionError(VectorStoreBackendError):
    """The vector database cannot be reached."""


@dataclass
class SearchResult:
    """A chunk that a search found."""

    id: Optional[str]
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    score: Optional[float] = None


@dataclass
class SnapshotInfo:
    """A Qdrant snapshot, or a Pinecone backup."""

    name: str
    size_bytes: Optional[int] = None
    ready: bool = True


class SmarterVectorstoreBackend(ABC):
    """
    Abstract base class of the vector database backends.

    :param vectorstore: The vectorstore.
    :param embeddings: Its embeddings model. Required for :meth:`upsert` and :meth:`search`.
    """

    def __init__(self, vectorstore: VectorstoreMeta, embeddings: Optional[Embeddings] = None):
        self.vectorstore = vectorstore
        self._embeddings = embeddings

    @property
    def embeddings(self) -> Embeddings:
        if self._embeddings is None:
            raise VectorStoreBackendError(f"Vectorstore {self.vectorstore.name} has no embeddings model.")
        return self._embeddings

    @property
    def index_name(self) -> str:
        return self.vectorstore.index_name or self.vectorstore.default_index_name()

    # --- lifecycle --------------------------------------------------------------
    def provision(self) -> None:
        """Create the database's infrastructure, if Smarter runs it.

        It returns without waiting for it.
        """

    def infrastructure_ready(self) -> tuple[bool, str]:
        """Whether the infrastructure that Smarter runs is ready, and why not.

        A managed service always is.
        """
        return True, ""

    def stop(self) -> None:
        """Stop the infrastructure that Smarter runs, keeping its data."""

    @abstractmethod
    def exists(self) -> bool:
        """Whether the index or collection exists."""

    @abstractmethod
    def create(self) -> None:
        """Create the index or collection."""

    @abstractmethod
    def drop(self) -> None:
        """Delete the index or collection, and its data."""

    def destroy(self) -> None:
        """Delete the index or collection, and any infrastructure that Smarter runs."""
        self.drop()

    @abstractmethod
    def stats(self) -> dict[str, Any]:
        """The database's statistics.

        It includes vector_count.
        """

    # --- data -------------------------------------------------------------------
    @abstractmethod
    def upsert(self, ids: list[str], texts: list[str], metadatas: list[dict[str, Any]], batch_size: int = 64) -> None:
        """Embed and insert, or replace, chunks."""

    @abstractmethod
    def delete(self, ids: list[str]) -> None:
        """Delete chunks.

        Ids that do not exist are ignored.
        """

    @abstractmethod
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
        """
        Find the chunks that are closest in meaning to a query.

        :param search_type: similarity, similarity_score_threshold, or mmr (maximal marginal relevance).
        :param metadata_filter: chunks whose metadata has these values, e.g. {"source": "faq"}.
        """

    # --- dumps ------------------------------------------------------------------
    @abstractmethod
    def create_snapshot(self, name: str) -> SnapshotInfo:
        """Take a snapshot, or backup."""

    @abstractmethod
    def delete_snapshot(self, name: str) -> None:
        """Delete a snapshot, or backup."""

    @abstractmethod
    def restore_snapshot(self, name: str) -> None:
        """Replace the index or collection's data with a snapshot's."""

    def logs(self, tail: int = 200) -> Optional[str]:  # pylint: disable=unused-argument
        """The database server's logs, if Smarter runs it."""
        return None


__all__ = [
    "SEARCH_TYPES",
    "SearchResult",
    "SmarterVectorstoreBackend",
    "SnapshotInfo",
    "VectorStoreBackendConnectionError",
    "VectorStoreBackendError",
]
