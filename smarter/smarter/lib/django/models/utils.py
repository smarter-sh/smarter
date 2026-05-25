"""
smarter.lib.django.models.utils
================================

This module provides utility functions for working with Django ORM base models and related data structures.
It includes helpers for validating string values, cleaning dictionary keys, and transforming lists of dictionaries.

**Main Features:**

- `dict_key_cleaner(key)`: Cleans a string key by replacing whitespace characters with underscores.
- `dict_keys_to_list(data, keys=None)`: Recursively extracts all keys from a nested dictionary into a flat list.
- `list_of_dicts_to_list(data)`: Converts a list of dictionaries into a list of cleaned keys from the first key in each dict.
- `list_of_dicts_to_dict(data)`: Converts a list of dictionaries into a single dictionary with cleaned keys mapped to their values.

These utilities are intended to simplify common data manipulation tasks in Django-based applications, especially when dealing with dynamic or nested data structures.

:copyright: 2024 Smarter, Inc. All rights reserved.
:license: MIT
"""

from typing import Optional

from smarter.lib import logging

logger = logging.getSmarterLogger(__name__)
cache_prefix = f"{__name__}."


def dict_key_cleaner(key: str) -> str:
    """
    Clean a key by replacing spaces and whitespace characters with underscores.

    This function removes newline (``\\n``), carriage return (``\\r``), tab (``\\t``), and space characters
    from the input string and replaces them with underscores (``_``).

    :param key: The string key to clean.
    :type key: str
    :return: The cleaned key with whitespace replaced by underscores.
    :rtype: str

    **Example:**

    .. code-block:: python

        dict_key_cleaner("my key\\nwith\\tspaces")
        # returns: 'my_key_with_spaces'
    """
    return str(key).replace("\n", "").replace("\r", "").replace("\t", "").replace(" ", "_")


def dict_keys_to_list(data: dict, keys=None) -> list[str]:
    """
    Recursively extract all keys from a nested dictionary.

    This function traverses a dictionary and all nested dictionaries,
    collecting every key encountered into a flat list.

    :param data: The dictionary to extract keys from.
    :type data: dict
    :param keys: (Optional) An existing list to append keys to (used for recursion).
    :type keys: list, optional
    :return: A list of all keys found in the dictionary and its nested dictionaries.
    :rtype: list[str]

    **Example:**

    .. code-block:: python

        data = {
            "a": 1,
            "b": {"c": 2, "d": {"e": 3}}
        }
        dict_keys_to_list(data)
        # returns: ['a', 'b', 'c', 'd', 'e']
    """
    if keys is None:
        keys = []
    for key, value in data.items():
        keys.append(key)
        if isinstance(value, dict):
            dict_keys_to_list(value, keys)
    return keys


def list_of_dicts_to_list(data: list[dict]) -> Optional[list[str]]:
    """
    Convert a list of dictionaries into a list of cleaned keys extracted from the first key in each dict.

    This function iterates over a list of dictionaries, extracts the value of the first key in each dictionary,
    cleans it using :func:`dict_key_cleaner`, and returns a list of these cleaned keys.

    :param data: A list of dictionaries.
    :type data: list[dict]
    :return: A list of cleaned keys, or None if input is invalid.
    :rtype: Optional[list[str]]

    **Example:**

    .. code-block:: python

        data = [{"name": "Alice"}, {"name": "Bob"}]
        list_of_dicts_to_list(data)
        # returns: ['Alice', 'Bob']
    """
    if not data or not isinstance(data[0], dict):
        return None
    logger.warning("list_of_dicts_to_list() converting list of dicts to a single dict")
    retval = []
    key = next(iter(data[0]))
    for d in data:
        if key in d:
            cleaned_key = dict_key_cleaner(d[key])
            retval.append(cleaned_key)
    return retval


def list_of_dicts_to_dict(data: list[dict]) -> Optional[dict]:
    """
    Convert a list of dictionaries into a single dict with keys extracted
    from the first key in the first dict.

    This function iterates over a list of dictionaries, extracts the value of the first key in each dictionary,
    cleans it using :func:`dict_key_cleaner`, and uses the cleaned key as the key in the resulting dictionary,
    mapping to the original value.

    :param data: A list of dictionaries.
    :type data: list[dict]
    :return: A dictionary with cleaned keys mapped to their corresponding values, or None if input is invalid.
    :rtype: Optional[dict]

    **Example:**

    .. code-block:: python

        data = [{"name": "Alice"}, {"name": "Bob"}]
        list_of_dicts_to_dict(data)
        # returns: {'Alice': 'Alice', 'Bob': 'Bob'}
    """
    if not data or not isinstance(data[0], dict):
        return None
    retval = {}
    key = next(iter(data[0]))
    for d in data:
        if key in d:
            cleaned_key = dict_key_cleaner(d[key])
            retval[cleaned_key] = d[key]
    return retval
