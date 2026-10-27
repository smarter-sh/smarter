"""Switch_is_active() - Check if a Waffle switch is active with caching and database readiness checks."""

import time
from importlib import import_module

from asgiref.sync import sync_to_async
from django.apps import apps
from django.core.exceptions import AppRegistryNotReady
from django.db.models.signals import post_delete, post_save
from django.db.utils import OperationalError, ProgrammingError
from waffle import get_waffle_switch_model
from waffle.utils import get_cache

from smarter.common.helpers.console_helpers import SmarterFormattedText
from smarter.lib import logging

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

prefix = f"{SmarterFormattedText.text(__name__)}.switch_is_active()"

SWITCH_CACHE_SECONDS = 5
"""
How long a process remembers a switch's state.

Every log call of a switched logger checks a switch, often dozens of times per request, and
waffle's own cache is Redis, so each check was a network round trip. A process now remembers
each switch for this many seconds. Saving or deleting a switch clears what this process
remembers at once; other processes see the change within this many seconds.
"""

_switch_cache: dict[str, tuple[bool, float]] = {}
"""Each switch's state, and the :func:`time.monotonic` time until which it is current."""


def clear_switch_cache(*args, **kwargs) -> None:
    """
    Forget every switch's remembered state, so that the next check reads it again.

    It receives the ``post_save`` and ``post_delete`` signals of waffle's Switch model, e.g. from
    the Django admin or ``waffle.testutils.override_switch``, and takes their arguments.
    """
    _switch_cache.clear()


post_save.connect(clear_switch_cache, sender="waffle.Switch", dispatch_uid="smarter_clear_switch_cache_on_save")
post_delete.connect(clear_switch_cache, sender="waffle.Switch", dispatch_uid="smarter_clear_switch_cache_on_delete")


def create_missing_switch(switch_name: str):
    """
    Create a switch that is missing from the database, with its Smarter default and comment.

    django-waffle creates missing switches with its global ``WAFFLE_SWITCH_DEFAULT``, which is
    inactive. A switch that is checked before ``manage.py initialize_waffle`` runs, e.g. by
    middleware while ``make init`` migrates the database, would then stay inactive even when its
    default is active, because ``initialize_waffle`` only creates switches that do not exist.

    :param switch_name: The name of a switch in :class:`SmarterWaffleSwitches`.
    :returns: The switch.
    :rtype: waffle.models.Switch
    """
    defaults = smarter_waffle_switches.switches[switch_name]  # type: ignore[index]
    switch, created = get_waffle_switch_model().objects.get_or_create(
        name=switch_name, defaults={"active": defaults.default, "note": defaults.comment}
    )
    get_cache().set(switch._cache_key(switch_name), switch)  # pylint: disable=protected-access
    if created:
        logger.info("%s created missing switch %s, active=%s", prefix, switch_name, switch.active)
    return switch


def switch_is_active(switch_name: str) -> bool:
    """
    Check if a Waffle switch is active, with caching and database readiness checks.

    .. important::

        This is the preferred method for checking Waffle switches in the Smarter codebase.
        It includes caching to optimize performance and handles database readiness to prevent errors.
        Each process remembers a switch's state for :data:`SWITCH_CACHE_SECONDS`.

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
    cached = _switch_cache.get(switch_name)
    if cached is not None and cached[1] > time.monotonic():
        return cached[0]
    try:
        switch = get_waffle_switch_model().get(switch_name)
        if not switch.pk:
            switch = create_missing_switch(switch_name)
        is_active = switch.is_active()
        _switch_cache[switch_name] = (is_active, time.monotonic() + SWITCH_CACHE_SECONDS)
        return is_active
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
