"""
smarter.common.utils
====================

Utility functions for the Smarter framework.

This module provides a collection of helper functions and classes
that are ostensibly implemented in more than one Smarter base class.
Hence, they are only here in order to keep the code DRY (Don't Repeat Yourself).

The module is intended for internal use within the Smarter framework and is
designed to be compatible with Python 3, Django, DRF, and Pydantic.
"""

from .conversion import (
    ConvertibleCaseType,
    to_camel_case,
    to_snake_case,
)
from .decorators import camel_case, snake_case
from .diagnostics import get_diagnostics
from .dict import dict_is_contained_in, dict_is_subset, recursive_sort_dict
from .file_handlers import get_readonly_csv_file, get_readonly_yaml_file
from .request import is_authenticated_request
from .request_to_json import RequestData, request_to_json
from .rfc1034_compliance import rfc1034_compliant_str, rfc1034_compliant_to_snake
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
    "camel_case",
    "snake_case",
    "is_async_context",
    "bool_environment_variable",
    "to_snake_case",
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
    "rfc1034_compliant_str",
    "rfc1034_compliant_to_snake",
    "recursive_sort_dict",
    "request_to_json",
    "RequestData",
    "uri",
    "to_camel_case",
    "ConvertibleCaseType",
]
