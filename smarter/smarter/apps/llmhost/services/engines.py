# pylint: disable=unused-argument
"""
Inference engines: the servers that load an LLMHost's weights and expose an API.

Each :class:`Engine` translates the engine-neutral ``spec.engine`` settings, e.g.
``contextLength``, and a :class:`~smarter.apps.llmhost.services.sources.ResolvedModel`, into
its own container: image, command, arguments, environment and probes. ``spec.engine.args``
and ``spec.engine.env`` are appended as they are, for everything else.

Secrets are never written into arguments. The renderer injects them as environment
variables from the LLMHost's Kubernetes Secret: ``HF_TOKEN``, and the API key, as
:attr:`Engine.api_key_env`. Engines that read the API key from an argument refer to the
variable with Kubernetes' ``$(VAR)`` expansion.
"""

import posixpath
from typing import Any, Optional

from smarter.apps.llmhost.const import (
    CONTAINER_BIND_ADDRESS,
    DEFAULT_CPU_IMAGES,
    DEFAULT_IMAGES,
    MODELS_MOUNT_PATH,
)
from smarter.apps.llmhost.manifest.enum import SAMLLMHostEngine, SAMLLMHostModelSource
from smarter.apps.llmhost.manifest.models.llmhost.spec import (
    SAMLLMHostSpec,
    engine_supports_api_key,
)

from .exceptions import LLMHostConfigurationError
from .sources import ResolvedModel

API_KEY_ENV = "SMARTER_API_KEY"
"""The environment variable with the API key, for engines that take it as an argument."""
HF_HOME = posixpath.join(MODELS_MOUNT_PATH, "huggingface")


class Engine:
    """
    An inference server.

    Subclasses set the class attributes, and override :meth:`model_args` and
    :meth:`setting_args`, which translate the model and the common settings into arguments.
    """

    name: str = ""
    port: int = 8000
    health_path: str = "/health"
    openai_path: str = "/v1"
    api_key_env: Optional[str] = None
    """The environment variable that the engine reads its API key from."""

    def image(self, spec: SAMLLMHostSpec) -> str:
        """The container image: spec.engine.image, or the official image for GPU or CPU nodes."""
        if spec.engine.image:
            return spec.engine.image
        if not spec.resources.gpuCount and self.name in DEFAULT_CPU_IMAGES:
            return DEFAULT_CPU_IMAGES[self.name]
        return DEFAULT_IMAGES[self.name]

    def container_port(self, spec: SAMLLMHostSpec) -> int:
        return spec.engine.port or self.port

    def served_name(self, spec: SAMLLMHostSpec, default: str) -> str:
        """The model name that clients send in their requests."""
        return spec.model.servedName or default

    def command(self, spec: SAMLLMHostSpec, model: ResolvedModel) -> Optional[list[str]]:
        """Overrides the image's entrypoint, if not None."""
        return spec.engine.command

    def model_args(self, spec: SAMLLMHostSpec, model: ResolvedModel, served_name: str) -> list[str]:
        """The arguments that tell the engine which model to load."""
        return []

    def setting_args(self, spec: SAMLLMHostSpec) -> list[str]:
        """The arguments of the common settings, e.g. contextLength."""
        return []

    def api_key_args(self) -> list[str]:
        """The arguments that pass the API key, for engines that do not read it from the environment."""
        return []

    def args(self, spec: SAMLLMHostSpec, model: ResolvedModel, served_name: str, api_key: bool) -> list[str]:
        """All the engine's arguments."""
        args = [*self.model_args(spec, model, served_name), *self.setting_args(spec)]
        if api_key:
            args += self.api_key_args()
        return args + list(spec.engine.args)

    def env(self, spec: SAMLLMHostSpec, model: ResolvedModel) -> dict[str, str]:
        """Environment variables, other than secrets.

        spec.engine.env overrides them.
        """
        return {"HF_HOME": HF_HOME, "HF_HUB_CACHE": posixpath.join(HF_HOME, "hub"), **spec.engine.env}

    def probe(self, spec: SAMLLMHostSpec) -> dict[str, Any]:
        """The handler of the startup and readiness probes."""
        return {"httpGet": {"path": self.health_path_for(spec), "port": "http"}}

    def health_path_for(self, spec: SAMLLMHostSpec) -> str:
        return spec.healthCheck.path or self.health_path

    def supports_api_key(self) -> bool:
        return engine_supports_api_key(self.name)


def flag(args: list[str], name: str, value: Any) -> None:
    """Append ``name value`` to args, if value is set."""
    if value is not None and value is not False:
        args += [name, str(value)]


class VllmEngine(Engine):
    """VLLM's OpenAI-compatible server."""

    name = SAMLLMHostEngine.VLLM.value
    api_key_env = "VLLM_API_KEY"

    def model_args(self, spec, model, served_name):
        args = ["--model", model.path if model.local else model.reference, "--served-model-name", served_name]
        args += ["--host", CONTAINER_BIND_ADDRESS, "--port", str(self.container_port(spec))]
        if not model.local:
            flag(args, "--revision", model.revision)
        return args

    def setting_args(self, spec):
        args: list[str] = []
        engine = spec.engine
        flag(args, "--max-model-len", engine.contextLength)
        flag(args, "--tensor-parallel-size", engine.tensorParallelSize)
        flag(args, "--gpu-memory-utilization", engine.gpuMemoryUtilization)
        flag(args, "--dtype", engine.dtype)
        flag(args, "--max-num-seqs", engine.maxConcurrentRequests)
        if engine.trustRemoteCode:
            args.append("--trust-remote-code")
        return args


class TgiEngine(Engine):
    """Hugging Face Text Generation Inference."""

    name = SAMLLMHostEngine.TGI.value
    port = 80

    def model_args(self, spec, model, served_name):
        args = ["--model-id", model.path if model.local else model.reference]
        args += ["--hostname", CONTAINER_BIND_ADDRESS, "--port", str(self.container_port(spec))]
        if not model.local:
            flag(args, "--revision", model.revision)
        return args

    def setting_args(self, spec):
        args: list[str] = []
        engine = spec.engine
        flag(args, "--max-total-tokens", engine.contextLength)
        if engine.contextLength:
            # TGI requires the input to leave room for at least one generated token.
            flag(args, "--max-input-tokens", engine.contextLength - 1)
        flag(args, "--num-shard", engine.tensorParallelSize)
        flag(args, "--dtype", engine.dtype)
        flag(args, "--max-concurrent-requests", engine.maxConcurrentRequests)
        if engine.trustRemoteCode:
            args.append("--trust-remote-code")
        return args


class SglangEngine(Engine):
    """SGLang's server."""

    name = SAMLLMHostEngine.SGLANG.value
    port = 30000
    api_key_env = API_KEY_ENV

    def command(self, spec, model):
        return ["python3", "-m", "sglang.launch_server"]

    def model_args(self, spec, model, served_name):
        args = ["--model-path", model.path if model.local else model.reference, "--served-model-name", served_name]
        args += ["--host", CONTAINER_BIND_ADDRESS, "--port", str(self.container_port(spec))]
        if not model.local:
            flag(args, "--revision", model.revision)
        return args

    def setting_args(self, spec):
        args: list[str] = []
        engine = spec.engine
        flag(args, "--context-length", engine.contextLength)
        flag(args, "--tp", engine.tensorParallelSize)
        flag(args, "--mem-fraction-static", engine.gpuMemoryUtilization)
        flag(args, "--dtype", engine.dtype)
        flag(args, "--max-running-requests", engine.maxConcurrentRequests)
        if engine.trustRemoteCode:
            args.append("--trust-remote-code")
        return args

    def api_key_args(self):
        return ["--api-key", f"$({API_KEY_ENV})"]


class LlamaCppEngine(Engine):
    """Llama.cpp's llama-server, for GGUF models, on CPU or GPU."""

    name = SAMLLMHostEngine.LLAMA_CPP.value
    port = 8080
    api_key_env = "LLAMA_API_KEY"

    def model_args(self, spec, model, served_name):
        if model.local:
            args = ["--model", model.path]
        else:
            args = ["--hf-repo", model.reference, "--hf-file", str(model.file)]
        args += ["--alias", served_name, "--host", CONTAINER_BIND_ADDRESS, "--port", str(self.container_port(spec))]
        if spec.model.task == "embedding":
            args.append("--embedding")
        return args

    def setting_args(self, spec):
        args: list[str] = []
        engine = spec.engine
        flag(args, "--ctx-size", engine.contextLength)
        flag(args, "--parallel", engine.maxConcurrentRequests)
        if spec.resources.gpuCount:
            args += ["--n-gpu-layers", "999"]
        return args

    def env(self, spec, model):
        return {"LLAMA_CACHE": posixpath.join(MODELS_MOUNT_PATH, "llama.cpp"), **super().env(spec, model)}


class OllamaEngine(Engine):
    """
    Ollama, for GGUF models, on CPU or GPU.

    The container starts ``ollama serve``, then pulls the model. The probes run
    ``ollama show``, so that a replica is ready only when the model is pulled.
    """

    name = SAMLLMHostEngine.OLLAMA.value
    port = 11434
    health_path = "/"
    MODEL_ENV = "SMARTER_OLLAMA_MODEL"

    @staticmethod
    def tag(model: ResolvedModel) -> str:
        """The Ollama tag.

        Hugging Face GGUF repositories are pulled as hf.co/<repository>[:<quantization>].
        """
        if model.source == SAMLLMHostModelSource.HUGGINGFACE.value:
            return f"hf.co/{model.reference}" + (f":{model.file}" if model.file else "")
        return model.reference

    def served_name(self, spec, default):
        # ollama names models by their tag.
        return self.tag(ResolvedModel(source=spec.model.source, reference=spec.model.repository, file=spec.model.file))

    def command(self, spec, model):
        script = (
            "ollama serve & pid=$!; until ollama list >/dev/null 2>&1; do sleep 1; done; "
            f'ollama pull "${self.MODEL_ENV}" && wait $pid'
        )
        return ["/bin/sh", "-c", script]

    def env(self, spec, model):
        env = {
            "OLLAMA_HOST": f"0.0.0.0:{self.container_port(spec)}",
            "OLLAMA_MODELS": posixpath.join(MODELS_MOUNT_PATH, "ollama"),
            "OLLAMA_KEEP_ALIVE": "-1",
            self.MODEL_ENV: self.tag(model),
        }
        if spec.engine.contextLength:
            env["OLLAMA_CONTEXT_LENGTH"] = str(spec.engine.contextLength)
        if spec.engine.maxConcurrentRequests:
            env["OLLAMA_NUM_PARALLEL"] = str(spec.engine.maxConcurrentRequests)
        return {**env, **spec.engine.env}

    def probe(self, spec):
        return {"exec": {"command": ["/bin/sh", "-c", f'ollama show "${self.MODEL_ENV}" >/dev/null']}}


class TeiEngine(Engine):
    """Hugging Face Text Embeddings Inference."""

    name = SAMLLMHostEngine.TEI.value
    port = 80
    api_key_env = "API_KEY"

    def model_args(self, spec, model, served_name):
        args = ["--model-id", model.path if model.local else model.reference]
        args += ["--hostname", CONTAINER_BIND_ADDRESS, "--port", str(self.container_port(spec))]
        if not model.local:
            flag(args, "--revision", model.revision)
        return args

    def setting_args(self, spec):
        args: list[str] = []
        flag(args, "--max-concurrent-requests", spec.engine.maxConcurrentRequests)
        flag(args, "--dtype", spec.engine.dtype)
        return args


class CustomEngine(Engine):
    """Any other image.

    Only spec.engine.command, args and env are used.
    """

    name = SAMLLMHostEngine.CUSTOM.value

    def image(self, spec):
        if not spec.engine.image:
            raise LLMHostConfigurationError("engine.image: is required when engine.name is custom.")
        return spec.engine.image


ENGINES: dict[str, Engine] = {
    engine.name: engine
    for engine in (
        VllmEngine(),
        TgiEngine(),
        SglangEngine(),
        LlamaCppEngine(),
        OllamaEngine(),
        TeiEngine(),
        CustomEngine(),
    )
}


def get_engine(name: str) -> Engine:
    """Return the engine named ``name``."""
    try:
        return ENGINES[name]
    except KeyError as e:
        raise LLMHostConfigurationError(f"engine.name: {name} is not supported.") from e


__all__ = ["API_KEY_ENV", "ENGINES", "Engine", "get_engine"]
