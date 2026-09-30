"""All models for the LLM Host app."""

from django.core.validators import MinValueValidator
from django.db import models

from smarter.apps.account.models import (
    MetaDataWithOwnershipModel,
)
from smarter.lib import logging
from smarter.lib.django.waffle.switches import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.LLM_HOST_LOGGING])


class LLMHost(MetaDataWithOwnershipModel):
    """Implements the LLMHost API model.

    Models a self-hosted LLM: its provenance (e.g. a Hugging Face repo),
    its serving stack (inference engine + endpoint), and the hardware
    it's deployed on. Distinct from a hosted/third-party provider config —
    this assumes the org owns the deployment lifecycle.
    """

    class InferenceEngine(models.TextChoices):
        VLLM = "vllm", "vLLM"
        TGI = "tgi", "Text Generation Inference"
        OLLAMA = "ollama", "Ollama"
        LLAMA_CPP = "llama_cpp", "llama.cpp"
        SGLANG = "sglang", "SGLang"
        TRANSFORMERS = "transformers", "Transformers (raw)"
        TRITON = "triton", "Triton Inference Server"
        CUSTOM = "custom", "Custom"

    class ApiFormat(models.TextChoices):
        OPENAI_COMPATIBLE = "openai_compatible", "OpenAI-compatible"
        HUGGINGFACE = "huggingface", "Hugging Face Inference API"
        OLLAMA_NATIVE = "ollama_native", "Ollama native"
        CUSTOM = "custom", "Custom"

    class Quantization(models.TextChoices):
        NONE = "none", "None (full precision)"
        FP16 = "fp16", "FP16"
        BF16 = "bf16", "BF16"
        INT8 = "int8", "INT8"
        INT4 = "int4", "INT4"
        GGUF = "gguf", "GGUF"
        AWQ = "awq", "AWQ"
        GPTQ = "gptq", "GPTQ"

    class DeploymentType(models.TextChoices):
        DOCKER = "docker", "Docker"
        KUBERNETES = "kubernetes", "Kubernetes"
        BARE_METAL = "bare_metal", "Bare metal"
        CLOUD_INSTANCE = "cloud_instance", "Cloud instance"

    class CloudProvider(models.TextChoices):
        AWS = "aws", "AWS"
        GCP = "gcp", "GCP"
        AZURE = "azure", "Azure"
        ON_PREM = "on_prem", "On-prem"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        DOWNLOADING = "downloading", "Downloading weights"
        DEPLOYING = "deploying", "Deploying"
        ACTIVE = "active", "Active"
        DEGRADED = "degraded", "Degraded"
        INACTIVE = "inactive", "Inactive"
        ERROR = "error", "Error"
        DEPRECATED = "deprecated", "Deprecated"

    # --- Provenance ---------------------------------------------------
    huggingface_repo_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="e.g. 'meta-llama/Meta-Llama-3-8B-Instruct'",
    )
    huggingface_revision = models.CharField(
        max_length=64,
        blank=True,
        help_text="Commit SHA or tag pinned for reproducible deploys.",
    )
    license = models.CharField(max_length=100, blank=True)
    model_architecture = models.CharField(
        max_length=100,
        blank=True,
        help_text="e.g. 'llama', 'mistral', 'mixtral', 'qwen2'",
    )

    # --- Model characteristics -----------------------------------------
    parameter_count = models.BigIntegerField(null=True, blank=True, validators=[MinValueValidator(0)])
    context_window = models.PositiveIntegerField(null=True, blank=True)
    quantization = models.CharField(max_length=20, choices=Quantization.choices, default=Quantization.NONE)
    embedding_dimensions = models.PositiveIntegerField(
        null=True, blank=True, help_text="Set only for embedding models."
    )
    supports_streaming = models.BooleanField(default=True)
    supports_function_calling = models.BooleanField(default=False)
    supports_vision = models.BooleanField(default=False)

    # --- Serving stack ---------------------------------------------------
    inference_engine = models.CharField(max_length=20, choices=InferenceEngine.choices)
    api_format = models.CharField(max_length=20, choices=ApiFormat.choices, default=ApiFormat.OPENAI_COMPATIBLE)
    endpoint_url = models.URLField(help_text="Base URL of the inference server.")
    # NOTE: swap this for whatever secret-backed field Smarter API already
    # uses for account/provider credentials (I don't have that class in
    # scope here) rather than storing plaintext.
    api_key = models.CharField(max_length=255, blank=True)

    # --- Infrastructure ---------------------------------------------------
    deployment_type = models.CharField(max_length=20, choices=DeploymentType.choices)
    cloud_provider = models.CharField(max_length=20, choices=CloudProvider.choices, blank=True)
    region = models.CharField(max_length=50, blank=True)
    instance_type = models.CharField(max_length=50, blank=True, help_text="e.g. 'g5.2xlarge'")
    gpu_type = models.CharField(max_length=50, blank=True, help_text="e.g. 'A100-80GB'")
    gpu_count = models.PositiveSmallIntegerField(default=0)
    vram_required_gb = models.PositiveIntegerField(null=True, blank=True)

    # --- Lifecycle / health -----------------------------------------------
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    health_check_url = models.URLField(blank=True)
    last_health_check_at = models.DateTimeField(null=True, blank=True)
    last_health_ok = models.BooleanField(null=True, blank=True)

    # --- Cost tracking ---------------------------------------------------
    cost_per_hour = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)

    # --- Escape hatch for engine-specific settings -----------------------
    engine_config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Engine-specific launch args, sampling defaults, etc.",
    )

    # pylint: disable=C0115
    class Meta:
        verbose_name_plural = "LLMHosts"
        unique_together = ("user_profile", "name")

    def __str__(self) -> str:
        return f"{self.name}"


__all__ = ["LLMHost"]
