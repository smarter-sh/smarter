"""
Backend implementation for the Qdrant vectorstore.
see: https://qdrant.tech/
"""

from .base import (
    SmarterVectorstoreBackend,
)


class QdrantBackend(SmarterVectorstoreBackend):
    """
    Backend implementation for the Qdrant vectorstore.
    """
