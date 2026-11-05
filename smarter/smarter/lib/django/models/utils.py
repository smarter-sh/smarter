"""
Utility functions for Django models and the dictionaries that are applied to them.

This module provides utility functions for working with Django ORM base models and related data structures.
It includes helpers for validating string values, cleaning dictionary keys, and transforming lists of dictionaries.

**Main Features:**

- :func:`dict_key_cleaner`: Cleans a string key by removing line breaks and tabs, and replacing spaces with underscores.
- :func:`dict_keys_to_list`: Recursively extracts all keys from a nested dictionary into a flat list.
- :func:`list_of_dicts_to_list`: Converts a list of dictionaries into a list of the cleaned values of their first key.
- :func:`list_of_dicts_to_dict`: Converts a list of dictionaries into one dictionary of those cleaned values.
- :func:`assign_changed_fields` and :func:`tags_changed`: Compare an ORM instance with the values to apply to it.

These utilities are intended to simplify common data manipulation tasks in Django-based applications, especially when dealing with dynamic or nested data structures.
"""

from typing import Iterable, Optional

from django.db import models

from smarter.lib import logging
from smarter.lib.typing import SmarterDictType

logger = logging.getSmarterLogger(__name__)
logger_prefix = logging.SmarterFormattedText.text(__name__)
cache_prefix = f"{__name__}."


def dict_key_cleaner(key: str) -> str:
    """
    Clean a key by removing line breaks and tabs, and replacing spaces with underscores.

    This function removes newline (``\\n``), carriage return (``\\r``) and tab (``\\t``) characters
    from the input string, and replaces its spaces with underscores (``_``).

    :param key: The string key to clean.
    :returns: The cleaned key.

    **Example:**

    .. code-block:: python

        dict_key_cleaner("my key\\nwith\\tspaces")
        # returns: 'my_keywithspaces'
    """
    cleaned = str(key)
    cleaned = cleaned.replace("\n", "")
    cleaned = cleaned.replace("\r", "")
    cleaned = cleaned.replace("\t", "")
    cleaned = cleaned.replace(" ", "_")
    return cleaned


def dict_keys_to_list(data: SmarterDictType, keys: Optional[list[str]] = None) -> list[str]:
    """
    Recursively extract all keys from a nested dictionary.

    This function traverses a dictionary and all nested dictionaries,
    collecting every key encountered into a flat list.

    :param data: The dictionary to extract keys from.
    :param keys: An existing list to append keys to, used for recursion.
    :returns: A list of all keys found in the dictionary and its nested dictionaries.

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


def list_of_dicts_to_list(data: list[SmarterDictType]) -> Optional[list[str]]:
    """
    Convert a list of dictionaries into a list of the cleaned values of the first dictionary's first key.

    This function takes the first key of the first dictionary, and, for each dictionary that has
    that key, cleans its value with :func:`dict_key_cleaner`. It logs a warning each time it runs.

    :param data: A list of dictionaries.
    :returns: A list of cleaned values, or None if the list is empty or doesn't start with a dict.

    **Example:**

    .. code-block:: python

        data = [{"name": "Alice"}, {"name": "Bob"}]
        list_of_dicts_to_list(data)
        # returns: ['Alice', 'Bob']
    """
    if not data or not isinstance(data[0], dict):
        return None
    logger.warning("%s.list_of_dicts_to_list() converting a list of dicts to a list of their values", logger_prefix)
    retval = []
    key = next(iter(data[0]))
    for d in data:
        if key in d:
            cleaned_key = dict_key_cleaner(d[key])
            retval.append(cleaned_key)
    return retval


def list_of_dicts_to_dict(data: list[SmarterDictType]) -> Optional[SmarterDictType]:
    """
    Convert a list of dictionaries into one dict, keyed by the cleaned values of the first dictionary's first key.

    This function takes the first key of the first dictionary, and, for each dictionary that has
    that key, maps its value, cleaned with :func:`dict_key_cleaner`, to the original value.

    :param data: A list of dictionaries.
    :returns: A dictionary of cleaned values to original values, or None if the list is empty or
        doesn't start with a dict.

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


def assign_changed_fields(instance: models.Model, data: SmarterDictType) -> list[str]:
    """
    Set the fields of an ORM instance whose values differ from the given ones.

    A caller that applies a manifest saves the instance only when this returns a field. Every deploy
    applies the built-in manifests again, and saving an unchanged row moves its ``updated_at``, sends
    ``post_save`` to every receiver, and invalidates its caches. A value that compares unequal to the
    stored one only because of its type, e.g. a float and a Decimal, counts as changed, so the instance
    is saved, as it always was.

    :param instance: The ORM instance.
    :param data: The values, by field name, e.g. from a broker's ``manifest_to_django_orm()``.
    :returns: The names of the fields that were set, because their values changed.
    """
    changed: list[str] = []
    for key, value in data.items():
        if getattr(instance, key, None) != value:
            setattr(instance, key, value)
            changed.append(key)
    return changed


def tags_changed(instance: models.Model, tags: Optional[Iterable[str]]) -> bool:
    """
    Return whether the tags of an ORM instance differ from the given ones.

    :param instance: The ORM instance, which has a ``tags`` TaggableManager.
    :param tags: The tags, e.g. a manifest's ``metadata.tags``.
    :returns: True if the instance is not saved yet, or its tags differ.
    """
    if instance.pk is None:
        return True
    current_tags = set(instance.tags.names())  # type: ignore[attr-defined]
    new_tags = set(tags or [])
    changed = current_tags != new_tags
    return changed
