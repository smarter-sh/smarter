# pylint: disable=duplicate-code
# pylint: disable=E1101
"""
Utility functions for the Smarter framework.

This module provides a collection of helper functions and classes
that are ostensibly implemented in more than one Smarter base class.
Hence, they are only here in order to keep the code DRY (Don't Repeat Yourself).

The module is intended for internal use within the Smarter framework and is
designed to be compatible with Python 3, Django, DRF, and Pydantic.

"""
import csv
import hashlib
import json  # library for interacting with JSON data https://www.json.org/json-en.html
import logging
import random
import re
import warnings
from datetime import datetime
from typing import Optional, Union

import yaml
from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpRequest
from pydantic import SecretStr
from rest_framework.request import Request

from smarter.common.exceptions import SmarterValueError
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib.django.validators import SmarterValidator


RequestType = Union[HttpRequest, Request, WSGIRequest]
logger = logging.getLogger(__name__)


class DateTimeEncoder(json.JSONEncoder):
    """
    Custom JSON encoder that handles serialization of ``datetime`` objects and ``SecretStr`` values.

    This encoder extends :class:`json.JSONEncoder` to provide special handling for objects that are not natively serializable by the standard JSON encoder.

    - ``datetime`` objects are converted to strings in the format ``YYYY-MM-DD``.
    - ``SecretStr`` objects are redacted and replaced with the string ``"*** REDACTED ***"``.

    :param o: The object to encode. This parameter is handled internally by the encoder and is not set directly by users.
    :type o: Any

    :return: A JSON-serializable representation of the input object.
    :rtype: str

    .. note::
        For all other types, the default encoding behavior of :class:`json.JSONEncoder` is used.

    .. warning::
        This encoder is intended for use cases where redacting sensitive information (such as secrets) and formatting dates is required. It does not handle all possible custom types.

    **Example usage:**

    .. code-block:: python

        import json
        from smarter.common.utils import DateTimeEncoder
        from datetime import datetime
        from pydantic import SecretStr

        data = {
            "created": datetime(2025, 12, 4),
            "password": SecretStr("supersecret"),
            "name": "Alice"
        }

        json_str = json.dumps(data, cls=DateTimeEncoder)
        print(json_str)
        # Output: {"created": "2025-12-04", "password": "*** REDACTED ***", "name": "Alice"}

    """

    def default(self, o):
        if isinstance(o, datetime):
            return o.strftime("%Y-%m-%d")
        if isinstance(o, SecretStr):
            return "*** REDACTED ***"

        return super().default(o)


def is_authenticated_request(request: Optional[RequestType]) -> bool:
    """
    Determines whether the provided request is authenticated.

    :param request: The request object to check. This can be an instance of :class:`django.http.HttpRequest`, :class:`rest_framework.request.Request`, or :class:`django.core.handlers.wsgi.WSGIRequest`. If ``None`` is provided, the function will return ``False``.

    :type request: Optional[Union[HttpRequest, Request, WSGIRequest]]

    :return: Returns ``True`` if the request is authenticated (i.e., the request has a ``user`` attribute and ``user.is_authenticated`` is ``True``). Returns ``False`` otherwise.
    :rtype: bool

    :raises Exception: Any unexpected error during attribute access will be caught and logged; the function will return ``False`` in such cases.

    .. note::
        This function is compatible with Django and Django REST Framework request objects. It also supports WSGIRequest and can be used in unit tests with mock objects that have the required attributes.

    .. warning::
        If the request object does not have a ``user`` attribute, or if ``user.is_authenticated`` is not available, the function will return ``False``. Any exceptions are logged as warnings.

    **Example usage:**

    .. code-block:: python

        from smarter.common.utils import is_authenticated_request
        from django.http import HttpRequest

        request = HttpRequest()
        request.user = SomeUserObject()
        authenticated = is_authenticated_request(request)
        print(authenticated)  # True or False depending on user.is_authenticated

    .. code-block:: python

        # Example with DRF Request
        from rest_framework.request import Request

        drf_request = Request(...)
        authenticated = is_authenticated_request(drf_request)
        print(authenticated)
    """
    try:
        return (
            isinstance(request, (HttpRequest, Request, WSGIRequest))
            and hasattr(request, "user")
            and hasattr(request.user, "is_authenticated")
            and request.user.is_authenticated
        )
    # pylint: disable=W0718
    except Exception as e:
        logger.warning("is_authenticated_request() failed: %s", formatted_text(str(e)))
        return False


def hash_factory(length: int = 16) -> str:
    """
    Generates a random hexadecimal hash string of the specified length.

    :param length: The desired length of the hash string. Must be a positive integer. If the value exceeds the length of a SHA-256 hash (64), the result will be truncated to the maximum available length.
    :type length: int, optional (default is 16)

    :return: A random hexadecimal string of the specified length.
    :rtype: str

    .. note::
        The hash is generated using a random 256-bit integer, encoded with SHA-256, and truncated to the requested length. The output is suitable for use as a unique identifier, token, or nonce in most application contexts.

    .. warning::
        This function does not guarantee cryptographic security for all use cases. For security-critical applications (such as password hashing or cryptographic keys), use dedicated libraries and algorithms.

    **Example usage:**

    .. code-block:: python

        from smarter.common.utils import hash_factory

        # Generate a 16-character random hash
        token = hash_factory()
        print(token)  # e.g., 'a3f9c1e2b4d5f6a7'

        # Generate a 32-character random hash
        long_token = hash_factory(length=32)
        print(long_token)  # e.g., 'a3f9c1e2b4d5f6a7c8e9d0b1a2c3d4e5'

    """
    return hashlib.sha256(str(random.getrandbits(256)).encode("utf-8")).hexdigest()[:length]


def get_readonly_yaml_file(file_path) -> dict:
    """
    Reads a YAML file from the specified path and returns its contents as a Python dictionary.

    :param file_path: The path to the YAML file to be read. This should be a string representing a valid file system path.
    :type file_path: str

    :return: The contents of the YAML file, parsed into a Python dictionary. If the file is empty or contains no valid YAML, ``None`` may be returned.
    :rtype: dict

    .. note::
        This function opens the file in read-only mode with UTF-8 encoding and uses ``yaml.safe_load`` for parsing. Only standard YAML types are supported.

    .. warning::
        If the file does not exist, is not readable, or contains invalid YAML, an exception will be raised. Always validate the file path and contents before use.

    **Example usage:**

    .. code-block:: python

        from smarter.common.utils import get_readonly_yaml_file

        config = get_readonly_yaml_file('/path/to/config.yaml')
        print(config)  # {'key': 'value', ...}

    """
    with open(file_path, encoding="utf-8") as file:
        return yaml.safe_load(file)


def get_readonly_csv_file(file_path):
    """
    Reads a CSV file from the specified path and returns its contents as a list of dictionaries.

    :param file_path: The path to the CSV file to be read. This should be a string representing a valid file system path.
    :type file_path: str

    :return: A list of dictionaries, where each dictionary represents a row in the CSV file. The keys of each dictionary correspond to the column headers in the CSV.
    :rtype: list[dict]

    .. note::
        The file is opened in read-only mode with UTF-8 encoding. The function uses ``csv.DictReader`` to parse the file, which means the first row must contain the column headers.

    .. warning::
        If the file does not exist, is not readable, or is not a valid CSV, an exception will be raised. Always validate the file path and ensure the CSV is properly formatted.

    **Example usage:**

    .. code-block:: python

        from smarter.common.utils import get_readonly_csv_file

        rows = get_readonly_csv_file('/path/to/data.csv')
        for row in rows:
            print(row)  # {'column1': 'value1', 'column2': 'value2', ...}
    """
    with open(file_path, encoding="utf-8") as file:
        reader = csv.DictReader(file)
        return list(reader)


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


def mask_string(string: str, mask_char: str = "*", mask_length: int = 4, string_length: int = 8) -> str:
    """
    Masks a string by replacing all but the last ``mask_length`` characters with ``mask_char``.

    .. deprecated:: 0.10.0
        This function is deprecated and will be removed in a future release.
        Use Pydantic's ``SecretStr`` or other secure alternatives for string masking.

    :param string: The string to mask. If a ``bytes`` object is provided, it will be decoded to UTF-8.
    :type string: str or bytes

    :param mask_char: The character to use for masking. Default is ``'*'``.
    :type mask_char: str, optional

    :param mask_length: The number of characters at the end of the string to leave unmasked. Must be non-negative and less than or equal to the length of the string.
    :type mask_length: int, optional

    :param string_length: The total length of the returned masked string. If the original string is shorter, the result will be truncated or padded accordingly.
    :type string_length: int, optional

    :return: The masked string, with all but the last ``mask_length`` characters replaced by ``mask_char``. The result is truncated to ``string_length`` if necessary.
    :rtype: str

    :raises TypeError: If ``string`` is not a string or bytes.
    :raises ValueError: If ``mask_length`` or ``string_length`` are negative, or if ``mask_length`` exceeds the length of the string.

    .. note::

        - If the input string is shorter than ``mask_length``, the original string is returned.
        - If ``mask_length`` is greater than ``string_length``, it is reduced to ``string_length``.


    **Example usage:**

    .. code-block:: python

        from smarter.common.utils import mask_string

        # Mask all but the last 4 characters
        masked = mask_string("supersecretpassword", mask_char="*", mask_length=4)
        print(masked)  # Output: *************word

        # Mask and truncate to 8 characters
        masked = mask_string("supersecretpassword", mask_char="#", mask_length=3, string_length=8)
        print(masked)  # Output: #####ord

        # Mask a short string
        masked = mask_string("abc", mask_length=4)
        print(masked)  # Output: abc

    """
    warnings.warn(
        "mask_string is deprecated and will be removed in a future release.", DeprecationWarning, stacklevel=2
    )
    if isinstance(string, bytes):
        string = string.decode("utf-8")
    if not isinstance(string, str):
        raise TypeError("string must be a string")
    if len(string) <= mask_length:
        return string
    if mask_length < 0:
        raise ValueError("mask_length must be greater than or equal to 0")
    if string_length < 0:
        raise ValueError("string_length must be greater than or equal to 0")
    if mask_length > len(string):
        raise ValueError("mask_length must be less than or equal to the length of the string")
    if string_length > len(string):
        string_length = len(string)
    if mask_length > string_length:
        mask_length = string_length

    masked_string = (
        f"{f'{mask_char}' * (len(string) - mask_length)}{string[-mask_length:]}"
        if len(string) > mask_length
        else string
    )
    masked_string = masked_string[-string_length:] if len(masked_string) > string_length else masked_string
    return masked_string


def smarter_build_absolute_uri(request: HttpRequest) -> Optional[str]:
    """
    Attempts to construct the absolute URI for a given request object.

    :param request: The request object, which may be an instance of :class:`django.http.HttpRequest`, :class:`rest_framework.request.Request`, :class:`django.core.handlers.wsgi.WSGIRequest`, or a mock object for testing.
    :type request: HttpRequest or compatible type

    :return: The absolute URI as a string, or a fallback test URL if the request is invalid or cannot be resolved.
    :rtype: Optional[str]

    .. note::
        - If the request is a Django REST Framework ``Request``, it is recast to a Django ``HttpRequest``.
        - If the request is a mock object (e.g., from unit tests), a synthetic test URL is returned.
        - The function first tries to use Django's ``build_absolute_uri`` method. If unavailable, it attempts to build the URL from scheme, host, and path attributes.
        - If all attempts fail, a generic fallback URL is returned.

    .. warning::
        If the request is ``None`` or cannot be resolved, the function logs a warning and returns a fallback test URL. Always validate the returned URL before using it in production.

    **Example usage:**

    .. code-block:: python

        from smarter.common.utils import smarter_build_absolute_uri
        from django.http import HttpRequest

        request = HttpRequest()
        request.META['HTTP_HOST'] = 'localhost:8000'
        request.path = '/api/v1/resource/'
        url = smarter_build_absolute_uri(request)
        print(url)  # Output: http://localhost:8000/api/v1/resource/

        # Example with DRF Request
        from rest_framework.request import Request
        drf_request = Request(...)
        url = smarter_build_absolute_uri(drf_request)
        print(url)

        # Example with None
        url = smarter_build_absolute_uri(None)
        print(url)  # Output: http://testserver/unknown/

    """
    if request is None:
        logger.warning("smarter_build_absolute_uri() called with None request")
        return "http://testserver/unknown/"

    if isinstance(request, Request):
        # recast DRF Request to Django HttpRequest
        # pylint: disable=W0212
        request = request._request

    # If it's a unittest.mock.Mock, synthesize a fake URL for testing
    if hasattr(request, "__class__") and request.__class__.__name__ == "Mock":
        logger.info("smarter_build_absolute_uri() called with Mock request; returning fake test URL")
        return "http://testserver/mockpath/"

    # Try to use Django's build_absolute_uri if available
    if hasattr(request, "build_absolute_uri"):
        try:
            url = request.build_absolute_uri()
            if url:
                return url
        # pylint: disable=W0718
        except Exception as e:
            logger.warning(
                "smarter_build_absolute_uri() failed to call request.build_absolute_uri(): %s",
                formatted_text(str(e)),
            )

    # Try to build from scheme, host, and path
    try:
        scheme = getattr(request, "scheme", None) or getattr(request, "META", {}).get("wsgi.url_scheme", "http")
        host = (
            getattr(request, "get_host", lambda: None)()
            or getattr(request, "META", {}).get("HTTP_HOST")
            or getattr(request, "META", {}).get("SERVER_NAME")
            or "testserver"
        )
        path = getattr(request, "get_full_path", lambda: None)() or "/"
        url = f"{scheme}://{host}{path}"
        if SmarterValidator.is_valid_url(url):
            return url
    # pylint: disable=W0718
    except Exception as e:
        logger.warning(
            "smarter_build_absolute_uri() failed to build URL from request attributes: %s",
            formatted_text(str(e)),
        )

    # Fallback: synthesize a generic test URL
    logger.warning("smarter_build_absolute_uri() could not determine URL, returning fallback test URL")
    return "http://testserver/unknown/"


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

    def convert(name: str):
        name = name.replace(" ", "_")
        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        result = re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()
        result = re.sub("_+", "_", result)
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
        new_key = convert(key)
        retval[new_key] = value
    return retval


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
    if not isinstance(val, str):
        raise SmarterValueError(f"Could not convert RFC 1034 compliant name from {type(val)}")
    # Replace hyphens with underscores
    name = val.replace("-", "_")
    return name
