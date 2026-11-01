"""Test the SmarterCsrfViewMiddleware class."""

# pylint: disable=W0718,W0212

from unittest.mock import MagicMock, patch

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, JsonResponse
from django.middleware.csrf import CSRF_SECRET_LENGTH
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

    def renewed_cookie(self, request, response) -> str | None:
        """Run a request through process_request() and process_response(), and return the csrftoken it sets."""
        self.assertIsNone(self.middleware.process_request(request))
        response = self.middleware.process_response(request, response)
        cookie = response.cookies.get(settings.CSRF_COOKIE_NAME)
        return cookie.value if cookie else None

    def test_a_console_page_sets_an_expired_csrf_cookie_again(self):
        """A signed-in user's page gets a new csrftoken cookie when theirs has expired (issue #885)."""
        request = RequestFactory().get("/llm-tools/plugins/1/")
        request.user = self.admin_user
        self.assertTrue(self.renewed_cookie(request, HttpResponse("<html></html>")))

    def test_a_console_page_renews_the_current_csrf_cookie(self):
        """A signed-in user's page sends their current csrftoken again, with a fresh max-age, keeping its value."""
        token = "a" * CSRF_SECRET_LENGTH
        request = RequestFactory().get("/llm-tools/plugins/1/")
        request.COOKIES[settings.CSRF_COOKIE_NAME] = token
        request.user = self.admin_user
        response = HttpResponse("<html></html>")
        self.assertEqual(self.renewed_cookie(request, response), token)
        self.assertEqual(response.cookies[settings.CSRF_COOKIE_NAME]["max-age"], settings.CSRF_COOKIE_AGE)

    def test_the_csrf_cookie_is_not_renewed_for_other_responses(self):
        """Anonymous visitors, api responses, redirects, errors and POSTs don't renew the cookie."""
        cases = {
            "anonymous": (RequestFactory().get("/"), AnonymousUser(), HttpResponse("<html></html>")),
            "json": (RequestFactory().get("/api/v1/x/"), self.admin_user, JsonResponse({})),
            "redirect": (RequestFactory().get("/"), self.admin_user, HttpResponseRedirect("/login/")),
            "error": (RequestFactory().get("/"), self.admin_user, HttpResponse("<html></html>", status=500)),
            "post": (RequestFactory().post("/"), self.admin_user, HttpResponse("<html></html>")),
        }
        for name, (request, user, response) in cases.items():
            with self.subTest(name):
                request.user = user
                self.assertIsNone(self.renewed_cookie(request, response))

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
