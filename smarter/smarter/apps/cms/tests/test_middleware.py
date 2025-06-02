"""Test HTMLMinifyMiddleware"""

from unittest.mock import MagicMock, Mock, patch

from django.http import FileResponse, HttpResponse

from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.cms.middleware import HTMLMinifyMiddleware
from smarter.lib.unittest.base_classes import SmarterTestBase


ALL_KINDS = SAMKinds.singular_slugs()


class TestHTMLMinifyMiddleware(SmarterTestBase):
    """Test HTMLMinifyMiddleware"""

    def setUp(self):
        self.middleware = HTMLMinifyMiddleware(get_response=lambda req: None)
        self.request = Mock()

    @patch("smarter.apps.cms.middleware.BeautifulSoup")
    def test_html_response_minified(self, mock_bs):
        # Mock BeautifulSoup and its methods
        mock_soup = MagicMock()
        mock_bs.return_value = mock_soup
        mock_soup.findAll.return_value = [Mock(), Mock()]
        mock_soup.prettify.return_value = "<html><body>test</body></html>"

        response = HttpResponse(b"<html><!-- comment --><body>test</body></html>", content_type="text/html")
        response["Content-Length"] = str(len(response.content))

        result = self.middleware.process_response(self.request, response)

        mock_bs.assert_called_once()
        mock_soup.findAll.assert_called()
        mock_soup.prettify.assert_called_once_with(formatter="minimal")
        self.assertIn(b"test", result.content)
        self.assertNotIn(b"comment", result.content)
        self.assertEqual(result["Content-Length"], str(len(result.content)))

    def test_fileresponse_is_untouched(self):
        response = FileResponse(open(__file__, "rb"))
        result = self.middleware.process_response(self.request, response)
        self.assertIs(result, response)
        response.close()

    def test_content_disposition_robots(self):
        for fname in ["robots.txt", "favicon.ico", "sitemap.xml"]:
            response = HttpResponse("data", content_type="text/plain")
            response["Content-Disposition"] = f"attachment; filename={fname}"
            result = self.middleware.process_response(self.request, response)
            self.assertIs(result, response)

    def test_content_is_robots(self):
        class DummyResponse(HttpResponse):
            pass

        for content in ["robots.txt", "favicon.ico", "sitemap.xml"]:
            response = DummyResponse(content, content_type="text/plain")
            result = self.middleware.process_response(self.request, response)
            self.assertEqual(result, content.encode("utf-8"))

    def test_non_html_response(self):
        response = HttpResponse("data", content_type="application/json")
        result = self.middleware.process_response(self.request, response)
        self.assertIs(result, response)
