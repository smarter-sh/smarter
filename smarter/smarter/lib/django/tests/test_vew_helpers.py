"""Test the view_helpers."""

from http import HTTPStatus
from unittest.mock import MagicMock, Mock, patch

from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.lib.django import view_helpers


class TestViewHelpersBase(TestAccountMixin):
    """Base class for view helpers tests."""


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


class TestSmarterAuthenticatedWebView(TestViewHelpersBase):
    """Test the SmarterAuthenticatedWebView class."""

    @patch("smarter.lib.django.view_helpers.UserProfile")
    @patch("smarter.lib.django.view_helpers.SmarterHttpResponseNotFound")
    @patch("smarter.lib.django.view_helpers.redirect_and_expire_cache")
    def test_smarter_init_success(self, mock_redirect, mock_notfound, mock_UserProfile):
        view = view_helpers.SmarterAuthenticatedWebView()
        request = Mock()
        request.user = self.non_admin_user
        profile = Mock()
        profile.account = "acc"
        mock_UserProfile.objects.get.return_value = profile
        response = view.smarter_init(request)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(view.account, "acc")
        self.assertEqual(view.user_profile, profile)
        mock_UserProfile.objects.get.assert_called_with(user=self.non_admin_user)
        mock_redirect.assert_not_called()
        mock_notfound.assert_not_called()

    @patch("smarter.lib.django.view_helpers.UserProfile")
    @patch("smarter.lib.django.view_helpers.SmarterHttpResponseNotFound")
    @patch("smarter.lib.django.view_helpers.redirect_and_expire_cache")
    def test_smarter_init_no_profile(self, mock_redirect, mock_notfound, mock_UserProfile):
        view = view_helpers.SmarterAuthenticatedWebView()
        request = Mock()
        request.user = AnonymousUser()
        # UserProfile.objects.get should not be called
        response = view.smarter_init(request)
        mock_redirect.assert_called_with(path="/login/")
        self.assertEqual(response, mock_redirect.return_value)
        mock_UserProfile.objects.get.assert_not_called()
        mock_notfound.assert_not_called()

    @patch("smarter.lib.django.view_helpers.UserProfile")
    @patch("smarter.lib.django.view_helpers.SmarterHttpResponseNotFound")
    @patch("smarter.lib.django.view_helpers.redirect_and_expire_cache")
    def test_smarter_init_profile_notfound(self, mock_redirect, mock_notfound, mock_UserProfile):
        view = view_helpers.SmarterAuthenticatedWebView()
        request = Mock()
        request.user = self.non_admin_user
        mock_UserProfile.objects.get.side_effect = mock_UserProfile.DoesNotExist
        response = view.smarter_init(request)
        mock_UserProfile.objects.get.assert_called_with(user=self.non_admin_user)
        mock_notfound.assert_called()
        self.assertEqual(response, mock_notfound.return_value)

    @patch("smarter.lib.django.view_helpers.patch_vary_headers")
    def test_dispatch_calls_smarter_init_and_patch_vary(self, mock_patch_vary):
        with patch.object(
            view_helpers.SmarterAuthenticatedWebView, "smarter_init", return_value=HttpResponse(status=HTTPStatus.OK)
        ) as mock_init:
            view = view_helpers.SmarterAuthenticatedWebView()
            request = Mock()
            request.method = "GET"
            request.user = self.admin_user
            response = view.dispatch(request)
            self.assertTrue(mock_init.called)
            mock_patch_vary.assert_called_with(response, ["Cookie"])
            self.assertEqual(response.status_code, HTTPStatus.OK)


class TestSmarterAuthenticatedCachedWebView(TestViewHelpersBase):
    """Test the SmarterAuthenticatedCachedWebView class."""

    @patch("smarter.lib.django.view_helpers.patch_vary_headers")
    def test_dispatch_calls_patch_vary_headers(self, mock_patch_vary):
        # Patch parent dispatch to return a response
        class DummyView(view_helpers.SmarterAuthenticatedCachedWebView):
            """Dummy view for testing."""

            def dispatch(self, request, *args, **kwargs):
                return HttpResponse(status=HTTPStatus.OK)

        view = DummyView()
        request = Mock()
        request.user = self.non_admin_user
        # Call the real dispatch method of SmarterAuthenticatedCachedWebView
        response = view_helpers.SmarterAuthenticatedCachedWebView.dispatch(view, request)
        mock_patch_vary.assert_called_with(response, ["Cookie"])
        self.assertEqual(response.status_code, HTTPStatus.OK)

        # Test with status_code > 299
        class DummyView2(view_helpers.SmarterAuthenticatedCachedWebView):
            def dispatch(self, request, *args, **kwargs):
                return HttpResponse(status=404)

        view2 = DummyView2()
        response2 = view_helpers.SmarterAuthenticatedCachedWebView.dispatch(view2, request)
        mock_patch_vary.assert_called_with(response2, ["Cookie"])
        self.assertEqual(response2.status_code, 404)


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
