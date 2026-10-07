"""Test the LLMHost Pydantic manifest: :mod:`smarter.apps.llmhost.manifest.models.llmhost`."""

import datetime
import glob
import os
from decimal import Decimal

from pydantic import ValidationError

from smarter.apps.llmhost.const import BUILTIN_MANIFESTS_PATH
from smarter.apps.llmhost.manifest.enum import (
    SAMLLMHostEngine,
    SAMLLMHostModelSource,
    SAMLLMHostQuantization,
    SAMLLMHostStatusEnum,
    SAMLLMHostTask,
)
from smarter.apps.llmhost.manifest.models.llmhost.model import SAMLLMHost
from smarter.apps.llmhost.manifest.models.llmhost.spec import (
    SAMLLMHostSpec,
    engine_supports_api_key,
    engine_supports_task,
)
from smarter.apps.llmhost.manifest.models.llmhost.status import SAMLLMHostStatus
from smarter.common.utils import get_readonly_yaml_file
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.unittest.base_classes import SmarterTestBase

from .base_classes import get_test_data, merge

INVALID = (SAMValidationError, ValidationError, ValueError)
MINIMAL = {"model": {"repository": "Qwen/Qwen3-8B"}, "engine": {"name": "vllm"}, "resources": {"gpuCount": 1}}


# pylint: disable=too-many-public-methods
class TestLLMHostManifest(SmarterTestBase):
    """Test SAMLLMHost, SAMLLMHostSpec and SAMLLMHostStatus."""

    def spec(self, **overrides) -> SAMLLMHostSpec:
        """A minimal spec, Qwen3 8B on vLLM with one GPU, with overrides deep merged."""
        return SAMLLMHostSpec(**merge(MINIMAL, overrides))

    def assertInvalid(self, **overrides):
        """Assert that a spec with these overrides is rejected."""
        with self.assertRaises(INVALID):
            self.spec(**overrides)

    def test_builtin_manifests(self):
        """Test that every built-in manifest is valid, unique, and that together they cover the engines, sources and tasks."""
        filespecs = sorted(glob.glob(os.path.join(BUILTIN_MANIFESTS_PATH, "*.yaml")))
        self.assertGreaterEqual(len(filespecs), 20)
        names, engines, sources, tasks = [], set(), set(), set()
        for filespec in filespecs:
            with self.subTest(filespec=os.path.basename(filespec)):
                manifest = SAMLLMHost(**get_readonly_yaml_file(filespec))
                names.append(manifest.metadata.name)
                engines.add(manifest.spec.engine.name)
                sources.add(manifest.spec.model.source)
                tasks.add(manifest.spec.model.task)
                self.assertTrue(manifest.metadata.description)
                self.assertIn("builtin", str(manifest.metadata.annotations))
                # built-ins never embed credentials; gated models refer to a Secret by name.
                if manifest.spec.model.tokenSecret:
                    self.assertEqual(manifest.spec.model.tokenSecret, "huggingface_token")
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(engines, set(SAMLLMHostEngine.all()) - {SAMLLMHostEngine.CUSTOM.value})
        self.assertTrue({"huggingface", "ollama", "url"}.issubset(sources))
        self.assertEqual(tasks, set(SAMLLMHostTask.all()))

    def test_test_manifests(self):
        """Test the test manifests."""
        manifest = SAMLLMHost(**get_test_data("llmhost.yaml"))
        self.assertEqual(manifest.spec.model.repository, "meta-llama/Llama-3.1-8B-Instruct")
        self.assertTrue(manifest.spec.network.ingress)
        self.assertEqual(manifest.spec.compute, "gpu_a10g_1x")
        ollama = SAMLLMHost(**get_test_data("llmhost-ollama.yaml"))
        self.assertEqual(ollama.spec.engine.name, "ollama")
        self.assertIsNone(ollama.spec.compute)
        self.assertFalse(ollama.spec.storage.retain)

    def test_defaults(self):
        """Test the defaults of the spec."""
        spec = self.spec()
        self.assertEqual(spec.model.source, SAMLLMHostModelSource.HUGGINGFACE.value)
        self.assertEqual(spec.model.task, SAMLLMHostTask.TEXT_GENERATION.value)
        self.assertEqual(spec.model.quantization, SAMLLMHostQuantization.NONE.value)
        self.assertTrue(spec.model.capabilities.streaming)
        self.assertFalse(spec.model.capabilities.functionCalling)
        self.assertEqual(spec.engine.apiFormat, "openai_compatible")
        self.assertEqual(spec.engine.args, [])
        self.assertEqual(spec.resources.gpuResource, "nvidia.com/gpu")
        self.assertEqual(spec.resources.shmSize, "8Gi")
        self.assertEqual((spec.storage.size, spec.storage.accessMode), ("50Gi", "ReadWriteOnce"))
        self.assertTrue(spec.storage.retain)
        self.assertFalse(spec.network.ingress)
        self.assertEqual(spec.scaling.replicas, 1)
        self.assertEqual((spec.healthCheck.startupTimeoutSeconds, spec.healthCheck.periodSeconds), (3600, 10))
        self.assertIsNone(spec.compute)

    def test_enums(self):
        """Test that the enumerated fields are validated, case insensitively."""
        spec = self.spec(engine={"name": "VLLM"}, model={"source": "HuggingFace", "quantization": "BF16"})
        self.assertEqual(
            (spec.engine.name, spec.model.source, spec.model.quantization), ("vllm", "huggingface", "bf16")
        )
        self.assertEqual(self.spec(storage={"accessMode": "readwritemany"}).storage.accessMode, "ReadWriteMany")
        self.assertInvalid(engine={"name": "pytorch"})
        self.assertInvalid(model={"source": "dropbox"})
        self.assertInvalid(model={"task": "image-generation"})
        self.assertInvalid(model={"quantization": "int3"})
        self.assertInvalid(engine={"apiFormat": "grpc"})

    def test_unknown_fields(self):
        """Test that unknown fields, e.g. typos, are rejected."""
        self.assertInvalid(model={"repo": "Qwen/Qwen3-8B"})
        self.assertInvalid(engine={"contextLenght": 4096})
        self.assertInvalid(gpus=1)

    def test_repository(self):
        """Test that the repository is validated against the source."""
        self.assertInvalid(model={"repository": "not a repo"})
        self.assertInvalid(model={"repository": "qwen3"})
        self.assertInvalid(model={"repository": "Qwen/Qwen3-8B;rm -rf /"})
        self.assertInvalid(model={"source": "s3", "repository": "bucket/prefix"})
        self.assertInvalid(model={"source": "url", "repository": "ftp://example.com/model.gguf"})
        self.assertInvalid(model={"source": "pvc", "repository": "/abs/path"}, storage={"existingClaim": "c"})
        self.assertInvalid(model={"source": "pvc", "repository": "../escape"}, storage={"existingClaim": "c"})
        spec = self.spec(model={"source": "s3", "repository": "s3://bucket/models/qwen3"})
        self.assertEqual(spec.model.repository, "s3://bucket/models/qwen3")

    def test_revision(self):
        """Test that revision applies only to Hugging Face, and rejects shell characters."""
        self.assertEqual(self.spec(model={"revision": "abc123"}).model.revision, "abc123")
        self.assertInvalid(model={"revision": "main; echo"})
        self.assertInvalid(model={"source": "s3", "repository": "s3://bucket/x", "revision": "main"})

    def test_engine_sources(self):
        """Test that an engine accepts only the sources it can load."""
        self.assertInvalid(model={"source": "ollama", "repository": "llama3.2:1b"})
        self.assertInvalid(
            engine={"name": "ollama"}, model={"source": "s3", "repository": "s3://bucket/x"}, resources={"gpuCount": 0}
        )
        spec = self.spec(
            engine={"name": "ollama"},
            model={"source": "huggingface", "repository": "bartowski/Llama-3.2-1B-Instruct-GGUF"},
        )
        self.assertEqual(spec.engine.name, "ollama")

    def test_engine_tasks(self):
        """Test that tgi serves only text generation, and tei only embeddings."""
        self.assertInvalid(engine={"name": "tgi"}, model={"task": "embedding"})
        self.assertInvalid(engine={"name": "tei"})
        self.spec(engine={"name": "tei"}, model={"task": "embedding"})
        self.spec(model={"task": "embedding"})
        self.assertTrue(engine_supports_task("vllm", "embedding"))
        self.assertFalse(engine_supports_task("tei", "text-generation"))

    def test_llama_cpp_file(self):
        """Test that llama_cpp requires a single weights file, except from a URL, which names it."""
        cpu = {"gpuCount": 0}
        self.assertInvalid(engine={"name": "llama_cpp"}, resources=cpu)
        self.spec(engine={"name": "llama_cpp"}, model={"file": "model-Q4_K_M.gguf"}, resources=cpu)
        self.spec(
            engine={"name": "llama_cpp"},
            model={"source": "url", "repository": "https://example.com/m.gguf", "revision": None},
            resources=cpu,
        )

    def test_gpu_engines(self):
        """Test that vllm and sglang require a GPU, unless the image is overridden, e.g. with a CPU build."""
        self.assertInvalid(resources={"gpuCount": 0})
        self.assertInvalid(engine={"name": "sglang"}, resources={"gpuCount": 0})
        self.spec(engine={"image": "example.com/vllm-cpu:1.0"}, resources={"gpuCount": 0})

    def test_gpu_settings(self):
        """Test that tensor parallelism cannot exceed the GPUs, and GPU memory utilization requires a GPU."""
        self.assertInvalid(engine={"tensorParallelSize": 2})
        self.spec(engine={"tensorParallelSize": 2}, resources={"gpuCount": 2})
        self.assertInvalid(engine={"gpuMemoryUtilization": 1.5})
        self.assertInvalid(
            engine={"name": "llama_cpp", "gpuMemoryUtilization": 0.9},
            model={"file": "m.gguf"},
            resources={"gpuCount": 0},
        )
        self.assertInvalid(resources={"gpuCount": 17})

    def test_replicas(self):
        """Test that several replicas require a volume that several pods can mount."""
        self.assertInvalid(scaling={"replicas": 2})
        self.assertEqual(
            self.spec(scaling={"replicas": 2}, storage={"accessMode": "ReadWriteMany"}).scaling.replicas, 2
        )
        self.assertInvalid(scaling={"replicas": 0})

    def test_ingress_authentication(self):
        """Test that a public Ingress requires an engine that authenticates requests, unless explicitly allowed."""
        self.spec(network={"ingress": True})
        self.assertInvalid(engine={"name": "tgi"}, network={"ingress": True})
        self.spec(engine={"name": "tgi"}, network={"ingress": True, "allowUnauthenticated": True})
        self.assertInvalid(engine={"name": "tgi"}, network={"apiKeySecret": "my_key"})
        self.assertTrue(engine_supports_api_key("vllm"))
        self.assertFalse(engine_supports_api_key("ollama"))

    def test_hostname(self):
        """Test that the hostname is validated and lower cased."""
        self.assertEqual(self.spec(network={"hostname": "LLM.Example.com"}).network.hostname, "llm.example.com")
        self.assertInvalid(network={"hostname": "not a hostname"})
        self.assertInvalid(network={"hostname": "https://llm.example.com"})

    def test_custom_engine(self):
        """Test that the custom engine requires an image and a port, and that only it may set a command."""
        self.assertInvalid(engine={"name": "custom"})
        spec = self.spec(engine={"name": "custom", "image": "example.com/server:1", "port": 9000, "command": ["serve"]})
        self.assertEqual(spec.engine.command, ["serve"])
        self.assertInvalid(engine={"command": ["serve"]})

    def test_env(self):
        """Test that env names are validated, and that the SMARTER_ prefix is reserved."""
        self.assertEqual(
            self.spec(engine={"env": {"VLLM_LOGGING_LEVEL": "DEBUG"}}).engine.env["VLLM_LOGGING_LEVEL"], "DEBUG"
        )
        self.assertInvalid(engine={"env": {"1BAD": "x"}})
        self.assertInvalid(engine={"env": {"SMARTER_API_KEY": "x"}})

    def test_quantities(self):
        """Test that cpu, memory, shmSize and storage size are Kubernetes quantities."""
        self.assertEqual(self.spec(resources={"cpu": "3500m", "memory": "24Gi"}).resources.cpu, "3500m")
        self.assertInvalid(resources={"memory": "lots"})
        self.assertInvalid(resources={"shmSize": "8 GB"})
        self.assertInvalid(storage={"size": "-5Gi"})

    def test_pvc_source(self):
        """Test that the pvc source requires an existing claim."""
        self.assertInvalid(model={"source": "pvc", "repository": "models/qwen3"})
        spec = self.spec(model={"source": "pvc", "repository": "models/qwen3"}, storage={"existingClaim": "weights"})
        self.assertEqual(spec.storage.existingClaim, "weights")

    def test_embedding_capabilities(self):
        """Test that embedding models cannot claim function calling."""
        self.assertInvalid(model={"task": "embedding", "capabilities": {"functionCalling": True}})

    def test_ollama_api_format(self):
        """Test that only ollama, and custom, speak ollama_native."""
        self.assertInvalid(engine={"apiFormat": "ollama_native"})
        spec = self.spec(
            engine={"name": "ollama", "apiFormat": "ollama_native"},
            model={"source": "ollama", "repository": "llama3.2:1b"},
        )
        self.assertEqual(spec.engine.apiFormat, "ollama_native")
        self.assertInvalid(
            engine={"name": "ollama", "apiFormat": "huggingface"},
            model={"source": "ollama", "repository": "llama3.2:1b"},
        )

    def test_round_trip(self):
        """Test that a spec survives model_dump() and re-validation, as the broker stores it."""
        spec = SAMLLMHostSpec(**get_test_data("llmhost.yaml")["spec"])
        dumped = spec.model_dump(mode="json", exclude_none=True)
        self.assertEqual(SAMLLMHostSpec(**dumped), spec)
        self.assertEqual(dumped["compute"], "gpu_a10g_1x")

    def test_status(self):
        """Test the status model, and that it is optional in the manifest."""
        now = datetime.datetime.now()
        status = SAMLLMHostStatus(
            accountNumber="1234-5678-9012",
            username="admin",
            recordLocator="abc",
            created=now,
            modified=now,
            hostStatus=SAMLLMHostStatusEnum.ACTIVE.value,
            readyReplicas=1,
            estimatedCost=Decimal("2.5"),
        )
        self.assertEqual(status.hostStatus, "active")
        manifest = SAMLLMHost(**get_test_data("llmhost.yaml"))
        self.assertIsNone(manifest.status)
