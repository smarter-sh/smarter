"""Logging utilities for the Smarter app."""

from typing import Callable

from smarter.common.helpers.console_helpers import SmarterFormattedText


def function_name(func: Callable) -> str:
    """
    Return the dotted name of a function, for logging.

    :param func: The function, e.g. :func:`verify_model_text_input`.
    :returns: Its module and qualified name followed by parentheses, e.g.
        ``smarter.apps.provider.verification.provider_model.verify_model_text_input()``.
    """
    return f"{func.__module__}.{func.__qualname__}()"


def formatted_log_prefix(func: Callable) -> str:
    """
    Return the formatted prefix for logging a function.

    :param func: The function, e.g. :func:`verify_model_text_input`.
    :returns: The formatted module and function name.
    """
    return SmarterFormattedText.text(function_name(func))
