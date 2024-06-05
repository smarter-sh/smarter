# pylint: disable=wrong-import-position
"""Test ManifestApiView."""

from http import HTTPStatus

from django.urls import reverse

from smarter.apps.api.v1.tests.base_class import ApiV1TestBase


class TestManifestApiView(ApiV1TestBase):
    """Test ManifestApiView"""

    def test_valid_manifest(self):
        """Test that we get OK responses for post, put, patch, delete when passing a valid manifest"""

        path = reverse("api_v1_cli_manifest_view", kwargs={"kind": "plugin"})
        response, status = self.get_response(path=path)
        print(response, status)
        self.assertEqual(status, HTTPStatus.OK)
