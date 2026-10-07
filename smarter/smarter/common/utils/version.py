"""
smarter.common.utils.version
=============================

Utility functions for version management.

This module provides helpers for retrieving and normalizing semantic version
numbers for the smarter project. It ensures compatibility with PyPI versioning
requirements and strips unsupported suffixes from version strings.

Functions
---------
- get_semantic_version: Returns the normalized semantic version string.

Notes
-----
- PyPI does not allow version numbers with dashes, 'v' prefixes, or 'next' suffixes.
"""

import re
from functools import cache

from smarter.common.const import VERSION


@cache
def get_semantic_version() -> str:
    """
    Return the semantic version number.

    Example valid values of __version__.py are:
    0.1.17
    0.1.17-alpha.1
    0.1.17-beta.1
    0.1.17-next.1
    0.1.17-next.2
    0.1.17-next.123456
    0.1.17-next-major.1
    0.1.17-next-major.2
    0.1.17-next-major.123456

    Note:
    - pypi does not allow semantic version numbers to contain a dash.
    - pypi does not allow semantic version numbers to contain a 'v' prefix.
    - pypi does not allow semantic version numbers to contain a 'next' suffix.
    """
    if not isinstance(VERSION, dict):
        return "unknown"

    version = VERSION.get("__version__")
    if not version:
        return "unknown"
    version = re.sub(r"-next\.\d+", "", version)
    return re.sub(r"-next-major\.\d+", "", version)


__all__ = ["get_semantic_version"]
