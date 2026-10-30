# pylint: disable=attribute-defined-outside-init
"""Test model discovery: :mod:`smarter.apps.llmhost.services.discovery`."""

import requests

from smarter.apps.llmhost.manifest.models.llmhost.model import SAMLLMHost
from smarter.apps.llmhost.models import LLMHost
from smarter.apps.llmhost.services.discovery import (
    CATALOGS,
    BuiltinCatalog,
    HuggingFaceCatalog,
    ModelInfo,
    default_engine,
    draft_manifest,
    estimate_vram_gb,
    get_catalog,
    recommend_resources,
)
from smarter.apps.llmhost.services.exceptions import LLMHostDiscoveryError
from smarter.common.api import SmarterApiVersions
from smarter.lib.unittest.base_classes import SmarterTestBase

from .base_classes import (
    BUILTIN_LLMHOST_PATH,
    BuiltinFixturesMixin,
    FakeSession,
    builtin_compute_models,
    builtin_manifests,
    smarter_admin_user_profile,
)


class TestBuiltinCatalog(BuiltinFixturesMixin):
    """Test the catalog of the Smarter admin's example LLMHosts."""

    def setUp(self):
        super().setUp()
        self.catalog = BuiltinCatalog()

    def fixture_names(self) -> list[str]:
        return sorted(manifest["metadata"]["name"] for manifest in builtin_manifests(BUILTIN_LLMHOST_PATH))

    def test_llmhosts(self):
        """Test that the catalog's LLMHosts are the Smarter admin's, including the fixtures."""
        llmhosts = BuiltinCatalog.llmhosts()
        admin = smarter_admin_user_profile()
        self.assertTrue(all(llmhost.user_profile_id == admin.pk for llmhost in llmhosts))
        names = set(llmhosts.values_list("name", flat=True))
        self.assertTrue(set(self.fixture_names()) <= names)

    def test_to_manifest(self):
        """Test that an LLMHost's manifest is its metadata, and its spec as it was applied."""
        llmhost = BuiltinCatalog.llmhosts().get(name="bge_m3")
        manifest = BuiltinCatalog.to_manifest(llmhost)
        self.assertEqual(manifest["apiVersion"], SmarterApiVersions.V1)
        self.assertEqual(manifest["kind"], "LLMHost")
        self.assertEqual(set(manifest), {"apiVersion", "kind", "metadata", "spec"})
        metadata = manifest["metadata"]
        self.assertEqual(metadata["name"], "bge_m3")
        self.assertEqual(metadata["description"], llmhost.description)
        self.assertEqual(metadata["version"], llmhost.version)
        self.assertEqual(sorted(metadata["tags"]), sorted(llmhost.tags_list))
        self.assertEqual(metadata["annotations"]["smarter.sh/llmhost/builtin"], "true")
        self.assertIs(manifest["spec"], llmhost.spec)
        self.assertEqual(manifest["spec"]["model"]["repository"], "BAAI/bge-m3")
        # the manifest is valid, and ready to apply again.
        self.assertEqual(SAMLLMHost(**manifest).spec.engine.name, "tei")

    def test_to_manifest_annotations(self):
        """Test that the manifest's annotations are the LLMHost's map of strings."""
        llmhost = LLMHost(name="x", description="", version="1.0.0", annotations=[{"example.com/a": 1}], spec={})
        llmhost.__dict__["tags_list"] = []  # an unsaved LLMHost has no tags to fetch.
        self.assertEqual(BuiltinCatalog.to_manifest(llmhost)["metadata"]["annotations"], {"example.com/a": "1"})

    def test_manifests(self):
        """Test that the manifests include the fixtures, are sorted by name, and skip LLMHosts without a spec."""
        admin = smarter_admin_user_profile()
        no_spec = LLMHost.objects.create(name="aaa_test_builtin_catalog_no_spec", user_profile=admin, spec={})
        self.addCleanup(LLMHost.objects.filter(pk=no_spec.pk).delete)
        names = [manifest["metadata"]["name"] for manifest in self.catalog.manifests()]
        # sorted by the database's collation, which may order "_" before digits, unlike Python.
        expected = [
            name
            for name in BuiltinCatalog.llmhosts().order_by("name").values_list("name", flat=True)
            if name != no_spec.name
        ]
        self.assertEqual(names, expected)
        self.assertTrue(set(self.fixture_names()) <= set(names))
        self.assertNotIn(no_spec.name, names)

    def test_search(self):
        """Test search by query and task."""
        everything = self.catalog.search(limit=100)
        self.assertGreaterEqual(len(everything), len(self.fixture_names()))
        self.assertTrue(all(info.catalog == "builtin" and info.manifest for info in everything))
        llamas = self.catalog.search(query="llama", limit=100)
        self.assertTrue(llamas)
        self.assertTrue(
            all(
                "llama" in (info.repository + str(info.tags) + info.manifest["metadata"]["name"]).lower()
                for info in llamas
            )
        )
        embeddings = self.catalog.search(task="embedding", limit=100)
        self.assertIn("BAAI/bge-m3", [info.repository for info in embeddings])
        self.assertTrue(all(info.task == "embedding" for info in embeddings))
        self.assertEqual(len(self.catalog.search(limit=3)), 3)

    def test_get(self):
        """Test get by repository or name, and that gated models are flagged."""
        info = self.catalog.get("meta-llama/Llama-3.1-8B-Instruct")
        self.assertTrue(info.gated)
        self.assertEqual(info.parameter_count, 8030261248)
        self.assertEqual(self.catalog.get("qwen3_8b").repository, "Qwen/Qwen3-8B")
        bge = self.catalog.get("bge_m3")
        self.assertEqual((bge.task, bge.license, bge.quantization), ("embedding", "mit", "fp32"))
        self.assertFalse(bge.gated)
        with self.assertRaises(LLMHostDiscoveryError):
            self.catalog.get("nobody/nothing")


class TestHuggingFaceCatalog(SmarterTestBase):
    """Test the Hugging Face catalog, with a fake session."""

    def catalog(self, **kwargs) -> HuggingFaceCatalog:
        self.session = FakeSession(**kwargs)
        return HuggingFaceCatalog(session=self.session, token="hf_x")

    def test_search(self):
        """Test that search sorts by downloads, and maps the task to a pipeline tag."""
        models = self.catalog().search(query="qwen", task="embedding", limit=5)
        self.assertEqual(
            [m.repository for m in models], ["Qwen/Qwen2.5-7B-Instruct", "meta-llama/Llama-3.1-8B-Instruct"]
        )
        url, params = self.session.calls[0]
        self.assertEqual(url, "https://huggingface.co/api/models")
        self.assertIn(("sort", "downloads"), params)
        self.assertIn(("pipeline_tag", "feature-extraction"), params)
        self.assertIn(("search", "qwen"), params)
        self.assertTrue(models[1].gated)
        self.assertEqual(models[1].license, "llama3.1")

    def test_get(self):
        """Test a model's details, including its context window from config.json."""
        info = self.catalog().get("Qwen/Qwen2.5-7B-Instruct")
        self.assertEqual(info.parameter_count, 7615616512)
        self.assertEqual(info.quantization, "bf16")
        self.assertEqual(info.architecture, "qwen2")
        self.assertEqual(info.license, "apache-2.0")
        self.assertEqual(info.context_window, 32768)
        self.assertEqual(info.files, ["model-00001-of-00004.safetensors", "model-00002-of-00004.safetensors"])

    def test_gguf_and_embedding(self):
        """Test that GGUF repositories, and sentence-similarity models, are recognized."""
        catalog = self.catalog()
        gguf = catalog.get("bartowski/Llama-3.2-3B-Instruct-GGUF")
        self.assertEqual(gguf.quantization, "gguf")
        self.assertEqual(len(gguf.files), 3)
        embedding = catalog.get("sentence-transformers/all-MiniLM-L6-v2")
        self.assertEqual((embedding.task, embedding.quantization), ("embedding", "fp32"))

    def test_errors(self):
        """Test that unavailable, denied and invalid requests raise LLMHostDiscoveryError."""
        for kwargs in (
            {"status_code": 401},
            {"status_code": 404},
            {"status_code": 500},
            {"error": requests.Timeout("slow")},
        ):
            with self.subTest(**{k: str(v) for k, v in kwargs.items()}):
                with self.assertRaises(LLMHostDiscoveryError):
                    self.catalog(**kwargs).search()
        with self.assertRaises(LLMHostDiscoveryError):
            self.catalog().get("not a repository")

    def test_context_window_unavailable(self):
        """Test that an unreadable config.json, e.g. of a gated model, leaves the context window unknown."""
        self.assertIsNone(self.catalog(status_code=403).context_window("meta-llama/Llama-3.1-8B-Instruct"))


class TestSizing(SmarterTestBase):
    """Test estimate_vram_gb() and recommend_resources(), with the built-in computes."""

    def setUp(self):
        self.computes = builtin_compute_models()

    def recommend(self, *args, **kwargs):
        return recommend_resources(*args, computes=self.computes, **kwargs)

    def test_estimate(self):
        self.assertIsNone(estimate_vram_gb(None))
        self.assertEqual(estimate_vram_gb(8_000_000_000, "bf16"), 20)
        self.assertEqual(estimate_vram_gb(8_000_000_000, "int4"), 6)
        self.assertEqual(estimate_vram_gb(1_000_000), 1)

    def test_recommend(self):
        """Test that a pod gets the fewest GPUs that fit, on the compute with the cheapest node that it fits."""
        self.assertEqual(self.recommend(None), {})
        cpu = self.recommend(1_000_000_000, "gguf", cpu_ok=True)
        self.assertEqual((cpu["compute"], cpu["gpuCount"], cpu["cpu"], cpu["memory"]), ("cpu_small", 0, "3", "3Gi"))
        small = self.recommend(8_030_000_000, "bf16")
        self.assertEqual(
            (small["compute"], small["gpuCount"], small["vramRequiredGb"], small["tensorParallelSize"]),
            ("gpu_l4_1x", 1, 21, None),
        )
        self.assertEqual((small["cpu"], small["memory"]), ("4", "24Gi"))
        # 4 L40S, in one g6e.12xlarge, are a cheaper node than 4 of a p5.48xlarge's H100s.
        large = self.recommend(70_553_706_496, "bf16")
        self.assertEqual((large["compute"], large["gpuCount"], large["tensorParallelSize"]), ("gpu_l40s_4x", 4, 4))
        self.assertEqual((large["cpu"], large["memory"]), ("10", "174Gi"))
        with self.assertRaises(LLMHostDiscoveryError):
            self.recommend(2_000_000_000_000, "bf16")
        with self.assertRaises(LLMHostDiscoveryError):
            recommend_resources(8_030_000_000, "bf16", computes=[])

    def test_pod_not_node(self):
        """Test that a small model's pod requests what it needs, not its node's CPU and memory."""
        tiny = self.recommend(751_632_384, "bf16")
        self.assertEqual((tiny["compute"], tiny["gpuCount"], tiny["cpu"], tiny["memory"]), ("gpu_l4_1x", 1, "4", "8Gi"))


class TestDraftManifest(BuiltinFixturesMixin):
    """Test default_engine() and draft_manifest()."""

    def setUp(self):
        self.computes = builtin_compute_models()

    def info(self, **kwargs) -> ModelInfo:
        data = {
            "catalog": "huggingface",
            "source": "huggingface",
            "repository": "Qwen/Qwen2.5-7B-Instruct",
            "parameter_count": 7615616512,
            "quantization": "bf16",
            "context_window": 131072,
            "license": "apache-2.0",
        }
        data.update(kwargs)
        return ModelInfo(**data)

    def test_default_engine(self):
        self.assertEqual(default_engine(self.info()), "vllm")
        self.assertEqual(default_engine(self.info(task="embedding")), "tei")
        self.assertEqual(default_engine(self.info(quantization="gguf")), "llama_cpp")
        self.assertEqual(default_engine(self.info(source="ollama", repository="llama3.2:1b")), "ollama")

    def test_draft(self):
        """Test that a drafted manifest is valid, sized, and caps a long context."""
        manifest = draft_manifest(self.info(gated=True), token_secret="huggingface_token", computes=self.computes)
        model = SAMLLMHost(**manifest)
        self.assertEqual(model.metadata.name, "qwen2_5_7b_instruct")
        self.assertEqual(model.spec.engine.name, "vllm")
        self.assertEqual(model.spec.engine.contextLength, 32768)
        self.assertEqual((model.spec.resources.gpuCount, model.spec.resources.memory), (1, "23Gi"))
        self.assertEqual(model.spec.compute, "gpu_l4_1x")
        self.assertEqual(model.spec.model.tokenSecret, "huggingface_token")
        draft = draft_manifest(self.info(), token_secret="x", computes=self.computes)
        self.assertIsNone(SAMLLMHost(**draft).spec.model.tokenSecret)

    def test_draft_gguf(self):
        """Test that a GGUF draft picks the Q4_K_M file, and runs a small model on CPU."""
        info = self.info(
            repository="bartowski/Llama-3.2-3B-Instruct-GGUF",
            quantization="gguf",
            parameter_count=3_212_749_824,
            files=["Llama-3.2-3B-Instruct-Q2_K.gguf", "Llama-3.2-3B-Instruct-Q4_K_M.gguf"],
        )
        model = SAMLLMHost(**draft_manifest(info, name="llama_gguf", computes=self.computes))
        self.assertEqual(model.spec.engine.name, "llama_cpp")
        self.assertEqual(model.spec.model.file, "Llama-3.2-3B-Instruct-Q4_K_M.gguf")
        self.assertEqual((model.spec.compute, model.spec.resources.gpuCount), ("cpu_small", 0))
        with self.assertRaises(LLMHostDiscoveryError):
            draft_manifest(self.info(), engine="llama_cpp", computes=self.computes)

    def test_draft_unknown_size(self):
        """Test that a model of unknown size gets one GPU on a GPU engine."""
        model = SAMLLMHost(**draft_manifest(self.info(parameter_count=None), computes=self.computes))
        self.assertEqual(model.spec.resources.gpuCount, 1)
        self.assertIsNone(model.spec.compute)

    def test_draft_builtin(self):
        """Test that a built-in model's draft is its manifest, unless the engine or name changes."""
        info = BuiltinCatalog().get("qwen3_8b")
        self.assertIs(draft_manifest(info), info.manifest)
        self.assertEqual(draft_manifest(info, name="my_qwen")["metadata"]["name"], "my_qwen")

    def test_get_catalog(self):
        self.assertEqual(sorted(CATALOGS), ["builtin", "huggingface"])
        self.assertIsInstance(get_catalog("builtin"), BuiltinCatalog)
        with self.assertRaises(LLMHostDiscoveryError):
            get_catalog("modelzoo")
