"""Smarter common configuration module."""

from .settings import Settings, smarter_settings

__all__ = [
    "smarter_settings",
    "Settings",  # for Sphinx autodoc
]
