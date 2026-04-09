"""
Service layer for managing vector databases, providing abstractions for
provisioning, deleting, and interacting
"""

from typing import Optional

from smarter.apps.provider.models import Provider
from smarter.apps.vectorstore.backends import Backends, BaseBackend
from smarter.apps.vectorstore.models import VectorDatabase
from smarter.apps.vectorstore.signals import (
    embed_failed,
    embed_started,
    embed_success,
    load_failed,
    load_started,
    load_success,
)


class VectorDatabaseService:
    """
    Service class for managing vector databases.
    This class provides the service layer abstractions for methods for
    managing vector databases using the appropriate backend implementations.

    Creates a binding between the VectorDatabase ORM model, which contains the
    metadata and configuration for a vector database, and the Backend implementations,
    which contain the logic for interacting with the underlying vector store.

    Original source comes from https://github.com/FullStackWithLawrence/openai-embeddings
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
        Original source comes from https://github.com/FullStackWithLawrence/openai-embeddings
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
        load_started.send(
            sender=self.__class__, backend=self.backend, provider=self.provider, user_profile=self.db.user_profile
        )
        try:
            self.backend.load(filepath, filespec)
            load_success.send(
                sender=self.__class__, backend=self.backend, provider=self.provider, user_profile=self.db.user_profile
            )
        except Exception as e:
            load_failed.send(
                sender=self.__class__, backend=self.backend, provider=self.provider, user_profile=self.db.user_profile
            )
            raise e

    def embed(self, text: str) -> list:
        """
        Vectorize text using the appropriate backend.
        Original source comes from https://github.com/FullStackWithLawrence/openai-embeddings/blob/main/models/pinecone.py
        """
        embed_started.send(
            sender=self.__class__, backend=self.backend, provider=self.provider, user_profile=self.db.user_profile
        )
        result = []
        try:
            result = []
            embed_success.send(
                sender=self.__class__, backend=self.backend, provider=self.provider, user_profile=self.db.user_profile
            )
        except Exception as e:
            embed_failed.send(
                sender=self.__class__, backend=self.backend, provider=self.provider, user_profile=self.db.user_profile
            )
            raise e
        return result
