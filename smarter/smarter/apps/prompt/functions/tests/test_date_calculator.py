"""Test :mod:`smarter.apps.prompt.functions.date_calculator`, the date calculator tool for LLM function calling."""

import unittest

from openai.types.chat.chat_completion_message_tool_call import (
    ChatCompletionMessageToolCall,
    Function,
)

from smarter.lib import json
from smarter.lib.unittest.base_classes import SmarterTestBase

from ..date_calculator import date_calculator, date_calculator_tool_factory


def calculate(**arguments) -> dict:
    """Call the date calculator with ``arguments``, and return its single result."""
    call = ChatCompletionMessageToolCall(
        id="test_date_calculator",
        function=Function(name="date_calculator", arguments=json.dumps(arguments)),
        type="function",
    )
    result = date_calculator(call)
    assert len(result) == 1
    return result[0]


class TestDateCalculator(SmarterTestBase):
    """Test each operation of date_calculator(), and its errors."""

    def test_difference(self):
        result = calculate(dates=["2024-01-01", "2024-12-31"], operation="difference")
        self.assertEqual(result["difference_days"], 365)
        self.assertEqual(result["difference_weeks"], round(365 / 7, 2))
        self.assertIn("error", calculate(dates=["2024-01-01"], operation="difference"))

    def test_difference_is_the_default_operation(self):
        self.assertEqual(calculate(dates=["2024-01-01", "2024-01-11"])["difference_days"], 10)

    def test_add_and_subtract(self):
        self.assertEqual(calculate(dates=["2024-02-28"], operation="add", days=2)["result"], "2024-03-01T00:00:00")
        self.assertEqual(calculate(dates=["2024-03-01"], operation="subtract", days=1)["result"], "2024-02-29T00:00:00")
        for operation in ("add", "subtract"):
            with self.subTest(operation=operation):
                self.assertIn("error", calculate(dates=["2024-01-01", "2024-01-02"], operation=operation))
                self.assertIn("error", calculate(dates=["2024-01-01"], operation=operation, days="many"))

    def test_oldest_and_newest(self):
        dates = ["2020-05-01", "1999-12-31", "2030-01-01"]
        self.assertEqual(calculate(dates=dates, operation="oldest"), {"oldest": "1999-12-31T00:00:00"})
        self.assertEqual(calculate(dates=dates, operation="newest"), {"newest": "2030-01-01T00:00:00"})

    def test_convert(self):
        self.assertEqual(
            calculate(dates=["2024-07-04"], operation="convert", date_format="US"), {"converted": "07/04/2024"}
        )
        self.assertEqual(
            calculate(dates=["2024-07-04"], operation="convert", date_format="EU"), {"converted": "04/07/2024"}
        )
        self.assertEqual(
            calculate(dates=["2024-07-04"], operation="convert", date_format="ISO"),
            {"converted": "2024-07-04T00:00:00"},
        )
        self.assertIn("error", calculate(dates=["2024-07-04"], operation="convert"))
        self.assertIn("error", calculate(dates=["2024-07-04", "2024-07-05"], operation="convert", date_format="US"))

    def test_errors(self):
        """Test that missing dates, an unknown operation or format, and an unparsable date each return an error."""
        cases = [
            {},
            {"dates": []},
            {"dates": ["2024-01-01"], "operation": "multiply"},
            {"dates": ["2024-01-01"], "operation": "convert", "date_format": "JP"},
            {"dates": ["not a date"], "operation": "oldest"},
        ]
        for arguments in cases:
            with self.subTest(arguments=arguments):
                self.assertIn("error", calculate(**arguments))

    def test_invalid_arguments(self):
        """Test that arguments that are not json, or not a json object, return an error."""
        for arguments in ("{not json", "[1, 2]"):
            with self.subTest(arguments=arguments):
                call = ChatCompletionMessageToolCall(
                    id="test_date_calculator",
                    function=Function(name="date_calculator", arguments=arguments),
                    type="function",
                )
                self.assertIn("error", date_calculator(call)[0])

    @unittest.expectedFailure
    def test_difference_of_aware_and_naive_dates(self):
        """
        Test that the difference of a date with a time zone and one without is an error, rather than an exception.

        Expected to fail: date_calculator() subtracts the parsed dates without handling the
        TypeError that subtracting an offset-aware from an offset-naive datetime raises.
        """
        self.assertIn("error", calculate(dates=["2024-01-01T00:00:00Z", "2024-01-02"], operation="difference"))

    def test_tool_factory(self):
        tool = date_calculator_tool_factory()
        self.assertEqual(tool["function"]["name"], "date_calculator")
        self.assertIn("dates", tool["function"]["parameters"]["properties"])
