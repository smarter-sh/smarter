"""
switch_is_active() - Check if a Waffle switch is active with caching and database readiness checks.
"""

import logging
from importlib import import_module

import waffle as waffle_orig
from asgiref.sync import sync_to_async
from django.apps import apps
from django.core.exceptions import AppRegistryNotReady
from django.db.utils import OperationalError, ProgrammingError

from smarter.common.helpers.console_helpers import formatted_text

from .ready import is_database_ready
from .switches import smarter_waffle_switches

logger = logging.getLogger(__name__)

# Also catch driver-specific DB errors for lower-level connector failures.
try:
    MySQLdbOperationalError = import_module("MySQLdb").OperationalError
except ImportError:
    MySQLdbOperationalError = None

try:
    mariadb = import_module("mariadb")
    MariaDBOperationalError = mariadb.OperationalError
    MariaDBProgrammingError = mariadb.ProgrammingError
except ImportError:
    MariaDBOperationalError = None
    MariaDBProgrammingError = None

prefix = f"{formatted_text(__name__)}.switch_is_active()"


def switch_is_active(switch_name: str) -> bool:
    """
    Check if a Waffle switch is active, with caching and database readiness checks.

    .. important::

        This is the preferred method for checking Waffle switches in the Smarter codebase.
        It includes caching to optimize performance and handles database readiness to prevent errors.

    Example:
        .. code-block:: python

            from smarter.lib.django.waffle import SmarterWaffleSwitches, switch_is_active

            if switch_is_active(smarter_waffle_switches.API_LOGGING):
                print("API logging is enabled.")

    :param switch_name: The name of the Waffle switch to check.
    :return: True if the switch is active, False otherwise.
    :rtype: bool
    """
    # Prevent model access before Django app registry is ready
    if not apps.ready:
        logger.warning("%s App registry not ready, assuming switch %s is inactive.", prefix, switch_name)
        return False

    try:
        if not is_database_ready():
            logger.debug("%s Database not ready, assuming switch %s is inactive.", prefix, switch_name)
            return False
    # pylint: disable=broad-except
    except Exception as e:
        logger.warning("%s Error checking database readiness: %s", prefix, e, exc_info=True)
        return False
    if not isinstance(switch_name, str):
        logger.error("%s switch_name must be a string, got %s", prefix, type(switch_name).__name__)
        return False
    if switch_name not in smarter_waffle_switches.all:
        logger.error("%s switch_name '%s' is not a valid SmarterWaffleSwitches attribute", prefix, switch_name)
        return False
    db_exceptions = tuple(
        t
        for t in (
            OperationalError,
            ProgrammingError,
            MySQLdbOperationalError,
            MariaDBOperationalError,
            MariaDBProgrammingError,
        )
        if t is not None
    ) or (Exception,)
    try:
        return waffle_orig.switch_is_active(switch_name)
    except (*db_exceptions, AppRegistryNotReady) as e:
        logger.error(
            "%s Database not ready, App Registry not ready, or switch does not exist: %s", prefix, e, exc_info=True
        )
        return False


async def async_switch_is_active(switch_name: str) -> bool:
    """
    Async-safe wrapper around :func:`switch_is_active`.

    Django's ORM-backed Waffle lookup is synchronous. Under ASGI callers should
    await this helper instead of calling :func:`switch_is_active` directly.
    ``thread_sensitive=True`` keeps the work on Django's thread-sensitive sync
    executor so connection-local state remains safe.
    """

    return await sync_to_async(switch_is_active, thread_sensitive=True)(switch_name)
