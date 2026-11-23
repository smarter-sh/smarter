"""
The interface of vector database backends.

A backend runs one vectorstore's database operations: its lifecycle, its data, and its dumps.
Lifecycle, status and scheduling are the job of
:class:`~smarter.apps.vectorstore.service.VectorstoreService`, which calls a backend.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from langchain_core.embeddings import Embeddings

from smarter.apps.vectorstore.deployment import TRUE
from smarter.apps.vectorstore.manifest.models.vectorstore.status import (
    SAMVectorstoreCondition,
)
from smarter.apps.vectorstore.models import VectorstoreMeta
from smarter.common.exceptions import SmarterException
from smarter.lib.typing import SmarterDictType

SEARCH_TYPES = ("similarity", "similarity_score_threshold", "mmr")


class VectorStoreBackendError(SmarterException):
    """A vector database operation failed."""


class VectorStoreBackendConnectionError(VectorStoreBackendError):
    """The vector database cannot be reached."""


class VectorStoreBackendRejectedError(VectorStoreBackendError):
    """
    The vector database refused a request, and would refuse it again, e.g. an invalid dimension or a full quota.

    A deploy that meets it fails at once, rather than retrying.
    """


class VectorStoreBackendCredentialsError(VectorStoreBackendRejectedError):
    """The vector database refused the api key, or there is none to send."""


@dataclass
class SearchResult:
    """A chunk that a search found."""

    id: Optional[str]
    text: str
    metadata: SmarterDictType = field(default_factory=dict)
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

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} vectorstore={self.vectorstore.name}>"

    @property
    def embeddings(self) -> Embeddings:
        """
        The embeddings model, which turns texts into vectors.

        :raises VectorStoreBackendError: If the backend was created without one.
        """
        if self._embeddings is None:
            raise VectorStoreBackendError(f"Vectorstore {self.vectorstore.name} has no embeddings model.")
        return self._embeddings

    @property
    def index_name(self) -> str:
        """The name of the index or collection: the vectorstore's ``index_name``, or its default."""
        return self.vectorstore.index_name or self.vectorstore.default_index_name()

    # --- lifecycle --------------------------------------------------------------
    def check_credentials(self) -> str:
        """
        Check, quickly, that the database accepts the vectorstore's credentials.

        By default it asks whether the index exists, which a managed service answers only with a valid api key.

        :returns: What was found, for a person.
        :raises VectorStoreBackendCredentialsError: If the database refuses them.
        :raises VectorStoreBackendConnectionError: If the database can't be reached, which may pass.
        """
        self.exists()
        return "The database accepted the api key."

    def provision(self) -> None:
        """Create the database's infrastructure, if Smarter runs it.

        It returns without waiting for it.
        """

    def infrastructure_conditions(self) -> list[SAMVectorstoreCondition]:
        """
        The conditions of the infrastructure that Smarter runs, e.g. a self-hosted server's volume and pod.

        A managed service has none.

        :returns: One condition per part of the infrastructure, in the order that they become ready.
        """
        return []

    def infrastructure_ready(self) -> tuple[bool, str]:
        """Whether the infrastructure that Smarter runs is ready, and why not.

        A managed service always is.
        """
        for condition in self.infrastructure_conditions():
            if condition.status != TRUE:
                return False, condition.message
        return True, ""

    def index_ready(self) -> tuple[bool, str]:
        """
        Whether the index or collection, which exists, is ready to use, and why not.

        By default it is as soon as it exists. Pinecone initializes a new index for a minute or two.
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
    def stats(self) -> SmarterDictType:
        """The database's statistics.

        It includes vector_count.
        """

    # --- data -------------------------------------------------------------------
    @abstractmethod
    def upsert(self, ids: list[str], texts: list[str], metadatas: list[SmarterDictType], batch_size: int = 64) -> None:
        """
        Embed and insert, or replace, chunks.

        :param ids: The chunks' ids.
        :param texts: The chunks' texts.
        :param metadatas: The chunks' metadata.
        :param batch_size: How many chunks to embed and upsert at a time.
        """

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
        metadata_filter: Optional[SmarterDictType] = None,
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
    "VectorStoreBackendCredentialsError",
    "VectorStoreBackendError",
    "VectorStoreBackendRejectedError",
]
