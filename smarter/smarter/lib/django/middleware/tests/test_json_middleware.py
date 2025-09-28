"""test JsonErrorMiddleware class"""

from unittest.mock import MagicMock

from django.http import HttpResponse, JsonResponse

from smarter.lib import json
from smarter.lib.django.middleware.json import JsonErrorMiddleware
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestJsonErrorMiddleware(SmarterTestBase):
    """Test the JsonErrorMiddleware class."""

    def setUp(self):
        super().setUp()
        self.middleware = JsonErrorMiddleware(get_response=MagicMock())

    def test_process_response_non_json_accept(self):
        request = MagicMock()
        request.headers = {"Accept": "text/html"}
        response = HttpResponse(status=404, reason="Not Found")
        result = self.middleware.process_response(request, response)
        self.assertIs(result, response)

    def test_process_response_json_accept_non_error(self):
        request = MagicMock()
        request.headers = {"Accept": "application/json"}
        response = HttpResponse(status=200, reason="OK")
        result = self.middleware.process_response(request, response)
        self.assertIs(result, response)

    def test_process_response_json_accept_error(self):
        request = MagicMock()
        request.headers = {"Accept": "application/json"}
        response = HttpResponse(status=404, reason="Not Found")
        result = self.middleware.process_response(request, response)
        self.assertIsInstance(result, JsonResponse)
        self.assertEqual(result.status_code, 404)
        result_json = json.loads(result.content.decode("utf-8"))
        self.assertEqual(result_json, {"error": {"status_code": 404, "message": "Not Found"}})

    def test_process_response_json_accept_error_already_json(self):
        request = MagicMock()
        request.headers = {"Accept": "application/json"}
        response = JsonResponse({"foo": "bar"}, status=404)
        result = self.middleware.process_response(request, response)
        self.assertIs(result, response)
