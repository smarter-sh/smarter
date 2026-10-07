"""
Vectorstore backends: the vector database products that Smarter supports.

:func:`get_backend` returns the backend of a vectorstore.
"""

from typing import Optional

from langchain_core.embeddings import Embeddings

from smarter.apps.vectorstore.enum import SmarterVectorStoreBackends
from smarter.apps.vectorstore.models import VectorstoreMeta
from smarter.common.exceptions import SmarterConfigurationError

from .base import (
    SEARCH_TYPES,
    SearchResult,
    SmarterVectorstoreBackend,
    SnapshotInfo,
    VectorStoreBackendConnectionError,
    VectorStoreBackendError,
)
from .pinecone import PineconeBackend
from .qdrant import QdrantBackend

BACKENDS: dict[str, type[SmarterVectorstoreBackend]] = {
    SmarterVectorStoreBackends.QDRANT.value: QdrantBackend,
    SmarterVectorStoreBackends.PINECONE.value: PineconeBackend,
}

if set(BACKENDS) != set(SmarterVectorStoreBackends.all()):
    raise SmarterConfigurationError(
        f"Every vectorstore backend needs an implementation: {set(SmarterVectorStoreBackends.all()) ^ set(BACKENDS)}"
    )


def get_backend(vectorstore: VectorstoreMeta, embeddings: Optional[Embeddings] = None) -> SmarterVectorstoreBackend:
    """The backend of a vectorstore."""
    try:
        backend_class = BACKENDS[vectorstore.backend]
    except KeyError as e:
        raise SmarterConfigurationError(f"Unsupported vectorstore backend: {vectorstore.backend}") from e
    return backend_class(vectorstore, embeddings=embeddings)


__all__ = [
    "BACKENDS",
    "PineconeBackend",
    "QdrantBackend",
    "SEARCH_TYPES",
    "SearchResult",
    "SmarterVectorstoreBackend",
    "SnapshotInfo",
    "VectorStoreBackendConnectionError",
    "VectorStoreBackendError",
    "get_backend",
]
