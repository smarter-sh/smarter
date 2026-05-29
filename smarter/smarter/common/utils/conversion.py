"""
Utility functions for the Smarter framework.

This module provides a collection of helper functions and classes
that are ostensibly implemented in more than one Smarter base class.
Hence, they are only here in order to keep the code DRY (Don't Repeat Yourself).

The module is intended for internal use within the Smarter framework and is
designed to be compatible with Python 3, Django, DRF, and Pydantic.

"""

import logging
import re
from functools import lru_cache
from typing import Optional, Union
from warnings import deprecated

from smarter.common.exceptions import SmarterValueError
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib.cache import cache_results
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

logger = logging.getLogger(__name__)
logger_prefix = formatted_text(__name__)

FOREVER = 60 * 60 * 24 * 365  # 1 year in seconds
SNAKE_PATTERN = re.compile(r"(?<!^)(?=[A-Z])")


# pylint: disable=W0613
def should_log_verbose(level):
    """Check if logging should be done based on the waffle switch."""
    # pylint: disable=C0415
    from smarter.common.conf import smarter_settings

    return smarter_settings.verbose_logging


verbose_logger = WaffleSwitchedLoggerWrapper(logger, should_log_verbose)


def camel_to_snake_dict(dictionary: dict) -> dict:
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
    verbose_logger.debug("%s.camel_to_snake_dict()", logger_prefix)

    @lru_cache(maxsize=128)
    def convert(name: str):
        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()

    retval = {}
    for key, value in dictionary.items():
        if isinstance(value, dict):
            value = camel_to_snake_dict(value)
        new_key = convert(key)
        retval[new_key] = value
    return retval


def recursive_sort_dict(d):
    """
    Recursively sorts a dictionary by its keys.

    :param d: The input dictionary to be sorted. Nested dictionaries are also sorted recursively.
    :type d: dict

    :return: A new dictionary with all keys sorted in ascending order. If a value is itself a dictionary, it is also sorted recursively.
    :rtype: dict

    .. note::
        This function is useful for producing deterministic dictionary outputs, such as for testing, serialization, or comparison purposes.

    .. warning::
        Non-dictionary values are left unchanged. Lists, sets, and other types within the dictionary are not sorted or modified.

    **Example usage:**

    .. code-block:: python

        from smarter.common.utils import recursive_sort_dict

        data = {
            "b": 2,
            "a": {
                "d": 4,
                "c": 3
            }
        }

        sorted_data = recursive_sort_dict(data)
        print(sorted_data)
        # Output: {'a': {'c': 3, 'd': 4}, 'b': 2}

    """
    verbose_logger.debug("%s.recursive_sort_dict()", logger_prefix)
    return {k: recursive_sort_dict(v) if isinstance(v, dict) else v for k, v in sorted(d.items())}


def dict_is_contained_in(dict1, dict2):
    """
    Checks whether all keys and values in ``dict1`` are present in ``dict2``, recursively.

    :param dict1: The dictionary whose keys and values are to be checked for containment.
    :type dict1: dict

    :param dict2: The dictionary in which to check for the presence of keys and values from ``dict1``.
    :type dict2: dict

    :return: Returns ``True`` if every key in ``dict1`` exists in ``dict2`` and the corresponding values match (including nested dictionaries). Returns ``False`` otherwise.
    :rtype: bool

    .. note::
        This function prints diagnostic messages to standard output if a key or value is missing or mismatched. Nested dictionaries are checked recursively.

    .. warning::
        The function is not silent: it prints to standard output when a mismatch is found. This may not be suitable for production use where logging is preferred.

    **Example usage:**

    .. code-block:: python

        from smarter.common.utils import dict_is_contained_in

        model = {
            "name": "Alice",
            "profile": {
                "age": 30,
                "city": "Wonderland"
            }
        }

        test = {
            "name": "Alice",
            "profile": {
                "age": 30,
                "city": "Wonderland"
            },
            "extra": "value"
        }

        result = dict_is_contained_in(model, test)
        print(result)  # True

        # Example with missing key
        test_missing = {
            "name": "Alice"
        }
        result = dict_is_contained_in(model, test_missing)
        print(result)  # False

    """
    verbose_logger.debug("%s.dict_is_contained_in()", logger_prefix)
    for key, value in dict1.items():
        if key not in dict2:
            print(f"the key {key} is not present in the model dict: ")
            return False
        if isinstance(value, dict):
            if not dict_is_contained_in(value, dict2[key]):
                print("dict not in the model dict: ", value)
                return False
        else:
            if dict2[key] != value:
                print(f"value {value} is not present in the model dict: ")
                return False
    return True


def dict_is_subset(small, big) -> bool:
    """
    Recursively checks that all items in the dictionary ``small`` exist in the dictionary ``big``.

    :param small: The dictionary (or list) whose items should be checked for existence in ``big``.
    :type small: dict or list

    :param big: The dictionary (or list) in which to check for the presence of items from ``small``.
    :type big: dict or list

    :return: Returns ``True`` if every item in ``small`` exists in ``big`` (including nested dictionaries and lists). Returns ``False`` otherwise.
    :rtype: bool

    .. note::
        - For dictionaries, all keys and their corresponding values must exist in ``big``.
        - For lists, all elements in ``small`` must be present in ``big``; order does not matter.
        - Nested dictionaries and lists are checked recursively.

    .. warning::
        This function does not print diagnostic messages. It is designed for silent, recursive subset checking. For more verbose output, use ``dict_is_contained_in``.

    **Example usage:**

    .. code-block:: python

        from smarter.common.utils import dict_is_subset

        big = {
            "name": "Alice",
            "profile": {
                "age": 30,
                "city": "Wonderland"
            },
            "roles": ["admin", "user"]
        }

        small = {
            "profile": {
                "age": 30
            },
            "roles": ["admin"]
        }

        result = dict_is_subset(small, big)
        print(result)  # True

        # Example with missing value
        small_missing = {
            "profile": {
                "age": 31
            }
        }
        result = dict_is_subset(small_missing, big)
        print(result)  # False

    """
    verbose_logger.debug("%s.dict_is_subset()", logger_prefix)
    if isinstance(small, dict) and isinstance(big, dict):
        for k, v in small.items():
            if k not in big:
                return False
            if not dict_is_subset(v, big[k]):
                return False
        return True
    elif isinstance(small, list) and isinstance(big, list):
        # Check that all items in 'small' are in 'big' (order does NOT matter)
        for sv in small:
            if isinstance(sv, dict):
                if not any(dict_is_subset(sv, bv) for bv in big if isinstance(bv, dict)):
                    return False
            else:
                if sv not in big:
                    return False
        return True
    else:
        return small == big


###############################################################################
# Conversion functions for string case formats (camelCase, snake_case,
# PascalCase)
###############################################################################


def snake_to_camel(data: Union[str, dict, list], convert_values: bool = False) -> Optional[Union[str, dict, list]]:
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
    verbose_logger.debug("%s.snake_to_camel()", logger_prefix)

    @lru_cache(maxsize=128)
    def convert(name: str) -> str:
        components = name.split("_")
        return components[0] + "".join(x.title() for x in components[1:])

    if isinstance(data, str):
        return convert(data)

    if isinstance(data, list):
        return [snake_to_camel(item, convert_values=convert_values) for item in data]

    if not isinstance(data, dict):
        raise SmarterValueError(f"Expected data to be a dict or list, got: {type(data)}")

    dictionary: dict = data if isinstance(data, dict) else {}
    retval = {}
    for key, value in dictionary.items():
        if isinstance(value, dict):
            value = snake_to_camel(data=value, convert_values=convert_values)
        new_key = convert(key)
        if convert_values:
            new_value = convert(value) if isinstance(value, str) else value
        else:
            new_value = value
        retval[new_key] = new_value
    return retval


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
    verbose_logger.debug("%s.pascal_to_snake()", logger_prefix)

    @lru_cache(maxsize=128)
    def _convert_str(s: str) -> str:
        s = s.replace(" ", "_")
        result = SNAKE_PATTERN.sub("_", s).lower()
        result = re.sub("_+", "_", result)
        return result

    if isinstance(name, str):
        return _convert_str(name)
    elif isinstance(name, list):
        return [pascal_to_snake(item) for item in name]
    elif isinstance(name, dict):
        return {
            pascal_to_snake(k): pascal_to_snake(v) if isinstance(v, (dict, list, str)) else v for k, v in name.items()
        }
    else:
        return name


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

    @lru_cache(maxsize=128)
    def convert(name: str):
        name = name.replace(" ", "_")
        name = name[0].lower() + name[1:] if name and len(name) > 1 and name[0].isupper() else name
        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        result = re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()
        result = re.sub("_+", "_", result)
        result = re.sub("-+", "_", result)
        return result

    if isinstance(data, str):
        return convert(data)
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
        new_key = convert(key)
        retval[new_key] = value
    return retval


def to_snake_case(obj) -> str:
    """
    Convert camelCase or PascalCase to snake_case for URL naming.

    :param name: The camelCase or PascalCase string to convert.
    :return: The converted snake_case string.
    :rtype: str
    """

    @cache_results(timeout=FOREVER)
    def convert(val: str) -> str:
        retval = str(camel_to_snake(val))
        retval = str(pascal_to_snake(retval))
        return retval

    if isinstance(obj, str):
        return convert(obj)
    else:
        return convert(obj.__name__)


@deprecated("Use to_snake_case() instead. This function will be removed in a future release.")
def snake_case(name: str) -> str:
    """
    Deprecated function. Use `to_snake_case()` instead.
    """
    return to_snake_case(name)


@lru_cache(maxsize=128)
def rfc1034_compliant_str(val) -> str:
    """
    Generates a RFC 1034-compliant name string suitable for use as a DNS label or resource identifier.

    :param val: The input string to convert to RFC 1034-compliant format.
    :type val: str

    :return: A string that is:
        - lower case
        - contains only alphanumeric characters and hyphens
        - starts and ends with an alphanumeric character
        - has a maximum length of 63 characters
    :rtype: str

    :raises SmarterValueError: If the input is not a string or is empty after conversion.

    .. note::
        - Underscores in the input are replaced with hyphens.
        - Invalid characters (anything other than a-z, 0-9, or '-') are removed.
        - Leading and trailing hyphens are stripped.
        - The result is truncated to 63 characters if necessary.

    .. warning::
        This function is intended for generating DNS-safe names. It does not guarantee uniqueness or suitability for all RFC 1034 use cases.

    **Example usage:**

    .. code-block:: python

        from smarter.common.utils import rfc1034_compliant_str

        # Basic usage
        print(rfc1034_compliant_str("My_ChatBot_2025"))  # Output: my-chatbot-2025

        # With special characters
        print(rfc1034_compliant_str("My@Bot!_Name"))  # Output: my-bot-name

        # With long input
        long_name = "ThisIsAReallyLongChatBotNameThatShouldBeTruncatedToSixtyThreeCharacters_Extra"
        print(rfc1034_compliant_str(long_name))  # Output: thisisareallylongchatbotnamethatshouldbetruncatedtosixtythreecharacters

    """
    if not isinstance(val, str):
        raise SmarterValueError(f"Could not generate RFC 1034 compliant name from {type(val)}")
    # Replace underscores with hyphens
    label = val.lower().replace("_", "-")
    # Remove invalid characters
    label = re.sub(r"[^a-z0-9-]", "", label)
    # Remove leading/trailing hyphens
    label = label.strip("-")
    # Truncate to 63 characters
    if label:
        return label[:63]
    else:
        raise SmarterValueError("Could not generate RFC 1034 compliant name from empty string")


@lru_cache(maxsize=128)
def rfc1034_compliant_to_snake(val) -> str:
    """
    Converts a RFC 1034-compliant name (typically used for DNS labels or resource identifiers) to a more human-readable ``snake_case`` name.

    This function is useful for translating machine-friendly names (which use hyphens as word separators) into Pythonic identifiers (which use underscores).

    :param val: The RFC 1034-compliant name to convert. This should be a string containing only lowercase letters, numbers, and hyphens.
    :type val: str

    :return: The converted name in ``snake_case`` format, with hyphens replaced by underscores.
    :rtype: str

    :raises SmarterValueError: If the input is not a string.

    .. note::
        - Only hyphens are replaced; other characters are preserved.
        - The function does not validate that the input is strictly RFC 1034-compliant. It assumes the input is already sanitized.

    .. warning::
        This function does not handle conversion of other non-alphanumeric characters. If the input contains characters other than hyphens, underscores, letters, or numbers, they will remain unchanged.

    **Example usage:**

    .. code-block:: python

        from smarter.common.utils import rfc1034_compliant_to_snake

        # Basic conversion
        print(rfc1034_compliant_to_snake("my-chatbot-2025"))
        # Output: my_chatbot_2025

        # Input with no hyphens
        print(rfc1034_compliant_to_snake("simplelabel"))
        # Output: simplelabel

        # Input with multiple hyphens
        print(rfc1034_compliant_to_snake("this-is-a-test-label"))
        # Output: this_is_a_test_label

        # Input with invalid type
        try:
            rfc1034_compliant_to_snake(12345)
        except SmarterValueError as e:
            print(e)
        # Output: Could not convert RFC 1034 compliant name from <class 'int'>
    """
    verbose_logger.debug("%s.rfc1034_compliant_to_snake()", logger_prefix)
    if not isinstance(val, str):
        raise SmarterValueError(f"Could not convert RFC 1034 compliant name from {type(val)}")
    # Replace hyphens with underscores
    name = val.replace("-", "_")
    return name


__all__ = [
    "to_snake_case",
    "camel_to_snake",
    "camel_to_snake_dict",
    "dict_is_contained_in",
    "dict_is_subset",
    "pascal_to_snake",
    "rfc1034_compliant_str",
    "rfc1034_compliant_to_snake",
    "recursive_sort_dict",
    "snake_case",
    "snake_to_camel",
]
