"""
Backend implementation for the Pinecode vectorstore.
see: https://www.pinecone.io/
"""

from .base import (
    BaseBackend,
    VectorStoreBackendConnectionError,
    VectorStoreBackendError,
)


class PineconeBackend(BaseBackend):
    """
    Backend implementation for the Pinecone vectorstore.
    """
