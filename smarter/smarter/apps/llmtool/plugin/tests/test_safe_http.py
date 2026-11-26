# pylint: disable=unused-argument
"""
Unit tests for :py:mod:`smarter.apps.llmtool.plugin.safe_http`, which protects the Smarter platform from requests to user-supplied URLs.

.. note::

    **Experimental.** This module was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

import socket
from typing import Optional
from unittest import mock

import requests
from cache_results import lazy_cache

from smarter.apps.llmtool.plugin import safe_http
from smarter.common.const import SmarterEnvironments
from smarter.common.exceptions import SmarterValueError
from smarter.lib.unittest.base_classes import SmarterTestBase

from .base_classes import (
    SAFE_HTTP_DNS_PATCH,
    SAFE_HTTP_REQUESTS_PATCH,
    SAFE_HTTP_SETTINGS_PATCH,
    FakeWebHost,
    mock_web_host,
    resolves_to,
)


class TestSafeHttp(SmarterTestBase):
    """Test safe HTTP requests."""

    def setUp(self):
        super().setUp()
        # safe_http caches responses, and these tests serve different content at the same urls.
        lazy_cache.clear()

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
        side_effect: object
        for side_effect in (socket.gaierror("no such host"), lambda *args, **kwargs: []):
            with mock.patch(SAFE_HTTP_DNS_PATCH, side_effect=side_effect):
                with self.assertRaises(safe_http.SafeHttpError):
                    safe_http.validate_public_url("https://no-such-host.example/")

    def test_is_loopback_host(self):
        """Localhost, its subdomains, the local hosts of SmarterValidator and loopback addresses are loopback hosts."""
        host: Optional[str]
        for host in (
            "localhost",
            "LOCALHOST",
            "localhost.",
            "api.localhost",
            "127.0.0.1",
            "127.8.9.10",
            "::1",
            "[::1]",
            "testserver",
        ):
            with self.subTest(host=host):
                self.assertTrue(safe_http.is_loopback_host(host))
        for host in (None, "", "example.com", "localhost.example.com", "10.0.0.1", "169.254.169.254", "8.8.8.8"):
            with self.subTest(host=host):
                self.assertFalse(safe_http.is_loopback_host(host))

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

    def test_fetch_redirect_to_another_origin_drops_credentials(self):
        """Test that a redirect to another host doesn't carry the caller's credential headers, and one on the same host does."""
        host = FakeWebHost()
        host.add("https://api.example.com/a", status_code=302, headers={"Location": "/b"})
        host.add("https://api.example.com/b", status_code=302, headers={"Location": "https://elsewhere.example/c"})
        host.add("https://elsewhere.example/c", b"ok")
        headers = {"Authorization": "Bearer x", "Cookie": "s=1", "Proxy-Authorization": "y", "Accept": "a/b"}
        with mock_web_host(host):
            safe_http.fetch("https://api.example.com/a", headers=headers)
        same_origin_headers = host.calls[1]["headers"]
        self.assertEqual(same_origin_headers["Authorization"], "Bearer x")
        other_origin_headers = host.calls[2]["headers"]
        for name in ("Authorization", "Cookie", "Proxy-Authorization"):
            self.assertNotIn(name, other_origin_headers)
        self.assertEqual(other_origin_headers["Accept"], "a/b")
        self.assertIn("User-Agent", other_origin_headers)
        # the first request still went out with the credential.
        self.assertEqual(host.calls[0]["headers"]["Authorization"], "Bearer x")
        self.assertEqual(headers["Authorization"], "Bearer x")

    def test_same_origin(self):
        """Test that the scheme, host and port make the origin."""
        self.assertTrue(safe_http.same_origin("https://a.example/x", "https://A.example/y?q=1"))
        self.assertFalse(safe_http.same_origin("https://a.example/", "http://a.example/"))
        self.assertFalse(safe_http.same_origin("https://a.example/", "https://b.example/"))
        self.assertFalse(safe_http.same_origin("https://a.example/", "https://a.example:8443/"))

    # =========================================================================
    # require_https=False, for an ApiConnection, and validate_destination_url()
    # =========================================================================
    def test_http_and_any_port_when_https_is_not_required(self):
        """Test that plain http, and any port, are permitted to a public address when https isn't required."""
        with mock.patch(SAFE_HTTP_DNS_PATCH, side_effect=resolves_to("93.184.215.14")) as getaddrinfo:
            for url in ("http://api.example.com/v1/", "http://api.example.com:8080/", "https://api.example.com:8443/"):
                safe_http.validate_public_url(url, require_https=False)
        # each url is resolved on its own port, or the scheme's default.
        ports = [call.args[1] for call in getaddrinfo.call_args_list]
        self.assertEqual(ports, [80, 8080, 8443])

    def test_non_public_addresses_when_https_is_not_required(self):
        """Test that an address that isn't public is refused, over http and on any port, e.g. instance metadata."""
        for address in ("169.254.169.254", "10.0.0.5", "127.0.0.1", "192.168.1.1", "::1"):
            with mock.patch(SAFE_HTTP_DNS_PATCH, side_effect=resolves_to(address)):
                for url in ("http://metadata.example/latest/", "http://api.example.com:6379/"):
                    with self.assertRaises(safe_http.SafeHttpError, msg=f"address={address} url={url}"):
                        safe_http.validate_public_url(url, require_https=False)

    def test_other_schemes_when_https_is_not_required(self):
        """Test that schemes other than http and https are still refused."""
        for url in ("ftp://example.com/", "file:///etc/passwd", "gopher://example.com/"):
            with self.assertRaises(safe_http.SafeHttpError, msg=f"url={url}"):
                safe_http.validate_public_url(url, require_https=False)

    def test_validate_destination_url_permits_loopback_in_the_local_environment_only(self):
        """Test that a loopback host is permitted in the local environment, and refused in a deployed one."""
        loopback_urls = ("http://localhost:9357/api/v1/", "https://127.0.0.1/", "http://api.localhost:9357/")
        with mock.patch(SAFE_HTTP_SETTINGS_PATCH) as settings:
            settings.environment = SmarterEnvironments.LOCAL
            for url in loopback_urls:
                safe_http.validate_destination_url(url, require_https=False)
            for environment in (SmarterEnvironments.ALPHA, SmarterEnvironments.PROD):
                settings.environment = environment
                for url in loopback_urls:
                    with self.assertRaises(safe_http.SafeHttpError, msg=f"{environment} {url}"):
                        safe_http.validate_destination_url(url, require_https=False)

    def test_fetch_permit_local_loopback(self):
        """Test that fetch() refuses a loopback host unless the caller permits it, in the local environment."""
        host = FakeWebHost()
        host.add("http://localhost:9357/api/", b"ok")
        with (
            mock_web_host(host),
            # localhost resolves to the loopback address, unlike mock_web_host()'s public one.
            mock.patch(SAFE_HTTP_DNS_PATCH, side_effect=resolves_to("127.0.0.1")),
            mock.patch(SAFE_HTTP_SETTINGS_PATCH) as settings,
        ):
            settings.environment = SmarterEnvironments.LOCAL
            with self.assertRaises(safe_http.SafeHttpError):
                safe_http.fetch("http://localhost:9357/api/", require_https=False)
            response = safe_http.fetch("http://localhost:9357/api/", require_https=False, permit_local_loopback=True)
            self.assertEqual(response.content, b"ok")
            settings.environment = SmarterEnvironments.PROD
            with self.assertRaises(safe_http.SafeHttpError):
                safe_http.fetch("http://localhost:9357/api/", require_https=False, permit_local_loopback=True)
        self.assertEqual(host.requested, ["http://localhost:9357/api/"])

    # =========================================================================
    # SafeResponse.json()
    # =========================================================================
    def test_response_json(self):
        """Test that a response body is parsed as JSON, in its declared charset, or UTF-8."""
        utf8 = safe_http.SafeResponse(url="u", status_code=200, headers={}, content='{"a": "é"}'.encode())
        self.assertEqual(utf8.json(), {"a": "é"})
        latin1 = safe_http.SafeResponse(
            url="u",
            status_code=200,
            headers={"content-type": "application/json; charset=ISO-8859-1"},
            content='["é"]'.encode("latin-1"),
        )
        self.assertEqual(latin1.json(), ["é"])
        unknown = safe_http.SafeResponse(
            url="u", status_code=200, headers={"content-type": "application/json; charset=nonsense"}, content=b"[1]"
        )
        self.assertEqual(unknown.json(), [1])
        not_json = safe_http.SafeResponse(url="u", status_code=200, headers={}, content=b"<html>")
        with self.assertRaises(ValueError):
            not_json.json()

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
