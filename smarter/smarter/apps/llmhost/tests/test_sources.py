"""Test the model sources: :mod:`smarter.apps.llmhost.services.sources`."""

from smarter.apps.llmhost.manifest.models.llmhost.spec import SAMLLMHostModel
from smarter.apps.llmhost.services.exceptions import LLMHostConfigurationError
from smarter.apps.llmhost.services.sources import SOURCES, resolve_model
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestModelSources(SmarterTestBase):
    """Test that each source resolves spec.model into what an engine loads, and how the weights get there."""

    def test_registry(self):
        """Test that every source is registered."""
        self.assertEqual(sorted(SOURCES), ["huggingface", "ollama", "pvc", "s3", "url"])

    def test_huggingface(self):
        """Test that the engine downloads Hugging Face models itself, at the revision, which defaults to main."""
        model = resolve_model(SAMLLMHostModel(repository="Qwen/Qwen3-8B"), "llmhost-1-qwen")
        self.assertEqual((model.reference, model.revision, model.local), ("Qwen/Qwen3-8B", "main", False))
        self.assertEqual(model.init_containers, [])
        pinned = resolve_model(SAMLLMHostModel(repository="Qwen/Qwen3-8B", revision="abc123"), "x")
        self.assertEqual(pinned.revision, "abc123")

    def test_ollama(self):
        """Test that Ollama tags are passed through."""
        model = resolve_model(SAMLLMHostModel(source="ollama", repository="llama3.2:1b"), "x")
        self.assertEqual((model.reference, model.local, model.revision), ("llama3.2:1b", False, None))

    def test_s3(self):
        """Test that an init container syncs an S3 prefix to the model volume."""
        model = resolve_model(SAMLLMHostModel(source="s3", repository="s3://bucket/qwen3"), "llmhost-1-qwen")
        self.assertTrue(model.local)
        self.assertEqual(model.reference, "/models/local/llmhost-1-qwen")
        init = model.init_containers[0]
        self.assertEqual(init["command"][:3], ["aws", "s3", "sync"])
        self.assertIn("s3://bucket/qwen3", init["command"])
        self.assertEqual(init["volumeMounts"][0]["mountPath"], "/models")

    def test_url(self):
        """Test that an init container downloads a file, unless it is there, without interpolating the URL into the script."""
        url = "https://example.com/files/model-Q4_K_M.gguf"
        model = resolve_model(SAMLLMHostModel(source="url", repository=url), "llmhost-1-x")
        self.assertEqual(model.file, "model-Q4_K_M.gguf")
        self.assertEqual(model.path, "/models/local/llmhost-1-x/model-Q4_K_M.gguf")
        command = model.init_containers[0]["command"]
        self.assertEqual(command[:2], ["/bin/sh", "-c"])
        self.assertNotIn(url, command[2])
        self.assertEqual(command[-2:], [url, model.path])
        named = resolve_model(SAMLLMHostModel(source="url", repository=url, file="other.gguf"), "x")
        self.assertEqual(named.file, "other.gguf")

    def test_url_without_file_name(self):
        """Test that a URL without a file name requires model.file."""
        with self.assertRaises(LLMHostConfigurationError):
            resolve_model(SAMLLMHostModel(source="url", repository="https://example.com/"), "x")

    def test_pvc(self):
        """Test that pvc weights are loaded from their path within the volume."""
        model = resolve_model(SAMLLMHostModel(source="pvc", repository="weights/qwen3", file="q.gguf"), "x")
        self.assertEqual(model.path, "/models/weights/qwen3/q.gguf")
        self.assertTrue(model.local)
        self.assertEqual(model.init_containers, [])
