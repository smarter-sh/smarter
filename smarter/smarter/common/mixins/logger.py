"""
logger: A logger instance for the mixins, with conditional logging based on a waffle switch.
"""

from django.apps import apps
from django.core.exceptions import AppRegistryNotReady

from smarter.lib import logging

# guard against Sphinx doc build circular import errors
logger = logging.getSmarterLogger(__name__)
if apps.ready:
    try:
        # this resolves an import issue in collect static assets where Django apps are not yet importable
        # pylint: disable=import-outside-toplevel,C0412
        from smarter.lib.django.waffle import SmarterWaffleSwitches

        logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.MIDDLEWARE_LOGGING])
    # pylint: disable=broad-except
    except (AppRegistryNotReady, ImportError):
        pass
