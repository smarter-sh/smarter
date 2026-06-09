"""Test URI utility functions."""

from unittest.mock import Mock

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
