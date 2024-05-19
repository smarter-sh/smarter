# pylint: disable=wrong-import-position
"""Test TestSAM."""

import os
import unittest

import yaml

from smarter.apps.account.models import Account
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.common.const import PYTHON_ROOT
from smarter.lib.manifest.enum import SAMApiVersions, SAMKeys
from smarter.lib.manifest.loader import SAMLoader, SAMLoaderError

from ..version import SMARTER_API_VERSION


class TestSAMLoader(unittest.TestCase):
    """Test TestSAM"""

    def setUp(self):
        """Set up test fixtures."""
        self.path = os.path.join(PYTHON_ROOT, "smarter", "apps", "api", "v1", "manifests", "tests", "data")
        self.good_manifest_path = os.path.join(self.path, "good-manifest.yaml")
        self.invalid_file_format = os.path.join(self.path, "invalid-file-format.yaml")
        self.account = Account.objects.create(
            company_name="Test Company",
            phone_number="1234567890",
            address1="123 Test St",
            address2="Apt 1",
            city="Test City",
            state="TX",
            postal_code="12345",
        )

    def test_valid_manifest(self):
        """Test valid file path and that we can instantiate with errors"""

        SAMLoader(
            api_version=SMARTER_API_VERSION,
            kind=SAMKinds.PLUGIN.value,
            file_path=self.good_manifest_path,
        )

    def test_validate(self):
        """Test valid file path and that we can instantiate with errors"""

        loader = SAMLoader(
            api_version=SMARTER_API_VERSION,
            kind=SAMKinds.PLUGIN.value,
            file_path=self.good_manifest_path,
        )
        loader.validate_manifest()

    def test_valid_manifest_properties(self):
        """Test valid file path and that we can instantiate with errors"""

        loader = SAMLoader(
            api_version=SMARTER_API_VERSION,
            kind=SAMKinds.PLUGIN.value,
            file_path=self.good_manifest_path,
        )
        sam = loader
        self.assertTrue(sam.specification is not None, f"sam.specification is {sam.specification}")
        self.assertTrue(isinstance(sam.specification, dict), f"sam.specification is {type(sam.specification)}")
        self.assertTrue(sam.json_data is not None, "sam.json_data is None")
        self.assertTrue(sam.yaml_data is not None, "sam.yaml_data is None")
        self.assertTrue(isinstance(sam.yaml_data, str), f"sam.yaml_data is {type(sam.yaml_data)}")
        self.assertTrue(sam.json_data is not None, f"sam.data is {sam.json_data}")
        self.assertIsInstance(sam.json_data, dict, f"sam.data is {type(sam.json_data)}")
        self.assertTrue(isinstance(sam.json_data, dict), f"sam.data is {type(sam.json_data)}")
        self.assertTrue(sam.formatted_data is not None, f"sam.formatted_data is {sam.formatted_data}")
        self.assertTrue(isinstance(sam.formatted_data, str), f"sam.formatted_data is {type(sam.formatted_data)}")

        apiVersion = sam.get_key(key=SAMKeys.APIVERSION.value)
        self.assertEqual(apiVersion, SAMApiVersions.V1.value, f"sam.get_key(key=SAMKeys.APIVERSION) is {apiVersion}")
        self.assertEqual(sam.data_format.value, "yaml", f"sam.data_format.value is {sam.data_format.value}")
        self.assertEqual(
            sam.manifest_metadata_keys,
            ["name", "description", "version", "tags", "annotations"],
            f"sam.manifest_metadata_keys is {sam.manifest_metadata_keys}",
        )
        kind = sam.get_key(key=SAMKeys.KIND.value)
        self.assertEqual(kind, SAMKinds.PLUGIN.value, f"sam.manifest_kind is {kind}")
        self.assertEqual(sam.manifest_spec_keys, [], f"sam.manifest_spec_keys is {sam.manifest_spec_keys}")
        self.assertTrue(isinstance(sam.manifest_spec, dict), f"sam.manifest_spec() is {type(sam.manifest_spec)}")
        self.assertEqual(sam.manifest_status_keys, [], f"sam.manifest_status_keys is {sam.manifest_status_keys}")
        self.assertTrue(sam.manifest_status is None, f"sam.manifest_status() is {sam.manifest_status}")

    def test_get_key(self):
        """Test valid file path and that we can instantiate with errors"""

        loader = SAMLoader(
            api_version=SMARTER_API_VERSION,
            kind=SAMKinds.PLUGIN.value,
            file_path=self.good_manifest_path,
        )
        sam = loader
        self.assertEqual(sam.get_key("apiVersion"), SAMApiVersions.V1.value)
        self.assertEqual(sam.get_key("kind"), SAMKinds.PLUGIN.value)
        self.assertEqual(sam.get_key("metadata"), sam.manifest_metadata)

    def test_missing_apiversion(self):
        """Test valid file path and that we can instantiate with errors"""

        loader = SAMLoader(
            api_version=SMARTER_API_VERSION,
            kind=SAMKinds.PLUGIN.value,
            file_path=self.good_manifest_path,
        )
        sam = loader
        bad_json = sam.json_data
        bad_json.pop("apiVersion")
        bad_yaml = yaml.dump(bad_json)
        try:
            bad_loader = SAMLoader(
                api_version=SMARTER_API_VERSION,
                kind=SAMKinds.PLUGIN.value,
                manifest=bad_yaml,
            )
            bad_loader.validate_manifest()
        except SAMLoaderError as e:
            self.assertEqual(str(e), "Smarter API Manifest Loader Error: Missing required key apiVersion")
        else:
            self.fail("SAMValidationError not raised")

    def test_unknown_kind(self):
        """Test valid file path and that we can instantiate with errors"""

        try:
            SAMLoader(
                api_version=SMARTER_API_VERSION,
                kind="bad_kind",
                file_path=self.good_manifest_path,
            )
        except SAMLoaderError as e:
            self.assertEqual(
                str(e),
                "Smarter API Manifest Loader Error: Invalid value for key kind. Expected bad_kind but got Plugin",
            )
        else:
            self.fail("SAMValidationError not raised")

    def test_invalid_file_format(self):
        """Test that a validation error is raised for an invalid file format"""

        try:
            SAMLoader(
                api_version=SMARTER_API_VERSION,
                kind=SAMKinds.PLUGIN.value,
                manifest=self.invalid_file_format,
            )
        except SAMLoaderError as e:
            self.assertEqual(
                str(e), "Smarter API Manifest Loader Error: Invalid data format. Expected dict but got <class 'str'>"
            )
        else:
            self.fail("SAMValidationError not raised")
