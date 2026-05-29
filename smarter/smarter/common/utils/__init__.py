# pylint: disable=C0411,E1101
"""
Utility functions for the Smarter framework.

This module provides a collection of helper functions and classes
that are ostensibly implemented in more than one Smarter base class.
Hence, they are only here in order to keep the code DRY (Don't Repeat Yourself).

The module is intended for internal use within the Smarter framework and is
designed to be compatible with Python 3, Django, DRF, and Pydantic.

"""

from .conversion import (
    camel_to_snake,
    camel_to_snake_dict,
    dict_is_contained_in,
    dict_is_subset,
    pascal_to_snake,
    recursive_sort_dict,
    rfc1034_compliant_str,
    rfc1034_compliant_to_snake,
    snake_case,
    snake_to_camel,
    to_snake_case,
)
from .diagnostics import get_diagnostics
from .file_handlers import get_readonly_csv_file, get_readonly_yaml_file
from .request import is_authenticated_request
from .request_to_json import request_to_json
from .uri import smarter_build_absolute_uri
from .utils import (
    bool_environment_variable,
    generate_fernet_encryption_key,
    hash_factory,
    is_async_context,
    mask_string,
)
from .version import get_semantic_version

__all__ = [
    "is_async_context",
    "bool_environment_variable",
    "camel_to_snake",
    "to_snake_case",
    "camel_to_snake_dict",
    "dict_is_contained_in",
    "dict_is_subset",
    "generate_fernet_encryption_key",
    "get_semantic_version",
    "hash_factory",
    "is_authenticated_request",
    "smarter_build_absolute_uri",
    "get_diagnostics",
    "get_readonly_csv_file",
    "get_readonly_yaml_file",
    "mask_string",
    "pascal_to_snake",
    "rfc1034_compliant_str",
    "rfc1034_compliant_to_snake",
    "recursive_sort_dict",
    "request_to_json",
    "uri",
    "snake_case",
    "snake_to_camel",
]
