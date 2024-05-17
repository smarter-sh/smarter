# pylint: disable=wrong-import-position
"""Test TestSAM."""

import os
import unittest

from smarter.apps.plugin.manifest.models.plugin.const import MANIFEST_KIND
from smarter.common.const import PYTHON_ROOT
from smarter.lib.manifest.loader import SAMLoader
from smarter.lib.unittest.utils import get_readonly_yaml_file


class TestSAM(unittest.TestCase):
    """Test TestSAM"""

    def setUp(self):
        """Set up test fixtures."""
        self.path = os.path.join(PYTHON_ROOT, "smarter", "apps", "plugin", "api", "v1", "tests", "data")
        self.good_manifest_path = os.path.join(self.path, "good-manifest.yaml")
        self.invalid_file_format = os.path.join(self.path, "invalid-file-format.yaml")

        self.good_manifest = get_readonly_yaml_file(self.good_manifest_path)

    def test_valid_manifest(self):
        """Test valid file path and that we can instantiate with errors"""

        loader = SAMLoader(kind=MANIFEST_KIND, manifest=self.good_manifest)

        self.assertIsNotNone(loader)
        self.assertIsInstance(loader.json_data, dict)
        self.assertIsInstance(loader.yaml_data, str)
        loader.validate_manifest()
        self.assertEqual(loader.manifest_kind, MANIFEST_KIND)
