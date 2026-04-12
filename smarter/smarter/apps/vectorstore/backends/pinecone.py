"""
Backend implementation for the Pinecode vectorstore.
see: https://www.pinecone.io/
"""

import logging
from typing import Any, Optional

from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone
from pinecone.core.openapi.db_data.models import (
    IndexDescription as PineconeIndexDescription,
)
from pinecone.db_control.enums import AwsRegion, CloudProvider, Metric, VectorType
from pinecone.db_control.models import IndexList, ServerlessSpec
from pinecone.db_data import Index
from pinecone.exceptions import PineconeApiException
from pydantic import SecretStr

from smarter.apps.provider.models import Provider
from smarter.apps.vectorstore.enum import SmarterVectorStoreBackends
from smarter.apps.vectorstore.models import VectorDatabase
from smarter.apps.vectorstore.signals import load_failed, load_started, load_success
from smarter.lib import json
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

from .base import (
    SmarterVectorstoreBackend,
    VectorStoreBackendConnectionError,
    VectorStoreBackendError,
)


# pylint: disable=unused-argument
def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.VECTORSTORE_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class PineconeBackend(SmarterVectorstoreBackend):
    """
    Backend implementation for the Pinecone vectorstore.
    """

    # Private attributes for lazy initialization
    _pinecone = None
    _index: Optional[Index] = None
    _index_name: Optional[str] = None
    _embeddings: Optional[OpenAIEmbeddings] = None
    _vector_store: Optional[PineconeVectorStore] = None

    # validated fields initialized in __init__
    pinecone_api_key: SecretStr

    def __init__(self, db: VectorDatabase):
        """
        Initialize the PineconeBackend instance.

        Sets up the Pinecone backend using the provided VectorDatabase
        configuration. Validates the backend type, provider, and API keys,
        then initializes the backend state and index name.

        :param db: The VectorDatabase configuration object.
        :type db: VectorDatabase

        :raises VectorStoreBackendError: If the backend type, provider, or API keys are invalid.
        """
        super().__init__(db=db)
        self.init()

        # Verify that we're supposed to be here.
        if db.backend != SmarterVectorStoreBackends.PINECONE.value:
            raise VectorStoreBackendError(f"Invalid backend for PineconeBackend: {db.backend}")

        # unpack some of the db fields for easier access.
        if not isinstance(db.provider, Provider):
            raise VectorStoreBackendError(f"Invalid provider for PineconeBackend: {db.provider}")

        if not isinstance(db.password, SecretStr):
            raise VectorStoreBackendError(f"Invalid password for PineconeBackend: {db.password}")
        self.pinecone_api_key = db.password

        self.index_name = db.name
        if self.ready:
            logging.debug("%s.__init__() initialized with index_name: %s", self.formatted_class_name, self.index_name)
            logging.debug("%s.__init__() %s", self.formatted_class_name, self.index_stats)
        else:
            logging.error("%s.__init__() not initialized.", self.formatted_class_name)

    @property
    def ready(self) -> bool:
        """
        Check if the Pinecone backend is fully ready.

        Returns True if the backend is fully initialized, the Pinecone index exists, and the vector store is available.

        :returns: True if the backend is ready for use, otherwise False.
        :rtype: bool
        """
        return super().ready and self.initialized and self.index is not None and self.vector_store is not None

    @property
    def index_name(self) -> Optional[str]:
        """index name."""
        return self._index_name

    @index_name.setter
    def index_name(self, value: str) -> None:
        """Set index name."""
        if self._index_name != value:
            self.init()
            self._index_name = value
            self.init_index()
            logging.debug("%s.index_name() set to: %s", self.formatted_class_name, self._index_name)

    @property
    def index(self) -> Optional[Index]:
        """
        Get the Pinecone index instance.

        Lazily initializes and returns the Pinecone Index instance for the
        current index name. If the index is already initialized, returns the
        existing instance.

        :returns: The Pinecone Index instance if initialized, otherwise None.
        :rtype: Optional[Index]

        :raises VectorStoreBackendConnectionError: If the Pinecone client or
            index name is not set, or if there is an error initializing the index.
        """
        if self._index is None:
            self.init_index()
            if not isinstance(self.pinecone, Pinecone):
                logging.error("%s.index() Pinecone client not initialized.", self.formatted_class_name)
                raise VectorStoreBackendConnectionError("Pinecone client not initialized.")
            if not isinstance(self.index_name, str):
                logging.error("%s.index() Index name not set.", self.formatted_class_name)
                raise VectorStoreBackendConnectionError("Index name not set.")

            try:
                self._index = self.pinecone.Index(name=self.index_name)
            except PineconeApiException as e:
                logging.error("%s.index() Error initializing index: %s", self.formatted_class_name, str(e))
                raise VectorStoreBackendConnectionError(f"Error initializing index: {str(e)}") from e
            except Exception as e:
                logging.error("%s.index() Unexpected error initializing index: %s", self.formatted_class_name, str(e))
                raise VectorStoreBackendConnectionError(f"Unexpected error initializing index: {str(e)}") from e

        return self._index

    @property
    def index_stats(self) -> str:
        """
        Get the statistics of the Pinecone index.

        Retrieves and returns the statistics of the current Pinecone index as
        a formatted JSON string. If the index is not initialized, returns a
        message indicating so.

        :returns: A JSON string with index statistics, or a message if the
            index is not initialized.
        :rtype: str
        """
        if self.index is not None:
            retval: PineconeIndexDescription = self.index.describe_index_stats()
            return json.dumps(retval.to_dict(), indent=4)
        return "Index not initialized."

    @property
    def initialized(self) -> bool:
        """
        Check if the Pinecone index is initialized.

        Verifies that the Pinecone client is initialized and that the index name exists in Pinecone.

        :returns: True if the index exists and the client is initialized, otherwise False.
        :rtype: bool
        """
        if isinstance(self.pinecone, Pinecone) and isinstance(self.index_name, str):
            indexes = self.pinecone.list_indexes()
            return self.index_name in indexes.names()
        return False

    @property
    def vector_store(self) -> PineconeVectorStore:
        """
        Get the Pinecone vector store.

        Lazily initializes and returns the PineconeVectorStore instance using
        the current index and embeddings. If the vector store is already
        initialized, returns the existing instance.

        :returns: The PineconeVectorStore instance.
        :rtype: PineconeVectorStore

        :raises VectorStoreBackendConnectionError: If the vector store
            cannot be initialized due to missing index or embeddings.
        """
        if self._vector_store is None:
            if not self.initialized:
                self.init_index()
            self._vector_store = PineconeVectorStore(
                index=self.index,
                embedding=self.embeddings,
                text_key="lc_id",  # FIX NOTE: I LIVE IN A DATABASE TABLE
            )
        return self._vector_store

    @property
    def pinecone(self) -> Optional[Pinecone]:
        """
        Get the Pinecone instance.

        Lazily initializes and returns the Pinecone client instance using the
        configured API key. If the client is already initialized, returns the
        existing instance.

        :returns: The Pinecone client instance if initialized, otherwise None.
        :rtype: Optional[Pinecone]

        :raises VectorStoreBackendConnectionError: If there is an error
            initializing the Pinecone client.
        """
        if self._pinecone is None:
            self.connect()
        return self._pinecone

    def init_index(self):
        """
        Verify and create Pinecone index if needed.

        Checks if an index with the name stored in `self.index_name` exists in
        Pinecone. If it does not exist, creates a new index with the current
        configuration.

        :returns: None
        :rtype: None

        :raises VectorStoreBackendConnectionError: If the Pinecone client is
            not initialized or the index name is not set.
        """
        if not isinstance(self.pinecone, Pinecone):
            logging.error("%s.init_index() Pinecone client not initialized.", self.formatted_class_name)
            raise VectorStoreBackendConnectionError("Pinecone client not initialized.")
        if not isinstance(self.index_name, str):
            logging.error("%s.init_index() Index name not set.", self.formatted_class_name)
            raise VectorStoreBackendConnectionError("Index name not set.")

        indexes: IndexList = self.pinecone.list_indexes()
        if self.index_name not in indexes.names():
            logging.debug("%s.init_index() %s does not exist.", self.formatted_class_name, self.index_name)
            self.create()

    def init(self):
        """
        Initialize Pinecone backend attributes.

        Resets all internal attributes related to the Pinecone backend,
        including index, index name, text splitter, embeddings, and vector
        store. This is typically called before re-initializing or
        switching the backend state.

        :returns: None
        :rtype: None
        """

        self._pinecone = None
        self._index = None
        self._index_name = None
        self._embeddings = None
        self._vector_store = None

    ###########################################################################
    # Abstract methods that must be implemented by all backends
    ###########################################################################

    def add_documents(self, documents: list[Document], embeddings: list[Any]) -> bool:
        """
        Add documents with their corresponding embeddings to the vector store.

        Adds a list of documents and their precomputed embeddings to the Pinecone vector store.
        It emits signals to indicate the start, success, or failure of the loading process.

        :param documents: List of LangChain Document objects to be added to the vector store.
        :type documents: list[Document]
        :param embeddings: List of embedding vectors corresponding to the documents.
        :type embeddings: list[Any]

        :returns: True if documents were added successfully.
        :rtype: bool

        :raises VectorStoreBackendError: If there is an error adding documents to the vector store.
        """
        try:
            load_started.send(
                sender=self.__class__, backend=self, provider=self.db.provider, user_profile=self.db.user_profile
            )
            self.vector_store.add_documents(documents=documents, embeddings=embeddings)
            load_success.send(
                sender=self.__class__, backend=self, provider=self.db.provider, user_profile=self.db.user_profile
            )
            return True
        except Exception as e:
            logger.error("%s.add_documents() Error adding documents: %s", self.formatted_class_name, str(e))
            load_failed.send(
                sender=self.__class__, backend=self, provider=self.db.provider, user_profile=self.db.user_profile
            )
            raise VectorStoreBackendError(f"Error adding documents: {str(e)}") from e

    def create(self):
        """
        Create a new Pinecone index.

        Creates a new Pinecone index with the current configuration. If the
        index already exists, this will raise an error.

        :returns: None
        :rtype: None

        :raises VectorStoreBackendConnectionError: If the Pinecone client
            is not initialized.
        :raises VectorStoreBackendError: If the index name is not set or
            if there is an error creating the index.
        """
        serverless_spec = ServerlessSpec(
            cloud=CloudProvider.AWS,
            region=AwsRegion.US_EAST_1,
        )
        if not isinstance(self.pinecone, Pinecone):
            logging.error("%s.create() Pinecone client not initialized.", self.formatted_class_name)
            raise VectorStoreBackendConnectionError("Pinecone client not initialized.")
        if not isinstance(self.index_name, str):
            logging.error("%s.create() Index name not set.", self.formatted_class_name)
            raise VectorStoreBackendError("Index name not set.")

        try:
            logging.debug("%s.create() Creating index. This may take a few minutes...", self.formatted_class_name)
            self.pinecone.create_index(
                name=self.index_name,
                dimension=1536,
                metric=Metric.DOTPRODUCT,
                spec=serverless_spec,
                vector_type=VectorType.DENSE,
            )
            logging.debug("%s.create() Index created: %s", self.formatted_class_name, self.index_name)
        except PineconeApiException as e:
            logging.error("%s.create() Error creating index: %s", self.formatted_class_name, str(e))
            raise VectorStoreBackendError(f"Error creating index: {str(e)}") from e
        except Exception as e:
            logging.error("%s.create() Unexpected error creating index: %s", self.formatted_class_name, str(e))
            raise VectorStoreBackendError(f"Unexpected error creating index: {str(e)}") from e

    def connect(self) -> bool:
        """
        Connect to the Pinecone service.

        Initializes the Pinecone client using the configured API key. If the connection is successful, the client instance is stored for future use.

        :returns: True if the connection was successful.
        :rtype: bool

        :raises VectorStoreBackendConnectionError: If there is an error initializing the Pinecone client.
        """

        logger.debug("%s.connect() connecting...", self.formatted_class_name)
        try:
            self._pinecone = Pinecone(api_key=self.pinecone_api_key.get_secret_value())
            logger.debug(
                "%s.connect() connected using API Key: ****%s",
                self.formatted_class_name,
                self.pinecone_api_key.get_secret_value()[-4:],
            )
            return True
        # pylint: disable=broad-except
        except Exception as e:
            logger.error("%s.connect() Error initializing Pinecone: %s", self.formatted_class_name, str(e))
            raise VectorStoreBackendConnectionError(f"Error initializing Pinecone: {str(e)}") from e

    def delete(self):
        """
        Delete the Pinecone index.

        Deletes the Pinecone index if it exists. If the index does not exist, the method returns without error.

        :returns: None
        :rtype: None

        :raises VectorStoreBackendConnectionError: If the Pinecone client is not initialized.
        :raises VectorStoreBackendError: If the index name is not set.
        """
        if not self.initialized:
            logging.debug("%s.delete() Index does not exist. Nothing to delete.", self.formatted_class_name)
            return
        if not isinstance(self.pinecone, Pinecone):
            logging.error("%s.delete() Pinecone client not initialized.", self.formatted_class_name)
            raise VectorStoreBackendConnectionError("Pinecone client not initialized.")
        if not isinstance(self.index_name, str):
            logging.error("%s.delete() Index name not set.", self.formatted_class_name)
            raise VectorStoreBackendError("Index name not set.")

        logging.debug("%s.delete() Deleting index: %s", self.formatted_class_name, self.index_name)
        self.pinecone.delete_index(self.index_name)

    def disconnect(self) -> None:
        """
        Disconnect from the Pinecone index.

        Resets the Pinecone client instance, effectively disconnecting from the Pinecone service.

        :returns: None
        :rtype: None
        """
        self._pinecone = None
        logger.debug("%s.disconnect() disconnected.", self.formatted_class_name)

    def initialize(self):
        """
        Initialize the Pinecone index.

        Deletes the existing index (if it exists) and creates a new one with
        the current configuration. This operation is typically used to reset
        the vector store to a clean state.

        :returns: None
        :rtype: None

        :raises VectorStoreBackendError: If there is an error deleting or creating the index.
        """
        self.delete()
        self.create()

    def query(self, query_vector: Any, top_k: int = 10):
        pass
