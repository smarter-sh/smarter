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

    To do:
    - settings.pinecone_vectorstore_text_key
    - settings.pinecone_dimensions,
    - settings.pinecone_metric,
    """

    # Private attributes for lazy initialization
    _pinecone = None
    _index: Optional[Index] = None
    _index_name: Optional[str] = None
    _openai_embeddings: Optional[OpenAIEmbeddings] = None
    _vector_store: Optional[PineconeVectorStore] = None

    # validated fields initialized in __init__
    llm_api_key: SecretStr
    pinecone_api_key: SecretStr

    def __init__(self, db: VectorDatabase):
        super().__init__(db=db)

        # Verify that we're supposed to be here.
        if db.backend != SmarterVectorStoreBackends.PINECONE.value:
            raise VectorStoreBackendError(f"Invalid backend for PineconeBackend: {db.backend}")

        # unpack some of the db fields for easier access.
        if not isinstance(db.provider, Provider):
            raise VectorStoreBackendError(f"Invalid provider for PineconeBackend: {db.provider}")
        if not isinstance(db.provider.api_key, SecretStr):
            raise VectorStoreBackendError(f"Invalid API key for PineconeBackend: {db.provider.api_key}")
        self.llm_api_key = db.provider.api_key

        if not isinstance(db.password, SecretStr):
            raise VectorStoreBackendError(f"Invalid password for PineconeBackend: {db.password}")
        self.pinecone_api_key = db.password

        self.init()
        self.index_name = db.name
        if self.ready:
            logging.debug("%s.__init__() initialized with index_name: %s", self.formatted_class_name, self.index_name)
            logging.debug("%s.__init__() %s", self.formatted_class_name, self.index_stats)
        else:
            logging.error("%s.__init__() not initialized.", self.formatted_class_name)

    @property
    def ready(self) -> bool:
        """ready read-only property."""
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
        """pinecone.Index lazy read-only property."""
        if self._index is None:
            self.init_index()
            if isinstance(self.pinecone, Pinecone) and isinstance(self.index_name, str):
                self._index = self.pinecone.Index(name=self.index_name)

        return self._index

    @property
    def index_stats(self) -> str:
        """
        Get the statistics of the Pinecone index.
        """
        if self.index is not None:
            retval: PineconeIndexDescription = self.index.describe_index_stats()
            return json.dumps(retval.to_dict(), indent=4)
        return "Index not initialized."

    @property
    def initialized(self) -> bool:
        """
        Check if the Pinecone index is initialized by verifying that the index
        name exists in Pinecone.
        """
        if isinstance(self.pinecone, Pinecone) and isinstance(self.index_name, str):
            indexes = self.pinecone.list_indexes()
            return self.index_name in indexes.names()
        return False

    @property
    def vector_store(self) -> PineconeVectorStore:
        """
        Get the Pinecone vector store.
        """
        if self._vector_store is None:
            if not self.initialized:
                self.init_index()
            self._vector_store = PineconeVectorStore(
                index=self.index,
                embedding=self.embeddings,
                text_key="lc_id",
            )
        return self._vector_store

    @property
    def embeddings(self) -> OpenAIEmbeddings:
        """Get the OpenAI embeddings."""
        if self._embeddings is None:
            self._embeddings = OpenAIEmbeddings(
                api_key=self.llm_api_key,
            )
        return self._embeddings

    @property
    def pinecone(self) -> Optional[Pinecone]:
        """Get the Pinecone instance."""
        if self._pinecone is None:
            logger.debug("%s.pinecone() Initializing Pinecone...", self.formatted_class_name)
            try:
                self._pinecone = Pinecone(api_key=self.pinecone_api_key.get_secret_value())
                logger.debug(
                    "%s.pinecone() connected using API Key: ****%s",
                    self.formatted_class_name,
                    self.pinecone_api_key.get_secret_value()[-4:],
                )
            # pylint: disable=broad-except
            except Exception as e:
                logger.error("%s.pinecone() Error initializing Pinecone: %s", self.formatted_class_name, str(e))
                raise VectorStoreBackendConnectionError(f"Error initializing Pinecone: {str(e)}") from e
        return self._pinecone

    def init_index(self):
        """Verify that an index named self.index_name exists in Pinecone. If not, create it."""
        if isinstance(self.pinecone, Pinecone):
            indexes: IndexList = self.pinecone.list_indexes()
            if self.index_name not in indexes.names():
                logging.debug("%s.init_index() %s does not exist.", self.formatted_class_name, self.index_name)
                self.create()

    def init(self):
        """Initialize Pinecone."""

        self._index = None
        self._index_name = None
        self._text_splitter = None
        self._openai_embeddings = None
        self._vector_store = None

    def delete(self):
        """Delete index."""
        if not self.initialized:
            logging.debug("%s.delete() Index does not exist. Nothing to delete.", self.formatted_class_name)
            return
        if isinstance(self.pinecone, Pinecone) and isinstance(self.index_name, str):
            logging.debug("%s.delete() Deleting index: %s", self.formatted_class_name, self.index_name)
            self.pinecone.delete_index(self.index_name)

    def create(self):
        """Create index."""
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

    def initialize(self):
        """Initialize index."""
        self.delete()
        self.create()

    def add_documents(self, documents: list[Document], embeddings: list[Any]) -> bool:
        """
        Add documents with their corresponding embeddings to the vector store.
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
