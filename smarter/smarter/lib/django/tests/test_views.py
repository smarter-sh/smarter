"""Test the base views of :mod:`smarter.lib.django.views`, and smarter_cache_page_by_user()."""

from http import HTTPStatus
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse
from django.test import RequestFactory

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.lib.django.shortcuts import reverse
from smarter.lib.django.views import (
    SmarterAdminWebView,
    SmarterAuthenticatedCachedWebView,
    SmarterOptionallyAuthenticatedApiView,
    SmarterView,
    SmarterWebHtmlView,
    SmarterWebTxtView,
    SmarterWebXmlView,
    redirect_and_expire_cache,
    smarter_cache_page_by_user,
)

MODULE = "smarter.lib.django.views"


class OkAdminView(SmarterAdminWebView):
    def get(self, request, *args, **kwargs):
        return HttpResponse("admin ok")


class NotFoundCachedView(SmarterAuthenticatedCachedWebView):
    def get(self, request, *args, **kwargs):
        return HttpResponse("missing", status=HTTPStatus.NOT_FOUND)


class OkOptionallyAuthenticatedApiView(SmarterOptionallyAuthenticatedApiView):
    def post(self, request, *args, **kwargs):
        return HttpResponse("api ok")


class TestSmarterViews(TestAccountMixin):
    """Test the txt, xml, admin and cached views, and the html helpers."""

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()

    def request(self, path="/", user=None):
        request = self.factory.get(path, HTTP_HOST="localhost:9357")
        SessionMiddleware(lambda r: None).process_request(request)  # type: ignore[arg-type]
        request.user = user or AnonymousUser()
        return request

    def test_txt_and_xml_views(self):
        txt = SmarterWebTxtView.as_view(template_path="robots.txt")(self.request("/robots.txt"))
        self.assertEqual(txt.status_code, HTTPStatus.OK)
        self.assertEqual(txt["Content-Type"], "text/plain")
        xml = SmarterWebXmlView.as_view(template_path="sitemap.xml")(self.request("/sitemap.xml"))
        self.assertEqual(xml.status_code, HTTPStatus.OK)

    def test_render_clean_html(self):
        view = SmarterView()
        self.assertFalse(view.ready)
        self.assertIn("SmarterView", view.formatted_class_name)
        self.assertEqual(view.remove_comments("<p><!-- x -->a</p>"), "<p>a</p>")
        response = view.render_clean_html(self.request(), template_path="not/a/template.html")
        self.assertEqual(response.status_code, HTTPStatus.INTERNAL_SERVER_ERROR)

    def test_missing_template_is_a_server_error(self):
        """Test that a view whose template is missing answers 500, not a 200 whose body is the error's repr."""
        html = SmarterWebHtmlView.as_view(template_path="not/a/template.html")(self.request())
        self.assertEqual(html.status_code, HTTPStatus.INTERNAL_SERVER_ERROR)
        txt = SmarterWebTxtView.as_view(template_path="not/a/template.txt")(self.request())
        self.assertEqual(txt.status_code, HTTPStatus.INTERNAL_SERVER_ERROR)

    def test_reverse_is_not_cached(self):
        """Test that reverse() follows the URLconf, rather than a path cached by an earlier release."""
        with patch("smarter.lib.django.shortcuts.django_reverse", return_value="/plugin/"):
            self.assertEqual(reverse("llmtool", "plugin_list_view"), "/plugin/")
        self.assertEqual(reverse("llmtool", "plugin_list_view"), "/llm-tools/")

    def test_admin_view(self):
        """Test that an anonymous user is sent to the login page, a mortal to the admin login, and staff get in."""
        view = OkAdminView.as_view()
        self.assertEqual(view(self.request()).status_code, HTTPStatus.FOUND)
        response = view(self.request("/admin-page/", user=self.non_admin_user))
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertIn("/admin/login/", response["Location"])
        self.assertEqual(view(self.request(user=self.admin_user)).content, b"admin ok")

    def test_cached_view_error_response(self):
        """Test that an error response of a cached view is returned as is."""
        response = NotFoundCachedView.as_view()(self.request(user=self.admin_user))
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_redirect_and_expire_cache(self):
        response = redirect_and_expire_cache("/login/")
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertEqual(response["Location"], "/login/")

    def test_optionally_authenticated_api_view_is_throttled(self):
        """Test that a throttled request gets 429 with Retry-After, and never reaches the handler."""
        request = self.factory.post("/api/v1/llmclient/", HTTP_HOST="localhost:9357")
        SessionMiddleware(lambda r: None).process_request(request)  # type: ignore[arg-type]
        request.user = AnonymousUser()
        view = OkOptionallyAuthenticatedApiView.as_view()
        with patch(f"{MODULE}.throttle_wait", return_value=None):
            self.assertEqual(view(request).content, b"api ok")
        with patch(f"{MODULE}.throttle_wait", return_value=7):
            response = view(request)
        self.assertEqual(response.status_code, HTTPStatus.TOO_MANY_REQUESTS)
        self.assertEqual(response["Retry-After"], "7")
        self.assertIn(b"throttled", response.content)
        self.assertIn("Cookie", response["Vary"])

    def test_throttle_counts_a_request_once(self):
        """Test that a subclass that checks the throttle before dispatch() doesn't count the request twice."""

        class EarlyThrottledView(OkOptionallyAuthenticatedApiView):
            def dispatch(self, request, *args, **kwargs):
                throttled = self.throttle(request)
                if throttled is not None:
                    return throttled
                return super().dispatch(request, *args, **kwargs)

        request = self.factory.post("/api/v1/llmclient/", HTTP_HOST="localhost:9357")
        SessionMiddleware(lambda r: None).process_request(request)  # type: ignore[arg-type]
        request.user = AnonymousUser()
        with patch(f"{MODULE}.throttle_wait", return_value=None) as wait:
            self.assertEqual(EarlyThrottledView.as_view()(request).content, b"api ok")
        wait.assert_called_once()
        with patch(f"{MODULE}.throttle_wait", return_value=3) as wait:
            response = EarlyThrottledView.as_view()(request)
        wait.assert_called_once()
        self.assertEqual((response.status_code, response["Retry-After"]), (HTTPStatus.TOO_MANY_REQUESTS, "3"))
        self.assertIn("Cookie", response["Vary"])


class TestSmarterCachePageByUser(TestAccountMixin):
    """Test that smarter_cache_page_by_user() caches a page for each user, and can be invalidated."""

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
        self.calls = 0

        @smarter_cache_page_by_user(timeout=60)
        def view(request):
            self.calls += 1
            return HttpResponse(f"call {self.calls}")

        self.view = view

    def request(self, user=None):
        request = self.factory.get("/cached/page/", HTTP_HOST="localhost:9357")
        request.user = user or AnonymousUser()
        return request

    def test_switch_off(self):
        with patch(f"{MODULE}.waffle.switch_is_active", return_value=False):
            self.view(self.request())
            self.view(self.request())
            self.view.invalidate(self.request())
        self.assertEqual(self.calls, 2)

    def test_cached_by_user(self):
        with patch(f"{MODULE}.waffle.switch_is_active", return_value=True):
            for user in (None, self.admin_user):
                self.view.invalidate(self.request(user))
                self.addCleanup(self.view.invalidate, self.request(user))
                first = self.view(self.request(user)).content
                self.assertEqual(self.view(self.request(user)).content, first)
            self.view.invalidate(None)
        self.assertEqual(self.calls, 2)
