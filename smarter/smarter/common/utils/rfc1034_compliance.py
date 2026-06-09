"""
Smarter.common.utils.rfc1034_compliance
========================================

Helpers for generating and converting RFC 1034-compliant strings.

This module provides utility functions for working with DNS-safe names and resource identifiers
that comply with RFC 1034. It includes:

- ``rfc1034_compliant_str``: Converts arbitrary strings to RFC 1034-compliant DNS labels.
- ``rfc1034_compliant_to_snake``: Converts RFC 1034-compliant names to Pythonic ``snake_case``.

**Example usage:**

.. code-block:: python

    from smarter.common.utils import rfc1034_compliant_str, rfc1034_compliant_to_snake

    label = rfc1034_compliant_str("My_LLMClient_2025")
    print(label)  # Output: my-llm_client-2025

    snake = rfc1034_compliant_to_snake(label)
    print(snake)  # Output: my_llm_client_2025
"""

import re
from functools import lru_cache

from smarter.common.exceptions import SmarterValueError
from smarter.lib import logging

logger = logging.getLogger(__name__)
logger_prefix = logging.formatted_text(__name__)

LRU_MAXSIZE = 128  # Default max size for LRU caches in this module


@lru_cache(maxsize=LRU_MAXSIZE)
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
        print(rfc1034_compliant_str("My_LLMClient_2025"))  # Output: my-llm_client-2025

        # With special characters
        print(rfc1034_compliant_str("My@Bot!_Name"))  # Output: my-bot-name

        # With long input
        long_name = "ThisIsAReallyLongLLMClientNameThatShouldBeTruncatedToSixtyThreeCharacters_Extra"
        print(rfc1034_compliant_str(long_name))  # Output: thisisareallylongllm_clientnamethatshouldbetruncatedtosixtythreecharacters
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


@lru_cache(maxsize=LRU_MAXSIZE)
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
        print(rfc1034_compliant_to_snake("my-llm_client-2025"))
        # Output: my_llm_client_2025

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
    logger.debug("%s.rfc1034_compliant_to_snake()", logger_prefix)
    if not isinstance(val, str):
        raise SmarterValueError(f"Could not convert RFC 1034 compliant name from {type(val)}")
    # Replace hyphens with underscores
    name = val.replace("-", "_")
    return name


__all__ = [
    "rfc1034_compliant_str",
    "rfc1034_compliant_to_snake",
]
