"""Test the branches of :mod:`smarter.lib.manifest.loader`: validate_key(), and SAMLoader's sources and formats."""

from unittest.mock import MagicMock, patch

import yaml

from smarter.lib import json
from smarter.lib.manifest.enum import (
    SAMDataFormats,
    SAMKeys,
    SAMSpecificationKeyOptions,
)
from smarter.lib.manifest.loader import SAMLoader, SAMLoaderError, validate_key
from smarter.lib.unittest.base_classes import SmarterTestBase

MANIFEST = {
    "apiVersion": "smarter.sh/v1",
    "kind": "Guardrail",
    "metadata": {"name": "a_guardrail", "description": "d", "version": "1.0.0"},
    "spec": {"config": {"stage": "both"}},
    "status": {"dependencies": []},
}


class TestValidateKey(SmarterTestBase):
    """Test validate_key() for each kind of specification: a list of values, a type and options, or a value."""

    def test_list_spec(self):
        validate_key(SAMKeys.KIND, "a", ["a", "b"])
        with self.assertRaises(SAMLoaderError):
            validate_key("kind", "c", ["a", "b"])

    def test_tuple_spec(self):
        validate_key("name", "a", (str, [SAMSpecificationKeyOptions.REQUIRED]))
        with self.assertRaises(SAMLoaderError):
            validate_key("name", "", (str, [SAMSpecificationKeyOptions.REQUIRED]))

    def test_value_spec(self):
        validate_key("apiVersion", "smarter.sh/v1", "smarter.sh/v1")
        for value in (None, 1, "smarter.sh/v2"):
            with self.subTest(value=value):
                with self.assertRaises(SAMLoaderError):
                    validate_key("apiVersion", value, "smarter.sh/v1")

    def test_key_must_be_a_string(self):
        with self.assertRaises(SAMLoaderError):
            validate_key(1, "a", "a")  # type: ignore[arg-type]


class TestSAMLoaderSources(SmarterTestBase):
    """Test SAMLoader's sources: a json string, a dict, yaml, a url, and their errors."""

    def test_dict_manifest(self):
        loader = SAMLoader(manifest=MANIFEST)
        self.assertTrue(loader.ready)
        self.assertEqual(loader.data_format, SAMDataFormats.JSON)
        self.assertEqual(loader.name, "a_guardrail")
        self.assertEqual(loader.kind, "Guardrail")
        self.assertEqual(loader.manifest_kind, "Guardrail")
        self.assertEqual(loader.manifest_status, {"dependencies": []})
        self.assertEqual(loader.source, "manifest dict")
        self.assertEqual(yaml.safe_load(loader.yaml_data), MANIFEST)
        self.assertIn("a_guardrail", str(loader))
        self.assertIn("a_guardrail", repr(loader))
        self.assertIsInstance(loader.to_json(), dict)
        self.assertIsInstance(loader.loader_ready_state(), str)
        loader.log_loader_state()

    def test_yaml_manifest(self):
        loader = SAMLoader(manifest=yaml.dump(MANIFEST))
        self.assertEqual(loader.data_format, SAMDataFormats.YAML)
        self.assertEqual(loader.json_data, MANIFEST)
        self.assertEqual(yaml.safe_load(loader.yaml_data), MANIFEST)
        self.assertEqual(loader.source, "manifest str")

    def test_json_string_manifest(self):
        loader = SAMLoader(manifest=json.dumps(MANIFEST))
        self.assertEqual(loader.data_format, SAMDataFormats.JSON)
        self.assertEqual(loader.json_data, MANIFEST)

    def test_url(self):
        with patch("smarter.lib.manifest.loader.requests.get", return_value=MagicMock(text=yaml.dump(MANIFEST))) as get:
            loader = SAMLoader(url="https://example.com/manifest.yaml")
        get.assert_called_once_with("https://example.com/manifest.yaml", timeout=30)
        self.assertEqual(loader.source, "url https://example.com/manifest.yaml")
        self.assertEqual(loader.name, "a_guardrail")

    def test_kind_only(self):
        loader = SAMLoader(kind="Guardrail")
        self.assertEqual(loader.kind, "Guardrail")
        self.assertEqual(loader.name, "unknown-name")
        self.assertEqual(loader.source, "unknown-source")
        self.assertEqual(loader.data_format, SAMDataFormats.UNKNOWN)
        self.assertIsNone(loader.json_data)
        self.assertIsNone(loader.yaml_data)

    def test_constructor_errors(self):
        for kwargs in (
            {"api_version": "smarter.sh/v2", "manifest": MANIFEST},
            {},
            {"manifest": MANIFEST, "url": "https://example.com/"},
            {"manifest": 42},
        ):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(SAMLoaderError):
                    SAMLoader(**kwargs)

    def test_invalid_format(self):
        with self.assertRaises(SAMLoaderError):
            SAMLoader(manifest="key: [unclosed")

    def test_missing_keys(self):
        """Test that a manifest without apiVersion, kind, metadata or spec is refused."""
        for key in ("apiVersion", "kind", "metadata", "spec"):
            manifest = {k: v for k, v in MANIFEST.items() if k != key}
            with self.subTest(key=key):
                with self.assertRaises(SAMLoaderError):
                    SAMLoader(manifest=manifest, kind="Guardrail")

    def test_not_a_dict(self):
        with self.assertRaises(SAMLoaderError):
            SAMLoader(manifest="- a\\n- list\\n", kind="Guardrail")
