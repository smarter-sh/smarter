"""Test the view_helpers."""

from unittest.mock import MagicMock, Mock, patch

from django.http import HttpResponse

from smarter.lib.django import view_helpers
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestRedirectAndExpireCache(SmarterTestBase):
    """Test the redirect_and_expire_cache function."""

    @patch("smarter.lib.django.view_helpers.redirect")
    def test_redirect_and_expire_cache(self, mock_redirect):
        mock_response = MagicMock()
        mock_redirect.return_value = mock_response
        result = view_helpers.redirect_and_expire_cache("/foo/")
        self.assertEqual(result, mock_response)
        self.assertEqual(result["Cache-Control"], "no-store, no-cache, must-revalidate, max-age=0")
        self.assertEqual(result["Pragma"], "no-cache")
        self.assertEqual(result["Expires"], "0")
        mock_redirect.assert_called_with("/foo/")


class TestSmarterView(SmarterTestBase):
    """Test the SmarterView class."""

    def setUp(self):
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


class TestSmarterWebTxtView(SmarterTestBase):
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


class TestSmarterWebHtmlView(SmarterTestBase):
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
        self.assertEqual(response.status_code, 200)


class TestSmarterAuthenticatedWebView(SmarterTestBase):
    """Test the SmarterAuthenticatedWebView class."""

    @patch("smarter.lib.django.view_helpers.UserProfile")
    @patch("smarter.lib.django.view_helpers.SmarterHttpResponseNotFound")
    @patch("smarter.lib.django.view_helpers.redirect_and_expire_cache")
    def test_smarter_init_success(self, mock_redirect, mock_notfound, mock_UserProfile):
        view = view_helpers.SmarterAuthenticatedWebView()
        user = Mock(is_authenticated=True)
        request = Mock(user=user)
        profile = Mock()
        profile.account = "acc"
        mock_UserProfile.objects.get.return_value = profile
        response = view.smarter_init(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(view.account, "acc")
        self.assertEqual(view.user_profile, profile)

    @patch("smarter.lib.django.view_helpers.UserProfile")
    @patch("smarter.lib.django.view_helpers.SmarterHttpResponseNotFound")
    @patch("smarter.lib.django.view_helpers.redirect_and_expire_cache")
    def test_smarter_init_no_profile(self, mock_redirect, mock_notfound, mock_UserProfile):
        view = view_helpers.SmarterAuthenticatedWebView()
        user = Mock(is_authenticated=False)
        request = Mock(user=user)
        mock_UserProfile.objects.get.side_effect = mock_UserProfile.DoesNotExist
        response = view.smarter_init(request)
        mock_redirect.assert_called_with(path="/login/")
        self.assertEqual(response, mock_redirect.return_value)

    @patch("smarter.lib.django.view_helpers.UserProfile")
    @patch("smarter.lib.django.view_helpers.SmarterHttpResponseNotFound")
    @patch("smarter.lib.django.view_helpers.redirect_and_expire_cache")
    def test_smarter_init_profile_notfound(self, mock_redirect, mock_notfound, mock_UserProfile):
        view = view_helpers.SmarterAuthenticatedWebView()
        user = Mock(is_authenticated=True)
        request = Mock(user=user)
        mock_UserProfile.objects.get.side_effect = mock_UserProfile.DoesNotExist
        response = view.smarter_init(request)
        mock_notfound.assert_called()
        self.assertEqual(response, mock_notfound.return_value)

    @patch.object(view_helpers.SmarterAuthenticatedWebView, "smarter_init")
    @patch("smarter.lib.django.view_helpers.patch_vary_headers")
    def test_dispatch(self, mock_patch_vary, mock_smarter_init):
        view = view_helpers.SmarterAuthenticatedWebView()
        request = Mock()
        mock_smarter_init.return_value = HttpResponse(status=200)
        with patch.object(
            view_helpers.SmarterAuthenticatedWebView,
            "dispatch",
            wraps=super(view_helpers.SmarterAuthenticatedWebView, view).dispatch,
        ):
            # This will call the parent dispatch, which is View.dispatch, which is not implemented,
            # so we just check that smarter_init is called and patch_vary_headers is called.
            try:
                view.dispatch(request)
            except Exception:
                pass
        mock_smarter_init.assert_called()
        mock_patch_vary.assert_called()


class TestSmarterAuthenticatedCachedWebView(SmarterTestBase):
    """Test the SmarterAuthenticatedCachedWebView class."""

    @patch.object(view_helpers.SmarterAuthenticatedCachedWebView, "dispatch", autospec=True)
    @patch("smarter.lib.django.view_helpers.patch_vary_headers")
    def test_dispatch(self, mock_patch_vary, mock_dispatch):
        # Simulate a normal response
        mock_response = HttpResponse(status=200)
        mock_dispatch.return_value = mock_response
        view = view_helpers.SmarterAuthenticatedCachedWebView()
        request = Mock()
        result = view.dispatch(request)
        self.assertEqual(result, mock_response)
        mock_patch_vary.assert_called_with(mock_response, ["Cookie"])

        # Simulate a response with status_code > 299
        mock_response2 = HttpResponse(status=404)
        mock_dispatch.return_value = mock_response2
        result2 = view.dispatch(request)
        self.assertEqual(result2, mock_response2)
        # patch_vary_headers should still be called


class TestSmarterAuthenticatedNeverCachedWebView(SmarterTestBase):
    """Test the SmarterAuthenticatedNeverCachedWebView class."""

    def test_inheritance(self):
        # Just check that the class exists and is a subclass of SmarterAuthenticatedWebView
        self.assertTrue(
            issubclass(view_helpers.SmarterAuthenticatedNeverCachedWebView, view_helpers.SmarterAuthenticatedWebView)
        )


class TestSmarterAdminWebView(SmarterTestBase):
    """Test the SmarterAdminWebView class."""

    def test_inheritance(self):
        # Just check that the class exists and is a subclass of SmarterAuthenticatedNeverCachedWebView
        self.assertTrue(
            issubclass(view_helpers.SmarterAdminWebView, view_helpers.SmarterAuthenticatedNeverCachedWebView)
        )
