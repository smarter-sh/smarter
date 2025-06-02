"""Test cases for the BlockSensitiveFilesMiddleware class."""

# pylint: disable=W0718,W0212

import unittest
from unittest.mock import MagicMock

from django.http import HttpResponse, HttpResponseForbidden

from smarter.lib.django.middleware.sensitive_files import BlockSensitiveFilesMiddleware


class TestBlockSensitiveFilesMiddleware(unittest.TestCase):
    """Test the BlockSensitiveFilesMiddleware class."""

    def setUp(self):
        self.get_response = MagicMock(return_value=HttpResponse("OK"))
        self.middleware = BlockSensitiveFilesMiddleware(self.get_response)

    def make_request(self, path):
        req = MagicMock()
        req.path = path
        return req

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
                self.assertIsInstance(resp, HttpResponseForbidden)
                self.assertIn("blocked by Smarter", resp.content.decode())

    def test_sensitive_file_blocked_case_insensitive(self):
        req = self.make_request("/ID_RSA")
        resp = self.middleware(req)
        self.assertIsInstance(resp, HttpResponseForbidden)

    def test_sensitive_file_partial_match(self):
        # Should block if sensitive file string is anywhere in the path
        req = self.make_request("/foo/bar/.env.local")
        resp = self.middleware(req)
        self.assertIsInstance(resp, HttpResponseForbidden)

    def test_sensitive_file_extension_wildcard(self):
        # Should block for wildcard extensions
        req = self.make_request("/foo/bar/secret.pem")
        resp = self.middleware(req)
        self.assertIsInstance(resp, HttpResponseForbidden)
        req = self.make_request("/foo/bar/backup.bak")
        resp = self.middleware(req)
        self.assertIsInstance(resp, HttpResponseForbidden)

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
                self.assertIsInstance(resp, HttpResponse)
                self.assertNotIsInstance(resp, HttpResponseForbidden)
                self.assertEqual(resp.content, b"OK")

    def test_non_sensitive_non_amnesty_allowed(self):
        req = self.make_request("/some/normal/path/")
        resp = self.middleware(req)
        self.assertIsInstance(resp, HttpResponse)
        self.assertNotIsInstance(resp, HttpResponseForbidden)
        self.assertEqual(resp.content, b"OK")

    def test_amnesty_pattern_does_not_grant_for_similar_but_not_exact(self):
        # Should be blocked if not matching amnesty pattern exactly
        req = self.make_request("/dashboard/account/password-reset-link/abc/")
        resp = self.middleware(req)
        # Not enough segments, so not amnesty, should be allowed (not sensitive)
        self.assertIsInstance(resp, HttpResponse)
        self.assertNotIsInstance(resp, HttpResponseForbidden)

        req = self.make_request("/dashboard/account/password-reset-link/abc/def/ghi/")
        resp = self.middleware(req)
        # Too many segments, not amnesty, but not sensitive either
        self.assertIsInstance(resp, HttpResponse)
        self.assertNotIsInstance(resp, HttpResponseForbidden)

    def test_sensitive_file_with_query_string(self):
        req = self.make_request("/.env?foo=bar")
        resp = self.middleware(req)
        self.assertIsInstance(resp, HttpResponseForbidden)

    def test_sensitive_file_with_subdirectory(self):
        req = self.make_request("/foo/.git/config")
        resp = self.middleware(req)
        self.assertIsInstance(resp, HttpResponseForbidden)

    def test_multiple_sensitive_files_in_path(self):
        req = self.make_request("/backup/db.sqlite3")
        resp = self.middleware(req)
        self.assertIsInstance(resp, HttpResponseForbidden)

    def test_allowed_pattern_with_sensitive_file(self):
        # If path matches amnesty pattern, it should be allowed even if it contains sensitive file string
        req = self.make_request("/dashboard/account/password-reset-link/.env/def/")
        resp = self.middleware(req)
        self.assertIsInstance(resp, HttpResponse)
        self.assertNotIsInstance(resp, HttpResponseForbidden)
        self.assertEqual(resp.content, b"OK")
