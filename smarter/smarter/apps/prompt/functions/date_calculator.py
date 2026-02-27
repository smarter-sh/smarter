# pylint: disable=broad-exception-caught
"""
This module provides date calculation functions for use with the OpenAI API
function calling feature.

Overview
--------
The main purpose of this module is to enable basic calculations on serialized
date values, suitable for integration with LLM function calling. It includes
reliability, logging, and signal features.

Features
--------
- Calculates the difference between two dates.
- Determines the oldest or newest date from a list.
- Converts a date to alternative date formats (ISO, US, EU).
- Emits custom signals when tools are presented, requested, and responded to,
  for integration with other system components.
- Logging is controlled via a Waffle switch and respects the configured log level.
- Handles errors gracefully, including invalid date formats.

Dependencies
------------
- pandas
- dateutil

Signals
-------
- `llm_tool_presented`
- `llm_tool_requested`
- `llm_tool_responded`

See individual function documentation for usage details.
"""

import datetime
import logging
from typing import List, Optional

from dateutil import parser
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


class DateCalculatorError(Exception):
    """Custom exception for date calculator errors."""


class DateCalculatorOperations(SmarterEnum):
    """Supported operations for the date calculator."""

    DIFFERENCE = "difference"
    OLDEST = "oldest"
    NEWEST = "newest"
    CONVERT = "convert"
    ADD = "add"
    SUBTRACT = "subtract"


class DateCalculatorFormats(SmarterEnum):
    """Supported date formats for conversion."""

    ISO = "ISO"
    US = "US"
    EU = "EU"


class DateCalculatorParameters(SmarterEnum):
    """Parameter names for the date calculator."""

    DATES = "dates"
    OPERATION = "operation"
    DATE_FORMAT = "date_format"
    DAYS = "days"


def date_calculator(tool_call: ChatCompletionMessageToolCall) -> list:
    """
    Performs basic calculations on serialized date values.

    Supported operations:
    - difference: Calculate the difference in days between two dates.
    - oldest: Find the oldest date in a list.
    - newest: Find the newest date in a list.
    - convert: Convert a date to an alternative format (ISO, US, EU).
    - add: Add a specified number of days to a date.
    - subtract: Subtract a specified number of days from a date.

    Parameters
    ----------
    tool_call : ChatCompletionMessageToolCall
        The OpenAI tool call object containing metadata about the request.

        .. code-block:: json

            {
                "id": "call_uXe8gjFjqppjkx2lNL7StOZz",
                "function": {
                    "arguments": "{\"dates\":[\"1966-12-31\",\"2026-02-27\"],\"operation\":\"difference\"}",
                    "name": "date_calculator"
                },
                "type": "function"
            }

    Returns
    -------
    list
        A JSON-compatible list containing the result or error message.
    """

    # Unescape and parse arguments if needed
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
        dates: List[str] = arguments.get(DateCalculatorParameters.DATES, [])
        logger.debug(f"{logger_prefix} Extracted dates: {dates}")
    except Exception as e:
        logger.error(
            f"{logger_prefix} Unexpected error processing tool call arguments: {arguments} leading to the following exception. {e}"
        )
        return [
            {
                "error": f'Unexpected error processing arguments: {e}. Received arguments: {arguments}. Expected arguments in the format: {{"{DateCalculatorParameters.DATES}": ["date1", "date2"], "{DateCalculatorParameters.OPERATION}": "operation_name", "{DateCalculatorParameters.DATE_FORMAT}": "format_name"}}'
            }
        ]

    if not dates or len(dates) == 0:
        return [{"error": f"No {DateCalculatorParameters.DATES} provided. Please provide at least one date."}]

    try:
        operation: str = arguments.get(DateCalculatorParameters.OPERATION, DateCalculatorOperations.DIFFERENCE)
        logger.debug(f"{logger_prefix} Extracted operation: {operation}")
    except Exception as e:
        logger.error(
            f"{logger_prefix} Unexpected error processing operation argument: {arguments} leading to the following exception. {e}"
        )
        return [
            {
                "error": f'Unexpected error processing arguments: {e}. Received arguments: {arguments}. Expected arguments in the format: {{"{DateCalculatorParameters.DATES}": ["date1", "date2"], "{DateCalculatorParameters.OPERATION}": "operation_name", "{DateCalculatorParameters.DATE_FORMAT}": "format_name"}}'
            }
        ]
    if not operation or operation not in DateCalculatorOperations.all():
        return [
            {
                "error": f"Invalid or missing {DateCalculatorParameters.OPERATION}. Supported operations are: {', '.join(DateCalculatorOperations.all())}."
            }
        ]

    try:
        date_format: Optional[str] = arguments.get(DateCalculatorParameters.DATE_FORMAT)
        logger.debug(f"{logger_prefix} Extracted date format: {date_format}")
    except Exception as e:
        logger.error(
            f"{logger_prefix} Unexpected error processing date format argument: {arguments} leading to the following exception. {e}"
        )
        return [
            {
                "error": f'Unexpected error processing arguments: {e}. Received arguments: {arguments}. Expected arguments in the format: {{"{DateCalculatorParameters.DATES}": ["date1", "date2"], "{DateCalculatorParameters.OPERATION}": "operation_name", "{DateCalculatorParameters.DATE_FORMAT}": "format_name"}}'
            }
        ]
    if date_format and date_format not in DateCalculatorFormats.all():
        return [
            {
                "error": f"Invalid {DateCalculatorParameters.DATE_FORMAT}. Supported formats are: {', '.join(DateCalculatorFormats.all())}."
            }
        ]

    llm_tool_requested.send(
        sender=date_calculator,
        tool_call=tool_call.model_dump(),
        dates=dates,
        operation=operation,
        date_format=date_format,
    )

    try:
        parsed_dates: list[datetime.datetime] = [parser.parse(d) for d in dates]
        logger.debug(f"{logger_prefix} Parsed dates: {parsed_dates}")
    except Exception as e:
        logger.error(f"{logger_prefix} Error parsing dates: {e}")
        return [{"error": f"Invalid date format: {e}"}]

    result = None
    if operation == DateCalculatorOperations.DIFFERENCE:
        if len(parsed_dates) != 2:
            result = {"error": f"Provide exactly two dates for {DateCalculatorOperations.DIFFERENCE} calculation."}
        else:
            diff = abs((parsed_dates[0] - parsed_dates[1]).days)
            result = {
                "difference_days": diff,
                "difference_years": round(diff / 365.25, 2),
                "difference_months": round(diff / 30.44, 2),
                "difference_weeks": round(diff / 7, 2),
            }
    elif operation == DateCalculatorOperations.ADD:
        if len(parsed_dates) != 1:
            result = {"error": f"Provide exactly one date for {DateCalculatorOperations.ADD} operation."}
        else:
            try:
                days_to_add = int(arguments.get("days", 0))
                new_date = parsed_dates[0] + datetime.timedelta(days=days_to_add)
                result = {"result": new_date.isoformat()}
            except Exception as e:
                logger.error(f"{logger_prefix} Error processing add operation: {e}")
                result = {"error": f"Invalid or missing 'days' parameter for add operation: {e}"}
    elif operation == DateCalculatorOperations.SUBTRACT:
        if len(parsed_dates) != 1:
            result = {"error": f"Provide exactly one date for {DateCalculatorOperations.SUBTRACT} operation."}
        else:
            try:
                days_to_subtract = int(arguments.get("days", 0))
                new_date = parsed_dates[0] - datetime.timedelta(days=days_to_subtract)
                result = {"result": new_date.isoformat()}
            except Exception as e:
                logger.error(f"{logger_prefix} Error processing subtract operation: {e}")
                result = {"error": f"Invalid or missing 'days' parameter for subtract operation: {e}"}
    elif operation == DateCalculatorOperations.OLDEST:
        oldest = min(parsed_dates)
        result = {"oldest": oldest.isoformat()}
    elif operation == DateCalculatorOperations.NEWEST:
        newest = max(parsed_dates)
        result = {"newest": newest.isoformat()}
    elif operation == DateCalculatorOperations.CONVERT:
        if len(parsed_dates) != 1:
            result = {"error": f"Provide exactly one date for {DateCalculatorOperations.CONVERT} operation."}
        else:
            dt = parsed_dates[0]
            if date_format == DateCalculatorFormats.ISO:
                result = {"converted": dt.isoformat()}
            elif date_format == DateCalculatorFormats.US:
                result = {"converted": dt.strftime("%m/%d/%Y")}
            elif date_format == DateCalculatorFormats.EU:
                result = {"converted": dt.strftime("%d/%m/%Y")}
            else:
                result = {
                    "error": f"Unsupported date format. Use {DateCalculatorFormats.ISO}, {DateCalculatorFormats.US}, or {DateCalculatorFormats.EU}."
                }
    else:
        result = {
            "error": f"Unsupported {DateCalculatorParameters.OPERATION}. Use {DateCalculatorOperations.DIFFERENCE}, {DateCalculatorOperations.OLDEST}, {DateCalculatorOperations.NEWEST}, or {DateCalculatorOperations.CONVERT}."
        }

    llm_tool_responded.send(
        sender=date_calculator,
        tool_call=tool_call.model_dump(),
        tool_response=result,
    )
    return [result]


def date_calculator_tool_factory() -> dict:
    """
    Constructs and returns a JSON-compatible dictionary defining the date calculator tool for OpenAI LLM function calling.

    This factory function builds the tool specification required by the OpenAI API to enable function calling from language models.
    The returned dictionary describes the `date_calculator` function, including its name, description, and parameter schema.
    The schema specifies the expected input parameters (`dates`, `operation`, `date_format`), their types, and constraints.

    The function also emits a signal (`llm_tool_presented`) to notify other system components that the tool definition has been presented.

    Returns
    -------
    dict
        A dictionary containing the tool definition for `date_calculator`, formatted for OpenAI LLM function calling.
    """
    tool = {
        "type": "function",
        "function": {
            "name": date_calculator.__name__,
            "description": f"Perform basic calculations on date values, including any of the following operations: {DateCalculatorOperations.list_all()}.",
            "parameters": {
                "type": "object",
                "properties": {
                    DateCalculatorParameters.DATES: {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of date strings to process, in any common format (e.g., 'YYYY-MM-DD', 'MM/DD/YYYY', etc.) that is readily convertible to Python datetime. The expected number of dates depends on the operation: 2 for 'difference', 1 or more for 'oldest'/'newest', and exactly 1 for 'convert'.",
                    },
                    DateCalculatorParameters.OPERATION: {
                        "type": "string",
                        "enum": DateCalculatorOperations.all(),
                        "description": "The operation to perform.",
                    },
                    DateCalculatorParameters.DATE_FORMAT: {
                        "type": "string",
                        "enum": DateCalculatorFormats.all(),
                        "description": f"Target format for conversion (only for {DateCalculatorOperations.CONVERT} operation. required for {DateCalculatorOperations.CONVERT} operation).",
                    },
                    DateCalculatorParameters.DAYS: {
                        "type": "integer",
                        "description": f"Number of days to add or subtract (required for {DateCalculatorOperations.ADD} and {DateCalculatorOperations.SUBTRACT} operations).",
                    },
                },
                "required": [DateCalculatorParameters.DATES, DateCalculatorParameters.OPERATION],
            },
        },
    }
    llm_tool_presented.send(sender=date_calculator_tool_factory, tool=tool)
    return tool
