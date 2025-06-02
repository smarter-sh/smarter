"""Test logger helper functions."""

import datetime

from smarter.lib.unittest.base_classes import SmarterTestBase

from ..logger_helpers import formatted_json, formatted_text


class TestLoggerHelpers(SmarterTestBase):
    """Test logger helper functions."""

    def test_formatted_json_basic(self):
        data = {"a": 1, "b": 2}
        result = formatted_json(data)
        self.assertTrue(result.startswith("\033[32m"))
        self.assertTrue(result.endswith("\033[0m"))
        self.assertIn('"a": 1', result)
        self.assertIn('"b": 2', result)

    def test_formatted_json_with_datetime(self):
        now = datetime.datetime(2024, 1, 1, 12, 0, 0)
        data = {"now": now}
        result = formatted_json(data)
        self.assertIn("2024-01-01T12:00:00", result)

    def test_formatted_json_type_error(self):
        class Foo:
            pass

        data = {"foo": Foo()}
        with self.assertRaises(TypeError):
            formatted_json(data)

    def test_formatted_text(self):
        text = "hello"
        result = formatted_text(text)
        self.assertTrue(result.startswith("\033[1;31m"))
        self.assertTrue(result.endswith("\033[0m"))
        self.assertIn("hello", result)
