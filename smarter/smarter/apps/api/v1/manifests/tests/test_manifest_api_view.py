# pylint: disable=wrong-import-position
"""Test ManifestApiView."""

from http import HTTPStatus

from django.urls import reverse

from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews

from .base_class import ApiV1CliTestBase


class TestManifestApiView(ApiV1CliTestBase):
    """Test ManifestApiView"""

    def test_valid_manifest(self):
        """Test that we get OK responses for post, put, patch, delete when passing a valid manifest"""

        path = reverse(self.namespace + ApiV1CliReverseViews.example_manifest, kwargs={"kind": "plugin"})
        _, status = self.get_response(path=path)
        self.assertEqual(status, HTTPStatus.OK)
