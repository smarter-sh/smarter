# pylint: disable=duplicate-code
# pylint: disable=E1101
"""Utility functions for the OpenAI Lambda functions"""
import csv
import hashlib
import json  # library for interacting with JSON data https://www.json.org/json-en.html
import logging
import random
import re
from datetime import datetime
from typing import Optional

import yaml
from django.http import HttpRequest
from pydantic import SecretStr
from rest_framework.request import Request

from smarter.common.exceptions import SmarterValueError
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib.django.validators import SmarterValidator


logger = logging.getLogger(__name__)


def hash_factory(length: int = 16) -> str:
    """
    Generates a random hash of the specified length.
    Args:
        length (int): The length of the hash to generate.
    Returns:
        str: A random hash of the specified length.
    """
    return hashlib.sha256(str(random.getrandbits(256)).encode("utf-8")).hexdigest()[:length]


def get_readonly_yaml_file(file_path) -> dict:
    with open(file_path, encoding="utf-8") as file:
        return yaml.safe_load(file)


def get_readonly_csv_file(file_path):
    with open(file_path, encoding="utf-8") as file:
        reader = csv.DictReader(file)
        return list(reader)


class DateTimeEncoder(json.JSONEncoder):
    """JSON encoder that handles datetime objects."""

    def default(self, o):
        if isinstance(o, datetime):
            return o.strftime("%Y-%m-%d")
        if isinstance(o, SecretStr):
            return "*** REDACTED ***"

        return super().default(o)


def camel_to_snake(name):
    """
    Converts camelCase or poorly formatted names to snake_case.
    examples:
        camel_to_snake("camelCase") -> "camel_case"
        camel_to_snake("CamelCase") -> "camel_case"
        camel_to_snake("Camel Case") -> "camel_case"
        camel_to_snake("camel case") -> "camel_case"
        camel_to_snake("camelCaseWithSpaces") -> "camel_case_with_spaces"
        camel_to_snake("CamelCaseWithSpaces") -> "camel_case_with_spaces"
        camel_to_snake("Camel Case With Spaces") -> "camel_case_with_spaces"
        camel_to_snake("MYEverlastingSUPERDUPERGobstopper") -> "my_everlasting_superduper_gobstopper"
    Args:
        name (str): The name to convert.
    Returns:
        str: The converted name in snake_case.
    """
    name = str(name or "")
    name = name.replace(" ", "_").replace("-", "_")

    # Split lowercase-uppercase boundary
    name = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)

    # Handle consecutive uppercase letters followed by lowercase letters
    name = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)

    # Reduce multiple underscores to a single underscore
    name = re.sub(r"_+", "_", name)

    # Remove non-alphanumeric characters except underscores
    name = re.sub(r"[^\w]", "", name)

    return name.lower()


def camel_to_snake_dict(dictionary: dict) -> dict:
    """Converts camelCase dict keys to snake_case."""

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
    """Recursively sort a dictionary by key."""
    return {k: recursive_sort_dict(v) if isinstance(v, dict) else v for k, v in sorted(d.items())}


def dict_is_contained_in(dict1, dict2):
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
    Recursively check that all items in dict 'small' exist in dict 'big'.
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
    Mask a string by replacing all but the last 'mask_length' characters with 'mask_char'.
    Args:
        string (str): The string to mask.
        mask_char (str): The character to use for masking.
        mask_length (int): The number of characters to leave unmasked at the end.
    Returns:
        str: The masked string.
    """
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
    A utility function to attempt to get the request URL from any valid
    child class of HttpRequest, or a mock for testing.
    :param request: The request object.
    :return: The request URL.
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
    except Exception as e:
        logger.warning(
            "smarter_build_absolute_uri() failed to build URL from request attributes: %s",
            formatted_text(str(e)),
        )

    # Fallback: synthesize a generic test URL
    logger.warning("smarter_build_absolute_uri() could not determine URL, returning fallback test URL")
    return "http://testserver/unknown/"
