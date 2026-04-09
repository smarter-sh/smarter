"""
Service layer for managing vector databases, providing abstractions for
provisioning, deleting, and interacting
"""

from typing import Optional

from smarter.apps.provider.models import Provider
from smarter.apps.vectorstore.backends import Backends
from smarter.apps.vectorstore.backends.base import BaseBackend
from smarter.apps.vectorstore.models import VectorDatabase


class VectorDatabaseService:
    """
    Service class for managing vector databases.
    This class provides the service layer abstractions for methods for
    managing vector databases using the appropriate backend implementations.

    Creates a binding between the VectorDatabase ORM model, which contains the
    metadata and configuration for a vector database, and the Backend implementations,
    which contain the logic for interacting with the underlying vector store.
    """

    db: VectorDatabase
    backend: BaseBackend
    provider: Provider

    def __init__(self, db: VectorDatabase):
        self.db = db
        self.backend = Backends.get_backend(name=db.name, backend=db.backend)
        self.provider = db.provider

    def provision(self):
        """
        Provision a new vector database using the appropriate backend.
        """
        self.backend.create()

    def delete(self):
        """
        Delete an existing vector database using the appropriate backend.
        """
        self.backend.delete()

    def upsert(self, vectors):
        """
        Upsert vectors into the vector database using the appropriate backend.
        """
        self.backend.upsert(vectors)

    def query(self, query_vector, top_k=10):
        """
        Query the vector database using the appropriate backend.
        """
        return self.backend.query(query_vector, top_k)

    def get_stats(self):
        """
        Get statistics of the vector database using the appropriate backend.
        """
        return self.backend.get_stats()

    def load(self, filepath: str, filespec: Optional[dict] = None):
        """
        Load vectors into the vector database from a file using the appropriate backend.
        """
        self.backend.load(filepath, filespec)

    def vectorize(self, text: str) -> list:
        """
        Vectorize text using the appropriate backend.
        """
        return self.backend.vectorize(text)
