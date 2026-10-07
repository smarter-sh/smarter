"""Test :mod:`smarter.apps.prompt.functions.calculator`, the calculator tool for LLM function calling."""

import math

from openai.types.chat.chat_completion_message_tool_call import (
    ChatCompletionMessageToolCall,
    Function,
)

from smarter.lib import json
from smarter.lib.unittest.base_classes import SmarterTestBase

from ..calculator import CalculatorError, calculator, calculator_tool_factory, safe_eval


def tool_call(arguments) -> ChatCompletionMessageToolCall:
    """Return a tool call of the calculator, whose arguments are json, unless they are a str already."""
    if not isinstance(arguments, str):
        arguments = json.dumps(arguments)
    return ChatCompletionMessageToolCall(
        id="test_calculator", function=Function(name="calculator", arguments=arguments), type="function"
    )


class TestSafeEval(SmarterTestBase):
    """Test safe_eval(), which evaluates only numbers, operators and math functions."""

    def test_operators_and_functions(self):
        cases = {
            "1 + 2 * 3": 7,
            "(1 + 2) * 3": 9,
            "10 / 4": 2.5,
            "2 ** 10": 1024,
            "10 % 3": 1,
            "-5 + +2": -3,
            "7 - 10": -3,
            "sqrt(16)": 4.0,
            "max(1, 5, 3) + min(2, 4)": 7,
            "abs(-3) + round(2.6) + pow(2, 3)": 14,
            "pi": math.pi,
            "degrees(pi)": 180.0,
        }
        for expression, expected in cases.items():
            with self.subTest(expression=expression):
                self.assertAlmostEqual(safe_eval(expression), expected)

    def test_refused(self):
        """Test that names, strings, other operators and syntax errors are refused."""
        for expression in (
            "__import__('os')",
            "open",
            "'a'",
            "1 // 2",
            "~1",
            "[1, 2]",
            "1 +",
            "sqrt",
            "1 / 0",
        ):
            with self.subTest(expression=expression), self.assertRaises(CalculatorError):
                safe_eval(expression)


class TestCalculator(SmarterTestBase):
    """Test calculator(), the function that the LLM calls, and its tool definition."""

    def test_calculator(self):
        self.assertEqual(calculator(tool_call({"expression": "(2 + 2) * 10"})), [{"result": 40}])

    def test_arguments_as_dict(self):
        """Test that arguments that were already parsed are accepted."""
        call = tool_call({"expression": "1 + 1"})
        call.function.arguments = {"expression": "1 + 1"}  # type: ignore[assignment]
        self.assertEqual(calculator(call), [{"result": 2}])

    def test_errors(self):
        """Test that invalid arguments, a missing expression and a bad expression each return an error."""
        for arguments in ("{not json", ["a list"], {}, {"expression": 42}, {"expression": "1 +"}):
            with self.subTest(arguments=arguments):
                result = calculator(tool_call(arguments))
                self.assertEqual(len(result), 1)
                self.assertIn("error", result[0])

    def test_no_arguments(self):
        call = tool_call("{}")
        call.function.arguments = ""
        self.assertIn("error", calculator(call)[0])

    def test_tool_factory(self):
        tool = calculator_tool_factory()
        self.assertEqual(tool["type"], "function")
        self.assertEqual(tool["function"]["name"], "calculator")
        self.assertIn("expression", tool["function"]["parameters"]["properties"])
