"""
Base class for vector store backends.

This class defines the interface that all
vectorstore backends must implement. It includes methods for creating, deleting,
upserting, querying, and getting stats for vector databases. Each backend should
inherit from this class and provide concrete implementations for these methods
based on the specific vector store being used (e.g., Pinecone, Weaviate, etc.).
"""

from abc import ABC, abstractmethod
from typing import Optional

from smarter.apps.vectorstore.models import VectorDatabase


class VectorStoreBackendConnection:
    """
    Represents a connection to a vector store backend.
    """


class BaseBackend(ABC):
    """
    Base class for vector store backends. All backends should inherit from this
    class and implement the required methods.
    """

    _connection: Optional[VectorStoreBackendConnection]

    db: VectorDatabase

    def __init__(self, db: VectorDatabase):
        self.db = db
        self._connection = None

    @abstractmethod
    def create(self):
        """
        Provision a new vector database in the backend.
        """
        raise NotImplementedError("Create method not implemented for this backend")

    @abstractmethod
    def delete(self):
        """
        Delete the vector database from the backend.
        """
        raise NotImplementedError("Delete method not implemented for this backend")

    @abstractmethod
    def upsert(self, vectors):
        """
        Upsert vectors into the vector database in the backend.
        """
        raise NotImplementedError("Upsert method not implemented for this backend")

    @abstractmethod
    def query(self, query_vector, top_k=10):
        """
        Query the vector database in the backend.
        """
        raise NotImplementedError("Query method not implemented for this backend")

    @abstractmethod
    def get_stats(self):
        """
        Get statistics about the vector database in the backend.
        """
        raise NotImplementedError("Get stats method not implemented for this backend")

    @abstractmethod
    def connect(self) -> VectorStoreBackendConnection:
        """
        Establish a connection to the vector database in the backend.
        """
        raise NotImplementedError("Connect method not implemented for this backend")

    @abstractmethod
    def disconnect(self) -> None:
        """
        Disconnect from the vector database in the backend.
        """
        raise NotImplementedError("Disconnect method not implemented for this backend")

    @property
    def connection(self) -> VectorStoreBackendConnection:
        """
        Get the connection to the vector database in the backend, establishing
        it if it doesn't already exist.
        """
        if self._connection is None:
            self._connection = self.connect()
        return self._connection

    @abstractmethod
    def load(self, filepath: str, filespec: Optional[dict] = None):
        """
        Load vectors into the vector database from a file.
        """
        raise NotImplementedError("Load method not implemented for this backend")
