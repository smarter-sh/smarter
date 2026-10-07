"""Test :class:`smarter.lib.django.middleware.html_minify.HTMLMinifyMiddleware`."""

from unittest.mock import patch

from django.http import FileResponse, HttpResponse, StreamingHttpResponse
from django.test import RequestFactory

from smarter.lib.django.middleware.html_minify import HTMLMinifyMiddleware
from smarter.lib.unittest.base_classes import SmarterTestBase

HTML = "<html>\n  <head><!-- a comment --><title>Title</title></head>\n  <body><p>Hello</p></body>\n</html>"


class TestHTMLMinifyMiddleware(SmarterTestBase):
    """Test that HTML responses are minified, and every other response is passed through."""

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
        patcher = patch("smarter.lib.django.waffle.switch_is_active", return_value=True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def middleware(self, response):
        return HTMLMinifyMiddleware(lambda request: response)

    def test_minifies_html(self):
        """Test that comments are removed, and Content-Length is updated."""
        response = self.middleware(HttpResponse(HTML))(self.factory.get("/dashboard/"))
        content = response.content.decode()
        self.assertNotIn("a comment", content)
        self.assertIn("<p>Hello</p>", content)
        self.assertEqual(response["Content-Length"], str(len(response.content)))

    def test_switch_off(self):
        with patch("smarter.lib.django.waffle.switch_is_active", return_value=False):
            response = self.middleware(HttpResponse(HTML))(self.factory.get("/dashboard/"))
        self.assertIn("a comment", response.content.decode())

    def test_amnesty(self):
        response = self.middleware(HttpResponse(HTML))(self.factory.get("/healthz/"))
        self.assertIn("a comment", response.content.decode())

    def test_skipped_paths(self):
        for path in ("/robots.txt", "/feed.xml", "/static/a.html", "/api/v1/cli/"):
            with self.subTest(path=path):
                response = self.middleware(HttpResponse(HTML))(self.factory.get(path))
                self.assertIn("a comment", response.content.decode())

    def test_should_skip(self):
        middleware = self.middleware(None)
        request = self.factory.get("/dashboard/")
        with open(__file__, "rb") as f:
            self.assertTrue(middleware.should_skip(request, FileResponse(f)))
        self.assertTrue(middleware.should_skip(request, StreamingHttpResponse(iter([b"a"]))))
        self.assertTrue(middleware.should_skip(request, object()))
        self.assertTrue(middleware.should_skip(request, HttpResponse(b"")))
        self.assertTrue(middleware.should_skip(request, HttpResponse("{}", content_type="application/json")))
        self.assertFalse(middleware.should_skip(request, HttpResponse(HTML)))

    def test_xml_is_not_minified(self):
        xml = '<?xml version="1.0"?><!-- keep --><root/>'
        response = self.middleware(None).minify_response(HttpResponse(xml))
        self.assertEqual(response.content.decode(), xml)

    def test_decode_content(self):
        self.assertEqual(HTMLMinifyMiddleware.decode_content(b"  <p>"), "<p>")
        self.assertEqual(HTMLMinifyMiddleware.decode_content("  <p>"), "<p>")
        self.assertTrue(HTMLMinifyMiddleware.looks_like_xml("<RSS>"))
        self.assertFalse(HTMLMinifyMiddleware.looks_like_xml("<html>"))

    def test_minify_error(self):
        """Test that an error while minifying returns the response unchanged."""
        middleware = self.middleware(None)
        response = HttpResponse(HTML)
        with patch.object(HTMLMinifyMiddleware, "serialize_html", side_effect=Exception("bad html")):
            self.assertIs(middleware.minify_response(response), response)
        self.assertIn("a comment", response.content.decode())

    def test_async(self):
        """Test that an async middleware minifies the view's response, and passes it through when the switch is off."""
        import asyncio  # pylint: disable=import-outside-toplevel

        async def get_response(request):
            return HttpResponse(HTML)

        middleware = HTMLMinifyMiddleware(get_response)
        with patch("smarter.lib.django.waffle.async_switch_is_active", return_value=True):
            self.assertNotIn("a comment", asyncio.run(middleware(self.factory.get("/dashboard/"))).content.decode())
        with patch("smarter.lib.django.waffle.async_switch_is_active", return_value=False):
            self.assertIn("a comment", asyncio.run(middleware(self.factory.get("/dashboard/"))).content.decode())

    def test_async_process_response(self):
        import asyncio  # pylint: disable=import-outside-toplevel

        middleware = self.middleware(None)
        response = asyncio.run(middleware.async_process_response(self.factory.get("/dashboard/"), HttpResponse(HTML)))
        self.assertNotIn("a comment", response.content.decode())
        skipped = asyncio.run(middleware.async_process_response(self.factory.get("/api/"), HttpResponse(HTML)))
        self.assertIn("a comment", skipped.content.decode())
