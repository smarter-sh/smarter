"""Test the OpenAPI contract's views in the docs app: :mod:`smarter.apps.docs.views.openapi`."""

import json
from http import HTTPStatus

from django.test import Client

from smarter.apps.api.v1.contract.const import OPENAPI_PATH
from smarter.apps.dashboard.context_processors import sidebar_context
from smarter.apps.docs.urls import DocsReverseNames
from smarter.lib.django.shortcuts import reverse
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestDocsOpenApi(SmarterTestBase):
    """Test the OpenAPI document's json view, its page, and the sidebar's link to the page."""

    def setUp(self):
        super().setUp()
        self.client = Client()

    def test_document(self):
        """The json view serves the committed document, with this platform's server first, anonymously."""
        response = self.client.get(reverse(DocsReverseNames.namespace, DocsReverseNames.openapi_json))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response["Content-Type"], "application/json")
        document = response.json()
        with open(OPENAPI_PATH, encoding="utf-8") as file:
            committed = json.load(file)
        self.assertEqual(document["servers"][0], {"url": "http://testserver/api/v1", "description": "This platform."})
        self.assertEqual(document["servers"][1:], committed["servers"])
        self.assertEqual({**document, "servers": committed["servers"]}, committed)

    def test_page(self):
        """The page renders the document with Scalar, and links to it."""
        response = self.client.get(reverse(DocsReverseNames.namespace, DocsReverseNames.openapi))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        html = response.content.decode()
        json_url = reverse(DocsReverseNames.namespace, DocsReverseNames.openapi_json)
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
