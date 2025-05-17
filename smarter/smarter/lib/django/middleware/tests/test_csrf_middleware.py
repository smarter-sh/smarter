"""Test the CsrfViewMiddleware class."""

# pylint: disable=W0718,W0212

from unittest.mock import MagicMock, patch

from smarter.lib.django.middleware.csrf import CsrfViewMiddleware
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestCsrfViewMiddleware(SmarterTestBase):
    """Test the CsrfViewMiddleware class."""

    def setUp(self):
        self.get_response = MagicMock()
        self.middleware = CsrfViewMiddleware(self.get_response)
        self.request = MagicMock()
        self.request.COOKIES = {}
        self.request.META = {}

    @patch("smarter.lib.django.middleware.csrf.get_cached_chatbot_by_request")
    def test_chatbot_property(self, mock_get_chatbot):
        mock_get_chatbot.return_value = "chatbot"
        self.middleware.request = self.request
        self.assertEqual(self.middleware.chatbot, "chatbot")
        # Should use cached value now
        self.assertEqual(self.middleware._chatbot, "chatbot")

    @patch("smarter.lib.django.middleware.csrf.settings")
    @patch("smarter.lib.django.middleware.csrf.waffle")
    @patch("smarter.lib.django.middleware.csrf.get_cached_chatbot_by_request")
    def test_CSRF_TRUSTED_ORIGINS_with_chatbot(self, mock_get_chatbot, mock_waffle, mock_settings):
        mock_settings.CSRF_TRUSTED_ORIGINS = ["https://allowed.com"]
        mock_get_chatbot.return_value = MagicMock(url="https://chatbot.com")
        mock_waffle.switch_is_active.return_value = False
        self.middleware.request = self.request
        self.middleware._chatbot = None
        origins = self.middleware.CSRF_TRUSTED_ORIGINS
        self.assertIn("https://allowed.com", origins)
        self.assertIn("https://chatbot.com", origins)

    @patch("smarter.lib.django.middleware.csrf.settings")
    @patch("smarter.lib.django.middleware.csrf.waffle")
    @patch("smarter.lib.django.middleware.csrf.get_cached_chatbot_by_request")
    def test_CSRF_TRUSTED_ORIGINS_without_chatbot(self, mock_get_chatbot, mock_waffle, mock_settings):
        mock_settings.CSRF_TRUSTED_ORIGINS = ["https://allowed.com"]
        mock_get_chatbot.return_value = None
        mock_waffle.switch_is_active.return_value = False
        self.middleware.request = self.request
        self.middleware._chatbot = None
        origins = self.middleware.CSRF_TRUSTED_ORIGINS
        self.assertEqual(origins, ["https://allowed.com"])

    @patch("smarter.lib.django.middleware.csrf.settings")
    @patch("smarter.lib.django.middleware.csrf.get_cached_chatbot_by_request")
    def test_csrf_trusted_origins_hosts(self, mock_get_chatbot, mock_settings):
        mock_settings.CSRF_TRUSTED_ORIGINS = ["https://foo.com", "https://*.bar.com"]
        mock_get_chatbot.return_value = None
        self.middleware.request = self.request
        self.middleware._chatbot = None
        hosts = self.middleware.csrf_trusted_origins_hosts
        self.assertIn("foo.com", hosts)
        self.assertIn(".bar.com", hosts)

    @patch("smarter.lib.django.middleware.csrf.settings")
    @patch("smarter.lib.django.middleware.csrf.get_cached_chatbot_by_request")
    def test_allowed_origins_exact(self, mock_get_chatbot, mock_settings):
        mock_settings.CSRF_TRUSTED_ORIGINS = ["https://foo.com", "https://*.bar.com"]
        mock_get_chatbot.return_value = None
        self.middleware.request = self.request
        self.middleware._chatbot = None
        allowed = self.middleware.allowed_origins_exact
        self.assertIn("https://foo.com", allowed)
        self.assertNotIn("https://*.bar.com", allowed)

    @patch("smarter.lib.django.middleware.csrf.settings")
    @patch("smarter.lib.django.middleware.csrf.get_cached_chatbot_by_request")
    def test_allowed_origin_subdomains(self, mock_get_chatbot, mock_settings):
        mock_settings.CSRF_TRUSTED_ORIGINS = ["https://foo.com", "https://*.bar.com"]
        mock_get_chatbot.return_value = None
        self.middleware.request = self.request
        self.middleware._chatbot = None
        allowed = self.middleware.allowed_origin_subdomains
        self.assertIn("https", allowed)
        self.assertIn(".bar.com", allowed["https"])

    @patch("smarter.lib.django.middleware.csrf.get_cached_chatbot_by_request")
    @patch("smarter.lib.django.middleware.csrf.waffle")
    def test_process_request_with_chatbot(self, mock_waffle, mock_get_chatbot):
        mock_get_chatbot.return_value = MagicMock()
        mock_waffle.switch_is_active.return_value = False
        self.middleware.request = self.request
        self.middleware._chatbot = None
        result = self.middleware.process_request(self.request)
        self.assertIsNone(result)

    @patch("smarter.lib.django.middleware.csrf.smarter_settings")
    @patch("smarter.lib.django.middleware.csrf.get_cached_chatbot_by_request")
    @patch("smarter.lib.django.middleware.csrf.waffle")
    def test_process_view_local_env(self, mock_waffle, mock_get_chatbot, mock_smarter_settings):
        mock_smarter_settings.environment = "local"
        mock_get_chatbot.return_value = None
        mock_waffle.switch_is_active.return_value = False
        self.middleware.request = self.request
        self.middleware._chatbot = None
        result = self.middleware.process_view(self.request, MagicMock(), [], {})
        self.assertIsNone(result)

    @patch("smarter.lib.django.middleware.csrf.smarter_settings")
    @patch("smarter.lib.django.middleware.csrf.get_cached_chatbot_by_request")
    @patch("smarter.lib.django.middleware.csrf.waffle")
    def test_process_view_csrf_suppress_for_chatbots(self, mock_waffle, mock_get_chatbot, mock_smarter_settings):
        mock_smarter_settings.environment = "prod"
        mock_get_chatbot.return_value = MagicMock()
        # First call for CSRF_SUPPRESS_FOR_CHATBOTS, second for MIDDLEWARE_LOGGING
        mock_waffle.switch_is_active.side_effect = [True, False]
        self.middleware.request = self.request
        self.middleware._chatbot = None
        result = self.middleware.process_view(self.request, MagicMock(), [], {})
        self.assertIsNone(result)
