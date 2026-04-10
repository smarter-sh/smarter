"""
Backend implementation for the Qdrant vectorstore.
see: https://qdrant.tech/
"""

from .base import (
    SmarterVectorstoreBackend,
    VectorStoreBackendConnectionError,
    VectorStoreBackendError,
)


class QdrantBackend(SmarterVectorstoreBackend):
    """
    Backend implementation for the Qdrant vectorstore.
    """
