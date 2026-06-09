"""
Provider Services
"""

from smarter.apps.provider.models import ProviderModel

from .embedding import (
    SmarterEmbeddingServiceInterface,
    SmarterOpenAICompatibleEmbeddingService,
)


def get_embedding_service(provider_model: ProviderModel) -> SmarterEmbeddingServiceInterface:
    """
    Factory function to get the appropriate embedding service based on the provider's configuration.
    """
    return SmarterOpenAICompatibleEmbeddingService(provider_model)


__all__ = [
    "SmarterEmbeddingServiceInterface",
    "SmarterOpenAICompatibleEmbeddingService",
]
