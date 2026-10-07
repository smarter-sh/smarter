"""Test the Proxy passthrough's api, :mod:`smarter.apps.proxy.api.v1.views`, end to end."""

from http import HTTPStatus

import httpx
from django.test import Client
from django.urls import reverse

from smarter.apps.proxy.api.v1.urls import ProxyApiV1ReverseViews as Names
from smarter.apps.proxy.services import PROXY_RESPONSE_HEADER, Usage
from smarter.lib import json

from .base_classes import API_KEY, BASE_URL, ProxyTestBase, get_test_text, sse_response

CHAT = {"model": "gpt-6-luna", "messages": [{"role": "user", "content": "Hi"}]}


def url(name: str, path: str = "") -> str:
    """The passthrough URL of a Proxy, and a path."""
    if path:
        return reverse(f"{Names.namespace}:{Names.passthrough}", kwargs={"name": name, "path": path})
    return reverse(f"{Names.namespace}:{Names.passthrough_root}", kwargs={"name": name})


class TestProxyPassthroughApi(ProxyTestBase):
    """Test the passthrough, as a provider's SDK calls it."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_proxy = cls.create_proxy("test_api_proxy")

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.key = self.api_key()

    def post(self, path: str = "chat/completions", name: str = "test_api_proxy", data=None, **headers):
        return self.client.post(
            url(name, path), data=json.dumps(data or CHAT), content_type="application/json", **headers
        )

    def test_openai_sdk(self):
        """Test a chat completion, with the Smarter API key as an OpenAI SDK sends it."""
        response = self.post(HTTP_AUTHORIZATION=f"Bearer {self.key}")
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content)
        self.assertEqual(json.loads(response.content)["usage"]["total_tokens"], 15)
        self.assertEqual(response[PROXY_RESPONSE_HEADER], "test_api_proxy")
        request = self.fake.last_request
        self.assertEqual(str(request.url), BASE_URL + "chat/completions")
        self.assertEqual(request.headers["authorization"], f"Bearer {API_KEY}")
        self.assertNotIn(self.key, str(request.headers))
        self.assertEqual(json.loads(request.content), CHAT)
        self.record_charges.assert_called_once_with(self.test_proxy, self.staff_user_profile, Usage(12, 3, 15))

    def test_other_sdks(self):
        """Test the Smarter API key as the Anthropic, Gemini and Azure OpenAI SDKs send it, and as Smarter's CLI does."""
        for headers in (
            {"HTTP_X_API_KEY": self.key},
            {"HTTP_X_GOOG_API_KEY": self.key},
            {"HTTP_API_KEY": self.key},
            {"HTTP_AUTHORIZATION": f"Token {self.key}"},
        ):
            with self.subTest(headers=list(headers)):
                response = self.post(**headers)
                self.assertEqual(response.status_code, HTTPStatus.OK, response.content)
                self.assertNotIn(self.key, str(self.fake.last_request.headers))

    def test_query_string_and_methods(self):
        response = self.client.get(url("test_api_proxy", "models/gpt-6-luna") + "?limit=1", HTTP_X_API_KEY=self.key)
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content)
        self.assertEqual(self.fake.last_request.method, "GET")
        self.assertEqual(str(self.fake.last_request.url), BASE_URL + "models/gpt-6-luna?limit=1")
        response = self.client.delete(url("test_api_proxy", "models/ft-x"), HTTP_X_API_KEY=self.key)
        self.assertEqual((response.status_code, self.fake.last_request.method), (HTTPStatus.OK, "DELETE"))

    def test_stream(self):
        stream = get_test_text("anthropic-stream.txt")
        self.fake.queue(sse_response(stream))
        response = self.post(HTTP_X_API_KEY=self.key, data={**CHAT, "stream": True})
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(b"".join(response.streaming_content), stream)  # type: ignore[attr-defined]
        self.record_charges.assert_called_once_with(self.test_proxy, self.staff_user_profile, Usage(25, 15, 40))

    def test_unauthenticated(self):
        response = self.post()
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertIn("Bearer", response["WWW-Authenticate"])
        self.assertEqual(
            self.post(HTTP_AUTHORIZATION="Bearer not-a-smarter-key-0123456789").status_code, HTTPStatus.UNAUTHORIZED
        )
        self.assertEqual(self.post(HTTP_AUTHORIZATION="Basic dXNlcjpwYXNz").status_code, HTTPStatus.UNAUTHORIZED)
        self.assertEqual(self.fake.requests, [])

    def test_session_not_accepted(self):
        """Test that the web console's session does not authenticate, so that other sites cannot use it."""
        self.client.force_login(self.staff_user)
        self.assertEqual(self.post().status_code, HTTPStatus.UNAUTHORIZED)
        self.assertEqual(self.fake.requests, [])

    def test_errors(self):
        """Test Smarter's own errors, in the shape that SDKs report."""
        response = self.post(name="test_api_no_such_proxy", HTTP_X_API_KEY=self.key)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        error = json.loads(response.content)["error"]
        self.assertEqual((error["type"], error["code"]), ("smarter_proxy_error", "proxy_not_found"))
        response = self.post(path="files", HTTP_X_API_KEY=self.key)
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        self.assertEqual(json.loads(response.content)["error"]["code"], "path_not_allowed")
        response = self.client.get(url("test_api_proxy"), HTTP_X_API_KEY=self.key)
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        self.assertEqual(self.fake.requests, [])

    def test_provider_error_passthrough(self):
        self.fake.queue(httpx.Response(401, json={"error": {"message": "Incorrect API key"}}))
        response = self.post(HTTP_X_API_KEY=self.key)
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertEqual(json.loads(response.content)["error"]["message"], "Incorrect API key")


class TestProxyListApi(ProxyTestBase):
    """Test the list of the Proxies that a caller may use."""

    def test_list(self):
        self.proxy("test_api_list_proxy")
        key = self.api_key()
        response = Client().get(reverse(f"{Names.namespace}:{Names.list_view}"), HTTP_AUTHORIZATION=f"Bearer {key}")
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content)
        proxies = {proxy["name"]: proxy for proxy in json.loads(response.content)["proxies"]}
        proxy = proxies["test_api_list_proxy"]
        self.assertTrue(proxy["url"].endswith("/api/v1/proxy/test_api_list_proxy/"))
        self.assertEqual(proxy["upstreamUrl"], BASE_URL)
        self.assertEqual(proxy["provider"], self.provider.name)
        self.assertNotIn(API_KEY, response.content.decode())

    def test_unauthenticated(self):
        response = Client().get(reverse(f"{Names.namespace}:{Names.list_view}"))
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
