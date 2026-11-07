"""Test the OpenAPI contract's views in the docs app: :mod:`smarter.apps.docs.views.openapi`."""

from http import HTTPStatus

from django.test import Client

from smarter.apps.api.v1.urls import ApiV1ReverseNames
from smarter.apps.dashboard.context_processors import sidebar_context
from smarter.apps.docs.urls import DocsReverseNames
from smarter.lib.django.shortcuts import reverse
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestDocsOpenApi(SmarterTestBase):
    """Test the OpenAPI document's earlier url, its page, and the sidebar's link to the page."""

    def setUp(self):
        super().setUp()
        self.client = Client()

    def test_document_redirects_to_the_api(self):
        """The document's earlier url redirects, permanently and with its query string, to the api's."""
        url = reverse(DocsReverseNames.namespace, DocsReverseNames.openapi_json)
        response = self.client.get(url + "?download=1")
        self.assertEqual(response.status_code, HTTPStatus.MOVED_PERMANENTLY)
        self.assertEqual(response["Location"], "/api/v1/openapi.json?download=1")

    def test_page(self):
        """The page renders the document with Scalar, and links to it."""
        response = self.client.get(reverse(DocsReverseNames.namespace, DocsReverseNames.openapi))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        html = response.content.decode()
        json_url = reverse(ApiV1ReverseNames.namespace, ApiV1ReverseNames.openapi_json)
        self.assertIn(f'url: "{json_url}"', html)
        self.assertIn("assets/plugins/custom/scalar/standalone.js", html)
        # Scalar calls none of its own services: see static/assets/plugins/custom/scalar/README.md.
        for setting in (
            'proxyUrl: ""',
            "telemetry: false",
            "withDefaultFonts: false",
            'showDeveloperTools: "never"',
            "agent: { disabled: true }",
        ):
            self.assertIn(setting, html)
        self.assertIn("Download openapi.json", html)

    def test_sidebar(self):
        """The web console's sidebar links to the page."""
        sidebar_context.invalidate()
        self.assertEqual(
            sidebar_context()["sidebar"]["openapi"], reverse(DocsReverseNames.namespace, DocsReverseNames.openapi)
        )
