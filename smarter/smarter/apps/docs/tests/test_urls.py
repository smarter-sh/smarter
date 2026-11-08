"""Test the docs app's urls: :mod:`smarter.apps.docs.urls`."""

from http import HTTPStatus

from django.test import Client

from smarter.apps.docs.urls import DocsReverseNames
from smarter.lib.django.shortcuts import reverse
from smarter.lib.unittest.base_classes import SmarterTestBase

DOCS = DocsReverseNames.namespace


class TestDocsUrls(SmarterTestBase):
    """Test the docs app's paths, which the sidebar, the sitemap and the smarter cli's help link to."""

    def setUp(self) -> None:
        super().setUp()
        self.client = Client()

    def test_paths(self) -> None:
        """Each page keeps the path that it had before the console showed it."""
        self.assertEqual(reverse(DOCS, DocsReverseNames.example_manifests), "/docs/manifests/")
        self.assertEqual(reverse(DOCS, DocsReverseNames.json_schemas), "/docs/json-schemas/")
        self.assertEqual(reverse(DOCS, DocsReverseNames.openapi), "/docs/openapi/")
        self.assertEqual(reverse(DOCS, DocsReverseNames.openapi_json), "/docs/openapi.json")
        manifest = reverse(f"{DOCS}:{DocsReverseNames.example_manifest}", kwargs={"kind": "llmclient"})
        self.assertEqual(manifest, "/docs/manifest/llmclient/")
        schema = reverse(f"{DOCS}:{DocsReverseNames.json_schema}", kwargs={"kind": "llmclient"})
        self.assertEqual(schema, "/docs/json-schema/llmclient/")

    def test_home_redirects_to_the_example_manifests(self) -> None:
        """/docs/ redirects to the example manifests."""
        response = self.client.get("/docs/")
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertEqual(response["Location"], "/docs/manifests/")

    def test_drf_yasg_pages_are_gone(self) -> None:
        """The Swagger and Redoc pages that drf-yasg generated were replaced by the OpenAPI contract."""
        for path in ("/docs/swagger/", "/docs/swagger.json", "/docs/swagger.yaml", "/docs/redoc/"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND, path)
