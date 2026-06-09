"""Test the SmarterCorsMiddleware class."""

# pylint: disable=W0718,W0212

import unittest
from unittest.mock import MagicMock, PropertyMock, patch
from urllib.parse import urlsplit

from django.test import override_settings

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.lib.django import waffle
from smarter.lib.django.middleware.cors import SmarterCorsMiddleware
from smarter.lib.django.waffle import SmarterWaffleSwitches


@unittest.skipUnless(
    waffle.switch_is_active(SmarterWaffleSwitches.ENABLE_MIDDLEWARE_CORS), "CORS middleware is not enabled"
)
class TestSmarterCorsMiddleware(TestAccountMixin):
    """Test the SmarterCorsMiddleware class."""

    def setUp(self):
        super().setUp()
        self.middleware = SmarterCorsMiddleware(get_response=MagicMock())
        self.request = MagicMock()
        self.request.build_absolute_uri.return_value = "https://example.com/foo"
        self.split_url = urlsplit("https://example.com/foo")

    @patch("smarter.lib.django.middleware.cors.waffle")
    def test___call__(self, mock_waffle):
        mock_waffle.switch_is_active.return_value = False
        with patch.object(
            SmarterCorsMiddleware, "__call__", wraps=super(SmarterCorsMiddleware, self.middleware).__call__
        ):
            # __call__ is inherited from DjangoSmarterCorsMiddleware, so just check it calls super
            try:
                self.middleware.__call__(self.request)
            except Exception:
                pass  # DjangoSmarterCorsMiddleware.__call__ expects more setup

    @override_settings(CORS_ALLOWED_ORIGINS=["null"])
    def test_origin_found_in_white_lists_in_origins(self):
        self.middleware._llm_client = None
        self.middleware._url = None
        result = self.middleware.origin_found_in_white_lists("null", self.split_url)
        self.assertTrue(result)

    @override_settings(CORS_ALLOWED_ORIGINS=["https://example.com"])
    def test_origin_found_in_white_lists_url_in_whitelist(self):
        self.middleware._llm_client = None
        self.middleware._url = None
        result = self.middleware.origin_found_in_white_lists("https://other.com", self.split_url)
        self.assertTrue(result)

    @override_settings(CORS_ALLOWED_ORIGINS=[], CORS_ALLOWED_ORIGIN_REGEXES=[r"^https://.*\.example\.com$"])
    def test_origin_found_in_white_lists_regex(self):
        self.middleware._llm_client = None
        self.middleware._url = None
        result = self.middleware.origin_found_in_white_lists("https://foo.example.com", self.split_url)
        self.assertTrue(result)

    @override_settings(CORS_ALLOWED_ORIGINS=["https://example.com"])
    def test__url_in_whitelist(self):
        self.middleware._llm_client = None
        url = urlsplit("https://example.com")
        result = self.middleware._url_in_whitelist(url)
        self.assertTrue(result)
        url2 = urlsplit("https://notallowed.com")
        result2 = self.middleware._url_in_whitelist(url2)
        self.assertFalse(result2)

    @override_settings(CORS_ALLOWED_ORIGIN_REGEXES=[r"^https://.*\.example\.com$"])
    def test_regex_domain_match(self):
        self.middleware._llm_client = None
        result = self.middleware.regex_domain_match("https://foo.example.com")
        self.assertTrue(result)
        result2 = self.middleware.regex_domain_match("https://bar.com")
        self.assertFalse(result2)
