"""
smarter.common.utils.conversion
===============================

Conversion utility functions for the Smarter framework.

This module provides functions to convert between different naming conventions,
such as camelCase, PascalCase, and snake_case, for strings, dictionary keys, and lists.
These utilities help maintain consistency in data representation across the framework
and are compatible with Python 3, Django, DRF, and Pydantic.

Functions
---------
- to_snake_case(obj): Converts camelCase or PascalCase strings (or class/type objects) to snake_case.
- camel_to_snake(data): Converts camelCase strings, dict keys, or lists to snake_case.
- camel_to_snake_dict(dictionary): Recursively converts dict keys from camelCase to snake_case.
- pascal_to_snake(name): Converts PascalCase strings, dict keys, or lists to snake_case.
- to_camel_case(data, convert_values=False): Converts snake_case strings, dict keys, or lists to camelCase.

Example
-------
.. code-block:: python

    from smarter.common.utils import to_snake_case, camel_to_snake, to_camel_case

    print(to_snake_case("UserProfile"))  # Output: user_profile
    print(camel_to_snake("userName"))    # Output: user_name
    print(to_camel_case("user_name"))   # Output: userName
"""

import re
from functools import lru_cache
from typing import Any, Union

from smarter.common.exceptions import SmarterValueError
from smarter.lib import logging

logger = logging.getLogger(__name__)
logger_prefix = logging.formatted_text(__name__)

LRU_MAXSIZE = 128  # Default max size for LRU caches in this module
SNAKE_PATTERN = re.compile(r"(?<!^)(?=[A-Z])")

ConvertibleCaseType = Union[str, dict[str, object], list[object], object]
"""
A type alias representing data that can be converted between different case
formats. This includes strings, dictionaries with string keys, lists of such
elements, or any object.
"""


@lru_cache(maxsize=LRU_MAXSIZE)
def _convert_snake_to_camel(name: str) -> str:
    components = name.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


def to_camel_case(data: ConvertibleCaseType, convert_values: bool = False, is_recursive: bool = False) -> Any:
    """
    Converts snake_case strings, dictionary keys, or lists of such, to camelCase format.

    :param data: The input to convert. Can be a string, a dictionary (with snake_case keys), or a list containing strings or dictionaries.
    :type data: str, dict, or list

    :param convert_values: If ``True``, string values within dictionaries are also converted to camelCase. Default is ``False``.
    :type convert_values: bool, optional

    :return: The converted data in camelCase format. Returns a string, dictionary, or list, matching the input type.
    :rtype: Any

    .. note::
        - For dictionaries, only keys are converted by default. If ``convert_values`` is set, string values are also converted.
        - Nested dictionaries and lists are processed recursively.

    .. warning::
        If the input is not a string, dictionary, or list, a ``SmarterValueError`` is raised.

    **Example usage:**

    .. code-block:: python

        from smarter.common.utils import to_camel_case

        # Convert a string
        print(to_camel_case("user_name"))  # Output: userName

        # Convert a dictionary
        data = {
            "user_name": "alice",
            "user_profile": {
                "first_name": "Alice",
                "last_name": "Smith"
            }
        }
        print(to_camel_case(data))
        # Output: {'userName': 'alice', 'userProfile': {'firstName': 'Alice', 'lastName': 'Smith'}}

        # Convert a list of strings
        print(to_camel_case(["first_name", "last_name"]))
        # Output: ['firstName', 'lastName']

        # Convert values as well
        data = {"user_name": "first_name"}
        print(to_camel_case(data, convert_values=True))
        # Output: {'userName': 'firstName'}

    """
    if isinstance(data, str):
        return _convert_snake_to_camel(data)

    if isinstance(data, list) and convert_values:
        return [to_camel_case(item, convert_values=convert_values, is_recursive=True) for item in data]

    if not isinstance(data, dict):
        return data

    # For dictionaries, convert keys and optionally the values as well
    retval = {}
    for key, value in data.items():
        if isinstance(value, dict):
            value = to_camel_case(data=value, convert_values=convert_values, is_recursive=True)
        new_key = _convert_snake_to_camel(key)
        if convert_values:
            new_value = _convert_snake_to_camel(value) if isinstance(value, str) else value
        else:
            new_value = value
        retval[new_key] = new_value
    if not is_recursive:
        logger.debug("%s.to_camel_case() - converted '%s' to '%s'", logger_prefix, data, retval)
    return retval


@lru_cache(maxsize=LRU_MAXSIZE)
def _convert_camel_to_snake(name: str):
    # convert PascalCase to pascalCase to ensure proper snake_case conversion
    name = name[0].lower() + name[1:] if len(name) > 1 and name[0].isupper() else name.lower()

    # replace spaces with underscores
    name = name.replace(" ", "_")

    # convert camelCase to snake_case using regex
    name = name[0].lower() + name[1:] if name and len(name) > 1 and name[0].isupper() else name

    # handle acronyms and consecutive uppercase letters
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    result = re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()
    result = re.sub("_+", "_", result)
    result = re.sub("-+", "_", result)
    return result


def camel_to_snake(data: ConvertibleCaseType, convert_values: bool = False) -> Any:
    """
    Converts camelCase strings, dictionary keys, or lists of such, to snake_case format.

    :param data: The input to convert. Can be a string, a dictionary (with camelCase keys), or a list containing strings or dictionaries.
    :type data: ConvertibleCaseType

    :return: The converted data in snake_case format. Returns a string, dictionary, or list, matching the input type.
    :rtype: Any

    .. note::
        - For dictionaries, only keys are converted. Values are preserved as-is, except for nested dictionaries, which are also converted.
        - Spaces in keys are replaced with underscores.
        - Multiple consecutive underscores are collapsed into a single underscore.
        - Nested dictionaries and lists are processed recursively.

    .. warning::
        If the input is not a string, dictionary, or list, a ``SmarterValueError`` is raised.

    **Example usage:**

    .. code-block:: python

        from smarter.common.utils import camel_to_snake

        # Convert a string
        print(camel_to_snake("userName"))  # Output: user_name

        # Convert a dictionary
        data = {
            "userName": "alice",
            "userProfile": {
                "firstName": "Alice",
                "lastName": "Smith"
            }
        }
        print(camel_to_snake(data))
        # Output: {'user_name': 'alice', 'user_profile': {'first_name': 'Alice', 'last_name': 'Smith'}}

        # Convert a list of strings
        print(camel_to_snake(["firstName", "lastName"]))
        # Output: ['first_name', 'last_name']
    """

    if isinstance(data, str):
        return _convert_camel_to_snake(data)
    elif isinstance(data, list):
        if convert_values:
            return [camel_to_snake(item, convert_values=convert_values) for item in data]
        return data
    elif isinstance(data, dict):
        if convert_values:
            retval = {}
            for key, value in data.items():
                key = _convert_camel_to_snake(key)
                if isinstance(value, dict) and convert_values:
                    value = camel_to_snake(data=value, convert_values=convert_values)
                elif isinstance(value, list) and convert_values:
                    value = [camel_to_snake(item, convert_values=convert_values) for item in value]
                retval[key] = value
            return retval
        return data
    else:
        try:
            data_str = data.__name__ if hasattr(data, "__name__") else str(data)  # type: ignore
            return camel_to_snake(data_str, convert_values=convert_values)
        except Exception as e:
            raise SmarterValueError(f"Received an unsupported type: {type(data)}") from e


def pascal_to_snake(name: ConvertibleCaseType) -> Any:
    return camel_to_snake(name)


def to_snake_case(obj: ConvertibleCaseType, convert_values: bool = False) -> str:
    return camel_to_snake(obj, convert_values=convert_values)


def camel_to_snake_dict(dictionary: dict[str, object], convert_values: bool = False) -> dict[str, object]:
    return camel_to_snake(dictionary, convert_values=convert_values)


__all__ = [
    "to_snake_case",
    "camel_to_snake",
    "camel_to_snake_dict",
    "pascal_to_snake",
    "to_camel_case",
    "ConvertibleCaseType",
]
