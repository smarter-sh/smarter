"""
smarter.common.utils.dict
==========================

Module providing dictionary utility functions for the Smarter framework.

This module includes helper functions for:
- Recursively sorting dictionaries by key for deterministic output.
- Checking if all keys and values in one dictionary are present in another (deep containment).
- Recursively verifying if a dictionary or list is a subset of another.

These utilities are useful for testing, serialization, comparison, and data validation tasks.

Functions
---------
- recursive_sort_dict(d): Recursively sorts a dictionary by its keys.
- dict_is_contained_in(dict1, dict2): Checks if all keys and values in dict1 are present in dict2, recursively.
- dict_is_subset(small, big): Recursively checks that all items in the dictionary or list 'small' exist in 'big'.

Example
-------
.. code-block:: python

    from smarter.common.utils import recursive_sort_dict, dict_is_contained_in, dict_is_subset

    d = {"b": 2, "a": {"d": 4, "c": 3}}
    sorted_d = recursive_sort_dict(d)

    model = {"name": "Alice", "profile": {"age": 30}}
    test = {"name": "Alice", "profile": {"age": 30}, "extra": "value"}
    result = dict_is_contained_in(model, test)

    big = {"roles": ["admin", "user"]}
    small = {"roles": ["admin"]}
    result = dict_is_subset(small, big)
"""

from smarter.lib import logging

logger = logging.getLogger(__name__)
logger_prefix = logging.formatted_text(__name__)


def recursive_sort_dict(d):
    """
    Recursively sorts a dictionary by its keys.

    :param d: The input dictionary to be sorted. Nested dictionaries are also sorted recursively.
    :type d: dict

    :return: A new dictionary with all keys sorted in ascending order. If a value is itself a dictionary, it is also sorted recursively.
    :rtype: dict

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
    logger.debug("%s.recursive_sort_dict()", logger_prefix)
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
    logger.debug("%s.dict_is_contained_in()", logger_prefix)
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
    logger.debug("%s.dict_is_subset()", logger_prefix)
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


__all__ = [
    "dict_is_contained_in",
    "dict_is_subset",
    "recursive_sort_dict",
]
