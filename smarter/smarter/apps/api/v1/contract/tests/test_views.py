"""Test the api's OpenAPI document view: :mod:`smarter.apps.api.v1.contract.views`."""

import json
from http import HTTPStatus

from django.test import Client

from smarter.apps.api.v1.contract.const import OPENAPI_PATH
from smarter.apps.api.v1.urls import ApiV1ReverseNames
from smarter.lib.django.shortcuts import reverse
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestApiV1OpenApiJsonView(SmarterTestBase):
    """Test GET /api/v1/openapi.json."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.url = reverse(ApiV1ReverseNames.namespace, ApiV1ReverseNames.openapi_json)

    def test_url(self):
        """The document is at /api/v1/openapi.json."""
        self.assertEqual(self.url, "/api/v1/openapi.json")

    def test_document(self):
        """It serves the committed document, with this platform's server first, anonymously."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response["Content-Type"], "application/json")
        document = response.json()
        with open(OPENAPI_PATH, encoding="utf-8") as file:
            committed = json.load(file)
        this_platform = {"url": "http://testserver/api/v1", "description": "This platform."}
        self.assertEqual(document["servers"][0], this_platform)
        self.assertEqual(document["servers"][1:], committed["servers"])
        self.assertEqual({**document, "servers": committed["servers"]}, committed)
