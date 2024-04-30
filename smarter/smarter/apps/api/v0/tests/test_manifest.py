# pylint: disable=wrong-import-position
"""Test TestSAM."""

import os
import unittest

from smarter.apps.api.v0.manifests.broker import SAMBroker
from smarter.apps.api.v0.manifests.version import SMARTER_API_VERSION
from smarter.common.const import PYTHON_ROOT


class TestSAM(unittest.TestCase):
    """Test TestSAM"""

    def setUp(self):
        """Set up test fixtures."""
        self.path = os.path.join(PYTHON_ROOT, "smarter", "apps", "api", "v0", "tests", "data")
        self.good_manifest_path = os.path.join(self.path, "good-manifest.yaml")
        self.invalid_file_format = os.path.join(self.path, "invalid-file-format.yaml")

    def test_valid_manifest(self):
        """Test valid file path and that we can instantiate with errors"""

        handler = SAMBroker(file_path=self.good_manifest_path)
        manifest = handler.manifest
        self.assertEqual(manifest.apiVersion, SMARTER_API_VERSION)
        self.assertEqual(manifest.kind, "Plugin")
        self.assertEqual(manifest.metadata.name, "ExampleConfiguration")
        self.assertEqual(manifest.metadata.version, "0.2.0")
