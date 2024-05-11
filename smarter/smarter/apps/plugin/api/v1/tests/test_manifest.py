# pylint: disable=wrong-import-position
"""Test TestSAM."""

import os
import unittest

from smarter.apps.account.models import Account
from smarter.apps.plugin.manifest.broker import SAMPluginBroker
from smarter.apps.plugin.manifest.const import MANIFEST_KIND
from smarter.common.const import PYTHON_ROOT
from smarter.lib.manifest.enum import SAMApiVersions


class TestSAM(unittest.TestCase):
    """Test TestSAM"""

    def setUp(self):
        """Set up test fixtures."""
        self.path = os.path.join(PYTHON_ROOT, "smarter", "apps", "api", "v1", "tests", "data")
        self.good_manifest_path = os.path.join(self.path, "good-manifest.yaml")
        self.invalid_file_format = os.path.join(self.path, "invalid-file-format.yaml")
        self.account = Account.objects.create(name="Test Account")

    def test_valid_manifest(self):
        """Test valid file path and that we can instantiate with errors"""

        handler = SAMPluginBroker(
            api_version=SAMApiVersions.V1.value, account=self.account, file_path=self.good_manifest_path
        )
        manifest = handler.manifest
        self.assertEqual(manifest.kind, MANIFEST_KIND)
        self.assertEqual(manifest.metadata.name, "ExampleConfiguration")
        self.assertEqual(manifest.metadata.version, "0.2.0")
