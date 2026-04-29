"""
logger: A logger instance for the mixins, with conditional logging based on a waffle switch.
"""

from django.apps import apps
from django.core.exceptions import AppRegistryNotReady

import smarter.lib.logging as logging

# guard against Sphinx doc build circular import errors
mixin_logging_is_active: bool = False
if apps.ready:
    try:
        # this resolves an import issue in collect static assets where Django apps are not yet importable
        # pylint: disable=import-outside-toplevel,C0412
        from smarter.lib.django import waffle
        from smarter.lib.django.waffle import SmarterWaffleSwitches

        mixin_logging_is_active = waffle.switch_is_active(SmarterWaffleSwitches.REQUEST_MIXIN_LOGGING)
    # pylint: disable=broad-except
    except (AppRegistryNotReady, ImportError):
        pass


# pylint: disable=W0613
def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return mixin_logging_is_active


logger = logging.getSmarterLogger(__name__, condition_func=should_log)
