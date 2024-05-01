# pylint: disable=wrong-import-position
"""Test ManifestApiView."""

import os

from django.test import Client, TestCase
from django.urls import reverse

from smarter.apps.account.models import Account
from smarter.common.const import PYTHON_ROOT


class TestManifestApiView(TestCase):
    """Test ManifestApiView"""

    def setUp(self):
        """Set up test fixtures."""
        self.path = os.path.join(PYTHON_ROOT, "smarter", "apps", "api", "v0", "tests", "data")
        self.good_manifest_path = os.path.join(self.path, "good-manifest.yaml")

        self.account = Account.objects.create(name="Test Account", description="Test Account Description")
        with open(self.good_manifest_path, encoding="utf-8") as file:
            self.good_manifest_text = file.read()

        self.client = Client()
        self.url = reverse("manifest_view")

    def test_valid_manifest(self):
        """Test that we get OK responses for post, put, patch, delete when passing a valid manifest"""

        response = self.client.post(self.url, data=self.good_manifest_text)
        self.assertEqual(response.status_code, 200)

        response = self.client.put(self.url, data=self.good_manifest_text)
        self.assertEqual(response.status_code, 200)

        response = self.client.patch(self.url, data=self.good_manifest_text)
        self.assertEqual(response.status_code, 200)

        response = self.client.delete(self.url, data=self.good_manifest_text)
        self.assertEqual(response.status_code, 200)
