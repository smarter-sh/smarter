"""Test the view_helpers."""

from http import HTTPStatus
from unittest.mock import MagicMock, Mock, patch

from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.test import RequestFactory

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.lib.django import view_helpers


class TestViewHelpersBase(TestAccountMixin):
    """Base class for view helpers tests."""

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()

    def tearDown(self):
        self.factory = None
        super().tearDown()


class TestRedirectAndExpireCache(TestViewHelpersBase):
    """Test the redirect_and_expire_cache function."""

    @patch("smarter.lib.django.view_helpers.redirect")
    def test_redirect_and_expire_cache(self, mock_redirect):
        # Use a real HttpResponse to test header logic
        response = HttpResponse()
        mock_redirect.return_value = response
        result = view_helpers.redirect_and_expire_cache("/foo/")
        self.assertEqual(result, response)
        self.assertEqual(result["Cache-Control"], "no-store, no-cache, must-revalidate, max-age=0")
        self.assertEqual(result["Pragma"], "no-cache")
        self.assertEqual(result["Expires"], "0")
        mock_redirect.assert_called_with("/foo/")


class TestSmarterView(TestViewHelpersBase):
    """Test the SmarterView class."""

    def setUp(self):
        super().setUp()
        self.view = view_helpers.SmarterView()

    def test_remove_comments(self):
        html = "<div><!-- comment -->content<!-- another --></div>"
        result = self.view.remove_comments(html)
        self.assertEqual(result, "<div>content</div>")

    @patch("smarter.lib.django.view_helpers.minify")
    def test_minify_html(self, mock_minify):
        mock_minify.return_value = "minified"
        result = self.view.minify_html("<div>   </div>")
        self.assertEqual(result, "minified")
        mock_minify.assert_called()

    @patch("smarter.lib.django.view_helpers.render")
    @patch.object(view_helpers.SmarterView, "remove_comments")
    @patch.object(view_helpers.SmarterView, "minify_html")
    def test_render_clean_html(self, mock_minify_html, mock_remove_comments, mock_render):
        mock_response = MagicMock()
        mock_response.content = b"<div>html</div>"
        mock_response.charset = "utf-8"
        mock_render.return_value = mock_response
        mock_remove_comments.return_value = "<div>html</div>"
        mock_minify_html.return_value = "minified"
        result = self.view.render_clean_html(Mock(), "template.html", {"foo": "bar"})
        self.assertEqual(result, "minified")


class TestSmarterWebTxtView(TestViewHelpersBase):
    """Test the SmarterWebTxtView class."""

    @patch.object(view_helpers.SmarterWebTxtView, "render_clean_html")
    def test_get(self, mock_render_clean_html):
        mock_render_clean_html.return_value = "plain text"
        view = view_helpers.SmarterWebTxtView()
        request = Mock()
        view.template_path = "foo.txt"
        response = view.get(request)
        self.assertIsInstance(response, HttpResponse)
        self.assertEqual(response.content, b"plain text")
        self.assertEqual(response["Content-Type"], "text/plain")


class TestSmarterWebHtmlView(TestViewHelpersBase):
    """Test the SmarterWebHtmlView class."""

    @patch.object(view_helpers.SmarterWebHtmlView, "render_clean_html")
    def test_clean_http_response(self, mock_render_clean_html):
        mock_render_clean_html.return_value = "html"
        view = view_helpers.SmarterWebHtmlView()
        response = view.clean_http_response(Mock(), "foo.html")
        self.assertIsInstance(response, HttpResponse)
        self.assertEqual(response.content, b"html")
        self.assertEqual(response["Content-Type"], "text/html")

    @patch.object(view_helpers.SmarterWebHtmlView, "clean_http_response")
    def test_get(self, mock_clean_http_response):
        mock_clean_http_response.return_value = HttpResponse("ok")
        view = view_helpers.SmarterWebHtmlView()
        response = view.get(Mock())
        self.assertEqual(response.status_code, HTTPStatus.OK)


class TestSmarterAuthenticatedNeverCachedWebView(TestViewHelpersBase):
    """Test the SmarterAuthenticatedNeverCachedWebView class."""

    def test_inheritance(self):
        self.assertTrue(
            issubclass(view_helpers.SmarterAuthenticatedNeverCachedWebView, view_helpers.SmarterAuthenticatedWebView)
        )


class TestSmarterAdminWebView(TestViewHelpersBase):
    """Test the SmarterAdminWebView class."""

    def test_inheritance(self):
        self.assertTrue(
            issubclass(view_helpers.SmarterAdminWebView, view_helpers.SmarterAuthenticatedNeverCachedWebView)
        )
