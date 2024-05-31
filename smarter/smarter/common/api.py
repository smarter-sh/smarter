"""Smarter API enumerations."""

from .enum import SmarterEnumAbstract


VERSION_PREFIX = "smarter.sh"


class SmarterApiVersions(SmarterEnumAbstract):
    """API Version enumeration."""

    V0 = f"{VERSION_PREFIX}/v0"
    V1 = f"{VERSION_PREFIX}/v1"
