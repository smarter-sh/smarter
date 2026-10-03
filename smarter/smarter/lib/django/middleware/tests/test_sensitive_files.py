"""Test cases for the SmarterBlockSensitiveFilesMiddleware class."""

# pylint: disable=W0718,W0212

import asyncio
import unittest
from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.http import HttpResponse, HttpResponseForbidden
from django.test import RequestFactory

from smarter.lib.django import waffle
from smarter.lib.django.middleware.sensitive_files import (
    SmarterBlockSensitiveFilesMiddleware,
)
from smarter.lib.django.waffle import SmarterWaffleSwitches


class TestSmarterBlockSensitiveFilesMiddleware(unittest.TestCase):
    """Test the SmarterBlockSensitiveFilesMiddleware class."""

    # The middleware is tested with its waffle switch on, whatever the switch's value in the database.
    switch = SmarterWaffleSwitches.ENABLE_MIDDLEWARE_SENSITIVE_FILES

    def setUp(self):
        original = waffle.switch_is_active
        patcher = patch(
            "smarter.lib.django.waffle.switch_is_active",
            side_effect=lambda name: True if name == self.switch else original(name),
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.get_response = MagicMock(return_value=HttpResponse("OK"))
        self.middleware = SmarterBlockSensitiveFilesMiddleware(self.get_response)
        self.factory = RequestFactory()
        self.ip_count = 0

    def public_ip(self) -> str:
        """Return a new public ip, whose throttle count is deleted after the test."""
        self.ip_count += 1
        ip = f"8.8.{self.ip_count // 250}.{self.ip_count % 250 + 1}"
        self.addCleanup(cache.delete, self.middleware.get_throttle_key(ip))
        return ip

    def make_request(self, path, ip=None):
        """Return a request from a public ip: the middleware ignores requests whose client ip it can't find."""
        return self.factory.get(path, REMOTE_ADDR=ip or self.public_ip())

    def test_sensitive_file_blocked(self):
        for sensitive in [
            "/.env",
            "/config.php",
            "/db.sqlite3",
            "/backup.sql",
            "/.git/config",
            "/credentials.json",
            "/secrets.json",
            "/id_rsa",
            "/package-lock.json",
            "/Gemfile.lock",
            "/requirements.txt",
            "/ecp/Current/exporttool/microsoft.exchange.ediscovery.exporttool.application",
        ]:
            with self.subTest(sensitive=sensitive):
                req = self.make_request(sensitive)
                resp = self.middleware(req)
                self.assertIsInstance(resp, HttpResponseForbidden, f"Failed to block sensitive file: {sensitive}")

    def test_sensitive_file_blocked_case_insensitive(self):
        req = self.make_request("/ID_RSA")
        resp = self.middleware(req)
        self.assertIsInstance(resp, HttpResponseForbidden, "Failed to block case-insensitive sensitive file")

    def test_sensitive_file_partial_match(self):
        # Should block if sensitive file string is anywhere in the path
        req = self.make_request("/foo/bar/.env.local")
        resp = self.middleware(req)
        self.assertIsInstance(resp, HttpResponseForbidden, "Failed to block partial match of sensitive file")

    def test_sensitive_file_extension_wildcard(self):
        # Should block for wildcard extensions
        req = self.make_request("/foo/bar/secret.pem")
        resp = self.middleware(req)
        self.assertIsInstance(
            resp, HttpResponseForbidden, "Failed to block sensitive file with wildcard extension .pem"
        )
        req = self.make_request("/foo/bar/backup.bak")
        resp = self.middleware(req)
        self.assertIsInstance(
            resp, HttpResponseForbidden, "Failed to block sensitive file with wildcard extension .bak"
        )

    def test_amnesty_patterns_allowed(self):
        for amnesty in [
            "/dashboard/account/password-reset-link/abc/def/",
            "/docs/json-schema/sqlconnection/",
            "/api/v1/cli/schema/sqlconnection/",
            "/docs/manifest/sqlconnection/",
            "/admin/journal/samjournal",
            "/admin/journal/samjournal/foo/bar",
        ]:
            with self.subTest(amnesty=amnesty):
                req = self.make_request(amnesty)
                resp = self.middleware(req)
                self.assertIsInstance(resp, HttpResponse, f"Failed to allow amnesty pattern: {amnesty}")
                self.assertNotIsInstance(resp, HttpResponseForbidden, f"Incorrectly blocked amnesty pattern: {amnesty}")
                self.assertEqual(resp.content, b"OK", f"Incorrect response content for amnesty pattern: {amnesty}")

    def test_non_sensitive_non_amnesty_allowed(self):
        req = self.make_request("/some/normal/path/")
        resp = self.middleware(req)
        self.assertIsInstance(resp, HttpResponse, "Failed to allow non-sensitive, non-amnesty path")
        self.assertNotIsInstance(resp, HttpResponseForbidden, "Incorrectly blocked non-sensitive, non-amnesty path")
        self.assertEqual(resp.content, b"OK", "Incorrect response content for non-sensitive, non-amnesty path")

    def test_amnesty_pattern_does_not_grant_for_similar_but_not_exact(self):
        # Should be blocked if not matching amnesty pattern exactly
        req = self.make_request("/dashboard/account/password-reset-link/abc/")
        resp = self.middleware(req)
        # Not enough segments, so not amnesty, should be allowed (not sensitive)
        self.assertIsInstance(resp, HttpResponse, "Failed to allow non-sensitive, non-amnesty path")
        self.assertNotIsInstance(resp, HttpResponseForbidden, "Incorrectly blocked non-sensitive, non-amnesty path")

        req = self.make_request("/dashboard/account/password-reset-link/abc/def/ghi/")
        resp = self.middleware(req)
        # Too many segments, not amnesty, but not sensitive either
        self.assertIsInstance(resp, HttpResponse, "Failed to allow non-sensitive, non-amnesty path")
        self.assertNotIsInstance(resp, HttpResponseForbidden, "Incorrectly blocked non-sensitive, non-amnesty path")

    def test_sensitive_file_with_query_string(self):
        req = self.make_request("/.env?foo=bar")
        resp = self.middleware(req)
        self.assertIsInstance(resp, HttpResponseForbidden, "Failed to block sensitive file with query string")

    def test_sensitive_file_with_subdirectory(self):
        req = self.make_request("/foo/.git/config")
        resp = self.middleware(req)
        self.assertIsInstance(
            resp, HttpResponseForbidden, "Failed to block sensitive file, /foo/.git/config, within subdirectory"
        )

    def test_multiple_sensitive_files_in_path(self):
        req = self.make_request("/backup/db.sqlite3")
        resp = self.middleware(req)
        self.assertIsInstance(resp, HttpResponseForbidden, "Failed to block path with multiple sensitive files")

    def test_allowed_pattern_with_sensitive_file(self):
        # If path matches amnesty pattern, it should be allowed even if it contains sensitive file string
        req = self.make_request("/dashboard/account/password-reset-link/.env/def/")
        resp = self.middleware(req)
        self.assertIsInstance(resp, HttpResponse, "Failed to allow amnesty pattern with sensitive file")
        self.assertNotIsInstance(resp, HttpResponseForbidden, "Incorrectly blocked amnesty pattern with sensitive file")
        self.assertEqual(resp.content, b"OK", "Incorrect response content for amnesty pattern with sensitive file")

    def test_throttle(self):
        """Test that a client is throttled after THROTTLE_LIMIT blocked requests, even for a normal path."""
        ip = self.public_ip()
        for _ in range(self.middleware.THROTTLE_LIMIT):
            self.assertIsInstance(self.middleware(self.make_request("/.env", ip=ip)), HttpResponseForbidden)
        self.assertTrue(self.middleware.is_throttled(ip))
        resp = self.middleware(self.make_request("/some/normal/path/", ip=ip))
        self.assertIsInstance(resp, HttpResponseForbidden)
        self.assertIn(b"Too many suspicious requests", resp.content)

    def test_private_ip_is_not_inspected(self):
        """Test that a request whose client ip is private, e.g. from inside the cluster, is not blocked."""
        resp = self.middleware(self.make_request("/.env", ip="10.0.0.1"))
        self.assertEqual(resp.content, b"OK")

    def test_switch_off(self):
        """Test that nothing is blocked when the waffle switch is off."""
        with patch("smarter.lib.django.waffle.switch_is_active", return_value=False):
            self.assertEqual(self.middleware(self.make_request("/.env")).content, b"OK")

    def test_health_check_amnesty(self):
        self.assertEqual(self.middleware(self.make_request("/healthz/")).content, b"OK")

    def test_normalize_path(self):
        normalize = SmarterBlockSensitiveFilesMiddleware.normalize_path
        self.assertEqual(normalize("/a//b/../.ENV"), "/a/.env")
        self.assertEqual(normalize("/a/%252eenv"), "/a/.env")
        self.assertEqual(normalize("a\\b\x00c"), "/a/bc")

    def test_async(self):
        """Test that an async middleware blocks a sensitive file, and passes a normal path through."""

        async def get_response(request):
            return HttpResponse("async OK")

        middleware = SmarterBlockSensitiveFilesMiddleware(get_response)
        with patch("smarter.lib.django.waffle.async_switch_is_active", return_value=True):
            self.assertIsInstance(asyncio.run(middleware(self.make_request("/.env"))), HttpResponseForbidden)
            self.assertEqual(asyncio.run(middleware(self.make_request("/normal/"))).content, b"async OK")
        with patch("smarter.lib.django.waffle.async_switch_is_active", return_value=False):
            self.assertEqual(asyncio.run(middleware(self.make_request("/.env"))).content, b"async OK")
