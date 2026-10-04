"""Test the Proxy passthrough, :mod:`smarter.apps.proxy.services`."""

import datetime
import socket
from unittest.mock import MagicMock, patch

import httpx
from django.http import StreamingHttpResponse
from django.utils import timezone

from smarter.apps.account.models.budget import SmarterChargeAuthorizationFailed
from smarter.apps.account.tests.factories import admin_user_factory
from smarter.apps.account.utils import smarter_cached_objects
from smarter.apps.proxy.exceptions import (
    ProxyBudgetExceeded,
    ProxyConfigurationError,
    ProxyInactive,
    ProxyNotFound,
    ProxyPathNotAllowed,
    ProxyUpstreamError,
    ProxyUpstreamTimeout,
)
from smarter.apps.proxy.models import Proxy
from smarter.apps.proxy.services import (
    PROXY_RESPONSE_HEADER,
    ProxyForwarder,
    SSEUsageReader,
    Usage,
    check_upstream_host,
    configure_transport,
    extract_usage,
    forwarded_request_headers,
    get_transport,
    is_public_address,
    resolve_proxy,
    returned_response_headers,
)
from smarter.apps.proxy.signals import proxy_request_completed, proxy_request_failed
from smarter.apps.secret.models import Secret
from smarter.apps.secret.tests.factories import secret_factory
from smarter.lib import json

from .base_classes import (
    API_KEY,
    BASE_URL,
    ProxyTestBase,
    get_test_data,
    get_test_text,
    json_response,
    sse_response,
)

CHAT_BODY = json.dumps({"model": "gpt-6-luna", "messages": [{"role": "user", "content": "Hi"}]}).encode()
CALLER_HEADERS = {
    "Authorization": "Bearer smarter-key-of-the-caller",
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Cookie": "sessionid=abc; csrftoken=def",
    "X-Forwarded-For": "10.0.0.1",
    "Host": "platform.smarter.sh",
    "Content-Length": str(len(CHAT_BODY)),
    "Connection": "keep-alive",
    "User-Agent": "OpenAI/Python 1.99.0",
    "X-Stainless-Lang": "python",
}


class TestUsage(ProxyTestBase):
    """Test the reading of token usage from providers' responses."""

    def test_extract_usage(self):
        responses = get_test_data("responses.yaml")
        expected = {
            "openai_chat_completion": Usage(12, 3, 15),
            "openai_responses": Usage(20, 5, 25),
            "anthropic_message": Usage(14, 7, 21),
            "gemini_generate_content": Usage(8, 5, 13),
            "cohere_v1_chat": Usage(6, 4, 10),
            "cohere_v2_chat": Usage(9, 1, 10),
        }
        for name, usage in expected.items():
            with self.subTest(response=name):
                self.assertEqual(extract_usage(responses[name]), usage)

    def test_no_usage(self):
        self.assertIsNone(extract_usage(get_test_data("responses.yaml")["models_list"]))
        self.assertIsNone(extract_usage([1, 2]))
        self.assertIsNone(extract_usage({"usage": {"prompt_tokens": "x"}}))
        self.assertIsNone(extract_usage({"usage": {"prompt_tokens": True}}))

    def test_merge(self):
        self.assertEqual(Usage(25, 1, 26).merge(Usage(0, 15, 0)), Usage(25, 15, 40))
        self.assertEqual(Usage(1, 2, 3).merge(None), Usage(1, 2, 3))
        self.assertFalse(Usage())

    def test_sse_openai(self):
        reader = SSEUsageReader()
        reader.feed(get_test_text("openai-stream.txt"))
        reader.close()
        self.assertEqual(reader.usage, Usage(12, 3, 15))

    def test_sse_anthropic_byte_by_byte(self):
        """Test that events split across chunks are read, and Anthropic's input and output counts are combined."""
        reader = SSEUsageReader()
        for byte in get_test_text("anthropic-stream.txt"):
            reader.feed(bytes([byte]))
        reader.close()
        self.assertEqual(reader.usage, Usage(25, 15, 40))

    def test_sse_garbage(self):
        reader = SSEUsageReader()
        reader.feed(b'data: not json\n\n: comment\nevent: x\ndata: [DONE]\ndata: {"usage": {"total_tokens": 4}}')
        reader.close()
        self.assertEqual(reader.usage.total_tokens, 4)


class TestHeaders(ProxyTestBase):
    """Test the headers that are forwarded to the provider, and returned to the caller."""

    def test_request_headers(self):
        proxy = self.proxy("test_services_headers", headers={"OpenAI-Beta": "assistants=v2", "x-stainless-lang": "go"})
        headers = forwarded_request_headers(proxy, CALLER_HEADERS, API_KEY)
        self.assertEqual(headers["Authorization"], f"Bearer {API_KEY}")
        self.assertEqual(headers["OpenAI-Beta"], "assistants=v2")
        self.assertEqual(headers["x-stainless-lang"], "go")
        self.assertNotIn("X-Stainless-Lang", headers)
        self.assertEqual(headers["Content-Type"], "application/json")
        self.assertEqual(headers["User-Agent"], "OpenAI/Python 1.99.0")
        lowered = {name.lower() for name in headers}
        for dropped in ("cookie", "x-forwarded-for", "host", "content-length", "connection"):
            self.assertNotIn(dropped, lowered)
        self.assertNotIn("smarter-key-of-the-caller", json.dumps(headers))

    def test_request_headers_api_key_header(self):
        """Test that the caller's credentials are removed from every header that SDKs use."""
        proxy = self.proxy("test_services_x_api_key", auth_header="x-api-key", auth_scheme="")
        caller = {"x-api-key": "smarter-key", "x-goog-api-key": "smarter-key", "api-key": "smarter-key"}
        caller["Authorization"] = "Token smarter-key"
        headers = forwarded_request_headers(proxy, caller, API_KEY)
        self.assertEqual(headers, {"x-api-key": API_KEY})

    def test_response_headers(self):
        proxy = self.proxy("test_services_response_headers")
        upstream = httpx.Headers(
            [
                ("content-type", "application/json"),
                ("content-length", "10"),
                ("content-encoding", "gzip"),
                ("set-cookie", "__cf_bm=x"),
                ("x-ratelimit-remaining-requests", "99"),
                ("request-id", "req_1"),
                ("transfer-encoding", "chunked"),
            ]
        )
        headers = dict(returned_response_headers(proxy, upstream))
        self.assertEqual(headers["x-ratelimit-remaining-requests"], "99")
        self.assertEqual(headers["request-id"], "req_1")
        self.assertEqual(headers[PROXY_RESPONSE_HEADER], proxy.name)
        for dropped in ("content-length", "content-encoding", "set-cookie", "transfer-encoding"):
            self.assertNotIn(dropped, headers)


class TestHosts(ProxyTestBase):
    """Test that Proxies cannot reach Smarter's internal network."""

    def test_is_public_address(self):
        self.assertTrue(is_public_address("93.184.215.14"))
        self.assertTrue(is_public_address("2606:4700::6810:84e5"))
        for address in (
            "10.0.0.1",
            "172.16.0.1",
            "192.168.1.1",
            "127.0.0.1",
            "169.254.169.254",
            "::1",
            "fd00::1",
            "0.0.0.0",  # nosec B104 - an address that must be refused, not one that is bound to.
            "100.64.0.1",
            "224.0.0.1",
        ):
            with self.subTest(address=address):
                self.assertFalse(is_public_address(address))

    def test_private_host_refused(self):
        proxy = self.proxy("test_services_private", user_profile=self.non_admin_user_profile)
        with patch("smarter.apps.proxy.services.host_addresses", return_value=["169.254.169.254"]):
            with self.assertRaises(ProxyConfigurationError):
                check_upstream_host(proxy)
        with patch("smarter.apps.proxy.services.host_addresses", return_value=["93.184.215.14", "10.1.2.3"]):
            with self.assertRaises(ProxyConfigurationError):
                check_upstream_host(proxy)

    def test_private_host_superuser(self):
        """Test that a superuser's Proxy may forward to a private address, e.g. an in-cluster LLM."""
        proxy = self.proxy("test_services_superuser_private", base_url="http://10.0.0.5:8000/v1/")
        with patch("smarter.apps.proxy.services.host_addresses", return_value=["10.0.0.5"]):
            check_upstream_host(proxy)

    def test_unresolvable_host(self):
        proxy = self.proxy("test_services_unresolvable", user_profile=self.non_admin_user_profile)
        with patch("smarter.apps.proxy.services.host_addresses", side_effect=socket.gaierror("no such host")):
            with self.assertRaises(ProxyUpstreamError):
                check_upstream_host(proxy)


class TestResolveProxy(ProxyTestBase):
    """Test resolve_proxy(): the user's own Proxy, else their account's, else the built-in one."""

    def test_precedence(self):
        name = "test_services_precedence"
        admin_proxy = self.proxy(name)
        # the account's Proxy, which the admin owns, is resolved for the mortal user.
        self.assertEqual(resolve_proxy(name, self.non_admin_user_profile), admin_proxy)
        own = self.proxy(name, user_profile=self.non_admin_user_profile)
        self.assertEqual(resolve_proxy(name, self.non_admin_user_profile), own)
        self.assertEqual(resolve_proxy(name, self.user_profile), admin_proxy)

    def test_builtin(self):
        """Test that the platform's Proxies are resolved for every account, after the account's own."""
        name = "test_services_builtin"
        builtin = self.proxy(name, user_profile=smarter_cached_objects.smarter_admin_user_profile)
        self.assertEqual(resolve_proxy(name, self.non_admin_user_profile), builtin)
        account = self.proxy(name)
        self.assertEqual(resolve_proxy(name, self.non_admin_user_profile), account)

    def test_not_found(self):
        with self.assertRaises(ProxyNotFound):
            resolve_proxy("test_services_no_such_proxy", self.non_admin_user_profile)

    def test_other_account(self):
        """Test that another account's Proxy is not resolved."""
        _, other_account, other_user_profile = admin_user_factory()
        try:
            self.proxy("test_services_other_account", user_profile=other_user_profile)
            with self.assertRaises(ProxyNotFound):
                resolve_proxy("test_services_other_account", self.non_admin_user_profile)
        finally:
            Proxy.objects.filter(user_profile=other_user_profile).delete()
            other_user = other_user_profile.user
            other_account.delete()
            other_user.delete()


class TestTransport(ProxyTestBase):
    """Test that the unit tests can never call a real provider."""

    def test_refused_in_tests(self):
        configure_transport(None)
        try:
            with self.assertRaises(ProxyConfigurationError):
                get_transport()
        finally:
            configure_transport(self.fake.transport)
        self.assertIsInstance(get_transport(), httpx.MockTransport)


class TestProxyForwarder(ProxyTestBase):
    """Test the forwarding of requests to the provider, and of its responses to the caller."""

    def forward(
        self, proxy: Proxy, path: str = "chat/completions", method: str = "POST", query: str = "", body=CHAT_BODY
    ):
        forwarder = ProxyForwarder(proxy, self.non_admin_user_profile)
        return forwarder.forward(method=method, path=path, query_string=query, headers=CALLER_HEADERS, body=body)

    def connect(self, signal) -> MagicMock:
        receiver = MagicMock()
        signal.connect(receiver, weak=False)
        self.addCleanup(signal.disconnect, receiver)
        return receiver

    def test_forward(self):
        """Test that the request is forwarded as it is, with the provider's API key, and its response returned."""
        completed = self.connect(proxy_request_completed)
        proxy = self.proxy("test_services_forward")
        response = self.forward(proxy, query="api-version=2024-10-21")
        request = self.fake.last_request
        self.assertEqual(request.method, "POST")
        self.assertEqual(str(request.url), BASE_URL + "chat/completions?api-version=2024-10-21")
        self.assertEqual(request.content, CHAT_BODY)
        self.assertEqual(request.headers["authorization"], f"Bearer {API_KEY}")
        self.assertNotIn("cookie", request.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertEqual(response[PROXY_RESPONSE_HEADER], proxy.name)
        self.assertEqual(json.loads(response.content), get_test_data("responses.yaml")["openai_chat_completion"])
        self.record_charges.assert_called_once_with(proxy, self.non_admin_user_profile, Usage(12, 3, 15))
        self.assertEqual(completed.call_args.kwargs["status"], 200)
        self.assertEqual(completed.call_args.kwargs["usage"], Usage(12, 3, 15))

    def test_get_without_body(self):
        proxy = self.proxy("test_services_get")
        self.fake.queue(json_response(get_test_data("responses.yaml")["models_list"]))
        response = self.forward(proxy, path="models", method="GET", body=b"")
        self.assertEqual((self.fake.last_request.method, self.fake.last_request.content), ("GET", b""))
        self.assertEqual(response.status_code, 200)
        self.record_charges.assert_not_called()

    def test_provider_error(self):
        """Test that the provider's error responses are returned as they are, e.g. rate limits."""
        proxy = self.proxy("test_services_provider_error")
        error = {"error": {"message": "Rate limit reached", "type": "requests", "code": "rate_limit_exceeded"}}
        self.fake.queue(json_response(error, status=429, headers={"retry-after": "20"}))
        response = self.forward(proxy)
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response["retry-after"], "20")
        self.assertEqual(json.loads(response.content), error)
        self.record_charges.assert_not_called()

    def test_non_json(self):
        proxy = self.proxy("test_services_audio", allowed_paths=[])
        self.fake.queue(httpx.Response(200, content=b"\x00\x01mp3", headers={"content-type": "audio/mpeg"}))
        response = self.forward(proxy, path="audio/speech")
        self.assertEqual((response.content, response["Content-Type"]), (b"\x00\x01mp3", "audio/mpeg"))

    def test_stream(self):
        """Test that event streams are streamed, and their usage charged when they end."""
        proxy = self.proxy("test_services_stream")
        stream = get_test_text("openai-stream.txt")
        self.fake.queue(sse_response(stream))
        response = self.forward(proxy)
        self.assertIsInstance(response, StreamingHttpResponse)
        self.assertEqual(response["Content-Type"], "text/event-stream")
        self.record_charges.assert_not_called()
        self.assertEqual(b"".join(response.streaming_content), stream)  # type: ignore[arg-type]
        self.record_charges.assert_called_once_with(proxy, self.non_admin_user_profile, Usage(12, 3, 15))

    def test_auth_header(self):
        """Test an Anthropic-style API key header, and a fixed header."""
        proxy = self.proxy(
            "test_services_anthropic",
            auth_header="x-api-key",
            auth_scheme="",
            headers={"anthropic-version": "2023-06-01"},
            allowed_paths=["messages"],
        )
        self.fake.queue(json_response(get_test_data("responses.yaml")["anthropic_message"]))
        self.forward(proxy, path="messages")
        request = self.fake.last_request
        self.assertEqual(request.headers["x-api-key"], API_KEY)
        self.assertEqual(request.headers["anthropic-version"], "2023-06-01")
        self.assertNotIn("authorization", request.headers)
        self.record_charges.assert_called_once_with(proxy, self.non_admin_user_profile, Usage(14, 7, 21))

    def test_inactive(self):
        failed = self.connect(proxy_request_failed)
        with self.assertRaises(ProxyInactive):
            self.forward(self.proxy("test_services_inactive", is_active=False))
        self.assertEqual(self.fake.requests, [])
        self.assertIsInstance(failed.call_args.kwargs["error"], ProxyInactive)

    def test_path_not_allowed(self):
        proxy = self.proxy("test_services_path")
        for path in ("files", "fine_tuning/jobs", "../v2/chat/completions", "chat/completions/../../files"):
            with self.subTest(path=path), self.assertRaises(ProxyPathNotAllowed):
                self.forward(proxy, path=path)
        self.assertEqual(self.fake.requests, [])

    def test_no_api_key(self):
        proxy = self.proxy("test_services_no_key", api_key_secret=None)
        proxy.provider.api_key = None
        with self.assertRaises(ProxyConfigurationError):
            self.forward(proxy)
        self.assertEqual(self.fake.requests, [])

    def test_other_accounts_secret(self):
        """Test that a Proxy cannot send another account's API key, e.g. the platform's."""
        _, other_account, other_user_profile = admin_user_factory()
        try:
            other_secret = secret_factory(other_user_profile, "test_services_other_secret", "test", "sk-other")
            proxy = self.proxy("test_services_other_secret", api_key_secret=other_secret)
            with self.assertRaises(ProxyConfigurationError):
                self.forward(proxy)
            self.assertEqual(self.fake.requests, [])
        finally:
            Proxy.objects.filter(api_key_secret__user_profile=other_user_profile).delete()
            Secret.objects.filter(user_profile=other_user_profile).delete()
            other_user = other_user_profile.user
            other_account.delete()
            other_user.delete()

    def test_expired_secret(self):
        expired = secret_factory(
            self.user_profile,
            "test_services_expired",
            "test",
            "sk-expired",
            expiration=timezone.now() - datetime.timedelta(days=1),
        )
        self.addCleanup(expired.delete)
        with self.assertRaises(ProxyConfigurationError):
            self.forward(self.proxy("test_services_expired", api_key_secret=expired))

    def test_budget_exceeded(self):
        proxy = self.proxy("test_services_budget")
        with patch(
            "smarter.apps.proxy.services.charge_authorization",
            side_effect=SmarterChargeAuthorizationFailed("resource lock"),
        ):
            with self.assertRaises(ProxyBudgetExceeded) as context:
                self.forward(proxy)
        self.assertEqual(context.exception.status, 402)
        self.assertEqual(self.fake.requests, [])

    def test_upstream_timeout(self):
        proxy = self.proxy("test_services_timeout")
        self.fake.queue(httpx.ReadTimeout("timed out"))
        with self.assertRaises(ProxyUpstreamTimeout) as context:
            self.forward(proxy)
        self.assertEqual(context.exception.status, 504)

    def test_upstream_unreachable(self):
        proxy = self.proxy("test_services_unreachable")
        self.fake.queue(httpx.ConnectError("connection refused"))
        with self.assertRaises(ProxyUpstreamError) as context:
            self.forward(proxy)
        self.assertEqual(context.exception.status, 502)
        self.assertEqual(context.exception.to_dict()["error"]["code"], "upstream_unreachable")

    def test_no_redirects(self):
        """Test that the provider's redirects are returned, not followed, so the API key is not sent elsewhere."""
        proxy = self.proxy("test_services_redirect")
        self.fake.queue(httpx.Response(307, headers={"location": "https://evil.example.com/steal"}))
        response = self.forward(proxy)
        self.assertEqual(response.status_code, 307)
        self.assertEqual(len(self.fake.requests), 1)
