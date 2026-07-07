"""Pydantic manifest spec for the LLMHost SAM (Smarter API Manifest) resource."""

import os
from decimal import Decimal
from typing import Any, ClassVar, Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator

from smarter.apps.llm_client.manifest.models.llm_client.const import MANIFEST_KIND
from smarter.apps.llmhost.enum import (
    ApiFormat,
    CloudProvider,
    DeploymentType,
    InferenceEngine,
    Quantization,
)
from smarter.lib.manifest.models import AbstractSAMSpecBase

filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"
SMARTER_PLUGIN_MAX_SYSTEM_ROLE_LENGTH = 2048

# --- Sub-blocks --------------------------------------------------------


class SAMLLMHostProvenanceConfig(BaseModel):
    """Where the model weights came from."""

    huggingfaceRepoId: Optional[str] = Field(default=None, description="e.g. 'meta-llama/Meta-Llama-3-8B-Instruct'")
    huggingfaceRevision: Optional[str] = Field(
        default=None, description="Commit SHA or tag pinned for reproducible deploys."
    )
    license: Optional[str] = None
    modelArchitecture: Optional[str] = Field(default=None, description="e.g. 'llama', 'mistral', 'mixtral', 'qwen2'")


class SAMLLMHostCharacteristicsConfig(BaseModel):
    """Model capability metadata."""

    parameterCount: Optional[int] = Field(default=None, ge=0)
    contextWindow: Optional[int] = Field(default=None, ge=0)
    quantization: Quantization = Quantization.NONE
    embeddingDimensions: Optional[int] = Field(default=None, ge=0)
    supportsStreaming: bool = True
    supportsFunctionCalling: bool = False
    supportsVision: bool = False


class SAMLLMHostServingConfig(BaseModel):
    """The inference server this LLM is exposed through."""

    inferenceEngine: InferenceEngine
    apiFormat: ApiFormat = ApiFormat.OPENAI_COMPATIBLE
    endpointUrl: HttpUrl
    apiKey: Optional[str] = Field(
        default=None,
        description="Reference/secret name, not a plaintext credential. "
        "Resolved against the account's secret store at apply time.",
    )
    engineConfig: dict[str, Any] = Field(
        default_factory=dict,
        description="Engine-specific launch args, sampling defaults, etc.",
    )


class SAMLLMHostInfrastructureConfig(BaseModel):
    """Where and on what hardware this LLM is deployed."""

    deploymentType: DeploymentType
    cloudProvider: Optional[CloudProvider] = None
    region: Optional[str] = None
    instanceType: Optional[str] = Field(default=None, description="e.g. 'g5.2xlarge'")
    gpuType: Optional[str] = Field(default=None, description="e.g. 'A100-80GB'")
    gpuCount: int = Field(default=0, ge=0)
    vramRequiredGb: Optional[int] = Field(default=None, ge=0)
    costPerHour: Optional[Decimal] = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_cloud_fields(self) -> "SAMLLMHostInfrastructureConfig":
        if self.deploymentType == DeploymentType.CLOUD_INSTANCE and not self.cloudProvider:
            raise ValueError("cloudProvider is required when deploymentType is 'cloud_instance'.")
        return self


class SAMLLMHostHealthCheckConfig(BaseModel):
    """Optional health check wiring."""

    healthCheckUrl: Optional[HttpUrl] = None


# --- Top-level spec ------------------------------------------------------


class SAMLLMHostSpecConfig(BaseModel):
    """Spec block for an LLMHost SAM manifest.

    Mirrors smarter.apps.llm_host.models.LLMHost. Consumed by the manifest
    controller to create/update the corresponding LLMHost model instance.
    """

    provenance: SAMLLMHostProvenanceConfig = Field(default_factory=SAMLLMHostProvenanceConfig)
    characteristics: SAMLLMHostCharacteristicsConfig = Field(default_factory=SAMLLMHostCharacteristicsConfig)
    serving: SAMLLMHostServingConfig
    infrastructure: SAMLLMHostInfrastructureConfig
    healthCheck: SAMLLMHostHealthCheckConfig = Field(default_factory=SAMLLMHostHealthCheckConfig)

    @field_validator("serving")
    @classmethod
    def validate_engine_api_format_pairing(cls, v: SAMLLMHostServingConfig) -> SAMLLMHostServingConfig:
        # Ollama's native engine should pair with its native API format,
        # not be silently treated as OpenAI-compatible.
        if v.inferenceEngine == InferenceEngine.OLLAMA and v.apiFormat not in (
            ApiFormat.OLLAMA_NATIVE,
            ApiFormat.OPENAI_COMPATIBLE,
        ):
            raise ValueError("inferenceEngine 'ollama' expects apiFormat 'ollama_native' or " "'openai_compatible'.")
        return v


class SAMLLMHostSpec(AbstractSAMSpecBase):
    """Smarter API LLMClient Manifest LLMClient.spec."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    config: SAMLLMHostSpecConfig = Field(
        ..., description=f"{class_identifier}.config[object]. The configuration for the {MANIFEST_KIND}."
    )


__all__ = [
    "SAMLLMHostSpec",
    "SAMLLMHostProvenanceConfig",
    "SAMLLMHostCharacteristicsConfig",
    "SAMLLMHostServingConfig",
    "SAMLLMHostInfrastructureConfig",
    "SAMLLMHostHealthCheckConfig",
]
