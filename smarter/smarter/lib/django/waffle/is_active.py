import logging

import waffle as waffle_orig
from django.apps import apps
from django.core.exceptions import AppRegistryNotReady
from django.db.utils import OperationalError, ProgrammingError

from smarter.common.helpers.console_helpers import formatted_text

from .ready import is_database_ready
from .switches import smarter_waffle_switches

logger = logging.getLogger(__name__)

# Also catch MySQLdb.OperationalError for lower-level DB errors
try:
    import MySQLdb

    MySQLdbOperationalError = MySQLdb.OperationalError
except ImportError:
    MySQLdbOperationalError = None

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
        t for t in (OperationalError, ProgrammingError, MySQLdbOperationalError) if t is not None
    ) or (Exception,)
    try:
        return waffle_orig.switch_is_active(switch_name)
    except (*db_exceptions, AppRegistryNotReady) as e:
        logger.error(
            "%s Database not ready, App Registry not ready, or switch does not exist: %s", prefix, e, exc_info=True
        )
        return False
