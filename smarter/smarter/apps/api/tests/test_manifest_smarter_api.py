# pylint: disable=wrong-import-position
"""Test TestSAM."""

import os

# python stuff
import unittest

from smarter.apps.api.v0.manifests import SAM
from smarter.common.const import PYTHON_ROOT


# pylint: disable=too-many-instance-attributes
class TestSAM(unittest.TestCase):
    """Test TestSAM"""

    def setUp(self):
        """Set up test fixtures."""
        self.good_manifest_path = os.path.join(
            PYTHON_ROOT, "smarter", "apps", "api", "tests", "data", "good-manifest.yaml"
        )
        print(self.good_manifest_path)

    def test_valid_manifest(self):
        """Test valid file path and that we can instantiate with errors"""

        SAM(file_path=self.good_manifest_path)

    def test_validate(self):
        """Test valid file path and that we can instantiate with errors"""

        sam = SAM(file_path=self.good_manifest_path)
        sam.validate()

    def test_valid_manifest_properties(self):
        """Test valid file path and that we can instantiate with errors"""

        sam = SAM(file_path=self.good_manifest_path)
        self.assertTrue(sam.specification is not None, f"sam.specification is {sam.specification}")
        self.assertTrue(isinstance(sam.specification, dict), f"sam.specification is {type(sam.specification)}")
        self.assertTrue(sam.json_data is None, f"sam.json_data is {sam.json_data}")
        self.assertTrue(sam.yaml_data is not None, f"sam.yaml_data is {sam.yaml_data}")
        self.assertTrue(isinstance(sam.yaml_data, dict), f"sam.yaml_data is {type(sam.yaml_data)}")
        self.assertTrue(sam.data is not None, f"sam.data is {sam.data}")
        self.assertTrue(isinstance(sam.data, dict), f"sam.data is {type(sam.data)}")
        self.assertTrue(sam.formatted_data is not None, f"sam.formatted_data is {sam.formatted_data}")
        self.assertTrue(isinstance(sam.formatted_data, str), f"sam.formatted_data is {type(sam.formatted_data)}")

        self.assertEqual(
            sam.manifest_api_version, "smarter/v0", f"sam.manifest_api_version is {sam.manifest_api_version}"
        )
        self.assertEqual(sam.data_format.value, "yaml", f"sam.data_format.value is {sam.data_format.value}")
        self.assertEqual(
            sam.manifest_metadata_keys,
            ["name", "description", "version", "tags", "annotations"],
            f"sam.manifest_metadata_keys is {sam.manifest_metadata_keys}",
        )
        self.assertEqual(sam.manifest_kind, "Plugin", f"sam.manifest_kind is {sam.manifest_kind}")
        self.assertEqual(sam.manifest_spec_keys, [], f"sam.manifest_spec_keys is {sam.manifest_spec_keys}")
        self.assertTrue(isinstance(sam.manifest_spec(), dict), f"sam.manifest_spec() is {type(sam.manifest_spec())}")
        self.assertEqual(sam.manifest_status_keys, [], f"sam.manifest_status_keys is {sam.manifest_status_keys}")
        self.assertTrue(sam.manifest_status() is None, f"sam.manifest_status() is {sam.manifest_status()}")

    def test_get_key(self):
        """Test valid file path and that we can instantiate with errors"""

        sam = SAM(file_path=self.good_manifest_path)
        self.assertEqual(sam.get_key("apiVersion"), "smarter/v0")
        self.assertEqual(sam.get_key("kind"), "Plugin")
        self.assertEqual(sam.get_key("metadata"), sam.manifest_metadata())
