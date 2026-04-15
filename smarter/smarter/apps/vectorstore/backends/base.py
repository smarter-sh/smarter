"""
Base class for vector store backends.

This class defines the interface that all
vectorstore backends must implement. It includes methods for creating, deleting,
upserting, querying, and getting stats for vector databases. Each backend should
inherit from this class and provide concrete implementations for these methods
based on the specific vector store being used (e.g., Pinecone, Weaviate, etc.).
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

from langchain_core.documents import Document
from langchain_core.embeddings.embeddings import Embeddings
from langchain_core.vectorstores import VectorStore

from smarter.apps.vectorstore.models import VectorestoreMeta
from smarter.apps.vectorstore.signals import connected
from smarter.common.exceptions import SmarterException
from smarter.common.mixins import SmarterHelperMixin
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper


# pylint: disable=unused-argument
def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.VECTORSTORE_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class VectorStoreBackendError(SmarterException):
    """
    Exception raised when there is an error with the vector store backend.
    """


class VectorStoreBackendConnectionError(SmarterException):
    """
    Exception raised when there is an error with the vector store backend connection.
    """


class VectorStoreBackendConnection(SmarterHelperMixin):
    """
    Represents a connection to a vector store backend.
    """

    _connection: Optional[object]

    @property
    def ready(self) -> bool:
        """
        Check if the connection is ready for operations.
        """
        return super().ready

    def connect(self):
        """
        Establish the connection to the vector store backend.
        """
        connected.send(sender=self.__class__, instance=self, connection=self._connection)


class SmarterVectorstoreBackend(ABC, SmarterHelperMixin):
    """
    Abstract base class for vector store backends.

    This class defines the service interface that all vector store backends must implement.
    All concrete backends (e.g., Pinecone, Weaviate, etc.) should inherit from this
    class and provide implementations for all abstract methods. The backend is responsible
    for managing the connection, storing and retrieving vectors, and handling database operations.

    Parameters
    ----------
    db : VectorestoreMeta
        The vector database instance to use.
    embeddings : Optional[Embeddings], optional
        The embeddings model to use for vectorization (default is None).
    vector_store : Optional[VectorStore], optional
        The vector store object (default is None).

    Methods
    -------
    add_documents(documents, embeddings)
        Add documents with their corresponding embeddings to the vector store.
    initialize()
        Initialize the backend, setting up any necessary connections or configurations.
    create()
        Provision a new vector database in the backend.
    delete()
        Delete the vector database from the backend.
    upsert(vectors)
        Upsert vectors into the vector database in the backend.
    query(query_vector, top_k=10)
        Query the vector database in the backend.
    connect()
        Establish a connection to the vector database in the backend.
    disconnect()
        Disconnect from the vector database in the backend.
    load(embeddings)
        Load vectors into the vector database from a list of embeddings.

    Properties
    ----------
    index_stats : str
        Get statistics about the vector database in the backend.
    vector_store : object
        Get the vector store object for the backend.
    embeddings : Embeddings
        Get the embeddings model.
    connection : VectorStoreBackendConnection
        Get or establish the connection to the vector database in the backend.
    is_connected : bool
        Check if there is an active connection to the vector database in the backend.
    ready : bool
        Check if the backend is ready for operations.
    """

    # Internal state variables for lazy initialization
    _connection: Optional[VectorStoreBackendConnection] = None
    _embeddings: Optional[Embeddings] = None
    _vector_store: Optional[VectorStore] = None

    db: VectorestoreMeta

    def __init__(
        self,
        *args,
        db: VectorestoreMeta,
        embeddings: Optional[Embeddings] = None,
        vector_store: Optional[VectorStore] = None,
        **kwargs,
    ):
        SmarterHelperMixin.__init__(self)
        self.db = db
        self._connection = None
        self._embeddings = embeddings
        self._vector_store = vector_store

        logger.debug("%s.__init__() Initializing backend for database: %s", self.formatted_class_name, db)

    @property
    def index_stats(self) -> str:
        """
        Get statistics about the vector database in the backend.
        """
        raise NotImplementedError("Index stats method not implemented for this backend")

    @property
    def vector_store(self) -> object:
        """
        Get the vector store object for the backend.
        """
        if self._vector_store is None:
            raise NotImplementedError("Vector store property not implemented for this backend")
        return self._vector_store

    @property
    def embeddings(self) -> Embeddings:
        """Get the embeddings."""
        if self._embeddings is None:
            raise NotImplementedError("Embeddings property not implemented for this backend")
        return self._embeddings

    @property
    def connection(self) -> VectorStoreBackendConnection:
        """
        Get the connection to the vector database in the backend, establishing
        it if it doesn't already exist.
        """
        if self._connection is None:
            self._connection = self.connect()
        return self._connection

    @property
    def is_connected(self) -> bool:
        """
        Check if there is an active connection to the vector database in the backend.
        """
        return self._connection is not None and self._connection.ready

    @property
    def ready(self) -> bool:
        """
        Check if the backend is ready for operations.
        """
        return super().ready and self.is_connected

    ###########################################################################
    # Abstract methods that must be implemented by all backends
    ###########################################################################
    @abstractmethod
    def add_documents(self, documents: list[Document], embeddings: list[Any]) -> bool:
        """
        Add documents with their corresponding embeddings to the vector store.
        """
        raise NotImplementedError("Add documents method not implemented for this backend")

    @abstractmethod
    def connect(self) -> VectorStoreBackendConnection:
        """
        Establish a connection to the vector database in the backend.
        """
        raise NotImplementedError("Connect method not implemented for this backend")

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
    def disconnect(self) -> None:
        """
        Disconnect from the vector database in the backend.
        """
        raise NotImplementedError("Disconnect method not implemented for this backend")

    @abstractmethod
    def initialize(self):
        """
        Initialize the backend, setting up any necessary connections or configurations.
        """
        raise NotImplementedError("Initialize method not implemented for this backend")

    @abstractmethod
    def query(self, query_vector: Any, top_k: int = 10):
        """
        Query the vector database in the backend.
        """
        raise NotImplementedError("Query method not implemented for this backend")
