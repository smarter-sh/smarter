"""
Logger helpers - Helper functions for formatting log messages with ANSI color.

codes for better readability in logs.
"""

from typing import Union
from warnings import deprecated

from smarter.lib import json
from smarter.lib.json import SmarterJSONEncoder


class SmarterFormattedTextColorCodes:
    """ANSI color codes for formatted text in logs."""

    BRIGHT_GREEN = "\033[92m"
    REGULAR_GREEN = "\033[32m"
    DARK_RED = "\033[31m"
    DEFAULT = "\033[1;31m"  # Default to bold dark red for emphasis in logs
    RESET = "\033[0m"


@deprecated("Use formatted_text with color_code parameter instead")
def formatted_json(json_obj: Union[dict, list]) -> str:
    """
    Format a JSON object as a pretty-printed string with ANSI color codes for.

    better readability in logs.

    .. param json_obj: The JSON object (dict or list) to format.
    .. return: A string representation of the JSON object with ANSI color codes.
    """
    pretty_json = json.dumps(json_obj, cls=SmarterJSONEncoder)
    return f"{SmarterFormattedTextColorCodes.REGULAR_GREEN}{pretty_json}{SmarterFormattedTextColorCodes.RESET}"


@deprecated("Use formatted_text with color_code parameter instead")
def formatted_text(text: str, color_code: str = SmarterFormattedTextColorCodes.DEFAULT) -> str:
    """
    Format a text string with ANSI color codes for better readability in logs.

    .. param text: The text string to format.
    .. param color_code: The ANSI color code to apply.
    .. return: A string representation of the text with ANSI color codes.
    """

    return f"{color_code}{text}{SmarterFormattedTextColorCodes.RESET}"
