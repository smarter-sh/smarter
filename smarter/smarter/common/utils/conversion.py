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

LRU_MAXSIZE = 128  # Default max size for LRU caches in this module
SNAKE_PATTERN = re.compile(r"(?<!^)(?=[A-Z])")
ACRONYM_PATTERN = re.compile(r"([A-Z]+)([A-Z][a-z])")
CAMEL_PATTERN = re.compile(r"([a-z0-9])([A-Z])")


ConvertibleCaseType = Union[str, dict[str, Any], list[Any]]
"""
A type alias representing data that can be converted between different case.

formats. This includes strings, dictionaries with string keys, lists of such
elements, or any object.
"""


@lru_cache(maxsize=LRU_MAXSIZE)
def _convert_snake_to_camel(name: str) -> str:
    components = name.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


# pylint: disable=W0613
def to_camel_case(data: ConvertibleCaseType, convert_values: bool = False, is_recursive: bool = True) -> Any:
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
        return [
            (
                to_camel_case(item, convert_values=convert_values, is_recursive=is_recursive)
                if isinstance(item, (dict, list)) and is_recursive
                else _convert_snake_to_camel(item) if isinstance(item, str) and convert_values else item
            )
            for item in data
        ]
    elif isinstance(data, dict):
        retval = {}
        for key, value in data.items():
            key = _convert_snake_to_camel(key) if isinstance(key, str) else key
            if isinstance(value, dict) and is_recursive:
                value = to_camel_case(data=value, convert_values=convert_values, is_recursive=is_recursive)
            elif isinstance(value, list) and is_recursive:
                value = [
                    to_camel_case(item, convert_values=convert_values, is_recursive=is_recursive) for item in value
                ]
            elif convert_values and isinstance(value, str):
                value = _convert_snake_to_camel(value)
            retval[key] = value
        return retval
    else:
        return data  # Return the original data if it's not a string, dict, or list, without raising an error.


@lru_cache(maxsize=LRU_MAXSIZE)
def _convert_camel_to_snake(name: str):
    name = name.replace(" ", "_").replace("-", "_")

    # Split acronym boundaries such as `LLMClient` -> `LLM_Client` before the general camelCase split.
    name = re.sub(ACRONYM_PATTERN, r"\1_\2", name)
    name = re.sub(CAMEL_PATTERN, r"\1_\2", name).lower()
    return re.sub(r"_+", "_", name)


def to_snake_case(data: ConvertibleCaseType, convert_values: bool = False, is_recursive: bool = True) -> Any:
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
        - If the input is not a string, dictionary, or list, the original value is returned.

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

    .. caution::

        key collisions may occur when converting from camelCase to snake_case.
        For example, "userName" and "user_name" would both convert to "user_name".
        In such cases, the last key processed will overwrite previous keys in the
        resulting dictionary.
    """

    if isinstance(data, str):
        return _convert_camel_to_snake(data)
    elif isinstance(data, list):
        return [
            (
                to_snake_case(item, convert_values=convert_values, is_recursive=is_recursive)
                if isinstance(item, (dict, list)) and is_recursive
                else _convert_camel_to_snake(item) if isinstance(item, str) and convert_values else item
            )
            for item in data
        ]
    elif isinstance(data, dict):
        retval = {}
        for key, value in data.items():
            key = _convert_camel_to_snake(key) if isinstance(key, str) else key
            if isinstance(value, dict) and is_recursive:
                value = to_snake_case(data=value, convert_values=convert_values, is_recursive=is_recursive)
            elif isinstance(value, list) and is_recursive:
                value = [
                    to_snake_case(item, convert_values=convert_values, is_recursive=is_recursive) for item in value
                ]
            elif convert_values and isinstance(value, str):
                value = _convert_camel_to_snake(value)
            retval[key] = value
        return retval
    else:
        return data  # Return the original data if it's not a string, dict, or list, without raising an error.


def search_replace(
    data: Union[dict[str, Any], list[Any]], replace_str: str, with_str: str
) -> Union[dict[str, Any], list[Any]]:
    """
    Recursively search through a dictionary and replace all occurrences of a specified string with another string.

    Args:
        data (dict): The input dictionary to search through.
        replace_str (str): The string to search for in the dictionary keys and values.
        with_str (str): The string to replace the found string with.

    Returns:
        Union[dict[str, Any], list[Any]]: A new dictionary or list with the specified replacements made.

    Notes:
        - This function will recursively search through nested dictionaries and lists within the input dictionary.
        - Only string keys and string values will be checked for replacements. Non-string types will be left unchanged.
        - This is particularly useful for handling legacy datauration formats where certain keys or values need to be updated for compatibility reasons, such as replacing 'chatbot' with 'llm_client' in prompt datauration dictionaries to maintain
    ·     compatibility with older versions of the React app that expect 'chatbot' instead of 'llm_client'.
    """
    if isinstance(data, dict):
        retval = {}
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                value = search_replace(value, replace_str, with_str)
            if replace_str in key:
                key = key.replace(replace_str, with_str)
            if key.lower().replace("_", "") == replace_str.lower().replace("_", ""):
                key = with_str
            retval[key] = value
    elif isinstance(data, list):
        retval = [
            search_replace(item, replace_str, with_str) if isinstance(item, (dict, list)) else item for item in data
        ]
    else:
        raise ValueError("Input data must be a dictionary or a list.")
    return retval


__all__ = [
    "to_snake_case",
    "to_camel_case",
    "search_replace",
    "ConvertibleCaseType",
]
