# pylint: disable=wrong-import-position
"""Test TestSAM."""

import os
import unittest

from smarter.apps.plugin.manifest.models.plugin.const import MANIFEST_KIND
from smarter.common.const import PYTHON_ROOT
from smarter.lib.manifest.enum import SAMApiVersions
from smarter.lib.manifest.loader import SAMLoader


class TestSAM(unittest.TestCase):
    """Test TestSAM"""

    def setUp(self):
        """Set up test fixtures."""
        self.path = os.path.join(PYTHON_ROOT, "smarter", "apps", "plugin", "api", "v1", "tests", "data")
        self.good_manifest_path = os.path.join(self.path, "good-manifest.yaml")
        self.invalid_file_format = os.path.join(self.path, "invalid-file-format.yaml")

        with open(self.good_manifest_path, encoding="utf-8") as file:
            self.good_manifest = file.read()

    def test_valid_manifest(self):
        """Test valid file path and that we can instantiate with errors"""

        loader = SAMLoader(api_version=SAMApiVersions.V1.value, kind=MANIFEST_KIND, manifest=self.good_manifest)

        self.assertIsNotNone(loader)
        self.assertIsInstance(loader.json_data, dict)
        self.assertIsInstance(loader.yaml_data, str)
        loader.validate_manifest()
        self.assertEqual(loader.manifest_kind, MANIFEST_KIND)
