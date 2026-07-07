"""Smarter API LLMHost Enumeration classes."""

from enum import Enum


class InferenceEngine(str, Enum):
    """
    Enumerates the supported model-serving backends for a self-hosted LLM.

    This enum identifies which inference server software is responsible for
    loading model weights and exposing a prediction/completion API. It is
    used by :py:class:`SAMLLMHostSpec` to select the correct client
    behavior and defaults for a given ``LLMHost``.

    :cvar VLLM: `vLLM <https://github.com/vllm-project/vllm>`_, a high-throughput
        serving engine with PagedAttention and continuous batching.
    :cvar TGI: Hugging Face's `Text Generation Inference
        <https://github.com/huggingface/text-generation-inference>`_ server.
    :cvar OLLAMA: `Ollama <https://ollama.com/>`_, a lightweight local model
        runner commonly used for GGUF-quantized models.
    :cvar LLAMA_CPP: `llama.cpp <https://github.com/ggerganov/llama.cpp>`_,
        a CPU/GPU inference engine for GGUF-format models.
    :cvar SGLANG: `SGLang <https://github.com/sgl-project/sglang>`_, a
        structured generation serving engine.
    :cvar TRANSFORMERS: Raw Hugging Face ``transformers`` inference, without
        a dedicated serving layer.
    :cvar TRITON: NVIDIA `Triton Inference Server
        <https://github.com/triton-inference-server/server>`_.
    :cvar CUSTOM: A bespoke or unlisted inference engine, configured via
        ``engineConfig``.
    """

    VLLM = "vllm"
    TGI = "tgi"
    OLLAMA = "ollama"
    LLAMA_CPP = "llama_cpp"
    SGLANG = "sglang"
    TRANSFORMERS = "transformers"
    TRITON = "triton"
    CUSTOM = "custom"


class ApiFormat(str, Enum):
    """
    Enumerates the wire-protocol conventions an ``LLMHost`` endpoint speaks.

    This is distinct from :py:class:`InferenceEngine`: the engine is the
    server software, while the API format is the request/response contract
    that server exposes. Some engines can be configured to speak more than
    one format, which is why this is modeled independently.

    :cvar OPENAI_COMPATIBLE: An endpoint implementing the OpenAI
        ``/v1/chat/completions``-style API, the most common format for
        self-hosted engines such as vLLM and TGI.
    :cvar HUGGINGFACE: The Hugging Face Inference API request/response
        contract.
    :cvar OLLAMA_NATIVE: Ollama's native ``/api/generate``-style API.
    :cvar CUSTOM: A bespoke or unlisted API contract, configured via
        ``engineConfig``.
    """

    OPENAI_COMPATIBLE = "openai_compatible"
    HUGGINGFACE = "huggingface"
    OLLAMA_NATIVE = "ollama_native"
    CUSTOM = "custom"


class Quantization(str, Enum):
    """
    Enumerates the numeric precision or compression scheme applied to a.

    self-hosted model's weights.

    Quantization affects VRAM footprint, inference latency, and output
    quality, and is used alongside ``vramRequiredGb`` to validate that a
    given ``LLMHost`` deployment is sized appropriately for its hardware.

    :cvar NONE: Full, unquantized precision (typically FP32).
    :cvar FP16: 16-bit floating point.
    :cvar BF16: 16-bit brain floating point.
    :cvar INT8: 8-bit integer quantization.
    :cvar INT4: 4-bit integer quantization.
    :cvar GGUF: The `GGUF <https://github.com/ggerganov/ggml/blob/master/docs/gguf.md>`_
        format used by llama.cpp and Ollama, which may itself encode a
        mixed-precision quantization scheme.
    :cvar AWQ: `Activation-aware Weight Quantization
        <https://github.com/mit-han-lab/llm-awq>`_.
    :cvar GPTQ: `GPTQ <https://github.com/IST-DASLab/gptq>`_ post-training
        quantization.
    """

    NONE = "none"
    FP16 = "fp16"
    BF16 = "bf16"
    INT8 = "int8"
    INT4 = "int4"
    GGUF = "gguf"
    AWQ = "awq"
    GPTQ = "gptq"


class DeploymentType(str, Enum):
    """
    Enumerates the infrastructure substrate an ``LLMHost`` is deployed on.

    This determines which of the infrastructure-related fields on
    :py:class:`SAMLLMHostSpec` are applicable; for example,
    ``cloudProvider`` is required when the deployment type is
    :py:attr:`CLOUD_INSTANCE`.

    :cvar DOCKER: A standalone Docker container, not orchestrated by
        Kubernetes.
    :cvar KUBERNETES: A Kubernetes-orchestrated deployment (pod, deployment,
        or similar workload).
    :cvar BARE_METAL: A directly installed process on physical or
        unvirtualized hardware.
    :cvar CLOUD_INSTANCE: A managed cloud VM or compute instance, requiring
        a corresponding :py:class:`CloudProvider` value.
    """

    DOCKER = "docker"
    KUBERNETES = "kubernetes"
    BARE_METAL = "bare_metal"
    CLOUD_INSTANCE = "cloud_instance"


class CloudProvider(str, Enum):
    """
    Enumerates the cloud (or non-cloud) provider hosting an ``LLMHost``.

    instance.

    Only meaningful when :py:class:`DeploymentType` is
    :py:attr:`DeploymentType.CLOUD_INSTANCE`; a
    :py:class:`SAMLLMHostSpec` validator enforces that this field is
    set in that case.

    :cvar AWS: Amazon Web Services.
    :cvar GCP: Google Cloud Platform.
    :cvar AZURE: Microsoft Azure.
    :cvar ON_PREM: Owned, on-premises infrastructure.
    :cvar OTHER: A provider not otherwise enumerated.
    """

    AWS = "aws"
    GCP = "gcp"
    AZURE = "azure"
    ON_PREM = "on_prem"
    OTHER = "other"


class HostStatus(str, Enum):
    """
    Enumerates the lifecycle state of an ``LLMHost`` deployment.

    Tracks a self-hosted model's progression from initial registration
    through active serving, and is surfaced to callers via ``get()`` and
    ``describe()`` on :py:class:`SAMLLMHostBroker` so the current
    operational state of the host is visible without a separate health
    check.

    :cvar PENDING: The ``LLMHost`` record has been created but deployment
        has not yet started.
    :cvar DOWNLOADING: Model weights are being fetched (e.g. from Hugging
        Face) prior to deployment.
    :cvar DEPLOYING: The inference server is being provisioned or started.
    :cvar ACTIVE: The host is deployed and passing health checks.
    :cvar DEGRADED: The host is reachable but not fully healthy (e.g.
        elevated latency or intermittent errors).
    :cvar INACTIVE: The host has been intentionally stopped or scaled down.
    :cvar ERROR: The host failed to deploy or has stopped unexpectedly.
    :cvar DEPRECATED: The host is scheduled for removal and should not
        receive new traffic.
    """

    PENDING = "pending"
    DOWNLOADING = "downloading"
    DEPLOYING = "deploying"
    ACTIVE = "active"
    DEGRADED = "degraded"
    INACTIVE = "inactive"
    ERROR = "error"
    DEPRECATED = "deprecated"
