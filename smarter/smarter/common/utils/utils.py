"""
smarter.common.utils.utils
==========================

Utility functions for the Smarter framework.

This module provides a collection of helper functions and classes that are shared across
multiple Smarter base classes to keep the code DRY (Don't Repeat Yourself).
It is intended for internal use within the Smarter framework and is designed to be compatible
with Python 3, Django, Django REST Framework (DRF), and Pydantic.

Functions in this module include helpers for asynchronous context detection, random hash generation,
environment variable parsing, encryption key generation, and string masking.

**Example usage:**

.. code-block:: python

    from smarter.common.utils import hash_factory, bool_environment_variable

    token = hash_factory(length=16)
    debug_mode = bool_environment_variable('DEBUG', default=False)

"""

import asyncio
import hashlib
import os
import random
import warnings
from functools import lru_cache
from typing import Union

from cryptography.fernet import Fernet

from smarter.lib import logging

logger = logging.getLogger(__name__)
logger_prefix = logging.formatted_text(__name__)

LRU_MAXSIZE = 128  # Default max size for LRU caches in this module


def is_async_context():
    """
    Checks if the current context is asynchronous.

    :return: True if running in an asynchronous context, False otherwise.
    :rtype: bool
    """
    try:
        asyncio.get_running_loop()
        return True
    except RuntimeError:
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


def mask_string(string: Union[str, bytes], mask_char: str = "*", mask_length: int = 4, string_length: int = 8) -> str:
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
    logger.debug("%s.mask_string()", logger_prefix)
    warnings.warn(
        "mask_string is deprecated and will be removed in a future release.", DeprecationWarning, stacklevel=2
    )
    if isinstance(string, bytes):
        string = string.decode("utf-8")
    if not isinstance(string, str):
        logger.warning("mask_string() - Input is not a string or bytes: %s", type(string))
        return str(string)
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


def generate_fernet_encryption_key() -> str:
    """
    Generates a new Fernet encryption key.

    :return: A URL-safe base64-encoded 32-byte key suitable for use with the Fernet symmetric encryption system.
    :rtype: str

    .. note::

        - This function uses the ``cryptography`` library to generate a secure random key. The key is encoded as a UTF-8 string for easy storage and transmission.
        - The generated key is random and should be securely stored. It is essential for encrypting and decrypting data using the Fernet protocol.

    **Example usage:**

    .. code-block:: python

        from smarter.common.utils import generate_fernet_encryption_key

        key = generate_fernet_encryption_key()
        print(key)  # e.g., 'gAAAAABh...'

    """
    logger.debug("%s.generate_fernet_encryption_key() Generating new Fernet encryption key.", logger_prefix)
    return Fernet.generate_key().decode("utf-8")


@lru_cache(maxsize=LRU_MAXSIZE)
def bool_environment_variable(var_name: str, default: bool) -> bool:
    """
    Retrieve a boolean value from an environment variable.

    This function checks for the presence of an environment variable with the given name,
    or with the prefix "SMARTER_" added to the name. If the variable is not set, the provided
    default value is returned. The value is interpreted as True if it matches any of the following
    (case-insensitive): "true", "1", "t", "y", or "yes".

    :param var_name: The name of the environment variable to check.
    :type var_name: str
    :param default: The default boolean value to return if the environment variable is not set.
    :type default: bool
    :return: The boolean value of the environment variable, or the default if not set.
    :rtype: bool

    **Example usage:**

    .. code-block:: python

        from smarter.common.utils import bool_environment_variable

        # Returns True if the environment variable 'DEBUG' is set to a truthy value
        debug_mode = bool_environment_variable('DEBUG', default=False)

    """
    logger.debug("%s.bool_environment_variable()", logger_prefix)
    value = os.environ.get(var_name) or os.environ.get(f"SMARTER_{var_name}")
    if value is None:
        return default
    return value.lower() in ["true", "1", "t", "y", "yes"]


__all__ = [
    "is_async_context",
    "hash_factory",
    "bool_environment_variable",
    "generate_fernet_encryption_key",
    "mask_string",
]
