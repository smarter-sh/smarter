"""
Smarter API Manifest - LLMHost.spec.

An LLMHost is a large language model that Smarter hosts on Kubernetes. Applying the
manifest stores it; ``smarter deploy`` launches it, creating a Deployment, Service,
PersistentVolumeClaim, and optionally an Ingress and a Secret, in the environment's
namespace; ``smarter undeploy`` destroys them.

The spec separates *what* is served (``model``) from *how* it is served (``engine``),
and from *where* it runs (``compute``, ``resources``, ``storage``, ``network``), so that a
model from any source can be served by any engine that supports that source.

``compute`` names an LLMHostCompute: a kind of node, e.g. g6.2xlarge with one NVIDIA L4, and the
node group of those nodes, which Smarter scales as LLMHosts are launched and destroyed.
``resources`` is what one replica's pod requests of that node; it must fit the node.

.. code-block:: yaml

    spec:
      model:
        source: huggingface                     # huggingface, ollama, s3, url or pvc
        repository: meta-llama/Llama-3.1-8B-Instruct
        revision: main
        servedName: llama-3.1-8b-instruct       # the model name of the OpenAI API
        tokenSecret: huggingface_token          # a Smarter Secret, for gated models
        task: text-generation                   # text-generation or embedding
        parameterCount: 8030000000
        contextWindow: 131072
        quantization: bf16
        capabilities:
          functionCalling: true
      engine:
        name: vllm                              # vllm, tgi, sglang, llama_cpp, ollama, tei or custom
        contextLength: 16384
        args:
          - --enable-auto-tool-choice
          - --tool-call-parser=llama3_json
      compute: gpu_a10g_1x                      # an LLMHostCompute: the node, and its node group
      resources:                                # what one replica's pod requests of the node
        gpuCount: 1
        cpu: "4"
        memory: 24Gi
      storage:
        size: 50Gi
      network:
        ingress: true
"""

import os
import re
from typing import Any, ClassVar, Optional

from pydantic import ConfigDict, Field, field_validator, model_validator

from smarter.apps.llmhost.manifest.enum import (
    SAMLLMHostApiFormat,
    SAMLLMHostEngine,
    SAMLLMHostModelSource,
    SAMLLMHostQuantization,
    SAMLLMHostStorageAccessMode,
    SAMLLMHostTask,
)
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.manifest.models import AbstractSAMSpecBase

from .const import (
    DEFAULT_GPU_RESOURCE,
    DEFAULT_PERIOD_SECONDS,
    DEFAULT_REPLICAS,
    DEFAULT_SHM_SIZE,
    DEFAULT_STARTUP_TIMEOUT_SECONDS,
    DEFAULT_STORAGE_SIZE,
    ENV_NAME_PATTERN,
    HOSTNAME_PATTERN,
    K8S_QUANTITY_PATTERN,
    MANIFEST_KIND,
    MAX_ARGS,
    MAX_GPU_COUNT,
    MAX_REPLICAS,
)

filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"

ALL_SOURCES = frozenset(SAMLLMHostModelSource.all())
HF_AND_LOCAL = frozenset(
    [SAMLLMHostModelSource.HUGGINGFACE.value, *SAMLLMHostModelSource.local()],
)

ENGINE_RULES: dict[str, dict[str, Any]] = {
    # sources: the model sources that the engine can load.
    # tasks: the tasks that the engine can serve.
    # apiKey: whether the engine authenticates requests with an API key.
    # requiresFile: whether the engine loads a single weights file, e.g. GGUF, rather than a directory.
    # requiresGpu: whether the engine's default image requires a GPU.
    SAMLLMHostEngine.VLLM.value: {"sources": HF_AND_LOCAL, "tasks": None, "apiKey": True, "requiresGpu": True},
    SAMLLMHostEngine.TGI.value: {"sources": HF_AND_LOCAL, "tasks": {"text-generation"}, "apiKey": False},
    SAMLLMHostEngine.SGLANG.value: {"sources": HF_AND_LOCAL, "tasks": None, "apiKey": True, "requiresGpu": True},
    SAMLLMHostEngine.LLAMA_CPP.value: {
        "sources": HF_AND_LOCAL,
        "tasks": None,
        "apiKey": True,
        "requiresFile": True,
    },
    SAMLLMHostEngine.OLLAMA.value: {
        "sources": frozenset([SAMLLMHostModelSource.OLLAMA.value, SAMLLMHostModelSource.HUGGINGFACE.value]),
        "tasks": None,
        "apiKey": False,
    },
    SAMLLMHostEngine.TEI.value: {"sources": HF_AND_LOCAL, "tasks": {"embedding"}, "apiKey": True},
    SAMLLMHostEngine.CUSTOM.value: {"sources": ALL_SOURCES, "tasks": None, "apiKey": False},
}
"""What each engine supports, for validation.

``tasks: None`` means any task.
"""


def engine_supports_task(engine: str, task: str) -> bool:
    """Return whether an engine can serve a task."""
    tasks = ENGINE_RULES[engine]["tasks"]
    return tasks is None or task in tasks


def engine_supports_api_key(engine: str) -> bool:
    """Return whether an engine authenticates requests with an API key."""
    return bool(ENGINE_RULES[engine]["apiKey"])


def choice(value: Optional[str], choices: list[str], field: str) -> str:
    """Return ``value``, lower cased, if it is one of ``choices``."""
    value = (value or "").strip().lower()
    lowered = {c.lower(): c for c in choices}
    if value not in lowered:
        raise SAMValidationError(f"{field}: must be one of {choices}, not '{value}'.")
    return lowered[value]


def quantity(value: Optional[str], field: str) -> Optional[str]:
    """Return ``value`` if it is a Kubernetes resource quantity, e.g. ``24Gi``."""
    if value is None:
        return None
    value = str(value).strip()
    if not re.match(K8S_QUANTITY_PATTERN, value):
        raise SAMValidationError(f"{field}: '{value}' is not a Kubernetes quantity, e.g. 500m, 4 or 24Gi.")
    return value


class LLMHostBaseModel(AbstractSAMSpecBase):
    """Base class of the LLMHost spec's blocks.

    Unknown fields are rejected, to catch typos.
    """

    model_config = ConfigDict(extra="forbid")


# --- spec.model -----------------------------------------------------------------------


class SAMLLMHostModelCapabilities(LLMHostBaseModel):
    """What the model can do.

    Informational, for discovery and for the LLMClients that use it.
    """

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER + ".model.capabilities"

    streaming: bool = Field(default=True, description=f"{class_identifier}.streaming[bool]: streams responses.")
    functionCalling: bool = Field(
        default=False,
        description=(
            f"{class_identifier}.functionCalling[bool]: supports tool calls. Some engines also require args, "
            "e.g. vLLM's --enable-auto-tool-choice and --tool-call-parser."
        ),
    )
    vision: bool = Field(default=False, description=f"{class_identifier}.vision[bool]: accepts images.")
    reasoning: bool = Field(default=False, description=f"{class_identifier}.reasoning[bool]: a reasoning model.")


class SAMLLMHostModel(LLMHostBaseModel):
    """Spec.model: what is served, and where its weights come from."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER + ".model"

    source: str = Field(
        default=SAMLLMHostModelSource.HUGGINGFACE.value,
        description=f"{class_identifier}.source[str]: where the weights come from. One of: {SAMLLMHostModelSource.all()}.",
    )
    repository: str = Field(
        ...,
        description=(
            f"{class_identifier}.repository[str]: the model, in the source's terms: a Hugging Face repository id, "
            "e.g. Qwen/Qwen3-8B; an Ollama tag, e.g. llama3.1:8b; an S3 prefix, e.g. s3://bucket/models/qwen3; "
            "a URL; or, for pvc, a path within the volume."
        ),
    )
    revision: Optional[str] = Field(
        default=None,
        description=(
            f"{class_identifier}.revision[str]: a Hugging Face branch, tag or commit SHA. "
            "Pin a commit SHA for reproducible deployments. Defaults to main."
        ),
    )
    file: Optional[str] = Field(
        default=None,
        description=(
            f"{class_identifier}.file[str]: a single weights file within the repository, e.g. a GGUF file for "
            "llama_cpp. For ollama with a Hugging Face source, the quantization tag, e.g. Q4_K_M."
        ),
    )
    servedName: Optional[str] = Field(
        default=None,
        description=(
            f"{class_identifier}.servedName[str]: the model name that clients send in their requests. "
            "Defaults to the LLMHost's name. Ollama always uses repository."
        ),
    )
    task: str = Field(
        default=SAMLLMHostTask.TEXT_GENERATION.value,
        description=f"{class_identifier}.task[str]: what the model does. One of: {SAMLLMHostTask.all()}.",
    )
    tokenSecret: Optional[str] = Field(
        default=None,
        description=(
            f"{class_identifier}.tokenSecret[str]: the name of a Smarter Secret with a Hugging Face access token, "
            "for gated models, e.g. Llama and Gemma. You must also accept the model's license on huggingface.co."
        ),
    )
    license: Optional[str] = Field(default=None, description=f"{class_identifier}.license[str]: e.g. apache-2.0.")
    architecture: Optional[str] = Field(
        default=None, description=f"{class_identifier}.architecture[str]: e.g. llama, qwen3, gemma3."
    )
    parameterCount: Optional[int] = Field(
        default=None, ge=0, description=f"{class_identifier}.parameterCount[int]: the number of parameters."
    )
    contextWindow: Optional[int] = Field(
        default=None,
        ge=0,
        description=f"{class_identifier}.contextWindow[int]: the model's maximum context, in tokens.",
    )
    embeddingDimensions: Optional[int] = Field(
        default=None, ge=0, description=f"{class_identifier}.embeddingDimensions[int]: for embedding models."
    )
    quantization: str = Field(
        default=SAMLLMHostQuantization.NONE.value,
        description=f"{class_identifier}.quantization[str]: the weights' precision. One of: {SAMLLMHostQuantization.all()}.",
    )
    capabilities: SAMLLMHostModelCapabilities = Field(
        default_factory=SAMLLMHostModelCapabilities,
        description=f"{class_identifier}.capabilities[object]: what the model can do.",
    )

    @field_validator("source")
    @classmethod
    def validate_source(cls, v: str) -> str:
        return choice(v, SAMLLMHostModelSource.all(), "model.source")

    @field_validator("task")
    @classmethod
    def validate_task(cls, v: str) -> str:
        return choice(v, SAMLLMHostTask.all(), "model.task")

    @field_validator("quantization")
    @classmethod
    def validate_quantization(cls, v: str) -> str:
        return choice(v, SAMLLMHostQuantization.all(), "model.quantization")

    @field_validator("repository")
    @classmethod
    def validate_repository(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise SAMValidationError("model.repository: is required.")
        if any(c in v for c in "\n\r\t \"'`$;&|<>"):
            raise SAMValidationError(f"model.repository: '{v}' contains whitespace or shell characters.")
        return v

    @field_validator("revision", "file", "servedName")
    @classmethod
    def validate_token(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = str(v).strip()
        if any(c in v for c in "\n\r\t \"'`$;&|<>"):
            raise SAMValidationError(f"'{v}' contains whitespace or shell characters.")
        return v or None

    @model_validator(mode="after")
    def validate_source_fields(self) -> "SAMLLMHostModel":
        """Validate repository against the source."""
        if self.source == SAMLLMHostModelSource.HUGGINGFACE.value:
            if not re.match(r"^[A-Za-z0-9][\w.-]*/[\w.-]+$", self.repository):
                raise SAMValidationError(
                    f"model.repository: '{self.repository}' is not a Hugging Face repository id, e.g. Qwen/Qwen3-8B."
                )
        elif self.source == SAMLLMHostModelSource.S3.value:
            if not self.repository.startswith("s3://"):
                raise SAMValidationError("model.repository: must be an s3:// URI when source is s3.")
        elif self.source == SAMLLMHostModelSource.URL.value:
            if not re.match(r"^https?://", self.repository):
                raise SAMValidationError("model.repository: must be an http(s):// URL when source is url.")
        elif self.source == SAMLLMHostModelSource.PVC.value:
            if self.repository.startswith("/") or ".." in self.repository.split("/"):
                raise SAMValidationError("model.repository: must be a relative path within the volume.")
        if self.revision and self.source != SAMLLMHostModelSource.HUGGINGFACE.value:
            raise SAMValidationError("model.revision: applies only when source is huggingface.")
        if self.task == SAMLLMHostTask.EMBEDDING.value and self.capabilities.functionCalling:
            raise SAMValidationError("model.capabilities.functionCalling: does not apply to embedding models.")
        return self


# --- spec.engine ----------------------------------------------------------------------


class SAMLLMHostEngineConfig(LLMHostBaseModel):
    """
    Spec.engine: the inference server.

    The common settings, e.g. ``contextLength``, are translated into each engine's own
    arguments, e.g. vLLM's ``--max-model-len`` and llama.cpp's ``--ctx-size``. ``args`` and
    ``env`` are passed to the engine as they are, for everything else.
    """

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER + ".engine"

    name: str = Field(
        ...,
        description=f"{class_identifier}.name[str]: the inference server. One of: {SAMLLMHostEngine.all()}.",
    )
    image: Optional[str] = Field(
        default=None,
        description=(
            f"{class_identifier}.image[str]: the container image. Defaults to the engine's official image. "
            "Pin a version in production. Required for custom."
        ),
    )
    apiFormat: str = Field(
        default=SAMLLMHostApiFormat.OPENAI_COMPATIBLE.value,
        description=f"{class_identifier}.apiFormat[str]: the wire protocol. One of: {SAMLLMHostApiFormat.all()}.",
    )
    port: Optional[int] = Field(
        default=None,
        ge=1,
        le=65535,
        description=f"{class_identifier}.port[int]: the container port. Defaults to the engine's port. Required for custom.",
    )
    command: Optional[list[str]] = Field(
        default=None,
        description=f"{class_identifier}.command[list]: overrides the image's entrypoint. For custom engines.",
    )
    contextLength: Optional[int] = Field(
        default=None,
        ge=1,
        description=f"{class_identifier}.contextLength[int]: the maximum context the server allocates, in tokens.",
    )
    tensorParallelSize: Optional[int] = Field(
        default=None,
        ge=1,
        le=MAX_GPU_COUNT,
        description=f"{class_identifier}.tensorParallelSize[int]: the GPUs that one replica shards the model across.",
    )
    gpuMemoryUtilization: Optional[float] = Field(
        default=None,
        gt=0.0,
        le=1.0,
        description=f"{class_identifier}.gpuMemoryUtilization[float]: the fraction of GPU memory the server may use.",
    )
    dtype: Optional[str] = Field(
        default=None, description=f"{class_identifier}.dtype[str]: e.g. auto, bfloat16, float16."
    )
    maxConcurrentRequests: Optional[int] = Field(
        default=None,
        ge=1,
        description=f"{class_identifier}.maxConcurrentRequests[int]: the requests that one replica serves at once.",
    )
    trustRemoteCode: bool = Field(
        default=False,
        description=(
            f"{class_identifier}.trustRemoteCode[bool]: run Python code from the model repository. "
            "Only for repositories that you trust."
        ),
    )
    args: list[str] = Field(
        default_factory=list,
        description=f"{class_identifier}.args[list]: additional arguments, passed to the engine as they are.",
    )
    env: dict[str, str] = Field(
        default_factory=dict,
        description=f"{class_identifier}.env[dict]: additional environment variables.",
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        return choice(v, SAMLLMHostEngine.all(), "engine.name")

    @field_validator("apiFormat")
    @classmethod
    def validate_api_format(cls, v: str) -> str:
        return choice(v, SAMLLMHostApiFormat.all(), "engine.apiFormat")

    @field_validator("args")
    @classmethod
    def validate_args(cls, v: list[str]) -> list[str]:
        if len(v) > MAX_ARGS:
            raise SAMValidationError(f"engine.args: at most {MAX_ARGS} are permitted.")
        return [str(arg) for arg in v]

    @field_validator("env")
    @classmethod
    def validate_env(cls, v: dict[str, str]) -> dict[str, str]:
        for key in v:
            if not re.match(ENV_NAME_PATTERN, key):
                raise SAMValidationError(f"engine.env: '{key}' is not a valid environment variable name.")
            if key.startswith("SMARTER_"):
                raise SAMValidationError(f"engine.env: '{key}': the SMARTER_ prefix is reserved.")
        return {key: str(value) for key, value in v.items()}

    @model_validator(mode="after")
    def validate_custom(self) -> "SAMLLMHostEngineConfig":
        if self.name == SAMLLMHostEngine.CUSTOM.value and (not self.image or not self.port):
            raise SAMValidationError("engine.image and engine.port: are required when engine.name is custom.")
        if self.command is not None and self.name != SAMLLMHostEngine.CUSTOM.value:
            raise SAMValidationError("engine.command: applies only when engine.name is custom. Use engine.args.")
        return self


# --- spec.resources, spec.storage, spec.network ---------------------------------------


class SAMLLMHostResources(LLMHostBaseModel):
    """
    Spec.resources: the compute that each replica, one pod, requests.

    These are the pod's resource requests, not a node's capacity. They must fit a node of the
    LLMHost's compute, which also determines the GPU model.
    """

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER + ".resources"

    gpuCount: int = Field(
        default=0,
        ge=0,
        le=MAX_GPU_COUNT,
        description=f"{class_identifier}.gpuCount[int]: the GPUs per replica. 0 runs on CPU.",
    )
    gpuResource: str = Field(
        default=DEFAULT_GPU_RESOURCE,
        description=f"{class_identifier}.gpuResource[str]: the Kubernetes extended resource, e.g. nvidia.com/gpu.",
    )
    vramRequiredGb: Optional[int] = Field(
        default=None,
        ge=0,
        description=f"{class_identifier}.vramRequiredGb[int]: the GPU memory the model requires. Informational.",
    )
    cpu: Optional[str] = Field(
        default=None, description=f"{class_identifier}.cpu[str]: the pod's CPU request, e.g. 4 or 3500m."
    )
    memory: Optional[str] = Field(
        default=None, description=f"{class_identifier}.memory[str]: the pod's memory request and limit, e.g. 24Gi."
    )
    shmSize: str = Field(
        default=DEFAULT_SHM_SIZE,
        description=f"{class_identifier}.shmSize[str]: the size of /dev/shm.",
    )
    nodeSelector: dict[str, str] = Field(
        default_factory=dict, description=f"{class_identifier}.nodeSelector[dict]: additional node labels."
    )
    tolerations: list[dict[str, Any]] = Field(
        default_factory=list,
        description=(
            f"{class_identifier}.tolerations[list]: Kubernetes tolerations. When gpuCount > 0, a toleration of "
            "the gpuResource taint is added."
        ),
    )
    serviceAccountName: Optional[str] = Field(
        default=None,
        description=f"{class_identifier}.serviceAccountName[str]: e.g. for IRSA access to an S3 model source.",
    )

    @field_validator("cpu", "memory", "shmSize")
    @classmethod
    def validate_quantity(cls, v: Optional[str], info) -> Optional[str]:
        return quantity(v, f"resources.{info.field_name}")


class SAMLLMHostStorage(LLMHostBaseModel):
    """
    Spec.storage: the model volume, a PersistentVolumeClaim mounted at /models.

    It caches the weights, so that a restarted server does not download them again. The
    cluster's storage class provisions its PersistentVolume.
    """

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER + ".storage"

    size: str = Field(default=DEFAULT_STORAGE_SIZE, description=f"{class_identifier}.size[str]: e.g. 50Gi.")
    storageClass: Optional[str] = Field(
        default=None, description=f"{class_identifier}.storageClass[str]: defaults to the cluster's default class."
    )
    accessMode: str = Field(
        default=SAMLLMHostStorageAccessMode.READ_WRITE_ONCE.value,
        description=f"{class_identifier}.accessMode[str]: One of: {SAMLLMHostStorageAccessMode.all()}.",
    )
    existingClaim: Optional[str] = Field(
        default=None,
        description=(
            f"{class_identifier}.existingClaim[str]: an existing PersistentVolumeClaim to mount, instead of "
            "creating one. Required when model.source is pvc."
        ),
    )
    retain: bool = Field(
        default=True,
        description=(
            f"{class_identifier}.retain[bool]: keep the volume, and its downloaded weights, on undeploy. "
            "It is always deleted when the LLMHost is deleted."
        ),
    )

    @field_validator("size")
    @classmethod
    def validate_size(cls, v: str) -> str:
        return quantity(v, "storage.size")  # type: ignore[return-value]

    @field_validator("accessMode")
    @classmethod
    def validate_access_mode(cls, v: str) -> str:
        return choice(v, SAMLLMHostStorageAccessMode.all(), "storage.accessMode")


class SAMLLMHostNetwork(LLMHostBaseModel):
    """
    Spec.network: how the LLMHost is reached.

    It is always reachable inside the cluster, at its Service. With ``ingress``, it is also
    reachable at ``https://<hostname>``, with a TLS certificate from cert-manager. A public
    endpoint requires an API key, unless ``allowUnauthenticated``.
    """

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER + ".network"

    ingress: bool = Field(default=False, description=f"{class_identifier}.ingress[bool]: create an Ingress.")
    hostname: Optional[str] = Field(
        default=None,
        description=(
            f"{class_identifier}.hostname[str]: the Ingress hostname. "
            "Defaults to <name>.llmhost.<account number>.<environment API domain>."
        ),
    )
    apiKeySecret: Optional[str] = Field(
        default=None,
        description=(
            f"{class_identifier}.apiKeySecret[str]: the name of a Smarter Secret with the API key that clients "
            "must send as a Bearer token. If omitted, Smarter generates one when the LLMHost is launched, and "
            "stores it in the Secret llmhost_<name>_api_key."
        ),
    )
    allowUnauthenticated: bool = Field(
        default=False,
        description=(
            f"{class_identifier}.allowUnauthenticated[bool]: permit an Ingress for an engine that does not "
            "authenticate requests, e.g. tgi and ollama. Anyone who knows the hostname can use the model."
        ),
    )

    @field_validator("hostname")
    @classmethod
    def validate_hostname(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip().lower()
        if not re.match(HOSTNAME_PATTERN, v):
            raise SAMValidationError(f"network.hostname: '{v}' is not a valid hostname.")
        return v


class SAMLLMHostScaling(LLMHostBaseModel):
    """Spec.scaling: the replicas."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER + ".scaling"

    replicas: int = Field(
        default=DEFAULT_REPLICAS,
        ge=1,
        le=MAX_REPLICAS,
        description=(
            f"{class_identifier}.replicas[int]: the replicas. More than one requires storage.accessMode "
            "ReadWriteMany or ReadOnlyMany."
        ),
    )


class SAMLLMHostHealthCheck(LLMHostBaseModel):
    """Spec.healthCheck: the probes that decide when a replica is ready."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER + ".healthCheck"

    path: Optional[str] = Field(
        default=None,
        description=f"{class_identifier}.path[str]: the HTTP health path. Defaults to the engine's, e.g. /health.",
    )
    startupTimeoutSeconds: int = Field(
        default=DEFAULT_STARTUP_TIMEOUT_SECONDS,
        ge=60,
        le=6 * 3600,
        description=(
            f"{class_identifier}.startupTimeoutSeconds[int]: the time the server has to download and load the "
            "weights before it is restarted. Large models need more."
        ),
    )
    periodSeconds: int = Field(
        default=DEFAULT_PERIOD_SECONDS,
        ge=1,
        le=300,
        description=f"{class_identifier}.periodSeconds[int]: how often the probes run.",
    )

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.startswith("/"):
            raise SAMValidationError("healthCheck.path: must start with /.")
        return v


# --- spec ---------------------------------------------------------------------------


class SAMLLMHostSpec(LLMHostBaseModel):
    """Smarter API LLMHost Manifest LLMHost.spec."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    model: SAMLLMHostModel = Field(..., description=f"{class_identifier}.model[object]: what is served.")
    engine: SAMLLMHostEngineConfig = Field(..., description=f"{class_identifier}.engine[object]: the inference server.")
    compute: Optional[str] = Field(
        default=None,
        description=(
            f"{class_identifier}.compute[str]: the LLMHostCompute that the LLMHost runs on, e.g. gpu_l4_1x. "
            "Defaults to the cheapest one that its resources fit."
        ),
    )
    resources: SAMLLMHostResources = Field(
        default_factory=SAMLLMHostResources, description=f"{class_identifier}.resources[object]: compute."
    )
    storage: SAMLLMHostStorage = Field(
        default_factory=SAMLLMHostStorage, description=f"{class_identifier}.storage[object]: the model volume."
    )
    network: SAMLLMHostNetwork = Field(
        default_factory=SAMLLMHostNetwork, description=f"{class_identifier}.network[object]: reachability."
    )
    scaling: SAMLLMHostScaling = Field(
        default_factory=SAMLLMHostScaling, description=f"{class_identifier}.scaling[object]: replicas."
    )
    healthCheck: SAMLLMHostHealthCheck = Field(
        default_factory=SAMLLMHostHealthCheck, description=f"{class_identifier}.healthCheck[object]: probes."
    )

    # pylint: disable=too-many-branches
    @model_validator(mode="after")
    def validate_compatibility(self) -> "SAMLLMHostSpec":
        """Validate that the model, engine, storage and network work together."""
        engine = self.engine.name
        source = self.model.source
        rules = ENGINE_RULES[engine]
        if source not in rules["sources"]:
            raise SAMValidationError(
                f"model.source: engine {engine} cannot load source {source}. It supports: {sorted(rules['sources'])}."
            )
        if not engine_supports_task(engine, self.model.task):
            raise SAMValidationError(f"model.task: engine {engine} cannot serve {self.model.task} models.")
        if rules.get("requiresFile") and not self.model.file and source != SAMLLMHostModelSource.URL.value:
            raise SAMValidationError(f"model.file: engine {engine} requires a single weights file, e.g. a GGUF file.")
        if rules.get("requiresGpu") and not self.resources.gpuCount and not self.engine.image:
            raise SAMValidationError(
                f"resources.gpuCount: engine {engine} requires a GPU. For CPU, use llama_cpp or ollama, "
                "or set engine.image to a CPU build."
            )
        if source == SAMLLMHostModelSource.PVC.value and not self.storage.existingClaim:
            raise SAMValidationError("storage.existingClaim: is required when model.source is pvc.")
        if engine == SAMLLMHostEngine.OLLAMA.value and self.engine.apiFormat not in (
            SAMLLMHostApiFormat.OPENAI_COMPATIBLE.value,
            SAMLLMHostApiFormat.OLLAMA_NATIVE.value,
        ):
            raise SAMValidationError("engine.apiFormat: ollama speaks openai_compatible or ollama_native.")
        if self.engine.apiFormat == SAMLLMHostApiFormat.OLLAMA_NATIVE.value and engine not in (
            SAMLLMHostEngine.OLLAMA.value,
            SAMLLMHostEngine.CUSTOM.value,
        ):
            raise SAMValidationError(f"engine.apiFormat: {engine} does not speak ollama_native.")
        if self.engine.tensorParallelSize and self.engine.tensorParallelSize > max(self.resources.gpuCount, 1):
            raise SAMValidationError("engine.tensorParallelSize: cannot exceed resources.gpuCount.")
        if self.engine.gpuMemoryUtilization and not self.resources.gpuCount:
            raise SAMValidationError("engine.gpuMemoryUtilization: requires resources.gpuCount > 0.")
        if (
            self.scaling.replicas > 1
            and self.storage.accessMode == SAMLLMHostStorageAccessMode.READ_WRITE_ONCE.value
            and not self.storage.existingClaim
        ):
            raise SAMValidationError(
                "scaling.replicas: more than one replica requires storage.accessMode ReadWriteMany or ReadOnlyMany."
            )
        if self.network.ingress and not self.network.allowUnauthenticated and not engine_supports_api_key(engine):
            raise SAMValidationError(
                f"network.ingress: engine {engine} does not authenticate requests, so a public Ingress would let "
                "anyone use the model. Use an engine that supports API keys, e.g. vllm, or set "
                "network.allowUnauthenticated: true."
            )
        if self.network.apiKeySecret and not engine_supports_api_key(engine):
            raise SAMValidationError(f"network.apiKeySecret: engine {engine} does not support API keys.")
        return self


__all__ = [
    "ENGINE_RULES",
    "SAMLLMHostEngineConfig",
    "SAMLLMHostHealthCheck",
    "SAMLLMHostModel",
    "SAMLLMHostModelCapabilities",
    "SAMLLMHostNetwork",
    "SAMLLMHostResources",
    "SAMLLMHostScaling",
    "SAMLLMHostSpec",
    "SAMLLMHostStorage",
    "engine_supports_api_key",
    "engine_supports_task",
]
