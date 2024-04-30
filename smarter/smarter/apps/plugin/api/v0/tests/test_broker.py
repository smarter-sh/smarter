# pylint: disable=wrong-import-position
"""Test TestSAM."""

import os
import unittest

from smarter.apps.plugin.api.v0.manifests.broker import SAMPluginBroker
from smarter.common.const import PYTHON_ROOT


class TestSAMPluginBroker(unittest.TestCase):
    """Test TestSAM"""

    def setUp(self):
        """Set up test fixtures."""
        self.path = os.path.join(PYTHON_ROOT, "smarter", "apps", "plugin", "v0", "tests", "data")
        self.good_manifest_path = os.path.join(self.path, "good-manifest.yaml")
        self.invalid_file_format = os.path.join(self.path, "invalid-file-format.yaml")

    def test_valid_manifest(self):
        """Test valid file path and that we can instantiate without errors"""

        SAMPluginBroker(file_path=self.good_manifest_path)
