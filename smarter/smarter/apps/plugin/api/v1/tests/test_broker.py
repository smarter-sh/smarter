# pylint: disable=wrong-import-position
"""Test TestSAM."""

import os
import unittest

from smarter.apps.account.models import Account
from smarter.apps.plugin.manifest.brokers.plugin import SAMPluginBroker
from smarter.common.const import PYTHON_ROOT

from .factories import create_generic_request


class TestSAMPluginBroker(unittest.TestCase):
    """Test TestSAM"""

    def setUp(self):
        """Set up test fixtures."""
        self.path = os.path.join(PYTHON_ROOT, "smarter", "apps", "plugin", "api", "v1", "tests", "data")
        self.good_manifest_path = os.path.join(self.path, "good-manifest.yaml")
        self.invalid_file_format = os.path.join(self.path, "invalid-file-format.yaml")
        # create a test account
        self.account = Account(account_number="1234-5678-9012")
        self.request = create_generic_request()

    def test_valid_manifest(self):
        """Test valid file path and that we can instantiate without errors"""

        SAMPluginBroker(request=self.request, account=self.account, file_path=self.good_manifest_path)
