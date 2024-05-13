"""Test SAMLoader"""

import os
import unittest

import yaml

from smarter.common.const import PYTHON_ROOT

from ..enum import SAMApiVersions, SAMDataFormats, SAMKeys, SAMMetadataKeys
from ..loader import SAMLoader, SAMLoaderError


class TestManifestLoader(unittest.TestCase):
    """Test SAMLoader"""

    def setUp(self):
        """Set up test fixtures."""
        self.path = os.path.join(PYTHON_ROOT, "smarter", "apps", "api", "v1", "cli", "tests", "data")
        self.url = "https://cdn.platform.smarter.sh/cli/example-manifests/plugin.yaml"
        self.good_manifest_path = os.path.join(self.path, "good-plugin-manifest.yaml")

        with open(self.good_manifest_path, encoding="utf-8") as file:
            self.good_manifest_text = file.read()

    def test_valid_manifest(self):
        """Test that we can load a valid manifest"""
        loader = SAMLoader(api_version=SAMApiVersions.V1.value, manifest=self.good_manifest_text)
        self.assertIsInstance(loader.json_data, dict)
        self.assertIsInstance(loader.specification, dict)
        self.assertIsInstance(loader.yaml_data, str)
        self.assertEqual(loader.data_format, SAMDataFormats.YAML)
        self.assertIsInstance(loader.formatted_data, str)

        # Validate the manifest, ensure that no exceptions are raised
        loader.validate_manifest()

        # validate that all items in manifest_metadata_keys are in SAMMetadataKeys
        for key in loader.manifest_metadata_keys:
            self.assertIn(key, SAMMetadataKeys.all_values())

        self.assertIsInstance(loader.manifest_spec_keys, list)
        self.assertIsInstance(loader.manifest_status_keys, list)
        self.assertIsInstance(loader.manifest_metadata, dict)
        self.assertIsInstance(loader.manifest_spec, dict)
        self.assertIsNone(loader.manifest_status)

    def init_from_filepath(self):
        filepath = self.path + "/good-plugin-manifest.yaml"
        loader = SAMLoader(api_version=SAMApiVersions.V1.value, manifest=filepath)
        loader.validate_manifest()
        self.assertIsInstance(loader.json_data, dict)
        self.assertIsInstance(loader.specification, dict)
        self.assertIsInstance(loader.yaml_data, str)
        self.assertEqual(loader.data_format, SAMDataFormats.YAML)
        self.assertIsInstance(loader.formatted_data, str)

    def init_from_url(self):
        loader = SAMLoader(api_version=SAMApiVersions.V1.value, manifest=self.url)
        loader.validate_manifest()
        self.assertIsInstance(loader.json_data, dict)
        self.assertIsInstance(loader.specification, dict)
        self.assertIsInstance(loader.yaml_data, str)
        self.assertEqual(loader.data_format, SAMDataFormats.YAML)
        self.assertIsInstance(loader.formatted_data, str)

    def test_getkey(self):
        loader = SAMLoader(api_version=SAMApiVersions.V1.value, manifest=self.good_manifest_text)
        self.assertEqual(loader.get_key("metadata"), loader.manifest_metadata)
        self.assertEqual(loader.get_key("spec"), loader.manifest_spec)
        self.assertEqual(loader.get_key("status"), loader.manifest_status)
        self.assertEqual(loader.get_key(SAMKeys.KIND.value), loader.manifest_kind)
        self.assertIsNone(loader.get_key("bad"))

    def test_invalid_api_version(self):
        """Test that we can load a valid manifest"""
        with self.assertRaises(SAMLoaderError):
            SAMLoader(api_version="bad", manifest=self.good_manifest_text)

    def test_missing_metadata(self):
        """Test that we can load a valid manifest"""

        def test_missing(element: str):
            loader = SAMLoader(api_version=SAMApiVersions.V1.value, manifest=self.good_manifest_text)
            json_data = loader.json_data
            del json_data[element]

            # convert back to yaml
            yaml_data = yaml.dump(json_data)
            with self.assertRaises(SAMLoaderError):
                SAMLoader(api_version=SAMApiVersions.V1.value, manifest=yaml_data)

        for element in ["metadata", "spec"]:
            test_missing(element)
