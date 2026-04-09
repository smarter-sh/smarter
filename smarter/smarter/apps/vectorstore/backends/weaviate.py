"""
Backend implementation for the Weaviate vectorstore.
see: https://weaviate.io/
"""

from .base import (
    BaseBackend,
    VectorStoreBackendConnectionError,
    VectorStoreBackendError,
)


class WeaviateBackend(BaseBackend):
    """
    Backend implementation for the Weaviate vectorstore.
    """
