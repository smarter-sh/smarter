"""The embeddings model of a vectorstore, from its Provider."""

from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings
from pydantic import SecretStr

from smarter.common.exceptions import SmarterConfigurationError

from .models import VectorstoreMeta

OPENAI_PROVIDER = "openai"


def get_embeddings(vectorstore: VectorstoreMeta) -> Embeddings:
    """
    The embeddings model of a vectorstore: an OpenAI-compatible embeddings API.

    It uses the Provider's base URL and API key, so any provider with an OpenAI-compatible
    embeddings endpoint works, including an LLMHost that serves an embeddings model, registered
    as a Provider.

    :raises SmarterConfigurationError: if the vectorstore has no Provider, model or API key.
    """
    provider = vectorstore.embeddings_provider
    if provider is None or not vectorstore.embeddings_model:
        raise SmarterConfigurationError(f"Vectorstore {vectorstore.name} has no embeddings provider or model.")
    api_key = provider.api_key.get_secret() if provider.api_key else None  # type: ignore[union-attr]
    if not api_key:
        raise SmarterConfigurationError(f"Provider {provider.name} has no API key.")
    embeddings_spec = (vectorstore.spec or {}).get("embeddings") or {}
    kwargs = {
        "model": vectorstore.embeddings_model,
        "api_key": SecretStr(api_key),
        "chunk_size": embeddings_spec.get("batchSize") or 64,
        # tiktoken's token counting is only right for OpenAI's own models.
        "check_embedding_ctx_length": provider.name.lower() == OPENAI_PROVIDER,
    }
    if provider.base_url:
        kwargs["base_url"] = provider.base_url
    if embeddings_spec.get("dimensions"):
        kwargs["dimensions"] = embeddings_spec["dimensions"]
    return OpenAIEmbeddings(**kwargs)


__all__ = ["get_embeddings"]
