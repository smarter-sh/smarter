"""Test SmarterHttpResponse classes"""

from unittest.mock import MagicMock, patch

from smarter.lib.django.http.shortcuts import (
    SmarterHttpResponse,
    SmarterHttpResponseBadRequest,
    SmarterHttpResponseForbidden,
    SmarterHttpResponseNotFound,
    SmarterHttpResponseServerError,
)
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestSmarterHttpResponses(SmarterTestBase):
    """Test SmarterHttpResponse classes."""

    def setUp(self):
        self.request = MagicMock()

    @patch("smarter.lib.django.http.shortcuts.render")
    def test_smarter_http_response_defaults(self, mock_render):
        mock_render.return_value.content = b"html"
        resp = SmarterHttpResponse(self.request)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"html", resp.content)
        self.assertEqual(resp.context["message"], "Something went wrong! Please try again later.")

    @patch("smarter.lib.django.http.shortcuts.render")
    def test_smarter_http_response_custom(self, mock_render):
        mock_render.return_value.content = b"custom"
        resp = SmarterHttpResponse(self.request, error_message="foo", status_code=201, template_file="foo.html")
        self.assertEqual(resp.status_code, 201)
        self.assertIn(b"custom", resp.content)
        self.assertEqual(resp.context["message"], "foo")

    @patch("smarter.lib.django.http.shortcuts.render")
    def test_bad_request(self, mock_render):
        mock_render.return_value.content = b"bad"
        resp = SmarterHttpResponseBadRequest(self.request)
        self.assertEqual(resp.status_code, 400)
        self.assertIn(b"bad", resp.content)
        self.assertEqual(resp.context["message"], "Dohhhh, that's a bad request my friend.")

    @patch("smarter.lib.django.http.shortcuts.render")
    def test_forbidden(self, mock_render):
        mock_render.return_value.content = b"forbidden"
        resp = SmarterHttpResponseForbidden(self.request)
        self.assertEqual(resp.status_code, 403)
        self.assertIn(b"forbidden", resp.content)
        self.assertEqual(resp.context["message"], "Awe shucks, you're not allowed to do that.")

    @patch("smarter.lib.django.http.shortcuts.render")
    def test_not_found(self, mock_render):
        mock_render.return_value.content = b"notfound"
        resp = SmarterHttpResponseNotFound(self.request)
        self.assertEqual(resp.status_code, 404)
        self.assertIn(b"notfound", resp.content)
        self.assertEqual(resp.context["message"], "Oh no!!! We couldn't find that page.")

    @patch("smarter.lib.django.http.shortcuts.render")
    def test_server_error(self, mock_render):
        mock_render.return_value.content = b"servererror"
        resp = SmarterHttpResponseServerError(self.request)
        self.assertEqual(resp.status_code, 500)
        self.assertIn(b"servererror", resp.content)
        self.assertEqual(resp.context["message"], "Ugh!!! Something went wrong on our end.")
