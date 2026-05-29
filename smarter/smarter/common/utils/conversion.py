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
- snake_to_camel(data, convert_values=False): Converts snake_case strings, dict keys, or lists to camelCase.

Example
-------
.. code-block:: python

    from smarter.common.utils import to_snake_case, camel_to_snake, snake_to_camel

    print(to_snake_case("UserProfile"))  # Output: user_profile
    print(camel_to_snake("userName"))    # Output: user_name
    print(snake_to_camel("user_name"))   # Output: userName
"""

import re
from functools import lru_cache
from typing import Optional, Union

from smarter.common.exceptions import SmarterValueError
from smarter.lib import logging

logger = logging.getLogger(__name__)
logger_prefix = logging.formatted_text(__name__)

LRU_MAXSIZE = 128  # Default max size for LRU caches in this module
SNAKE_PATTERN = re.compile(r"(?<!^)(?=[A-Z])")


@lru_cache(maxsize=LRU_MAXSIZE)
def _convert_to_camel(name: str):
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def camel_to_snake_dict(dictionary: dict, is_recursive: bool = False) -> dict:
    """
    Converts the keys of a dictionary from camelCase to snake_case recursively.

    :param dictionary: The input dictionary whose keys are in camelCase format. Nested dictionaries are also converted.
    :type dictionary: dict

    :return: A new dictionary with all keys converted to snake_case. Nested dictionaries are processed recursively.
    :rtype: dict

    .. note::
        This function only converts dictionary keys. Values are preserved as-is, except for nested dictionaries, which are also converted.

    .. warning::
        Keys that are not strings will not be converted. If a key is already in snake_case, it will remain unchanged.

    **Example usage:**

    .. code-block:: python

        from smarter.common.utils import camel_to_snake_dict

        data = {
            "userName": "alice",
            "userProfile": {
                "firstName": "Alice",
                "lastName": "Smith"
            }
        }

        result = camel_to_snake_dict(data)
        print(result)
        # Output: {'user_name': 'alice', 'user_profile': {'first_name': 'Alice', 'last_name': 'Smith'}}

    """
    logger.debug("%s.camel_to_snake_dict()", logger_prefix)

    retval = {}
    for key, value in dictionary.items():
        if isinstance(value, dict) and is_recursive:
            value = camel_to_snake_dict(value, is_recursive=True)
        new_key = _convert_to_camel(key)
        retval[new_key] = value
    if not is_recursive:
        logger.debug("%s.camel_to_snake_dict() - converted '%s' to '%s'", logger_prefix, dictionary, retval)
    return retval


@lru_cache(maxsize=LRU_MAXSIZE)
def _convert_snake_to_camel(name: str) -> str:
    components = name.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


def snake_to_camel(
    data: Union[str, dict, list], convert_values: bool = False, is_recursive: bool = False
) -> Optional[Union[str, dict, list]]:
    """
    Converts snake_case strings, dictionary keys, or lists of such, to camelCase format.

    :param data: The input to convert. Can be a string, a dictionary (with snake_case keys), or a list containing strings or dictionaries.
    :type data: str, dict, or list

    :param convert_values: If ``True``, string values within dictionaries are also converted to camelCase. Default is ``False``.
    :type convert_values: bool, optional

    :return: The converted data in camelCase format. Returns a string, dictionary, or list, matching the input type.
    :rtype: Optional[Union[str, dict, list]]

    .. note::
        - For dictionaries, only keys are converted by default. If ``convert_values`` is set, string values are also converted.
        - Nested dictionaries and lists are processed recursively.

    .. warning::
        If the input is not a string, dictionary, or list, a ``SmarterValueError`` is raised.

    **Example usage:**

    .. code-block:: python

        from smarter.common.utils import snake_to_camel

        # Convert a string
        print(snake_to_camel("user_name"))  # Output: userName

        # Convert a dictionary
        data = {
            "user_name": "alice",
            "user_profile": {
                "first_name": "Alice",
                "last_name": "Smith"
            }
        }
        print(snake_to_camel(data))
        # Output: {'userName': 'alice', 'userProfile': {'firstName': 'Alice', 'lastName': 'Smith'}}

        # Convert a list of strings
        print(snake_to_camel(["first_name", "last_name"]))
        # Output: ['firstName', 'lastName']

        # Convert values as well
        data = {"user_name": "first_name"}
        print(snake_to_camel(data, convert_values=True))
        # Output: {'userName': 'firstName'}

    """
    if not isinstance(data, (str, dict, list)):
        raise SmarterValueError(f"Expected data to be a str, dict, or list, got: {type(data)}")

    if isinstance(data, str):
        return _convert_snake_to_camel(data)

    if isinstance(data, list):
        return [snake_to_camel(item, convert_values=convert_values, is_recursive=True) for item in data]

    if not isinstance(data, dict):
        raise SmarterValueError(f"Expected data to be a dict or list, got: {type(data)}")

    dictionary: dict = data if isinstance(data, dict) else {}
    retval = {}
    for key, value in dictionary.items():
        if isinstance(value, dict):
            value = snake_to_camel(data=value, convert_values=convert_values, is_recursive=True)
        new_key = _convert_snake_to_camel(key)
        if convert_values:
            new_value = _convert_snake_to_camel(value) if isinstance(value, str) else value
        else:
            new_value = value
        retval[new_key] = new_value
    if not is_recursive:
        logger.debug("%s.snake_to_camel() - converted '%s' to '%s'", logger_prefix, data, retval)
    return retval


@lru_cache(maxsize=LRU_MAXSIZE)
def _convert_pascal_to_snake(s: str) -> str:
    s = s.replace(" ", "_")
    result = SNAKE_PATTERN.sub("_", s).lower()
    result = re.sub("_+", "_", result)
    return result


def pascal_to_snake(name: Union[str, dict, list]) -> Union[str, dict, list]:
    """
    Converts a PascalCase string to pascal_case snake_case format.

    :param name: The PascalCase string to convert.
    :type name: str

    :return: The converted string in snake_case format.
    :rtype: str

    .. note::
        - Spaces in the input string are replaced with underscores.
        - Multiple consecutive underscores are collapsed into a single underscore.

    **Example usage:**

    .. code-block:: python

        from smarter.common.utils import pascal_to_snake

        print(pascal_to_snake("UserProfile"))  # Output: user_profile
        print(pascal_to_snake("FirstName LastName"))  # Output: first_name_last_name

    """
    if isinstance(name, str):
        retval = _convert_pascal_to_snake(name)
    elif isinstance(name, list):
        retval = [pascal_to_snake(item) for item in name]
    elif isinstance(name, dict):
        retval = {
            pascal_to_snake(k): pascal_to_snake(v) if isinstance(v, (dict, list, str)) else v for k, v in name.items()
        }
    else:
        retval = name
    return retval


@lru_cache(maxsize=LRU_MAXSIZE)
def _convert_camel_to_snake(name: str):
    name = name.replace(" ", "_")
    name = name[0].lower() + name[1:] if name and len(name) > 1 and name[0].isupper() else name
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    result = re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()
    result = re.sub("_+", "_", result)
    result = re.sub("-+", "_", result)
    return result


def camel_to_snake(data: Union[str, dict, list]) -> Optional[Union[str, dict, list]]:
    """
    Converts camelCase strings, dictionary keys, or lists of such, to snake_case format.

    :param data: The input to convert. Can be a string, a dictionary (with camelCase keys), or a list containing strings or dictionaries.
    :type data: str, dict, or list

    :return: The converted data in snake_case format. Returns a string, dictionary, or list, matching the input type.
    :rtype: Optional[Union[str, dict, list]]

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
    if isinstance(data, list):
        return [camel_to_snake(item) for item in data]
    if not isinstance(data, dict):
        raise SmarterValueError(f"Expected data to be a dict or list, got: {type(data)}")
    dictionary: dict = data if isinstance(data, dict) else {}
    retval = {}
    for key, value in dictionary.items():
        if isinstance(value, dict):
            value = camel_to_snake(value)
        elif isinstance(value, list):
            value = [camel_to_snake(item) for item in value]
        new_key = _convert_camel_to_snake(key)
        retval[new_key] = value
    return retval


@lru_cache(maxsize=LRU_MAXSIZE)
def _convert_to_snake_case(val: str) -> str:
    """
    handle high-level conversion logic for to_snake_case, which includes
    both camelCase and PascalCase conversion to snake_case, then
    cache to a longer-lasting persistent cache to optimize for repeat
    conversions of the same strings.
    """
    retval = str(camel_to_snake(val))
    retval = str(pascal_to_snake(retval))
    return retval


def to_snake_case(obj) -> str:
    """
    Converts a camelCase or PascalCase string (or class/type object) to
    snake_case format, suitable for URL naming or Python identifiers.

    Handles both camelCase and PascalCase inputs, and can also accept a
    class or type object (using its `__name__`). The conversion is cached
    long term.

    :param obj: The string or class/type object to convert. If a string, it is converted directly. If a class/type, its `__name__` is used.
    :type obj: str or type

    :return: The converted snake_case string.
    :rtype: str

    .. note::
        - Spaces and hyphens are replaced with underscores.
        - Multiple consecutive underscores are collapsed into a single underscore.
        - The conversion is case-insensitive and works for both camelCase and PascalCase.
        - Results are cached for performance on repeated conversions of the same strings.

    **Example usage:**

    .. code-block:: python

        from smarter.common.utils import to_snake_case

        class MyClass:
            pass

        print(to_snake_case("UserProfile"))  # Output: user_profile
        print(to_snake_case("userName"))     # Output: user_name
        print(to_snake_case(MyClass))        # Output: my_class

    """

    if isinstance(obj, str):
        retval = _convert_to_snake_case(obj)
    else:
        retval = _convert_to_snake_case(obj.__name__)
    logger.debug("%s.to_snake_case() - converted '%s' to '%s'", logger_prefix, obj, retval)
    return retval


__all__ = [
    "to_snake_case",
    "camel_to_snake",
    "camel_to_snake_dict",
    "pascal_to_snake",
    "snake_to_camel",
]
