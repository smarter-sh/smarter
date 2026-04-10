"""
Service layer for managing vector databases, providing abstractions for
provisioning, deleting, and interacting
"""

import glob
import logging
import os
from typing import Optional

from langchain_community.document_loaders.pdf import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from smarter.apps.provider.models import Provider, ProviderModel
from smarter.apps.provider.services import (
    SmarterEmbeddingServiceInterface,
    get_embedding_service,
)
from smarter.apps.vectorstore.backends import Backends, SmarterVectorstoreBackend
from smarter.apps.vectorstore.models import VectorDatabase
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


class VectorstoreService(SmarterHelperMixin):
    """
    Service class for managing vector databases.

    This class provides service layer abstractions for provisioning, deleting, and interacting with
    vector databases using the appropriate backend implementations. It creates a binding between the
    :class:`smarter.apps.vectorstore.models.VectorDatabase` ORM model, which contains the metadata and
    configuration for a vector database, and the backend implementations, which contain the logic for
    interacting with the underlying vector store.

    The service also manages the association with LLM provider models and embedding services, enabling
    seamless integration for embedding and querying operations.

    **Original source:** https://github.com/FullStackWithLawrence/openai-embeddings

    Attributes
    ----------
    db : VectorDatabase
        The ORM model instance containing metadata and configuration for the vector database.
    backend : SmarterVectorstoreBackend
        The backend implementation for interacting with the vector store.
    provider : Provider
        The provider company (e.g., OpenAI, Cohere, etc.).
    provider_model : ProviderModel
        The specific model used for embeddings (e.g., gpt-4o-mini).
    embedding_service : SmarterEmbeddingServiceInterface
        The service for generating embeddings using the provider and model.

    """

    _text_splitter: Optional[RecursiveCharacterTextSplitter] = None

    # Vector metadata and backend implementation
    db: VectorDatabase  # the VectorDatabase ORM model instance containing metadata and configuration for the vector database
    backend: SmarterVectorstoreBackend  # the backend implementation for interacting with the vector store

    # LLM provider models and services
    provider: Provider  # the provider company (e.g. OpenAI, Cohere, etc.)
    provider_model: ProviderModel  # the specific model (e.g. gpt-4o-mini)
    embedding_service: (
        SmarterEmbeddingServiceInterface  # the service for generating embeddings using the provider and model
    )

    def __init__(self, db: VectorDatabase):
        super().__init__()

        # 1.) start with the vectorstore metadata from the VectorDatabase ORM model instance
        self.db = db

        # 2.) get the LLM provider metadata
        self.provider = db.provider
        if not isinstance(self.provider, Provider):
            raise ValueError("db.provider must be an instance of Provider")

        # 3.) get the specific provider model
        self.provider_model = db.provider_model
        if not isinstance(self.provider_model, ProviderModel):
            raise ValueError("db.provider_model must be an instance of ProviderModel")

        # 4.) the embedding service that we need is determined by the provider model attributes.
        self.embedding_service = get_embedding_service(self.provider_model)

        # 5.) initialize the vectorstore backend implementation
        embeddings = self.embedding_service.embeddings
        self.backend = Backends.get_backend(name=db.name, backend=db.backend, embeddings=embeddings, vector_store=None)

        if self.ready:
            logger.debug(
                "%s.__init__() VectorstoreService initialized and ready to use for vector database: %s",
                self.formatted_class_name,
                db,
            )
        else:
            logger.error(
                "%s.__init__() VectorstoreService initialized but not ready to use for vector database: %s",
                self.formatted_class_name,
                db,
            )

    @property
    def ready(self) -> bool:
        """
        Check if the vector database backend is ready for operations.
        """
        return self.backend.ready

    @property
    def text_splitter(self) -> RecursiveCharacterTextSplitter:
        """Get the text splitter."""
        if self._text_splitter is None:
            self._text_splitter = RecursiveCharacterTextSplitter()
        return self._text_splitter

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

    def pdf_loader(self, filepath: str):
        """
        Embed PDF.
        1. Load PDF document text data
        2. Split into pages
        3. Embed each page
        4. Store in Pinecone

        Note: it's important to make sure that the "context" field that holds the document text
        in the metadata is not indexed. Currently you need to specify explicitly the fields you
        do want to index. For more information checkout
        https://docs.pinecone.io/docs/manage-indexes#selective-metadata-indexing
        """
        self.backend.initialize()

        pdf_files = glob.glob(os.path.join(filepath, "*.pdf"))
        i = 0
        for pdf_file in pdf_files:
            i += 1
            j = len(pdf_files)
            logger.debug("%s.pdf_loader() Loading PDF %d of %d: %s", self.formatted_class_name, i, j, pdf_file)
            loader = PyPDFLoader(file_path=pdf_file)
            docs = loader.load()
            k = 0
            for doc in docs:
                k += 1
                logger.debug(
                    "%s.pdf_loader() Loading page %d of %d from PDF: %s",
                    self.formatted_class_name,
                    k,
                    len(docs),
                    pdf_file,
                )
                documents = self.text_splitter.create_documents([doc.page_content])
                document_texts = [doc.page_content for doc in documents]
                embeddings = self.embedding_service.embed_documents(document_texts)
                self.backend.add_documents(documents=documents, embeddings=embeddings)

        logger.debug("%s.pdf_loader() Finished loading PDFs. \n%s", self.formatted_class_name, self.backend.index_stats)
