"""Test request_to_json utility."""

from unittest.mock import Mock

from django.core.handlers.asgi import ASGIRequest

from smarter.common.utils.request_to_json import request_to_json
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestRequestToJson(SmarterTestBase):
    """Test request_to_json utility."""

    def test_dict_passthrough(self):
        data = {"foo": "bar"}
        result = request_to_json(data)
        self.assertEqual(result, data)

    def test_list_passthrough(self):
        data = [1, 2, 3]
        result = request_to_json(data)
        self.assertEqual(result, data)

    def test_asgirequest_json_body(self):
        mock_request = Mock(spec=ASGIRequest)
        mock_request.body = b'{"key": "value"}'
        mock_request.method = "POST"
        mock_request.build_absolute_uri.return_value = "http://testserver/test/"
        result = request_to_json(mock_request)
        self.assertEqual(result["method"], "POST")  # type: ignore
        self.assertEqual(result["url"], "http://testserver/test/")  # type: ignore
        self.assertEqual(result["body"], {"key": "value"})  # type: ignore

    def test_asgirequest_non_json_body(self):
        mock_request = Mock(spec=ASGIRequest)
        mock_request.body = b"not-json"
        mock_request.method = "GET"
        mock_request.build_absolute_uri.return_value = "http://testserver/"
        result = request_to_json(mock_request)
        self.assertEqual(result["method"], "GET")  # type: ignore
        self.assertEqual(result["url"], "http://testserver/")  # type: ignore
        self.assertIsNone(result["body"])  # type: ignore

    def test_asgirequest_empty_body(self):
        mock_request = Mock(spec=ASGIRequest)
        mock_request.body = b""
        mock_request.method = "PUT"
        mock_request.build_absolute_uri.return_value = "http://testserver/empty/"
        result = request_to_json(mock_request)
        self.assertEqual(result["method"], "PUT")  # type: ignore
        self.assertEqual(result["url"], "http://testserver/empty/")  # type: ignore
        self.assertIsNone(result["body"])  # type: ignore
