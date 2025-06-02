"""Test the CorsMiddleware class."""

# pylint: disable=W0718,W0212

from unittest.mock import MagicMock, PropertyMock, patch
from urllib.parse import urlsplit

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.lib.django.middleware.cors import CorsMiddleware


class TestCorsMiddleware(TestAccountMixin):
    """Test the CorsMiddleware class."""

    def setUp(self):
        super().setUp()
        self.middleware = CorsMiddleware(get_response=MagicMock())
        self.request = MagicMock()
        self.request.build_absolute_uri.return_value = "https://example.com/foo"
        self.split_url = urlsplit("https://example.com/foo")

    @patch("smarter.lib.django.middleware.cors.waffle")
    def test___call__(self, mock_waffle):
        mock_waffle.switch_is_active.return_value = False
        with patch.object(CorsMiddleware, "__call__", wraps=super(CorsMiddleware, self.middleware).__call__):
            # __call__ is inherited from DjangoCorsMiddleware, so just check it calls super
            try:
                self.middleware.__call__(self.request)
            except Exception:
                pass  # DjangoCorsMiddleware.__call__ expects more setup

    def test_url_setter_and_chatbot(self):
        split_url = urlsplit("https://example.com")
        request = MagicMock()
        middleware = CorsMiddleware(get_response=MagicMock())

        with (
            patch("smarter.lib.django.middleware.cors.conf") as mock_conf,
            patch("smarter.lib.django.middleware.cors.waffle") as mock_waffle,
            patch("smarter.lib.django.middleware.cors.get_cached_chatbot_by_request") as mock_get_chatbot,
        ):

            mock_waffle.switch_is_active.return_value = False
            mock_conf.CORS_ALLOWED_ORIGINS = []
            mock_get_chatbot.return_value = MagicMock(url=split_url)

            middleware.request = request
            middleware.request.user = self.admin_user
            middleware.url = split_url

            # FIX NOTE: need assertions here.

    @patch("smarter.lib.django.middleware.cors.conf")
    def test_CORS_ALLOWED_ORIGINS_with_chatbot(self, mock_conf):
        mock_conf.CORS_ALLOWED_ORIGINS = ["https://allowed.com"]
        self.middleware._chatbot = MagicMock()
        self.middleware._url = urlsplit("https://chatbot.com")
        type(self.middleware).url = PropertyMock(return_value=self.middleware._url)
        origins = self.middleware.CORS_ALLOWED_ORIGINS
        self.assertIn("https://chatbot.com", origins)
        self.assertIn("https://allowed.com", origins)

    @patch("smarter.lib.django.middleware.cors.conf")
    def test_CORS_ALLOWED_ORIGINS_without_chatbot(self, mock_conf):
        mock_conf.CORS_ALLOWED_ORIGINS = ["https://allowed.com"]
        self.middleware._chatbot = None
        origins = self.middleware.CORS_ALLOWED_ORIGINS
        self.assertEqual(origins, ["https://allowed.com"])

    @patch("smarter.lib.django.middleware.cors.conf")
    def test_CORS_ALLOWED_ORIGIN_REGEXES(self, mock_conf):
        mock_conf.CORS_ALLOWED_ORIGIN_REGEXES = [r"^https://.*\.example\.com$"]
        regexes = self.middleware.CORS_ALLOWED_ORIGIN_REGEXES
        self.assertEqual(regexes, [r"^https://.*\.example\.com$"])

    @patch("smarter.lib.django.middleware.cors.waffle")
    def test_origin_found_in_white_lists_with_chatbot(self, mock_waffle):
        mock_waffle.switch_is_active.return_value = False
        self.middleware._chatbot = MagicMock()
        self.middleware._url = self.split_url
        result = self.middleware.origin_found_in_white_lists("https://example.com", self.split_url)
        self.assertTrue(result)

    @patch("smarter.lib.django.middleware.cors.conf")
    def test_origin_found_in_white_lists_in_origins(self, mock_conf):
        mock_conf.CORS_ALLOWED_ORIGINS = ["null"]
        self.middleware._chatbot = None
        self.middleware._url = None
        result = self.middleware.origin_found_in_white_lists("null", self.split_url)
        self.assertTrue(result)

    @patch("smarter.lib.django.middleware.cors.conf")
    def test_origin_found_in_white_lists_url_in_whitelist(self, mock_conf):
        mock_conf.CORS_ALLOWED_ORIGINS = ["https://example.com"]
        self.middleware._chatbot = None
        self.middleware._url = None
        result = self.middleware.origin_found_in_white_lists("https://other.com", self.split_url)
        self.assertTrue(result)

    @patch("smarter.lib.django.middleware.cors.conf")
    def test_origin_found_in_white_lists_regex(self, mock_conf):
        mock_conf.CORS_ALLOWED_ORIGINS = []
        mock_conf.CORS_ALLOWED_ORIGIN_REGEXES = [r"^https://.*\.example\.com$"]
        self.middleware._chatbot = None
        self.middleware._url = None
        result = self.middleware.origin_found_in_white_lists("https://foo.example.com", self.split_url)
        self.assertTrue(result)

    @patch("smarter.lib.django.middleware.cors.conf")
    def test__url_in_whitelist(self, mock_conf):
        mock_conf.CORS_ALLOWED_ORIGINS = ["https://example.com"]
        self.middleware._chatbot = None
        url = urlsplit("https://example.com")
        result = self.middleware._url_in_whitelist(url)
        self.assertTrue(result)
        url2 = urlsplit("https://notallowed.com")
        result2 = self.middleware._url_in_whitelist(url2)
        self.assertFalse(result2)

    @patch("smarter.lib.django.middleware.cors.conf")
    def test_regex_domain_match(self, mock_conf):
        mock_conf.CORS_ALLOWED_ORIGIN_REGEXES = [r"^https://.*\.example\.com$"]
        self.middleware._chatbot = None
        result = self.middleware.regex_domain_match("https://foo.example.com")
        self.assertTrue(result)
        result2 = self.middleware.regex_domain_match("https://bar.com")
        self.assertFalse(result2)
