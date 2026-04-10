"""
Backend implementation for the Weaviate vectorstore.
see: https://weaviate.io/
"""

from .base import (
    SmarterVectorstoreBackend,
    VectorStoreBackendConnectionError,
    VectorStoreBackendError,
)


class WeaviateBackend(SmarterVectorstoreBackend):
    """
    Backend implementation for the Weaviate vectorstore.
    """
