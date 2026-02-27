# pylint: disable=broad-exception-caught
"""
This module provides calculator functions for use with the OpenAI API function calling feature.

Overview
--------
The main purpose of this module is to enable basic arithmetic and trigonometric calculations, suitable for integration with LLM function calling. It includes reliability, logging, and signal features.

Features
--------
- Performs addition, subtraction, multiplication, and division.
- Supports basic trigonometric functions: sin, cos, tan, asin, acos, atan, degrees, radians.
- Emits custom signals when tools are presented, requested, and responded to, for integration with other system components.
- Logging is controlled via a Waffle switch and respects the configured log level.
- Handles errors gracefully, including invalid input values.

Signals
-------
- `llm_tool_presented`
- `llm_tool_requested`
- `llm_tool_responded`

See individual function documentation for usage details.
"""

import ast
import logging
import math
import operator

from openai.types.chat.chat_completion_message_tool_call import (
    ChatCompletionMessageToolCall,
)

from smarter.apps.prompt.signals import (
    llm_tool_presented,
    llm_tool_requested,
    llm_tool_responded,
)
from smarter.common.enum import SmarterEnum
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib import json
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper


# pylint: disable=W0613
def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.PROMPT_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)
logger_prefix = formatted_text(__name__)


class CalculatorError(Exception):
    """Custom exception for calculator errors."""


class CalculatorOperations(SmarterEnum):
    """Supported operations for the calculator."""

    ADD = "add"
    SUBTRACT = "subtract"
    MULTIPLY = "multiply"
    DIVIDE = "divide"
    SIN = "sin"
    COS = "cos"
    TAN = "tan"
    ASIN = "asin"
    ACOS = "acos"
    ATAN = "atan"
    DEGREES = "degrees"
    RADIANS = "radians"
    EXPRESSION = "expression"  # New: evaluate a string expression


class CalculatorParameters(SmarterEnum):
    """Parameter names for the calculator."""

    EXPRESSION = "expression"


def safe_eval(expr: str) -> float:
    """
    Safely evaluate a mathematical expression string supporting parentheses and math functions.
    Only allows numbers, math functions, and operators.
    """
    allowed_names = {k: getattr(math, k) for k in dir(math) if not k.startswith("_")}
    allowed_names.update(
        {
            "abs": abs,
            "round": round,
            "pow": pow,
            "min": min,
            "max": max,
        }
    )
    # Add built-in constants
    allowed_names["pi"] = math.pi
    allowed_names["e"] = math.e

    class SafeEvalVisitor(ast.NodeVisitor):
        """AST visitor that safely evaluates mathematical expressions."""

        def visit(self, node):
            if isinstance(node, ast.Expression):
                return self.visit(node.body)
            elif isinstance(node, ast.BinOp):
                left = self.visit(node.left)
                right = self.visit(node.right)
                return self._binop(node.op, left, right)
            elif isinstance(node, ast.UnaryOp):
                operand = self.visit(node.operand)
                return self._unaryop(node.op, operand)
            elif isinstance(node, ast.Num):
                return node.n
            elif isinstance(node, ast.Constant):
                if isinstance(node.value, (int, float)):
                    return node.value
                raise CalculatorError("Invalid constant")
            elif isinstance(node, ast.Call):
                func = self.visit(node.func)
                args = [self.visit(arg) for arg in node.args]
                return func(*args)
            elif isinstance(node, ast.Name):
                if node.id in allowed_names:
                    return allowed_names[node.id]
                raise CalculatorError(f"Use of name '{node.id}' not allowed")
            else:
                raise CalculatorError(f"Unsupported expression: {ast.dump(node)}")

        def _binop(self, op, left, right):
            ops = {
                ast.Add: operator.add,
                ast.Sub: operator.sub,
                ast.Mult: operator.mul,
                ast.Div: operator.truediv,
                ast.Pow: operator.pow,
                ast.Mod: operator.mod,
            }
            op_type = type(op)
            if op_type in ops:
                return ops[op_type](left, right)
            raise CalculatorError(f"Unsupported binary operator: {op_type}")

        def _unaryop(self, op, operand):
            ops = {
                ast.UAdd: operator.pos,
                ast.USub: operator.neg,
            }
            op_type = type(op)
            if op_type in ops:
                return ops[op_type](operand)
            raise CalculatorError(f"Unsupported unary operator: {op_type}")

    try:
        tree = ast.parse(expr, mode="eval")
        retval = SafeEvalVisitor().visit(tree)
        if not isinstance(retval, (int, float)):
            raise CalculatorError("Expression did not evaluate to a number")
        return retval
    except Exception as e:
        raise CalculatorError(f"Invalid expression: {e}") from e


def calculator(tool_call: ChatCompletionMessageToolCall) -> list:
    """
    Performs basic arithmetic and trigonometric calculations.
    Accepts a single 'expression' string parameter.
    """
    arguments = None
    if tool_call and tool_call.function and tool_call.function.arguments:
        if isinstance(tool_call.function.arguments, str):
            try:
                arguments = json.loads(tool_call.function.arguments)
                logger.debug(f"{logger_prefix} Parsed arguments: {json.dumps(arguments, indent=4)}")
            except Exception as e:
                logger.error(f"{logger_prefix} Error parsing arguments JSON: {e}")
                return [{"error": f"Invalid arguments JSON: {e}. Received arguments: {tool_call.function.arguments}"}]
        else:
            arguments = tool_call.function.arguments
    else:
        arguments = {}

    try:
        expression: str = arguments.get(CalculatorParameters.EXPRESSION, "")
        logger.debug(f"{logger_prefix} Extracted expression: {expression}")
    except Exception as e:
        logger.error(
            f"{logger_prefix} Unexpected error processing tool call arguments: {arguments} leading to the following exception. {e}"
        )
        return [
            {
                "error": (
                    f"Unexpected error processing arguments: {e}.\n"
                    f"Received arguments: {arguments}.\n"
                    f"Expected arguments in the format: {json.dumps({CalculatorParameters.EXPRESSION: '(2+2)/log(pi)'})}"
                )
            }
        ]

    if not expression or not isinstance(expression, str):
        return [
            {
                "error": f"No {CalculatorParameters.EXPRESSION} provided. Please provide a valid mathematical expression as a string."
            }
        ]

    llm_tool_requested.send(
        sender=calculator,
        tool_call=tool_call.model_dump(),
        expression=expression,
    )

    result = None
    try:
        eval_result = safe_eval(expression)
        result = {"result": eval_result}
    except CalculatorError as e:
        logger.error(f"{logger_prefix} Error during calculation: {e}")
        result = {"error": f"Calculation error: {e}"}

    llm_tool_responded.send(
        sender=calculator,
        tool_call=tool_call.model_dump(),
        tool_response=result,
    )
    return [result]


def calculator_tool_factory() -> dict:
    """
    Constructs and returns a JSON-compatible dictionary defining the calculator tool for OpenAI LLM function calling.

    This factory function builds the tool specification required by the OpenAI API to enable function calling from language models.
    The returned dictionary describes the `calculator` function, including its name, description, and parameter schema.
    The schema specifies the expected input parameters (`numbers`, `operation`), their types, and constraints.

    The function also emits a signal (`llm_tool_presented`) to notify other system components that the tool definition has been presented.

    Returns
    -------
    dict
            A dictionary containing the tool definition for `calculator`, formatted for OpenAI LLM function calling.
    """

    tool = {
        "type": "function",
        "function": {
            "name": calculator.__name__,
            "description": (
                f"""
                Evaluate a mathematical expression string, supporting parentheses and any combination of the
                following math functions: {CalculatorOperations.list_all()}.
                The expression can include numbers, operators (+, -, *, /, **, %), and function calls.
                Example input: '2 + 3 * (4 - 1)' or 'sin(pi / 2) + log(10)'.
                """
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    CalculatorParameters.EXPRESSION: {
                        "type": "string",
                        "description": "A mathematical expression string to evaluate, supporting parentheses and math functions.",
                    },
                },
                "required": [CalculatorParameters.EXPRESSION],
            },
        },
    }
    llm_tool_presented.send(sender=calculator_tool_factory, tool=tool)
    return tool
