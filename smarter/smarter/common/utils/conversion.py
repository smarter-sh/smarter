"""
Smarter.common.utils.conversion
===============================

Case conversion utility functions for the Smarter framework.

This module provides functions to convert between different naming conventions,
such as camelCase, PascalCase, and snake_case, for strings, dictionary keys, and lists.
These utilities assure consistent treatment to/from various case formats.

Functions
---------
- to_snake_case(obj): Converts camelCase or PascalCase strings (or class/type objects) to snake_case.
- to_camel_case(data, convert_values=False): Converts snake_case strings, dict keys, or lists to camelCase.

Example
-------
.. code-block:: python

    from smarter.common.utils import to_snake_case, to_snake_case, to_camel_case

    print(to_snake_case("UserProfile"))  # Output: user_profile
    print(to_snake_case("userName"))     # Output: user_name
    print(to_camel_case("user_name"))    # Output: userName
"""

import re
from functools import lru_cache
from typing import Any, Union

from smarter.common.exceptions import SmarterValueError
from smarter.lib import logging

logger = logging.getLogger(__name__)
logger_prefix = logging.formatted_text(__name__)

LRU_MAXSIZE = 32  # Default max size for LRU caches in this module
SNAKE_PATTERN = re.compile(r"(?<!^)(?=[A-Z])")

ConvertibleCaseType = Union[str, dict[str, object], list[object], object]
"""
A type alias representing data that can be converted between different case.

formats. This includes strings, dictionaries with string keys, lists of such
elements, or any object.
"""


@lru_cache(maxsize=LRU_MAXSIZE)
def _convert_snake_to_camel(name: str) -> str:
    components = name.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


def to_camel_case(data: ConvertibleCaseType, convert_values: bool = False, is_recursive: bool = False) -> Any:
    """
    Convert snake_case strings, dictionary keys, or lists to camelCase format.

    Args:
        data (str | dict | list):
            The input to convert. Can be a string, a dictionary (with snake_case keys),
            or a list containing strings or dictionaries.
        convert_values (bool, optional):
            If True, string values within dictionaries and lists are also converted to camelCase.
            Default is False.

    Returns:
        Any: The converted data in camelCase format. The return type matches the input type (str, dict, or list).

    Notes:
        - For dictionaries, only keys are converted by default. If ``convert_values`` is True, string values are also converted.
        - Nested dictionaries and lists are processed recursively.
        - If the input is not a string, dictionary, or list, the original value is returned.

    Raises:
        SmarterValueError: If the input is not a string, dictionary, or list, and cannot be converted.

    Examples:
        >>> from smarter.common.utils import to_camel_case

        # Convert a string
        >>> to_camel_case("user_name")
        'userName'

        # Convert a dictionary
        >>> data = {
        ...     "user_name": "alice",
        ...     "user_profile": {
        ...         "first_name": "Alice",
        ...         "last_name": "Smith"
        ...     }
        ... }
        >>> to_camel_case(data)
        {'userName': 'alice', 'userProfile': {'firstName': 'Alice', 'lastName': 'Smith'}}

        # Convert a list of strings
        >>> to_camel_case(["first_name", "last_name"])
        ['firstName', 'lastName']

        # Convert values as well
        >>> data = {"user_name": "first_name"}
        >>> to_camel_case(data, convert_values=True)
        {'userName': 'firstName'}
    """
    if isinstance(data, str):
        return _convert_snake_to_camel(data)
    elif isinstance(data, list):
        return [to_camel_case(item, convert_values=convert_values, is_recursive=True) for item in data]
    elif isinstance(data, dict):
        # For dictionaries, convert keys and optionally the values as well
        retval = {}
        for key, value in data.items():
            key = _convert_snake_to_camel(key)
            if convert_values:
                value = to_camel_case(value, convert_values=convert_values, is_recursive=True)
            retval[key] = value
        if not is_recursive:
            logger.debug("%s.to_camel_case() - converted '%s' to '%s'", logger_prefix, data, retval)
        return retval
    else:
        try:
            data_str = data.__name__ if hasattr(data, "__name__") else str(data)  # type: ignore
            return to_camel_case(data_str, convert_values=convert_values)
        except Exception as e:
            raise SmarterValueError(f"Received an unsupported type: {type(data)}") from e


@lru_cache(maxsize=LRU_MAXSIZE)
def _convert_camel_to_snake(name: str):
    name = name.replace(" ", "_").replace("-", "_")

    # Split acronym boundaries such as `LLMClient` -> `LLM_Client` before the general camelCase split.
    name = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", "_", name)
    name = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", name).lower()
    return re.sub(r"_+", "_", name)


def to_snake_case(data: ConvertibleCaseType, convert_values: bool = False) -> Any:
    """
    Convert camelCase or PascalCase strings, dictionary keys, or lists to snake_case format.

    Args:
        data (str | dict | list):
            The input to convert. Can be a string, a dictionary (with camelCase or PascalCase keys),
            or a list containing strings or dictionaries.
        convert_values (bool, optional):
            If True, string values within dictionaries and lists are also converted to snake_case.
            Default is False.

    Returns:
        Any: The converted data in snake_case format. The return type matches the input type (str, dict, or list).

    Notes:
        - For dictionaries, only keys are converted by default. If ``convert_values`` is True, string values are also converted.
        - Spaces in keys are replaced with underscores.
        - Multiple consecutive underscores are collapsed into a single underscore.
        - Nested dictionaries and lists are processed recursively.
        - If the input is not a string, dictionary, or list, the function attempts to convert its string representation.

    Raises:
        SmarterValueError: If the input is not a string, dictionary, or list, and cannot be converted.

    Examples:
        >>> from smarter.common.utils import to_snake_case

        # Convert a string
        >>> to_snake_case("userName")
        'user_name'

        # Convert a dictionary
        >>> data = {
        ...     "userName": "alice",
        ...     "userProfile": {
        ...         "firstName": "Alice",
        ...         "lastName": "Smith"
        ...     }
        ... }
        >>> to_snake_case(data)
        {'user_name': 'alice', 'user_profile': {'first_name': 'Alice', 'last_name': 'Smith'}}

        # Convert a list of strings
        >>> to_snake_case(["firstName", "lastName"])
        ['first_name', 'last_name']
    """

    if isinstance(data, str):
        return _convert_camel_to_snake(data)
    elif isinstance(data, list):
        logger.debug("%s.to_snake_case() - converting list: %s", logger_prefix, data)
        return [
            to_snake_case(item, convert_values=convert_values) if isinstance(item, (dict, list)) else item
            for item in data
        ]
    elif isinstance(data, dict):
        logger.debug("%s.to_snake_case() - converting dict: %s", logger_prefix, data)
        retval = {}
        for key, value in data.items():
            key = _convert_camel_to_snake(key)
            if isinstance(value, dict) and convert_values:
                value = to_snake_case(data=value, convert_values=convert_values)
            elif isinstance(value, list) and convert_values:
                value = [to_snake_case(item, convert_values=convert_values) for item in value]
            retval[key] = value
        return retval
    else:
        try:
            data_str = data.__name__ if hasattr(data, "__name__") else str(data)  # type: ignore
            return to_snake_case(data_str, convert_values=convert_values)
        except Exception as e:
            raise SmarterValueError(f"Received an unsupported type: {type(data)}") from e


__all__ = [
    "to_snake_case",
    "to_camel_case",
    "ConvertibleCaseType",
]
