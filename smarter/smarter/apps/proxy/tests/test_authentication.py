"""Test the authentication of the Proxy passthrough's callers, :mod:`smarter.apps.proxy.authentication`."""

from django.test import RequestFactory
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.request import Request

from smarter.apps.proxy.authentication import SmarterProxyAuthentication, get_api_key
from smarter.lib.drf.models import SmarterAuthToken

from .base_classes import ProxyTestBase


def request(**headers) -> Request:
    """A request with headers, given as request.META keys, e.g. HTTP_X_API_KEY."""
    return Request(RequestFactory().post("/api/v1/proxy/openai/chat/completions", **headers))


class TestGetApiKey(ProxyTestBase):
    """Test that the Smarter API key is read from each SDK's header."""

    def test_headers(self):
        cases = {
            "HTTP_AUTHORIZATION": "Bearer abc",
            "HTTP_X_API_KEY": "abc",
            "HTTP_X_GOOG_API_KEY": "abc",
            "HTTP_API_KEY": "abc",
        }
        for header, value in cases.items():
            with self.subTest(header=header):
                self.assertEqual(get_api_key(request(**{header: value})), "abc")
        self.assertEqual(get_api_key(request(HTTP_AUTHORIZATION="Token abc")), "abc")
        self.assertEqual(get_api_key(request(HTTP_AUTHORIZATION="bearer abc")), "abc")

    def test_precedence(self):
        """Test that the Authorization header takes precedence."""
        self.assertEqual(get_api_key(request(HTTP_AUTHORIZATION="Bearer one", HTTP_X_API_KEY="two")), "one")

    def test_none(self):
        self.assertIsNone(get_api_key(request()))
        self.assertIsNone(get_api_key(request(HTTP_X_API_KEY="  ")))

    def test_malformed(self):
        for value in ("Basic dXNlcjpwYXNz", "Bearer", "Bearer a b"):
            with self.subTest(value=value), self.assertRaises(AuthenticationFailed):
                get_api_key(request(HTTP_AUTHORIZATION=value))


class TestSmarterProxyAuthentication(ProxyTestBase):
    """Test that a Smarter API key authenticates its user, in any SDK's header."""

    def test_authenticate(self):
        key = self.api_key()
        auth = SmarterProxyAuthentication()
        for header in ("HTTP_X_API_KEY", "HTTP_X_GOOG_API_KEY", "HTTP_API_KEY"):
            with self.subTest(header=header):
                user, token = auth.authenticate(request(**{header: key}))  # type: ignore[misc]
                self.assertEqual(user, self.staff_user)
                self.assertIsInstance(token, SmarterAuthToken)
        user, _ = auth.authenticate(request(HTTP_AUTHORIZATION=f"Bearer {key}"))  # type: ignore[misc]
        self.assertEqual(user, self.staff_user)

    def test_no_key(self):
        self.assertIsNone(SmarterProxyAuthentication().authenticate(request()))

    def test_invalid_key(self):
        with self.assertRaises(AuthenticationFailed):
            SmarterProxyAuthentication().authenticate(request(HTTP_X_API_KEY="not-a-smarter-api-key-0123456789"))

    def test_inactive_key(self):
        key = self.api_key()
        SmarterAuthToken.objects.filter(user=self.staff_user, name__startswith="test_proxy_").update(is_active=False)
        with self.assertRaises(AuthenticationFailed):
            SmarterProxyAuthentication().authenticate(request(HTTP_X_API_KEY=key))

    def test_authenticate_header(self):
        self.assertIn("Bearer", SmarterProxyAuthentication().authenticate_header(request()))
