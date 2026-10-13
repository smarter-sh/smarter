"""Test the Proxies' list against the Smarter api's OpenAPI document."""

from http import HTTPStatus

from rest_framework.test import APIClient

from smarter.apps.api.v1.contract.tests.mixins import OpenApiResponseMixin
from smarter.apps.proxy.tests.base_classes import ProxyTestBase


class TestProxyOpenApi(OpenApiResponseMixin, ProxyTestBase):
    """The Proxies' list, with a Proxy, against the document."""

    def test_list(self):
        proxy = self.create_proxy("test_proxy_openapi")
        self.addCleanup(proxy.delete)
        client = APIClient()
        client.force_authenticate(user=self.admin_user)
        response = client.get("/api/v1/proxy/")
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content)
        self.assertValidResponse("/proxy/", "get", response.json())
        self.assertIn(proxy.name, [item["name"] for item in response.json()["proxies"]])
