"""
Smarter common configuration module.
"""

from smarter.common.conf.defaults import settings_defaults
from smarter.common.conf.services import services
from smarter.common.conf.settings import smarter_settings

__all__ = [
    "services",
    "settings_defaults",
    "smarter_settings",
]
