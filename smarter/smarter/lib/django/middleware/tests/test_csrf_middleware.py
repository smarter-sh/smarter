"""Test the SmarterCsrfViewMiddleware class."""

# pylint: disable=W0718,W0212

from unittest.mock import MagicMock, patch

from django.http import HttpRequest
from django.test import RequestFactory, override_settings

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.lib.django.middleware.csrf import SmarterCsrfViewMiddleware

MODULE = "smarter.lib.django.middleware.csrf"


class TestSmarterCsrfViewMiddleware(TestAccountMixin):
    """Test the SmarterCsrfViewMiddleware class."""

    def setUp(self):
        super().setUp()

        def dummy_get_response(request):
            return None

        self.get_response = dummy_get_response
        self.middleware = SmarterCsrfViewMiddleware(self.get_response)

        self.request = HttpRequest()
        self.request.user = self.admin_user

    @patch("smarter.lib.django.middleware.csrf.settings")
    def test_csrf_trusted_origins_hosts(self, mock_settings):
        mock_settings.CSRF_TRUSTED_ORIGINS = ["https://foo.com", "https://*.bar.com"]
        setattr(self.middleware, "request", self.request)  # type: ignore
        hosts = self.middleware.csrf_trusted_origins_hosts
        self.assertIn("foo.com", hosts)
        self.assertIn(".bar.com", hosts)

    @patch("smarter.lib.django.middleware.csrf.settings")
    def test_allowed_origins_exact(self, mock_settings):
        mock_settings.CSRF_TRUSTED_ORIGINS = ["https://foo.com", "https://*.bar.com"]
        setattr(self.middleware, "request", self.request)  # type: ignore
        allowed = self.middleware.allowed_origins_exact
        self.assertIn("https://foo.com", allowed)
        self.assertNotIn("https://*.bar.com", allowed)

    @patch("smarter.lib.django.middleware.csrf.settings")
    def test_allowed_origin_subdomains(self, mock_settings):
        mock_settings.CSRF_TRUSTED_ORIGINS = ["https://foo.com", "https://*.bar.com"]
        setattr(self.middleware, "request", self.request)  # type: ignore
        allowed = self.middleware.allowed_origin_subdomains
        self.assertIn("https", allowed)
        self.assertIn(".bar.com", allowed["https"])

    @override_settings(ALLOWED_HOSTS=["example.com"])
    @patch("smarter.lib.django.middleware.csrf.settings")
    @patch("smarter.lib.django.middleware.csrf.waffle")
    def test_process_request_with_llmclient(self, mock_waffle, mock_settings):
        self.request.build_absolute_uri = MagicMock(return_value="https://example.com/")
        self.request.META["SERVER_NAME"] = "example.com"
        self.request.META["SERVER_PORT"] = "443"
        self.request.META["HTTP_HOST"] = "example.com:443"
        setattr(self.middleware, "request", self.request)  # type: ignore
        result = self.middleware.process_request(self.request)
        self.assertIsNone(result)

    @patch("smarter.lib.django.middleware.csrf.smarter_settings")
    @patch("smarter.lib.django.middleware.csrf.waffle")
    def test_process_view_local_env(self, mock_waffle, mock_smarter_settings):
        mock_smarter_settings.environment = "local"
        mock_waffle.switch_is_active.return_value = False
        setattr(self.middleware, "request", self.request)  # type: ignore
        result = self.middleware.process_view(self.request, MagicMock(), (), {})
        self.assertIsNone(result)

    @override_settings(ALLOWED_HOSTS=["example.com"])
    @patch("smarter.lib.django.middleware.csrf.smarter_settings")
    @patch("smarter.lib.django.middleware.csrf.waffle")
    def test_process_view_csrf_suppress_for_llmclients(self, mock_waffle, mock_smarter_settings):
        mock_smarter_settings.environment = "prod"
        mock_smarter_settings.internal_ip_prefixes = []
        # ENABLE_MIDDLEWARE_CSRF and CSRF_SUPPRESS_FOR_LLM_CLIENTS
        mock_waffle.switch_is_active.return_value = True
        self.request.path = "/"
        self.request.META["SERVER_NAME"] = "example.com"
        self.request.META["SERVER_PORT"] = "443"
        setattr(self.middleware, "request", self.request)  # type: ignore
        with patch.object(SmarterCsrfViewMiddleware, "llmclient_request_kind", return_value=(True, False)):
            result = self.middleware.process_view(self.request, MagicMock(), (), {})
        self.assertIsNone(result)

    @override_settings(ALLOWED_HOSTS=["example.com"])
    @patch("smarter.lib.django.middleware.csrf.smarter_settings")
    @patch("smarter.lib.django.middleware.csrf.waffle")
    def test_process_view_rejects_post_without_token(self, mock_waffle, mock_smarter_settings):
        """Test that a POST without a CSRF token, from a host that has no bypass, is forbidden."""
        mock_waffle.switch_is_active.return_value = True
        mock_smarter_settings.environment = "prod"
        mock_smarter_settings.internal_ip_prefixes = []
        self.request.method = "POST"
        self.request.path = "/test-csrf-protected/"
        self.request.META["SERVER_NAME"] = "example.com"
        self.request.META["SERVER_PORT"] = "443"
        self.request.META["HTTP_HOST"] = "example.com"
        setattr(self.middleware, "request", self.request)  # type: ignore
        with (
            patch.object(SmarterCsrfViewMiddleware, "llmclient_request_kind", return_value=(False, False)),
            patch.object(
                SmarterCsrfViewMiddleware, "get_dynamic_trusted_origins", return_value=["https://*.example.com"]
            ),
        ):
            response = self.middleware.process_view(self.request, lambda request: None, (), {})
        self.assertEqual(response.status_code, 403)

    def test_llmclient_request_kind_reads_the_request(self):
        """Each request is classified by its own url, and the result is kept on the request."""
        llmclient_request = RequestFactory().post("/api/v1/cli/prompt/example/")
        llmclient_request.user = self.admin_user
        other_request = RequestFactory().post("/dashboard/")
        other_request.user = self.admin_user
        self.assertEqual(self.middleware.llmclient_request_kind(llmclient_request), (True, False))
        self.assertEqual(self.middleware.llmclient_request_kind(other_request), (False, False))
        with patch(f"{MODULE}.SmarterRequestMixin") as srm:
            self.assertEqual(self.middleware.llmclient_request_kind(llmclient_request), (True, False))
            srm.assert_not_called()

    def test_a_request_that_cannot_be_classified_gets_the_full_check(self):
        request = RequestFactory().post("/api/v1/cli/prompt/example/")
        with patch(f"{MODULE}.SmarterRequestMixin", side_effect=ValueError("boom")):
            self.assertEqual(self.middleware.llmclient_request_kind(request), (False, False))

    @patch("smarter.lib.django.middleware.csrf.smarter_settings")
    @patch("smarter.lib.django.middleware.csrf.waffle")
    def test_a_safe_request_is_not_classified(self, mock_waffle, mock_smarter_settings):
        mock_waffle.switch_is_active.return_value = True
        mock_smarter_settings.environment = "prod"
        mock_smarter_settings.internal_ip_prefixes = []
        request = RequestFactory().get("/dashboard/")
        request.user = self.admin_user
        with patch.object(SmarterCsrfViewMiddleware, "llmclient_request_kind") as kind:
            self.assertIsNone(self.middleware.process_view(request, lambda request: None, (), {}))
            kind.assert_not_called()
