"""
Model discovery: find models to host, size their pods, and draft their manifests.

Catalogs are pluggable, so that discovery is not tied to one model hub:

- :class:`BuiltinCatalog`: the example manifests in ``data/llmhost``, of the most popular
  open-weight models. Offline, and ready to apply.
- :class:`HuggingFaceCatalog`: the Hugging Face Hub, through its public REST API.

A new hub is a new :class:`ModelCatalog`, registered in :data:`CATALOGS`.
:func:`draft_manifest` turns any catalog's :class:`ModelInfo` into an LLMHost manifest, sized
by :func:`estimate_vram_gb` and :func:`recommend_resources`.
"""

import glob
import math
import os
import re
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable, Optional
from urllib.parse import quote

import requests

from smarter.apps.llmhost.const import BUILTIN_MANIFESTS_PATH
from smarter.apps.llmhost.manifest.enum import (
    SAMLLMHostEngine,
    SAMLLMHostModelSource,
    SAMLLMHostQuantization,
    SAMLLMHostTask,
)
from smarter.apps.llmhost.models import LLMHostCompute
from smarter.common.utils import get_readonly_yaml_file
from smarter.lib.journal.enum import SmarterJournalThings

from .compute import (
    PodRequests,
    builtin_computes,
    choose_compute,
    cpu_millicores,
    memory_mib,
)
from .exceptions import LLMHostComputeError, LLMHostDiscoveryError
from .renderer import dns_label

HF_TASKS = {
    SAMLLMHostTask.TEXT_GENERATION.value: "text-generation",
    SAMLLMHostTask.EMBEDDING.value: "feature-extraction",
}
"""The Hugging Face pipeline tag of each task."""
EMBEDDING_PIPELINE_TAGS = frozenset(["feature-extraction", "sentence-similarity"])


@dataclass
class ModelInfo:
    """
    A model, as a catalog describes it.

    Only ``catalog``, ``source`` and ``repository`` are always set. The rest are set when the
    catalog knows them.
    """

    catalog: str
    source: str
    repository: str
    task: str = SAMLLMHostTask.TEXT_GENERATION.value
    description: Optional[str] = None
    license: Optional[str] = None
    gated: bool = False
    architecture: Optional[str] = None
    parameter_count: Optional[int] = None
    context_window: Optional[int] = None
    quantization: str = SAMLLMHostQuantization.NONE.value
    downloads: Optional[int] = None
    likes: Optional[int] = None
    tags: list[str] = field(default_factory=list)
    files: list[str] = field(default_factory=list)
    manifest: Optional[dict[str, Any]] = None
    """A ready-made manifest, for built-in models."""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ModelCatalog(ABC):
    """A searchable collection of models."""

    name: str

    @abstractmethod
    def search(self, query: Optional[str] = None, task: Optional[str] = None, limit: int = 20) -> list[ModelInfo]:
        """Return the models that match ``query`` and ``task``, most popular first."""

    @abstractmethod
    def get(self, repository: str) -> ModelInfo:
        """Return one model.

        Raises LLMHostDiscoveryError if it does not exist.
        """


class BuiltinCatalog(ModelCatalog):
    """The example LLMHost manifests that ship with Smarter."""

    name = "builtin"

    def __init__(self, path: str = BUILTIN_MANIFESTS_PATH):
        self.path = path

    def manifests(self) -> list[dict[str, Any]]:
        """The built-in manifests, sorted by file name."""
        retval = []
        for filespec in sorted(glob.glob(os.path.join(self.path, "*.yaml"))):
            manifest = get_readonly_yaml_file(filespec)
            if isinstance(manifest, dict) and manifest.get("kind") == SmarterJournalThings.LLMHOST.value:
                retval.append(manifest)
        return retval

    @staticmethod
    def to_info(manifest: dict[str, Any]) -> ModelInfo:
        metadata = manifest.get("metadata", {})
        model = manifest.get("spec", {}).get("model", {})
        return ModelInfo(
            catalog=BuiltinCatalog.name,
            source=model.get("source", SAMLLMHostModelSource.HUGGINGFACE.value),
            repository=model["repository"],
            task=model.get("task", SAMLLMHostTask.TEXT_GENERATION.value),
            description=metadata.get("description"),
            license=model.get("license"),
            gated=bool(model.get("tokenSecret")),
            architecture=model.get("architecture"),
            parameter_count=model.get("parameterCount"),
            context_window=model.get("contextWindow"),
            quantization=model.get("quantization", SAMLLMHostQuantization.NONE.value),
            tags=list(metadata.get("tags") or []),
            manifest=manifest,
        )

    def search(self, query: Optional[str] = None, task: Optional[str] = None, limit: int = 20) -> list[ModelInfo]:
        query = (query or "").lower()
        retval = []
        for manifest in self.manifests():
            info = self.to_info(manifest)
            haystack = " ".join([manifest["metadata"]["name"], info.repository, *info.tags]).lower()
            if query and query not in haystack:
                continue
            if task and info.task != task:
                continue
            retval.append(info)
        return retval[:limit]

    def get(self, repository: str) -> ModelInfo:
        for manifest in self.manifests():
            if repository in (manifest["metadata"]["name"], manifest["spec"]["model"]["repository"]):
                return self.to_info(manifest)
        raise LLMHostDiscoveryError(f"{repository} is not a built-in LLMHost.")


class HuggingFaceCatalog(ModelCatalog):
    """
    The Hugging Face Hub.

    :param token: An access token, to read gated models' details. Optional.
    :param base_url: The Hub's URL, e.g. a mirror.
    :param session: A requests session, e.g. a mock in tests.
    """

    name = "huggingface"

    def __init__(
        self,
        token: Optional[str] = None,
        base_url: str = "https://huggingface.co",
        session: Optional[requests.Session] = None,
        timeout: float = 15,
    ):
        self.token = token
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()
        self.timeout = timeout

    def _get(self, path: str, params: Optional[Any] = None) -> Any:
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        try:
            response = self.session.get(f"{self.base_url}{path}", params=params, headers=headers, timeout=self.timeout)
        except requests.RequestException as e:
            raise LLMHostDiscoveryError(f"Hugging Face is unavailable: {e}") from e
        if response.status_code == 404:
            raise LLMHostDiscoveryError(f"Hugging Face does not have {path}.")
        if response.status_code in (401, 403):
            raise LLMHostDiscoveryError(f"Hugging Face denied access to {path}. It may be gated: use a token.")
        if response.status_code >= 400:
            raise LLMHostDiscoveryError(f"Hugging Face returned {response.status_code} for {path}.")
        return response.json()

    @staticmethod
    def _task(pipeline_tag: Optional[str]) -> str:
        if pipeline_tag in EMBEDDING_PIPELINE_TAGS:
            return SAMLLMHostTask.EMBEDDING.value
        return SAMLLMHostTask.TEXT_GENERATION.value

    @staticmethod
    def _quantization(data: dict[str, Any], files: list[str]) -> str:
        tags = [str(t).lower() for t in data.get("tags", []) or []]
        if "gguf" in tags or any(f.lower().endswith(".gguf") for f in files):
            return SAMLLMHostQuantization.GGUF.value
        for quantization in ("awq", "gptq", "fp8", "mxfp4"):
            if quantization in tags or quantization in data.get("id", "").lower():
                return quantization
        parameters = (data.get("safetensors") or {}).get("parameters") or {}
        if parameters:
            dtype = max(parameters, key=parameters.get).lower()
            return {"bf16": "bf16", "f16": "fp16", "fp16": "fp16", "f32": "fp32"}.get(dtype, "none")
        return SAMLLMHostQuantization.NONE.value

    def to_info(self, data: dict[str, Any]) -> ModelInfo:
        files = [s.get("rfilename", "") for s in data.get("siblings", []) or []]
        card = data.get("cardData") or {}
        config = data.get("config") or {}
        tags = [str(t) for t in data.get("tags", []) or []]
        license_ = card.get("license") or next((t.split(":", 1)[1] for t in tags if t.startswith("license:")), None)
        return ModelInfo(
            catalog=self.name,
            source=SAMLLMHostModelSource.HUGGINGFACE.value,
            repository=data.get("id") or data.get("modelId", ""),
            task=self._task(data.get("pipeline_tag")),
            license=license_,
            gated=bool(data.get("gated")),
            architecture=config.get("model_type"),
            parameter_count=(data.get("safetensors") or {}).get("total"),
            quantization=self._quantization(data, files),
            downloads=data.get("downloads"),
            likes=data.get("likes"),
            tags=tags,
            files=[f for f in files if f.lower().endswith((".gguf", ".safetensors"))],
        )

    def search(self, query: Optional[str] = None, task: Optional[str] = None, limit: int = 20) -> list[ModelInfo]:
        params: list[tuple[str, Any]] = [("sort", "downloads"), ("direction", "-1"), ("limit", limit)]
        if query:
            params.append(("search", query))
        if task:
            params.append(("pipeline_tag", HF_TASKS.get(task, task)))
        data = self._get("/api/models", params=params)
        return [self.to_info(item) for item in data if isinstance(item, dict)]

    def get(self, repository: str) -> ModelInfo:
        if not re.match(r"^[\w.-]+/[\w.-]+$", repository):
            raise LLMHostDiscoveryError(f"{repository} is not a Hugging Face repository id, e.g. Qwen/Qwen3-8B.")
        info = self.to_info(self._get(f"/api/models/{quote(repository)}"))
        info.context_window = self.context_window(repository)
        return info

    def context_window(self, repository: str, revision: str = "main") -> Optional[int]:
        """The model's context window, from its config.json, if it is readable."""
        try:
            config = self._get(f"/{quote(repository)}/resolve/{quote(revision)}/config.json")
        except (LLMHostDiscoveryError, ValueError):
            return None
        config = config.get("text_config", config) if isinstance(config, dict) else {}
        for key in ("max_position_embeddings", "n_positions", "max_seq_len", "seq_length"):
            if isinstance(config.get(key), int):
                return config[key]
        return None


CATALOGS: dict[str, type[ModelCatalog]] = {
    BuiltinCatalog.name: BuiltinCatalog,
    HuggingFaceCatalog.name: HuggingFaceCatalog,
}


def get_catalog(name: str, **kwargs) -> ModelCatalog:
    """Return the catalog named ``name``, e.g. huggingface."""
    try:
        return CATALOGS[name](**kwargs)
    except KeyError as e:
        raise LLMHostDiscoveryError(f"{name} is not a model catalog. Use one of: {sorted(CATALOGS)}.") from e


# --- sizing ---------------------------------------------------------------------------


def weights_gb(
    parameter_count: Optional[int], quantization: str = SAMLLMHostQuantization.NONE.value
) -> Optional[float]:
    """The size of a model's weights, at the quantization's bytes per parameter, or None if unknown."""
    if not parameter_count:
        return None
    return parameter_count * SAMLLMHostQuantization.bytes_per_parameter(quantization) / 1e9


def estimate_vram_gb(
    parameter_count: Optional[int], quantization: str = SAMLLMHostQuantization.NONE.value, overhead: float = 1.25
) -> Optional[int]:
    """
    Estimate the GPU memory that serving a model requires.

    The weights, at the quantization's bytes per parameter, plus ``overhead`` for the KV cache,
    activations and the CUDA context. It is a starting point, not a guarantee: long contexts
    and many concurrent requests need more.

    :returns: Gigabytes, rounded up, or None if the parameter count is unknown.
    """
    size = weights_gb(parameter_count, quantization)
    if size is None:
        return None
    return max(1, math.ceil(size * overhead))


def pod_cpu(gpu_count: int) -> str:
    """
    The CPU that an inference server pod requests: two cores, plus two per GPU, or three on CPU,.

    which fits a 4 vCPU node after the kubelet's and the DaemonSets' share.
    """
    return str(2 + 2 * gpu_count) if gpu_count else "3"


def pod_memory(size_gb: Optional[float], gpu_count: int) -> str:
    """
    The memory that an inference server pod requests.

    The server reads the weights through host memory as it loads them, so the pod requests
    their size plus headroom for the server itself, which on CPU also holds the KV cache.
    """
    size_gb = size_gb or 0
    if gpu_count:
        return f"{max(8, math.ceil(size_gb * 1.2) + 4)}Gi"
    return f"{max(2, math.ceil(size_gb * 1.2) + 2)}Gi"


def gpus_for(vram_gb: int, compute: LLMHostCompute) -> Optional[int]:
    """The fewest of the compute's GPUs that fit ``vram_gb``, in powers of two for tensor parallelism, or None."""
    if not compute.has_gpu:
        return None
    count = 1
    while count * compute.gpu_memory_gb < vram_gb:
        count *= 2
    return count if count <= compute.gpu_count else None


def recommend_resources(
    parameter_count: Optional[int],
    quantization: str = SAMLLMHostQuantization.NONE.value,
    cpu_ok: bool = False,
    computes: Optional[Iterable[LLMHostCompute]] = None,
) -> dict[str, Any]:
    """
    Recommend the compute, and the spec.resources of one replica's pod, for a model.

    The pod requests what the model needs: the fewest GPUs that fit its GPU memory, and the CPU
    and memory that its inference server needs. The compute is the cheapest whose node fits
    the pod: see :func:`~smarter.apps.llmhost.services.compute.choose_compute`.

    :param parameter_count: The model's parameters.
    :param quantization: The model's quantization, e.g. bf16.
    :param cpu_ok: Whether the engine can run on CPU, e.g. llama_cpp and ollama. Small models then
        run without a GPU.
    :param computes: The computes to choose from. Defaults to the built-in LLMHostComputes.
    :returns: spec.resources fields, plus spec.compute, under ``compute``, and
        engine.tensorParallelSize, under ``tensorParallelSize``. Empty if the size is unknown.
    :raises LLMHostDiscoveryError: if no compute fits the model.
    """
    vram_gb = estimate_vram_gb(parameter_count, quantization)
    if vram_gb is None:
        return {}
    computes = list(computes if computes is not None else builtin_computes())
    size_gb = weights_gb(parameter_count, quantization)
    options: list[tuple[dict[str, Any], PodRequests]] = []
    if cpu_ok and vram_gb <= 4:
        resources = {"gpuCount": 0, "cpu": pod_cpu(0), "memory": pod_memory(size_gb, 0)}
        options.append((resources, PodRequests(cpu_millicores(resources["cpu"]), memory_mib(resources["memory"]))))
    # then the fewest GPUs that fit, of any compute.
    for count in sorted({c for c in (gpus_for(vram_gb, compute) for compute in computes) if c}):
        resources = {
            "gpuCount": count,
            "vramRequiredGb": vram_gb,
            "cpu": pod_cpu(count),
            "memory": pod_memory(size_gb, count),
        }
        pod = PodRequests(cpu_millicores(resources["cpu"]), memory_mib(resources["memory"]), count, vram_gb)
        options.append((resources, pod))
    for resources, pod in options:
        try:
            compute = choose_compute(pod, computes)
        except LLMHostComputeError:
            continue
        count = resources["gpuCount"]
        return {**resources, "compute": compute.name, "tensorParallelSize": count if count > 1 else None}
    raise LLMHostDiscoveryError(
        f"The model requires about {vram_gb} GB of GPU memory, which no LLMHostCompute's node provides. "
        "Use a quantized variant, or add an LLMHostCompute with more GPU memory."
    )


def default_engine(info: ModelInfo) -> str:
    """The engine that best serves a model: tei for embeddings, ollama for Ollama, llama_cpp for GGUF, else vllm."""
    if info.source == SAMLLMHostModelSource.OLLAMA.value:
        return SAMLLMHostEngine.OLLAMA.value
    if info.task == SAMLLMHostTask.EMBEDDING.value:
        return SAMLLMHostEngine.TEI.value
    if info.quantization == SAMLLMHostQuantization.GGUF.value:
        return SAMLLMHostEngine.LLAMA_CPP.value
    return SAMLLMHostEngine.VLLM.value


def draft_manifest(
    info: ModelInfo,
    engine: Optional[str] = None,
    name: Optional[str] = None,
    token_secret: Optional[str] = None,
    computes: Optional[Iterable[LLMHostCompute]] = None,
) -> dict[str, Any]:
    """
    Draft an LLMHost manifest for a model.

    Built-in models return their manifest. For others, the manifest is sized by
    :func:`recommend_resources`; review it, especially resources and engine.args, before
    applying it.

    :param info: From a catalog.
    :param engine: The engine. Defaults to :func:`default_engine`.
    :param name: The LLMHost's name. Defaults to the repository's name.
    :param token_secret: A Smarter Secret with a Hugging Face token, for gated models.
    :param computes: The computes to choose from. Defaults to the built-in LLMHostComputes.
    """
    if info.manifest and engine is None and name is None:
        return info.manifest
    engine = engine or default_engine(info)
    repository_name = info.repository.split("/")[-1]
    name = name or dns_label(repository_name).replace("-", "_")[:50].strip("_")
    gguf_files = sorted(f for f in info.files if f.lower().endswith(".gguf"))
    file = None
    if engine == SAMLLMHostEngine.LLAMA_CPP.value:
        # prefer the popular Q4_K_M quantization, else the first file.
        file = next((f for f in gguf_files if "q4_k_m" in f.lower()), gguf_files[0] if gguf_files else None)
        if file is None and info.source == SAMLLMHostModelSource.HUGGINGFACE.value:
            raise LLMHostDiscoveryError(f"{info.repository} has no GGUF file, which llama_cpp requires.")

    cpu_ok = engine in (SAMLLMHostEngine.LLAMA_CPP.value, SAMLLMHostEngine.OLLAMA.value, SAMLLMHostEngine.TEI.value)
    resources = recommend_resources(info.parameter_count, info.quantization, cpu_ok=cpu_ok, computes=computes)
    tensor_parallel_size = resources.pop("tensorParallelSize", None)
    compute = resources.pop("compute", None)
    if not resources and engine in (SAMLLMHostEngine.VLLM.value, SAMLLMHostEngine.SGLANG.value):
        resources = {"gpuCount": 1}

    model: dict[str, Any] = {
        "source": info.source,
        "repository": info.repository,
        "task": info.task,
        "quantization": info.quantization,
    }
    if info.source == SAMLLMHostModelSource.HUGGINGFACE.value:
        model["revision"] = "main"
    optional = {
        "file": file,
        "tokenSecret": token_secret if info.gated else None,
        "license": info.license,
        "architecture": info.architecture,
        "parameterCount": info.parameter_count,
        "contextWindow": info.context_window,
    }
    model.update({key: value for key, value in optional.items() if value is not None})
    engine_config: dict[str, Any] = {"name": engine}
    if tensor_parallel_size:
        engine_config["tensorParallelSize"] = tensor_parallel_size
    if info.context_window and engine == SAMLLMHostEngine.VLLM.value and info.context_window > 32768:
        # a long context's KV cache rarely fits by default; raise it deliberately.
        engine_config["contextLength"] = 32768

    return {
        "apiVersion": "smarter.sh/v1",
        "kind": SmarterJournalThings.LLMHOST.value,
        "metadata": {
            "name": name,
            "description": info.description or f"{info.repository}, served by {engine}.",
            "version": "1.0.0",
            "tags": [info.task, engine],
            "annotations": [{"smarter.sh/llmhost/catalog": info.catalog}],
        },
        "spec": {
            "model": model,
            "engine": engine_config,
            **({"compute": compute} if compute else {}),
            "resources": resources,
        },
    }


__all__ = [
    "BuiltinCatalog",
    "CATALOGS",
    "HuggingFaceCatalog",
    "ModelCatalog",
    "ModelInfo",
    "default_engine",
    "draft_manifest",
    "estimate_vram_gb",
    "get_catalog",
    "gpus_for",
    "pod_cpu",
    "pod_memory",
    "recommend_resources",
    "weights_gb",
]
