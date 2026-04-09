"""
Backend implementation for the Qdrant vectorstore.
see: https://qdrant.tech/
"""

from .base import (
    BaseBackend,
    VectorStoreBackendConnectionError,
    VectorStoreBackendError,
)


class QdrantBackend(BaseBackend):
    """
    Backend implementation for the Qdrant vectorstore.
    """
