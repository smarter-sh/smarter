"""Smarter API Manifest - Plugin.spec"""

import logging
import os
from typing import Any, ClassVar, Dict, Literal, Mapping, Optional, Sequence

from langchain_community.vectorstores.utils import DistanceStrategy
from pinecone.db_control.enums import DeletionProtection, Metric, VectorType
from pinecone.db_control.models import ByocSpec, PodSpec, ServerlessSpec
from pydantic import Field, field_validator

from smarter.apps.vectorstore.enum import SmarterVectorStoreBackends
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib.django import waffle
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.manifest.models import AbstractSAMSpecBase, SmarterBasePydanticModel

from .const import MANIFEST_KIND


# pylint: disable=W0613
def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.VECTORSTORE_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)

filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"
logger_prefix = formatted_text(f"{__name__}.SAMVectorstoreSpec()")


class SAMIndexModelInterface(SmarterBasePydanticModel):
    """
    Interface for index model configuration, inspired by LangChain IndexModel.

    original interface comes from pinecone.db_control.models.IndexModel
    """

    spec: Optional[dict[str, Any]] = Field(
        None,
        description="Index deployment spec. Accepts a dict, ServerlessSpec, PodSpec, or ByocSpec. Example: ServerlessSpec(cloud=CloudProvider.AWS, region=AwsRegion.US_EAST_1)",
        alias="spec",
    )
    dimension: Optional[int] = Field(
        None,
        description="Number of dimensions for the index. Must be between 1 and 20,000, or None. Example: 1536.",
        alias="dimension",
        ge=1,
        le=20000,
    )
    metric: Optional[str] = Field(
        "cosine",
        description="Distance metric for similarity search. Accepts Metric enum or string. Default: 'cosine'.",
        alias="metric",
    )
    timeout: Optional[int] = Field(
        None,
        description="Timeout in seconds for index operations. Must be greater than zero or None.",
        alias="timeout",
        gt=0,
    )
    deletion_protection: Optional[str] = Field(
        "disabled",
        description="Deletion protection setting. Accepts DeletionProtection enum or string. Default: 'disabled'.",
        alias="deletionProtection",
    )
    vector_type: Optional[str] = Field(
        "dense", description="Type of vector. Accepts VectorType enum or string. Default: 'dense'.", alias="vectorType"
    )

    @field_validator("spec")
    def validate_spec(cls, v):
        """
        Validate that the spec value is either a dict, ServerlessSpec, PodSpec, or ByocSpec if provided.

        spec: Dict[Unknown, Unknown] | ServerlessSpec | PodSpec | ByocSpec, <---- ServerlessSpec(cloud=CloudProvider.AWS, region=AwsRegion.US_EAST_1)

        from pinecone.db_control.models import ServerlessSpec
        from pinecone.db_control.enums import CloudProvider, AwsRegion

        """
        if v is not None:
            if not isinstance(v, dict):
                raise SAMValidationError(
                    "IndexModel spec must be a dictionary, or Pinecone ServerlessSpec, PodSpec, or ByocSpec."
                )
            # ensure that the value is a dict, ServerlessSpec, PodSpec, or ByocSpec
            try:
                ServerlessSpec(**v)
                logger.debug("%s IndexModel spec validated as ServerlessSpec.", logger_prefix)
            # pylint: disable=broad-except
            except Exception:
                try:
                    PodSpec(**v)
                    logger.debug("%s IndexModel spec validated as PodSpec.", logger_prefix)
                # pylint: disable=broad-except
                except Exception:
                    try:
                        ByocSpec(**v)
                        logger.debug("%s IndexModel spec validated as ByocSpec.", logger_prefix)
                    # pylint: disable=broad-except
                    except Exception as e:
                        raise SAMValidationError(
                            "IndexModel spec must be a dict that conforms to Pinecone ServerlessSpec, PodSpec, or ByocSpec."
                        ) from e
        return v

    @field_validator("metric")
    def validate_metric(cls, v):
        """
        Validate that the metric value is a valid Metric enum value or string.
        """
        valid_metrics = {item.value.lower() for item in Metric}
        if v.lower() not in valid_metrics:
            raise SAMValidationError(f"Invalid metric: {v}. Supported metrics are: {', '.join(valid_metrics)}.")
        return v.lower()

    @field_validator("deletion_protection")
    def validate_deletion_protection(cls, v):
        """
        Validate that the deletion_protection value is a valid DeletionProtection enum value or string.
        """
        valid_options = {item.value.lower() for item in DeletionProtection}
        if v.lower() not in valid_options:
            raise SAMValidationError(
                f"Invalid deletion_protection: {v}. Supported options are: {', '.join(valid_options)}."
            )
        return v.lower()

    @field_validator("vector_type")
    def validate_vector_type(cls, v):
        """
        Validate that the vector_type value is a valid VectorType enum value or string.
        """
        valid_types = {item.value.lower() for item in VectorType}
        if v.lower() not in valid_types:
            raise SAMValidationError(f"Invalid vector_type: {v}. Supported types are: {', '.join(valid_types)}.")
        return v.lower()


class SAMEmbeddingsInterface(SmarterBasePydanticModel):
    """
    Interface for embedding services. Defines methods for generating embeddings
    from text inputs, with optional metadata support.

    This interface originates from https://github.com/langchain-ai/langchain/blob/master/libs/partners/openai/langchain_openai/embeddings/base.py
    """

    model: str = Field(default="text-embedding-ada-002", description="OpenAI model name.", alias="model")
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


class SAMVectorstoreInterface(SmarterBasePydanticModel):
    """
    Smarter API - Vectorstore ORM Specification.

    This interface derives from a combination of
    langchain_core.vectorstores.base.VectorStoreRetriever,
    plus that which is required for establishing an authenticated connections to a
    vector database and for configuring the vectorstore manifest in the Smarter API.
    """

    name: str = Field(
        ...,
        description="The name of the Vectorstore. Case sensitive. Must be unique and not empty, with no leading or trailing whitespace and no special characters. examples: 'OpenAI', 'GoogleAI', 'MetaAI'.",
        alias="name",
    )
    description: Optional[str] = Field(None, description="A brief description of the Vectorstore.", alias="description")
    backend: str = Field(
        ..., description="The backend type for the vector database (e.g., qdrant, weaviate, pinecone).", alias="backend"
    )
    host: str = Field(..., description="The host address of the vector database.", alias="host")
    port: int = Field(..., description="The port number for the vector database.", alias="port")
    auth_config: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="The authentication configuration for the vector database.",
        alias="authConfig",
    )
    password: Optional[str] = Field(
        None,
        description=(
            "The name of a Smarter Secret object containing the "
            "password or API key for the vector database and owned by the "
            "authenticated API user."
        ),
        alias="password",
    )
    config: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="The configuration settings for the vector database.", alias="config"
    )
    is_active: bool = Field(
        default=True, description="Indicates whether the vector database is active.", alias="isActive"
    )
    provider: str = Field(
        ...,
        description="The name of a Smarter provider associated with this vector database and owned by the authenticated API user.",
        alias="provider",
    )
    provider_model: Optional[str] = Field(
        None, description="The name of a Smarter provider model related to the Smarter Provider.", alias="providerModel"
    )
    text_key: Optional[str] = Field(
        None,
        description="The key in the vector database where the original text is stored, if applicable.",
        alias="textKey",
    )
    namespace: Optional[str] = Field(
        None, description="The namespace to use for the vector database, if applicable.", alias="namespace"
    )
    distance_strategy: Optional[str] = Field(
        None,
        description="The distance strategy to use for similarity search (e.g., cosine, euclidean, dot_product), if applicable.",
        alias="distanceStrategy",
    )

    @field_validator("backend")
    def validate_backend(cls, v):
        """
        Validate that the backend value is not empty and is one of the
        supported vectorstore backends.
        """
        v = str(v).strip()
        if not v:
            raise SAMValidationError("Vectorstore backend must not be empty.")
        if v not in SmarterVectorStoreBackends.all():
            raise SAMValidationError(
                f"Unsupported vectorstore backend: {v}. Supported backends are: {', '.join(SmarterVectorStoreBackends.all())}."
            )
        return v

    @field_validator("host")
    def validate_host(cls, v):
        """
        Validate that the host value is not empty and is a valid hostname or IP address.
        """
        v = str(v).strip()
        if not v:
            raise SAMValidationError("Vectorstore host must not be empty.")
        if not SmarterValidator.is_valid_hostname(v):
            raise SAMValidationError(f"Invalid vectorstore host: {v}. Must be a valid hostname or IP address.")
        return v

    @field_validator("port")
    def validate_port(cls, v):
        """
        Validate that the port value is a valid integer between 1 and 65535."""
        if not SmarterValidator.is_valid_port(v):
            raise SAMValidationError(f"Invalid vectorstore port: {v}. Must be an integer between 1 and 65535.")
        return v

    @field_validator("auth_config")
    def validate_auth_config(cls, v):
        """
        Validate that the auth_config value is a dictionary if provided.
        """
        if v is not None and not isinstance(v, dict):
            raise SAMValidationError("Vectorstore auth_config must be a dictionary.")
        return v

    @field_validator("password")
    def validate_password(cls, v):
        """
        Validate that the password value is a non-empty string if provided.
        """
        if v is not None:
            v = str(v).strip()
            if not v:
                raise SAMValidationError("Vectorstore password must not be empty if provided.")
        return v

    @field_validator("config")
    def validate_config(cls, v):
        """
        Validate that the config value is a dictionary if provided.
        """
        if v is not None and not isinstance(v, dict):
            raise SAMValidationError("Vectorstore config must be a dictionary.")
        return v

    @field_validator("is_active")
    def validate_is_active(cls, v):
        """
        Validate that the is_active value is a boolean.
        """
        if not isinstance(v, bool):
            raise SAMValidationError("Vectorstore is_active must be a boolean value.")
        return v

    @field_validator("provider")
    def validate_provider(cls, v):
        """
        Validate that the provider value is a non-empty string if provided.
        """
        v = str(v).strip()
        if not v:
            raise SAMValidationError("Vectorstore provider must not be empty.")
        return v

    @field_validator("provider_model")
    def validate_provider_model(cls, v):
        """
        Validate that the provider_model value is a non-empty string if provided.
        """
        if v is not None:
            v = str(v).strip()
            if not v:
                raise SAMValidationError("Vectorstore provider_model must not be empty if provided.")
        return v

    @field_validator("text_key")
    def validate_text_key(cls, v):
        """
        Validate that the text_key value is a non-empty string if provided.
        """
        if v is not None:
            v = str(v).strip()
            if not v:
                raise SAMValidationError("Vectorstore text_key must not be empty if provided.")
        return v

    @field_validator("namespace")
    def validate_namespace(cls, v):
        """
        Validate that the namespace value is a non-empty string if provided.
        """
        if v is not None:
            v = str(v).strip()
            if not v:
                raise SAMValidationError("Vectorstore namespace must not be empty if provided.")
        return v

    @field_validator("distance_strategy")
    def validate_distance_strategy(cls, v):
        """
        Validate that the distance_strategy value is a non-empty string and matches DistanceStrategy enum if provided.
        """
        if v is not None:
            v = str(v).strip()
            if not v:
                raise SAMValidationError("Vectorstore distance_strategy must not be empty if provided.")
            valid_values = {item.value for item in DistanceStrategy}
            if v not in valid_values:
                raise SAMValidationError(
                    f"Unsupported distance_strategy: {v}. Supported strategies are: {', '.join(valid_values)}."
                )
        return v


class SAMVectorstoreSpec(AbstractSAMSpecBase):
    """Smarter API Vectorstore Manifest Vectorstore.spec"""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    vectorstore: SAMVectorstoreInterface = Field(
        ..., description=f"{class_identifier}.selector[obj]: the spec for the {MANIFEST_KIND} vectorstore interface"
    )
    embeddings: SAMEmbeddingsInterface = Field(
        ..., description=f"{class_identifier}.selector[obj]: the spec for the {MANIFEST_KIND} embeddings interface"
    )
    indexModel: SAMIndexModelInterface = Field(
        ..., description=f"{class_identifier}.selector[obj]: the spec for the {MANIFEST_KIND} index model configuration"
    )
