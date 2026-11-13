"""Test :mod:`smarter.lib.unittest.narrowing`."""

import unittest

from django.http import HttpResponse, StreamingHttpResponse

from smarter.lib.unittest.narrowing import http_response, json_list, json_object


class TestNarrowing(unittest.TestCase):
    """Each function returns what the test expected, and fails it clearly otherwise."""

    def test_json_object(self) -> None:
        value = {"data": 1}
        self.assertIs(json_object(value), value)
        with self.assertRaisesRegex(AssertionError, "body is not a JSON object, but list"):
            json_object([1], "body")

    def test_json_list(self) -> None:
        value = [1, 2]
        self.assertIs(json_list(value), value)
        with self.assertRaisesRegex(AssertionError, "value is not a JSON array, but NoneType"):
            json_list(None)

    def test_http_response(self) -> None:
        response = HttpResponse(b"ok")
        self.assertIs(http_response(response), response)
        with self.assertRaisesRegex(AssertionError, "StreamingHttpResponse"):
            http_response(StreamingHttpResponse(iter([b"ok"])))
