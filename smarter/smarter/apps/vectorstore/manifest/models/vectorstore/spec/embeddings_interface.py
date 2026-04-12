"""Smarter API Manifest - Plugin.spec"""

import logging
import os
from typing import Any, Dict, Literal, Mapping, Optional, Sequence

from pydantic import Field, field_validator

from smarter.apps.provider.models import Provider, ProviderModel
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.manifest.models import SmarterBasePydanticModel

from ..const import MANIFEST_KIND


# pylint: disable=W0613
def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.VECTORSTORE_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)

filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"
logger_prefix = formatted_text(f"{__name__}.SAMVectorstoreSpec()")


class SAMEmbeddingsInterface(SmarterBasePydanticModel):
    """
    Interface for embedding services. Defines methods for generating embeddings
    from text inputs, with optional metadata support.

    This interface originates from langchain_openai.embeddings.base.Embeddings
    """

    provider: str = Field(
        ...,
        description="The name of a Smarter provider associated with this vector database and owned by the authenticated API user.",
        alias="provider",
    )
    provider_model: Optional[str] = Field(
        None,
        description="The name of a Smarter provider model related to the Smarter Provider. Example: 'text-embedding-ada-002'",
        alias="providerModel",
    )
    config: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional configuration settings for the embeddings interface.",
        alias="config",
    )
    dimensions: Optional[int] = Field(None, description="Number of embedding dimensions.", alias="dimensions")
    deployment: Optional[str] = Field(None, description="Deployment name or model name.", alias="deployment")
    api_version: Optional[str] = Field(None, description="OpenAI API version.", alias="apiVersion")
    base_url: Optional[str] = Field(None, description="Base URL for OpenAI API.", alias="baseUrl")
    openai_api_type: Optional[str] = Field(None, description="OpenAI API type.", alias="openaiApiType")
    openai_proxy: Optional[str] = Field(None, description="Proxy URL for OpenAI API.", alias="openaiProxy")
    embedding_ctx_length: int = Field(default=8191, description="Embedding context length.", alias="embeddingCtxLength")
    api_key: Optional[str] = Field(None, description="OpenAI API key or secret reference.", alias="apiKey")
    organization: Optional[str] = Field(None, description="OpenAI organization ID.", alias="organization")
    allowed_special: set[str] | Literal["all"] | None = Field(
        None, description="Allowed special tokens (set[str] or 'all').", alias="allowedSpecial"
    )
    disallowed_special: set[str] | Sequence[str] | Literal["all"] | None = Field(
        None, description="Disallowed special tokens (set, sequence, or 'all').", alias="disallowedSpecial"
    )
    chunk_size: int = Field(default=1000, description="Chunk size for embedding requests.", alias="chunkSize")
    max_retries: int = Field(default=2, description="Maximum number of retries for API calls.", alias="maxRetries")
    timeout: Optional[float] = Field(
        None, description="Timeout for API requests (float, tuple, or other).", alias="timeout"
    )
    headers: Optional[Any] = Field(None, description="Custom headers for API requests.", alias="headers")
    tiktoken_enabled: bool = Field(
        default=True, description="Enable tiktoken for tokenization.", alias="tiktokenEnabled"
    )
    tiktoken_model_name: Optional[str] = Field(None, description="Tiktoken model name.", alias="tiktokenModelName")
    show_progress_bar: bool = Field(
        default=False, description="Show progress bar during embedding.", alias="showProgressBar"
    )
    model_kwargs: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional model keyword arguments.", alias="modelKwargs"
    )
    skip_empty: bool = Field(default=False, description="Skip empty inputs.", alias="skipEmpty")
    default_headers: Mapping[str, str] | None = Field(
        None, description="Default headers for API requests.", alias="defaultHeaders"
    )
    default_query: Optional[Mapping[str, object]] = Field(
        None, description="Default query parameters for API requests.", alias="defaultQuery"
    )
    retry_min_seconds: int = Field(default=4, description="Minimum seconds between retries.", alias="retryMinSeconds")
    retry_max_seconds: int = Field(default=20, description="Maximum seconds between retries.", alias="retryMaxSeconds")
    check_embedding_ctx_length: bool = Field(
        default=True, description="Check embedding context length.", alias="checkEmbeddingCtxLength"
    )

    @field_validator("provider")
    def validate_provider(cls, v):
        """
        Validate that the provider value is a non-empty string if provided and that
        at least 1 record exists in the Provider table with the given name.

        If the model includes an authenticated user then also validate that at
        least 1 record exists in the Provider table with the given name
        that is accessible by the authenticated user.
        """
        v = str(v).strip()
        if not v:
            raise SAMValidationError("Vectorstore provider must not be empty.")
        providers = Provider.objects.filter(name=v)
        if not providers.exists():
            raise SAMValidationError(f"Vectorstore provider '{v}' does not exist or is not accessible.")
        if cls.user:
            for provider in providers:
                if provider.is_readable_by(cls.user):
                    break
            else:
                raise SAMValidationError(f"No Vectorstore provider '{v}' is accessible by the authenticated user.")
        return v

    @field_validator("provider_model")
    def validate_provider_model(cls, v):
        """
        Validate that the provider_model value is a non-empty string if
        provided and that at least 1 record exists in the ProviderModel
        table with the given name and provider.

        If the model includes an authenticated user then also validate that at
        least 1 record exists in the ProviderModel table with the given name and
        provider that is accessible by the authenticated user.
        """
        if v is not None:
            v = str(v).strip()
            if not v:
                raise SAMValidationError("Vectorstore provider_model must not be empty if provided.")
        provider_models = ProviderModel.objects.filter(name=v, provider__name=cls.provider)
        if not provider_models.exists():
            raise SAMValidationError(f"Vectorstore provider_model '{v}' does not exist or is not accessible.")
        if cls.user:
            for provider_model in provider_models:
                if provider_model.provider.is_readable_by(cls.user):
                    break
            else:
                raise SAMValidationError(
                    f"No Vectorstore provider_model '{v}' is accessible by the authenticated user."
                )
        return v


__all__ = ["SAMEmbeddingsInterface"]
