"""Test URI utility functions."""

from unittest.mock import Mock, patch

from django.http import HttpRequest

from smarter.common.utils.uri import smarter_build_absolute_uri
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestUriUtils(SmarterTestBase):
    """Test URI utility functions."""

    def test_smarter_build_absolute_uri_django(self):
        # Simulate a Django HttpRequest

        req = HttpRequest()
        req.META["HTTP_HOST"] = "localhost:9357"
        req.path = "/api/v1/resource/"
        url = smarter_build_absolute_uri(req)
        self.assertEqual(url, "http://localhost:9357/api/v1/resource/")

    def test_smarter_build_absolute_uri_mock(self):
        # Simulate a Mock request

        mock_req = Mock()
        url = smarter_build_absolute_uri(mock_req)
        self.assertEqual(url, "http://testserver/mockpath/")

    def test_smarter_build_absolute_uri_none(self):
        url = smarter_build_absolute_uri(None)  # type: ignore
        self.assertEqual(url, "http://testserver/unknown/")


class FakeRequest:
    """A request-like object, without Django's HttpRequest methods."""

    def __init__(self, meta=None, scheme="https", path="/a/path/", host=None, host_error=None):
        self.META = meta or {}
        self.scheme = scheme
        self._path = path
        if host is not None or host_error is not None:
            self.get_host = lambda: self._get_host(host, host_error)

    @staticmethod
    def _get_host(host, error):
        if error:
            raise error
        return host

    def get_full_path(self):
        return self._path


class TestUriUtilsBranches(SmarterTestBase):
    """Test how smarter_build_absolute_uri() finds a request's host, and its fallbacks."""

    def test_build_absolute_uri(self):
        """Test that Django's build_absolute_uri() is used when the request has a SERVER_NAME."""
        req = HttpRequest()
        req.META.update({"SERVER_NAME": "testserver", "SERVER_PORT": "80", "HTTP_HOST": "testserver"})
        req.path = "/x/"
        self.assertEqual(smarter_build_absolute_uri(req), "http://testserver/x/")

    def test_build_absolute_uri_error(self):
        """Test that an error of build_absolute_uri() falls back to the request's scheme, host and path."""
        req = Mock(spec=["build_absolute_uri", "META", "scheme", "get_full_path", "get_host"])
        req.META = {"SERVER_NAME": "example.com"}
        req.build_absolute_uri.side_effect = Exception("DisallowedHost")
        # a spec'd Mock is still a Mock, which returns the fake test url first.
        self.assertEqual(smarter_build_absolute_uri(req), "http://testserver/mockpath/")

    def test_host_from_get_host(self):
        req = FakeRequest(host="example.com")
        self.assertEqual(smarter_build_absolute_uri(req), "https://example.com/a/path/")

    def test_host_from_meta(self):
        """Test that the host is HTTP_HOST, then SERVER_NAME, when get_host() is missing or fails."""
        self.assertEqual(
            smarter_build_absolute_uri(FakeRequest(meta={"HTTP_HOST": "a.example.com"})),
            "https://a.example.com/a/path/",
        )
        self.assertEqual(
            smarter_build_absolute_uri(FakeRequest(meta={"SERVER_NAME": "b.example.com"}, host_error=KeyError("host"))),
            "https://b.example.com/a/path/",
        )

    def test_host_fallback(self):
        """Test that a request without a host gets testserver."""
        self.assertEqual(smarter_build_absolute_uri(FakeRequest()), "https://testserver/a/path/")

    def test_build_error_falls_back(self):
        """Test that an error while building the url returns the fallback url."""
        req = FakeRequest(host_error=RuntimeError("no host"))
        self.assertEqual(smarter_build_absolute_uri(req), "http://testserver/unknown/")

    def test_invalid_url_falls_back(self):
        req = FakeRequest(host="example.com")
        with patch("smarter.common.utils.uri.SmarterValidator.is_valid_url", return_value=False):
            self.assertEqual(smarter_build_absolute_uri(req), "http://testserver/unknown/")

    def test_drf_request(self):
        """Test that a DRF Request whose url can't be built from its attributes uses its Django request."""
        from rest_framework.request import (  # pylint: disable=import-outside-toplevel
            Request,
        )

        django_request = HttpRequest()
        django_request.META.update({"SERVER_NAME": "testserver", "SERVER_PORT": "80"})
        django_request.path = "/drf/"
        request = Request(django_request)
        with (
            patch.object(Request, "build_absolute_uri", create=True, side_effect=Exception("no")),
            patch("smarter.common.utils.uri.SmarterValidator.is_valid_url", return_value=False),
        ):
            self.assertEqual(smarter_build_absolute_uri(request), "http://testserver/drf/")
