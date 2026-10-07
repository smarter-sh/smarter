"""
Smarter common configuration module.
"""

from .defaults import settings_defaults
from .services import services
from .settings import Settings, smarter_settings

__all__ = [
    "services",
    "settings_defaults",
    "smarter_settings",
    "Settings",  # for Sphinx autodoc
]
