"""
Embedding Service Interface
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Type

from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings
from pydantic import SecretStr

from smarter.apps.provider.models import ProviderModel
from smarter.apps.secret.models import Secret
from smarter.common.exceptions import SmarterValueError
from smarter.common.mixins import SmarterHelperMixin


class SmarterEmbeddingServiceInterface(ABC, SmarterHelperMixin):
    """
    Interface for embedding services. Defines methods for generating embeddings
    from text inputs, with optional metadata support.

    """

    _EmbeddingsClass: Type[Embeddings] = Embeddings
    _embeddings: Optional[Embeddings] = None
    _api_key: Optional[SecretStr] = None

    def __init__(self, provider_model: ProviderModel):
        super().__init__()
        self.provider_model = provider_model
        if not isinstance(provider_model, ProviderModel):
            raise SmarterValueError("provider_model must be an instance of ProviderModel")
        if not isinstance(provider_model.provider.api_key, Secret):
            raise SmarterValueError("provider_model.provider.api_key must be an instance of Secret")
        api_key_value = provider_model.provider.api_key.get_secret()
        if api_key_value is not None:
            self._api_key = SecretStr(api_key_value)

    @property
    def api_key(self) -> Optional[SecretStr]:
        """Get the API key for the embedding service."""
        return self._api_key

    @property
    def EmbeddingsClass(self) -> Type[Embeddings]:
        """Get the Embeddings class to use for this service."""
        return self._EmbeddingsClass

    @property
    def embeddings(self) -> Embeddings:
        """Get the OpenAI embeddings instance."""
        raise NotImplementedError("The 'embeddings' property must be implemented by subclasses.")

    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts."""
        raise NotImplementedError("The 'embed' method must be implemented by subclasses.")


class SmarterOpenAICompatibleEmbeddingService(SmarterEmbeddingServiceInterface):
    """
    Implementation of the SmarterEmbeddingServiceInterface using OpenAI's embedding API.
    """

    _embeddings: Optional[OpenAIEmbeddings] = None

    def __init__(self, provider_model: ProviderModel):
        super().__init__(provider_model)
        self._EmbeddingsClass = OpenAIEmbeddings

    @property
    def embeddings(self) -> OpenAIEmbeddings:
        """Get the OpenAI embeddings."""
        if self._embeddings is None:
            self._embeddings = OpenAIEmbeddings(
                api_key=self.api_key,
            )
        return self._embeddings

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self.embeddings.embed_documents(texts)
