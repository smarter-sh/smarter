"""
Smarter API LLMHost Manifest - enumerated datatypes.

An LLMHost separates *what* is served from *how* it is served, so that no single
model hub or inference server is baked into the manifest:

- :class:`SAMLLMHostModelSource`: where the weights come from, e.g. Hugging Face,
  the Ollama library, S3, a URL, or a pre-populated volume.
- :class:`SAMLLMHostEngine`: the inference server that loads the weights and
  exposes an API, e.g. vLLM or llama.cpp.
- :class:`SAMLLMHostApiFormat`: the wire protocol that the inference server speaks.
"""

from smarter.common.enum import SmarterEnumAbstract


class SAMLLMHostModelSource(SmarterEnumAbstract):
    """
    Where an LLMHost's model weights come from.

    - ``huggingface``: a Hugging Face Hub repository, e.g. ``meta-llama/Llama-3.1-8B-Instruct``.
      The inference engine downloads it, with the optional ``tokenSecret`` for gated models.
    - ``ollama``: an Ollama library tag, e.g. ``llama3.1:8b``. Requires the ollama engine.
    - ``s3``: an S3 prefix, e.g. ``s3://bucket/models/llama``, copied to the model volume by an
      init container. Credentials come from the pod's service account (IRSA).
    - ``url``: a single file, e.g. a GGUF file, downloaded to the model volume by an init container.
    - ``pvc``: weights already on a PersistentVolumeClaim, named by ``storage.existingClaim``.
      ``repository`` is the path within the volume.
    """

    HUGGINGFACE = "huggingface"
    OLLAMA = "ollama"
    S3 = "s3"
    URL = "url"
    PVC = "pvc"

    @classmethod
    def downloaded(cls) -> list[str]:
        """The sources that an init container copies to the model volume."""
        return [cls.S3.value, cls.URL.value]

    @classmethod
    def local(cls) -> list[str]:
        """The sources that the engine loads from a path on the model volume."""
        return [cls.S3.value, cls.URL.value, cls.PVC.value]


class SAMLLMHostEngine(SmarterEnumAbstract):
    """
    The inference server that loads an LLMHost's weights and exposes an API.

    - ``vllm``: `vLLM <https://github.com/vllm-project/vllm>`_, high-throughput GPU serving.
    - ``tgi``: Hugging Face `Text Generation Inference <https://github.com/huggingface/text-generation-inference>`_.
    - ``sglang``: `SGLang <https://github.com/sgl-project/sglang>`_.
    - ``llama_cpp``: `llama.cpp <https://github.com/ggml-org/llama.cpp>`_'s ``llama-server``, for GGUF
      models, on CPU or GPU.
    - ``ollama``: `Ollama <https://ollama.com/>`_, for GGUF models, on CPU or GPU.
    - ``tei``: Hugging Face `Text Embeddings Inference <https://github.com/huggingface/text-embeddings-inference>`_,
      for embedding models.
    - ``custom``: any other container image, configured with ``engine.image``, ``engine.port`` and
      ``engine.args``.
    """

    VLLM = "vllm"
    TGI = "tgi"
    SGLANG = "sglang"
    LLAMA_CPP = "llama_cpp"
    OLLAMA = "ollama"
    TEI = "tei"
    CUSTOM = "custom"


class SAMLLMHostApiFormat(SmarterEnumAbstract):
    """
    The wire protocol that an LLMHost's inference server speaks.

    - ``openai_compatible``: the OpenAI ``/v1/chat/completions``, ``/v1/completions`` and
      ``/v1/embeddings`` API. Every built-in engine speaks it.
    - ``huggingface``: the Hugging Face ``/generate`` API, of TGI.
    - ``ollama_native``: Ollama's ``/api/chat`` API.
    - ``custom``: anything else.
    """

    OPENAI_COMPATIBLE = "openai_compatible"
    HUGGINGFACE = "huggingface"
    OLLAMA_NATIVE = "ollama_native"
    CUSTOM = "custom"


class SAMLLMHostTask(SmarterEnumAbstract):
    """
    What an LLMHost's model does.

    - ``text-generation``: chat and completions.
    - ``embedding``: vector embeddings.
    """

    TEXT_GENERATION = "text-generation"
    EMBEDDING = "embedding"


class SAMLLMHostQuantization(SmarterEnumAbstract):
    """
    The numeric precision or compression of an LLMHost's weights.

    It is informational, and is used to estimate the GPU memory that a model requires.
    It does not change how the engine loads the weights: use ``engine.dtype`` or ``engine.args``.
    """

    NONE = "none"
    FP32 = "fp32"
    FP16 = "fp16"
    BF16 = "bf16"
    FP8 = "fp8"
    MXFP4 = "mxfp4"
    INT8 = "int8"
    INT4 = "int4"
    GGUF = "gguf"
    AWQ = "awq"
    GPTQ = "gptq"

    @classmethod
    def bytes_per_parameter(cls, quantization: str) -> float:
        """The approximate bytes that each parameter occupies in GPU memory."""
        return {
            cls.FP32.value: 4.0,
            cls.FP8.value: 1.0,
            cls.INT8.value: 1.0,
            cls.MXFP4.value: 0.55,
            cls.INT4.value: 0.55,
            cls.AWQ.value: 0.55,
            cls.GPTQ.value: 0.55,
            cls.GGUF.value: 0.6,
        }.get(quantization, 2.0)


class SAMLLMHostStorageAccessMode(SmarterEnumAbstract):
    """The access mode of an LLMHost's model volume."""

    READ_WRITE_ONCE = "ReadWriteOnce"
    READ_WRITE_MANY = "ReadWriteMany"
    READ_ONLY_MANY = "ReadOnlyMany"


class SAMLLMHostStatusEnum(SmarterEnumAbstract):
    """
    The lifecycle state of an LLMHost.

    - ``provisioning``: Smarter is adding a node to the LLMHost's compute's node group, and the
      pods wait for it to join the cluster.
    - ``pending``: deployed, and waiting for the pods to be scheduled.
    - ``downloading``: an init container is copying the weights to the model volume.
    - ``deploying``: the inference server is starting, downloading or loading the weights.
    - ``active``: every replica is ready.
    - ``degraded``: some, but not all, replicas are ready, or the health check fails.
    - ``inactive``: not deployed, e.g. after undeploy.
    - ``error``: the deployment failed, e.g. the image cannot be pulled, or the server crashes.
    """

    PROVISIONING = "provisioning"
    PENDING = "pending"
    DOWNLOADING = "downloading"
    DEPLOYING = "deploying"
    ACTIVE = "active"
    DEGRADED = "degraded"
    INACTIVE = "inactive"
    ERROR = "error"

    @classmethod
    def deployed(cls) -> list[str]:
        """
        The states in which the LLMHost's Kubernetes resources may exist, and so may use nodes.

        ``error`` is included: e.g. a pod whose image cannot be pulled still holds its node.
        Status checks correct it to ``inactive`` if the resources do not exist.
        """
        return [
            cls.PROVISIONING.value,
            cls.PENDING.value,
            cls.DOWNLOADING.value,
            cls.DEPLOYING.value,
            cls.ACTIVE.value,
            cls.DEGRADED.value,
            cls.ERROR.value,
        ]


class SAMLLMHostEventType(SmarterEnumAbstract):
    """The type of an LLMHost lifecycle event."""

    LAUNCHED = "launched"
    STATUS_CHANGED = "status_changed"
    DESTROYED = "destroyed"
    NODES_SCALED = "nodes_scaled"
    ERROR = "error"
