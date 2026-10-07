"""Enumeration classes for the manifest models."""

from smarter.lib.manifest.enum import SmarterEnumAbstract


class AuthMethods(SmarterEnumAbstract):
    """Authentication method enumeration."""

    NONE = "none"
    BASIC = "basic"
    TOKEN = "token"
    OAUTH = "oauth"
