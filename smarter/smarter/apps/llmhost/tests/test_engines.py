"""Test the inference engines: :mod:`smarter.apps.llmhost.services.engines`."""

from smarter.apps.llmhost.const import DEFAULT_CPU_IMAGES, DEFAULT_IMAGES
from smarter.apps.llmhost.manifest.models.llmhost.spec import SAMLLMHostSpec
from smarter.apps.llmhost.services.engines import API_KEY_ENV, ENGINES, get_engine
from smarter.apps.llmhost.services.exceptions import LLMHostConfigurationError
from smarter.apps.llmhost.services.sources import resolve_model
from smarter.lib.unittest.base_classes import SmarterTestBase

from .base_classes import merge

BASE = {"model": {"repository": "Qwen/Qwen3-8B"}, "engine": {"name": "vllm"}, "resources": {"gpuCount": 1}}


def build(**overrides):
    """Return (engine, spec, args, env) for a spec, with an API key."""
    spec = SAMLLMHostSpec(**merge(BASE, overrides))
    engine = get_engine(spec.engine.name)
    model = resolve_model(spec.model, "llmhost-1-test")
    served = engine.served_name(spec, "test")
    return engine, spec, engine.args(spec, model, served, api_key=True), engine.env(spec, model)


def value(args: list[str], flag: str) -> str:
    """The value that follows a flag."""
    return args[args.index(flag) + 1]


class TestEngines(SmarterTestBase):
    """Test that each engine translates the engine-neutral spec into its own container."""

    def test_registry(self):
        """Test that every engine is registered, and that unknown engines are rejected."""
        self.assertEqual(sorted(ENGINES), ["custom", "llama_cpp", "ollama", "sglang", "tei", "tgi", "vllm"])
        with self.assertRaises(LLMHostConfigurationError):
            get_engine("pytorch")

    def test_vllm(self):
        """Test vLLM's model and common setting arguments, and that extra args come last."""
        engine, spec, args, env = build(
            model={"servedName": "qwen3"},
            engine={
                "contextLength": 8192,
                "tensorParallelSize": 1,
                "gpuMemoryUtilization": 0.85,
                "dtype": "bfloat16",
                "maxConcurrentRequests": 64,
                "trustRemoteCode": True,
                "args": ["--enable-prefix-caching"],
            },
        )
        self.assertEqual(value(args, "--model"), "Qwen/Qwen3-8B")
        self.assertEqual(value(args, "--served-model-name"), "qwen3")
        self.assertEqual(value(args, "--revision"), "main")
        self.assertEqual(value(args, "--max-model-len"), "8192")
        self.assertEqual(value(args, "--gpu-memory-utilization"), "0.85")
        self.assertEqual(value(args, "--max-num-seqs"), "64")
        self.assertEqual(value(args, "--port"), "8000")
        self.assertIn("--trust-remote-code", args)
        self.assertEqual(args[-1], "--enable-prefix-caching")
        self.assertEqual(engine.api_key_env, "VLLM_API_KEY")
        self.assertNotIn("--api-key", args)
        self.assertEqual(env["HF_HOME"], "/models/huggingface")
        self.assertEqual(engine.image(spec), DEFAULT_IMAGES["vllm"])
        self.assertIsNone(engine.command(spec, resolve_model(spec.model, "x")))

    def test_vllm_defaults(self):
        """Test that unset settings add no arguments, and that the served name defaults to the LLMHost's name."""
        _, _, args, _ = build()
        for flag in ("--max-model-len", "--tensor-parallel-size", "--dtype", "--trust-remote-code"):
            self.assertNotIn(flag, args)
        self.assertEqual(value(args, "--served-model-name"), "test")

    def test_local_model(self):
        """Test that local weights are loaded by path, without a revision."""
        _, _, args, _ = build(model={"source": "s3", "repository": "s3://bucket/qwen3"})
        self.assertEqual(value(args, "--model"), "/models/local/llmhost-1-test")
        self.assertNotIn("--revision", args)

    def test_tgi(self):
        """Test TGI's arguments, including the input length, which must leave room for one token."""
        engine, _, args, _ = build(
            engine={"name": "tgi", "contextLength": 4096, "tensorParallelSize": 1, "maxConcurrentRequests": 32}
        )
        self.assertEqual(value(args, "--model-id"), "Qwen/Qwen3-8B")
        self.assertEqual(value(args, "--max-total-tokens"), "4096")
        self.assertEqual(value(args, "--max-input-tokens"), "4095")
        self.assertEqual(value(args, "--num-shard"), "1")
        self.assertEqual(value(args, "--port"), "80")
        self.assertFalse(engine.supports_api_key())

    def test_sglang(self):
        """Test SGLang's command, and that its API key is an argument that refers to an environment variable."""
        engine, spec, args, _ = build(engine={"name": "sglang", "contextLength": 8192, "gpuMemoryUtilization": 0.8})
        self.assertEqual(
            engine.command(spec, resolve_model(spec.model, "x")), ["python3", "-m", "sglang.launch_server"]
        )
        self.assertEqual(value(args, "--model-path"), "Qwen/Qwen3-8B")
        self.assertEqual(value(args, "--context-length"), "8192")
        self.assertEqual(value(args, "--mem-fraction-static"), "0.8")
        self.assertEqual(value(args, "--api-key"), f"$({API_KEY_ENV})")
        self.assertEqual(engine.api_key_env, API_KEY_ENV)

    def test_llama_cpp(self):
        """Test llama.cpp's Hugging Face download, GPU offload, and CPU image."""
        engine, spec, args, env = build(
            engine={"name": "llama_cpp", "contextLength": 4096, "maxConcurrentRequests": 4},
            model={"repository": "bartowski/Llama-3.2-3B-Instruct-GGUF", "file": "Llama-3.2-3B-Instruct-Q4_K_M.gguf"},
        )
        self.assertEqual(value(args, "--hf-repo"), "bartowski/Llama-3.2-3B-Instruct-GGUF")
        self.assertEqual(value(args, "--hf-file"), "Llama-3.2-3B-Instruct-Q4_K_M.gguf")
        self.assertEqual(value(args, "--ctx-size"), "4096")
        self.assertEqual(value(args, "--parallel"), "4")
        self.assertEqual(value(args, "--n-gpu-layers"), "999")
        self.assertEqual(env["LLAMA_CACHE"], "/models/llama.cpp")
        self.assertEqual(engine.image(spec), DEFAULT_IMAGES["llama_cpp"])
        engine, spec, args, _ = build(
            engine={"name": "llama_cpp"},
            model={"source": "url", "repository": "https://example.com/m.gguf"},
            resources={"gpuCount": 0},
        )
        self.assertEqual(value(args, "--model"), "/models/local/llmhost-1-test/m.gguf")
        self.assertNotIn("--n-gpu-layers", args)
        self.assertEqual(engine.image(spec), DEFAULT_CPU_IMAGES["llama_cpp"])

    def test_llama_cpp_embedding(self):
        """Test that llama.cpp serves embeddings with --embedding."""
        _, _, args, _ = build(
            engine={"name": "llama_cpp"}, model={"task": "embedding", "file": "e.gguf"}, resources={"gpuCount": 0}
        )
        self.assertIn("--embedding", args)

    def test_ollama(self):
        """Test that Ollama serves, pulls the model named in its environment, and is probed with ollama show."""
        engine, spec, args, env = build(
            engine={"name": "ollama", "contextLength": 8192, "maxConcurrentRequests": 2, "env": {"OLLAMA_DEBUG": "1"}},
            model={"source": "ollama", "repository": "llama3.2:1b"},
            resources={"gpuCount": 0},
        )
        command = engine.command(spec, resolve_model(spec.model, "x"))
        self.assertEqual(command[:2], ["/bin/sh", "-c"])
        self.assertIn("ollama pull", command[2])
        self.assertNotIn("llama3.2:1b", command[2])
        self.assertEqual(env[engine.MODEL_ENV], "llama3.2:1b")
        self.assertEqual(env["OLLAMA_HOST"], "0.0.0.0:11434")
        self.assertEqual(env["OLLAMA_CONTEXT_LENGTH"], "8192")
        self.assertEqual(env["OLLAMA_NUM_PARALLEL"], "2")
        self.assertEqual(env["OLLAMA_DEBUG"], "1")
        self.assertEqual(args, [])
        self.assertEqual(engine.served_name(spec, "ignored"), "llama3.2:1b")
        self.assertIn("ollama show", str(engine.probe(spec)))

    def test_ollama_huggingface(self):
        """Test that Ollama pulls Hugging Face GGUF repositories as hf.co/<repository>:<quantization>."""
        engine, spec, _, env = build(
            engine={"name": "ollama"},
            model={"repository": "bartowski/Llama-3.2-1B-Instruct-GGUF", "file": "Q4_K_M"},
        )
        self.assertEqual(env[engine.MODEL_ENV], "hf.co/bartowski/Llama-3.2-1B-Instruct-GGUF:Q4_K_M")
        self.assertEqual(engine.served_name(spec, "x"), "hf.co/bartowski/Llama-3.2-1B-Instruct-GGUF:Q4_K_M")

    def test_tei(self):
        """Test Text Embeddings Inference's arguments, API key and CPU image."""
        engine, spec, args, _ = build(
            engine={"name": "tei", "maxConcurrentRequests": 128},
            model={"repository": "BAAI/bge-m3", "task": "embedding"},
            resources={"gpuCount": 0},
        )
        self.assertEqual(value(args, "--model-id"), "BAAI/bge-m3")
        self.assertEqual(value(args, "--max-concurrent-requests"), "128")
        self.assertEqual(engine.api_key_env, "API_KEY")
        self.assertEqual(engine.image(spec), DEFAULT_CPU_IMAGES["tei"])

    def test_custom(self):
        """Test that a custom engine uses only the spec's image, port, command and args."""
        engine, spec, args, _ = build(
            engine={
                "name": "custom",
                "image": "example.com/server:1",
                "port": 9000,
                "command": ["serve"],
                "args": ["--x"],
            },
            healthCheck={"path": "/ready"},
        )
        self.assertEqual(engine.image(spec), "example.com/server:1")
        self.assertEqual(engine.container_port(spec), 9000)
        self.assertEqual(engine.command(spec, resolve_model(spec.model, "x")), ["serve"])
        self.assertEqual(args, ["--x"])
        self.assertEqual(engine.probe(spec), {"httpGet": {"path": "/ready", "port": "http"}})

    def test_image_override(self):
        """Test that spec.engine.image overrides the official image."""
        engine, spec, _, _ = build(engine={"image": "vllm/vllm-openai:v0.10.1"})
        self.assertEqual(engine.image(spec), "vllm/vllm-openai:v0.10.1")
