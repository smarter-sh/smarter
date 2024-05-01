# pylint: disable=wrong-import-position
"""Test TestSAM."""

import os
import unittest

from smarter.apps.account.models import Account
from smarter.apps.api.v0.manifests.enum import SAMKeys
from smarter.apps.api.v0.manifests.exceptions import SAMValidationError
from smarter.apps.api.v0.manifests.loader import SAMLoader
from smarter.common.const import PYTHON_ROOT


class TestSAMLoader(unittest.TestCase):
    """Test TestSAM"""

    def setUp(self):
        """Set up test fixtures."""
        self.path = os.path.join(PYTHON_ROOT, "smarter", "apps", "api", "v0", "tests", "data")
        self.good_manifest_path = os.path.join(self.path, "good-manifest.yaml")
        self.invalid_file_format = os.path.join(self.path, "invalid-file-format.yaml")
        self.account = Account.objects.create(name="Test Account", description="Test Account Description")

    def test_valid_manifest(self):
        """Test valid file path and that we can instantiate with errors"""

        SAMLoader(account_number=self.account.account_number, file_path=self.good_manifest_path)

    def test_validate(self):
        """Test valid file path and that we can instantiate with errors"""

        loader = SAMLoader(account_number=self.account.account_number, file_path=self.good_manifest_path)
        loader.validate_manifest()

    def test_valid_manifest_properties(self):
        """Test valid file path and that we can instantiate with errors"""

        loader = SAMLoader(account_number=self.account.account_number, file_path=self.good_manifest_path)
        sam = loader
        self.assertTrue(sam.specification is not None, f"sam.specification is {sam.specification}")
        self.assertTrue(isinstance(sam.specification, dict), f"sam.specification is {type(sam.specification)}")
        self.assertTrue(sam.json_data is None, f"sam.json_data is {sam.json_data}")
        self.assertTrue(sam.yaml_data is not None, f"sam.yaml_data is {sam.yaml_data}")
        self.assertTrue(isinstance(sam.yaml_data, dict), f"sam.yaml_data is {type(sam.yaml_data)}")
        self.assertTrue(sam.data is not None, f"sam.data is {sam.data}")
        self.assertTrue(isinstance(sam.data, dict), f"sam.data is {type(sam.data)}")
        self.assertTrue(sam.formatted_data is not None, f"sam.formatted_data is {sam.formatted_data}")
        self.assertTrue(isinstance(sam.formatted_data, str), f"sam.formatted_data is {type(sam.formatted_data)}")

        apiVersion = sam.get_key(key=SAMKeys.APIVERSION.value)
        self.assertEqual(apiVersion, "smarter/v0", f"sam.get_key(key=SAMKeys.APIVERSION) is {apiVersion}")
        self.assertEqual(sam.data_format.value, "yaml", f"sam.data_format.value is {sam.data_format.value}")
        self.assertEqual(
            sam.manifest_metadata_keys,
            ["name", "description", "version", "tags", "annotations"],
            f"sam.manifest_metadata_keys is {sam.manifest_metadata_keys}",
        )
        kind = sam.get_key(key=SAMKeys.KIND.value)
        self.assertEqual(kind, "Plugin", f"sam.manifest_kind is {kind}")
        self.assertEqual(sam.manifest_spec_keys, [], f"sam.manifest_spec_keys is {sam.manifest_spec_keys}")
        self.assertTrue(isinstance(sam.manifest_spec, dict), f"sam.manifest_spec() is {type(sam.manifest_spec)}")
        self.assertEqual(sam.manifest_status_keys, [], f"sam.manifest_status_keys is {sam.manifest_status_keys}")
        self.assertTrue(sam.manifest_status is None, f"sam.manifest_status() is {sam.manifest_status}")

    def test_get_key(self):
        """Test valid file path and that we can instantiate with errors"""

        loader = SAMLoader(account_number=self.account.account_number, file_path=self.good_manifest_path)
        sam = loader
        self.assertEqual(sam.get_key("apiVersion"), "smarter/v0")
        self.assertEqual(sam.get_key("kind"), "Plugin")
        self.assertEqual(sam.get_key("metadata"), sam.manifest_metadata)

    def test_missing_apiversion(self):
        """Test valid file path and that we can instantiate with errors"""

        loader = SAMLoader(account_number=self.account.account_number, file_path=self.good_manifest_path)
        sam = loader
        sam.data.pop("apiVersion")
        try:
            sam.validate_manifest()
        except SAMValidationError as e:
            self.assertEqual(str(e), "Missing required key apiVersion")
        else:
            self.fail("SAMValidationError not raised")

    def test_unknown_kind(self):
        """Test valid file path and that we can instantiate with errors"""

        loader = SAMLoader(account_number=self.account.account_number, file_path=self.good_manifest_path)
        sam = loader
        sam.data["kind"] = "WrongKind"
        try:
            sam.validate_manifest()
        except SAMValidationError as e:
            self.assertEqual(
                str(e),
                "Invalid value WrongKind for key kind. Expected one of ['Plugin', 'Account', 'User', 'Chat', 'Chatbot']",
            )
        else:
            self.fail("SAMValidationError not raised")

    def test_invalid_file_format(self):
        """Test that a validation error is raised for an invalid file format"""

        try:
            SAMLoader(account_number=self.account.account_number, file_path=self.invalid_file_format)
        except SAMValidationError as e:
            self.assertEqual(str(e), "Invalid data format. Supported formats: json, yaml")
        else:
            self.fail("SAMValidationError not raised")
