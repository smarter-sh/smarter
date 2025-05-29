# pylint: disable=wrong-import-position
"""Test ManifestApiView."""

from http import HTTPStatus

from django.urls import reverse

from .base_class import ApiV1CliTestBase


class TestManifestApiView(ApiV1CliTestBase):
    """Test ManifestApiView"""

    def test_valid_manifest(self):
        """Test that we get OK responses for post, put, patch, delete when passing a valid manifest"""

        path = reverse(self.namespace + "manifest_view", kwargs={"kind": "plugin"})
        _, status = self.get_response(path=path)
        self.assertEqual(status, HTTPStatus.OK)
