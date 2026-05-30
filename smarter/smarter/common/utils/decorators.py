"""
Decorators for converting function return values between camelCase and snake_case.
"""

from functools import wraps
from typing import Callable

from .conversion import camel_to_snake, to_camel_case


def snake_case(convert_values: bool = False):
    """
    Decorator to convert the return value of a function from camelCase to snake_case.
    """

    def decorator(func: Callable) -> Callable:

        @wraps(func)
        def wrapper(*args, **kwargs):

            function_return = func(*args, **kwargs)
            converted_return = camel_to_snake(function_return, convert_values=convert_values)
            return converted_return

        return wrapper

    return decorator


def camel_case(convert_values: bool = False):
    """
    Decorator to convert the return value of a function from snake_case to camelCase.
    """

    def decorator(func: Callable) -> Callable:

        @wraps(func)
        def wrapper(*args, **kwargs):

            function_return = func(*args, **kwargs)
            converted_return = to_camel_case(function_return, convert_values=convert_values)
            return converted_return

        return wrapper

    return decorator


__all__ = ["snake_case", "camel_case"]
