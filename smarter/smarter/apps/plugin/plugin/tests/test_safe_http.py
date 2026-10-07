# pylint: disable=unused-argument
"""
Unit tests for :py:mod:`smarter.apps.plugin.plugin.safe_http`, which protects the Smarter platform from requests to user-supplied URLs.

.. note::

    **Experimental.** This module was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

import socket
from unittest import mock

import requests

from smarter.apps.plugin.plugin import safe_http
from smarter.common.exceptions import SmarterValueError
from smarter.lib.unittest.base_classes import SmarterTestBase

from .base_classes import (
    SAFE_HTTP_DNS_PATCH,
    SAFE_HTTP_REQUESTS_PATCH,
    FakeWebHost,
    mock_web_host,
)


def resolves_to(address: str):
    """Return a stand-in for socket.getaddrinfo that resolves every host to an address."""

    def getaddrinfo(host, port, *args, **kwargs):
        family = socket.AF_INET6 if ":" in address else socket.AF_INET
        return [(family, socket.SOCK_STREAM, 6, "", (address, port))]

    return getaddrinfo


class TestSafeHttp(SmarterTestBase):
    """Test safe HTTP requests."""

    # =========================================================================
    # validate_public_url()
    # =========================================================================
    def test_public_https_url(self):
        """Test that a public https URL is permitted."""
        with mock.patch(SAFE_HTTP_DNS_PATCH, side_effect=resolves_to("93.184.215.14")):
            safe_http.validate_public_url("https://example.com/page?q=1")
            safe_http.validate_public_url("https://example.com:443/page")

    def test_non_https_urls(self):
        """Test that URLs other than https are rejected, without resolving the host."""
        with mock.patch(SAFE_HTTP_DNS_PATCH) as getaddrinfo:
            for url in ("http://example.com/", "ftp://example.com/", "file:///etc/passwd", "example.com", "https:///a"):
                with self.assertRaises(safe_http.SafeHttpError, msg=f"url={url}"):
                    safe_http.validate_public_url(url)
        getaddrinfo.assert_not_called()

    def test_non_standard_ports(self):
        """Test that ports other than 443 are rejected, e.g. to prevent scanning internal services."""
        with mock.patch(SAFE_HTTP_DNS_PATCH, side_effect=resolves_to("93.184.215.14")):
            for url in ("https://example.com:8443/", "https://example.com:22/", "https://example.com:80/"):
                with self.assertRaises(safe_http.SafeHttpError, msg=f"url={url}"):
                    safe_http.validate_public_url(url)

    def test_invalid_port(self):
        """Test that an invalid port is rejected."""
        with self.assertRaises(safe_http.SafeHttpError):
            safe_http.validate_public_url("https://example.com:99999/")

    def test_credentials(self):
        """Test that URLs containing credentials are rejected."""
        with self.assertRaises(safe_http.SafeHttpError):
            safe_http.validate_public_url("https://user:password@example.com/")

    def test_non_public_addresses(self):
        """Test that hosts resolving to non-public addresses are rejected."""
        for address in ("127.0.0.1", "10.1.2.3", "169.254.169.254", "192.168.0.1", "::1", "fd00::1"):
            with mock.patch(SAFE_HTTP_DNS_PATCH, side_effect=resolves_to(address)):
                with self.assertRaises(safe_http.SafeHttpError, msg=f"address={address}"):
                    safe_http.validate_public_url("https://example.com/")

    def test_unresolvable_host(self):
        """Test that a host that cannot be resolved is rejected."""
        for side_effect in (socket.gaierror("no such host"), lambda *args, **kwargs: []):
            with mock.patch(SAFE_HTTP_DNS_PATCH, side_effect=side_effect):
                with self.assertRaises(safe_http.SafeHttpError):
                    safe_http.validate_public_url("https://no-such-host.example/")

    def test_error_is_a_value_error(self):
        """Test that SafeHttpError is a SmarterValueError, and carries the HTTP status code."""
        self.assertTrue(issubclass(safe_http.SafeHttpError, SmarterValueError))
        self.assertEqual(safe_http.SafeHttpError("x", status_code=404).status_code, 404)

    # =========================================================================
    # fetch()
    # =========================================================================
    def test_fetch(self):
        """Test a successful request, and the response."""
        host = FakeWebHost()
        host.add("https://example.com/a", b"hello", headers={"Content-Type": "Text/HTML; charset=ISO-8859-1"})
        with mock_web_host(host):
            response = safe_http.fetch("https://example.com/a")
        self.assertEqual(response.content, b"hello")
        self.assertEqual(response.url, "https://example.com/a")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, "text/html")
        self.assertEqual(response.charset, "ISO-8859-1")
        self.assertEqual(response.redirects, [])

    def test_fetch_request_options(self):
        """Test that the method, headers, parameters, body and timeout are passed, and redirects are not automatic."""
        host = FakeWebHost()
        host.add("https://api.example.com/search", b"{}")
        with mock_web_host(host):
            safe_http.fetch(
                "https://api.example.com/search",
                method="POST",
                headers={"Authorization": "Bearer x"},
                params={"q": "a"},
                json_body={"query": "a"},
                timeout=7,
            )
        call = host.calls[0]
        self.assertEqual(call["method"], "POST")
        self.assertEqual(call["headers"]["Authorization"], "Bearer x")
        self.assertIn("User-Agent", call["headers"])
        self.assertEqual(call["params"], {"q": "a"})
        self.assertEqual(call["json"], {"query": "a"})
        self.assertEqual(call["timeout"], 7)
        self.assertFalse(call["allow_redirects"])
        self.assertTrue(call["stream"])

    def test_fetch_custom_user_agent(self):
        """Test that a caller's User-Agent replaces the default."""
        host = FakeWebHost()
        host.add("https://example.com/", b"")
        with mock_web_host(host):
            safe_http.fetch("https://example.com/", headers={"User-Agent": "custom"})
        self.assertEqual(host.calls[0]["headers"]["User-Agent"], "custom")

    def test_fetch_status(self):
        """Test that an unaccepted status raises, with its status code, and an accepted one does not."""
        host = FakeWebHost()
        host.add("https://example.com/missing", b"", status_code=404)
        host.add("https://example.com/created", b"ok", status_code=201)
        with mock_web_host(host):
            with self.assertRaises(safe_http.SafeHttpError) as context:
                safe_http.fetch("https://example.com/missing")
            self.assertEqual(context.exception.status_code, 404)
            self.assertEqual(safe_http.fetch("https://example.com/created", accept_status=(201,)).content, b"ok")

    def test_fetch_too_large(self):
        """Test that an oversized response is abandoned."""
        host = FakeWebHost()
        host.add("https://example.com/big", b"x" * 101)
        with mock_web_host(host):
            with self.assertRaises(safe_http.SafeHttpError):
                safe_http.fetch("https://example.com/big", max_bytes=100)

    def test_fetch_redirects(self):
        """Test that redirects are followed and recorded."""
        host = FakeWebHost()
        host.add("https://example.com/old", status_code=301, headers={"Location": "/new"})
        host.add("https://example.com/new", b"new")
        with mock_web_host(host):
            response = safe_http.fetch("https://example.com/old")
        self.assertEqual(response.url, "https://example.com/new")
        self.assertEqual(response.redirects, ["https://example.com/old"])

    def test_fetch_redirect_changes_post_to_get(self):
        """Test that a 303 redirect of a POST becomes a GET, without the body, and a 307 preserves it."""
        for status_code, method in ((303, "GET"), (307, "POST")):
            host = FakeWebHost()
            host.add("https://example.com/a", status_code=status_code, headers={"Location": "/b"})
            host.add("https://example.com/b", b"ok")
            with mock_web_host(host):
                safe_http.fetch("https://example.com/a", method="POST", json_body={"a": 1}, params={"q": 1})
            self.assertEqual(host.calls[1]["method"], method, f"status_code={status_code}")
            self.assertIsNone(host.calls[1]["params"])

    def test_fetch_redirect_policy(self):
        """Test that a caller's redirect policy can refuse a redirect before it is requested."""
        host = FakeWebHost()
        host.add("https://example.com/a", status_code=302, headers={"Location": "https://blocked.example/"})

        def refuse_blocked(url):
            if "blocked.example" in url:
                raise safe_http.SafeHttpError("redirect refused")

        with mock_web_host(host):
            with self.assertRaises(safe_http.SafeHttpError) as context:
                safe_http.fetch("https://example.com/a", redirect_policy=refuse_blocked)
        self.assertIn("redirect refused", str(context.exception))
        self.assertEqual(host.requested, ["https://example.com/a"])

    def test_fetch_redirect_to_http(self):
        """Test that a redirect to plain http is refused."""
        host = FakeWebHost()
        host.add("https://example.com/a", status_code=302, headers={"Location": "http://example.com/a"})
        with mock_web_host(host):
            with self.assertRaises(safe_http.SafeHttpError):
                safe_http.fetch("https://example.com/a")

    def test_fetch_too_many_redirects(self):
        """Test that a redirect loop is abandoned."""
        host = FakeWebHost()
        host.add("https://example.com/a", status_code=302, headers={"Location": "/a"})
        with mock_web_host(host):
            with self.assertRaises(safe_http.SafeHttpError):
                safe_http.fetch("https://example.com/a", max_redirects=2)
        self.assertEqual(len(host.requested), 3)

    def test_fetch_network_error_does_not_disclose_the_url(self):
        """Test that network errors are raised without the full URL, which may contain secrets."""
        with (
            mock.patch(SAFE_HTTP_DNS_PATCH, side_effect=resolves_to("93.184.215.14")),
            mock.patch(
                SAFE_HTTP_REQUESTS_PATCH,
                side_effect=requests.exceptions.ConnectionError("https://api.example.com/?key=s3cret"),
            ),
        ):
            with self.assertRaises(safe_http.SafeHttpError) as context:
                safe_http.fetch("https://api.example.com/", params={"key": "s3cret"})
        self.assertNotIn("s3cret", str(context.exception))
        self.assertIn("api.example.com", str(context.exception))
