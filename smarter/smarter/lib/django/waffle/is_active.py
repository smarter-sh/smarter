"""Check whether a Waffle switch is active, with caching and database readiness checks."""

import time
from importlib import import_module
from typing import TYPE_CHECKING, Optional

from asgiref.sync import sync_to_async
from django.apps import apps
from django.core.exceptions import AppRegistryNotReady
from django.db.models.signals import post_delete, post_save
from django.db.utils import OperationalError, ProgrammingError
from django_redis.exceptions import ConnectionInterrupted
from redis.exceptions import RedisError
from waffle import get_waffle_switch_model
from waffle.utils import get_cache

from smarter.common.helpers.console_helpers import SmarterFormattedText
from smarter.lib import logging

from .ready import is_database_ready
from .switches import smarter_waffle_switches

if TYPE_CHECKING:
    from waffle.models import AbstractBaseSwitch

logger = logging.getLogger(__name__)
logger_prefix = SmarterFormattedText.text(__name__)

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

prefix = f"{logger_prefix}.switch_is_active()"

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


DB_EXCEPTIONS: tuple[type[BaseException], ...] = (OperationalError, ProgrammingError)
"""The database errors that mean a switch can't be read yet, including the drivers' own, when installed."""
for _driver_error in (MySQLdbOperationalError, MariaDBOperationalError, MariaDBProgrammingError):
    if _driver_error is not None:
        DB_EXCEPTIONS += (_driver_error,)

CACHE_EXCEPTIONS: tuple[type[BaseException], ...] = (ConnectionInterrupted, RedisError)
"""The errors of waffle's cache, Redis, e.g. while Redis restarts, after which a switch is read from the database."""


def switch_from_database(switch_name: str) -> bool:
    """
    Read a switch's state from the database, without waffle's cache.

    :func:`switch_is_active` calls it when the cache, Redis, can't be read, e.g. while its pod
    restarts on another node. Every request checks switches, in middleware and in switched loggers,
    so without it each request, the readiness probe's included, would fail with a 500 until Redis
    is back (issue #941).

    :param switch_name: The name of the switch.
    :returns: Whether the switch is active, or its Smarter default if it isn't in the database.
    """
    switch = get_waffle_switch_model().objects.filter(name=switch_name).first()
    if switch is None:
        defaults = smarter_waffle_switches.switches[switch_name]  # type: ignore[index]
        return bool(defaults.default)
    return bool(switch.active)


def cached_switch_state(switch_name: str) -> Optional[bool]:
    """
    Return the state that this process remembers for a switch, if it is still current.

    It never touches the database or Redis, so it is safe to call from async code.

    :param switch_name: The name of the switch.
    :returns: The switch's state, or None if it isn't remembered or has expired.
    """
    if not isinstance(switch_name, str):
        return None
    cached = _switch_cache.get(switch_name)
    if cached is None:
        return None
    is_active, expires_at = cached
    if expires_at <= time.monotonic():
        return None
    return is_active


def clear_switch_cache(*args, **kwargs) -> None:
    """
    Forget every switch's remembered state, so that the next check reads it again.

    It receives the ``post_save`` and ``post_delete`` signals of waffle's Switch model, e.g. from
    the Django admin or ``waffle.testutils.override_switch``, and takes their arguments.
    """
    _switch_cache.clear()


post_save.connect(clear_switch_cache, sender="waffle.Switch", dispatch_uid="smarter_clear_switch_cache_on_save")
post_delete.connect(clear_switch_cache, sender="waffle.Switch", dispatch_uid="smarter_clear_switch_cache_on_delete")


def create_missing_switch(switch_name: str) -> "AbstractBaseSwitch":
    """
    Create a switch that is missing from the database, with its Smarter default and comment.

    django-waffle creates missing switches with its global ``WAFFLE_SWITCH_DEFAULT``, which is
    inactive. A switch that is checked before ``manage.py initialize_waffle`` runs, e.g. by
    middleware while ``make init`` migrates the database, would then stay inactive even when its
    default is active, because ``initialize_waffle`` only creates switches that do not exist.

    :param switch_name: The name of a switch in :class:`SmarterWaffleSwitches`.
    :returns: The switch, a :class:`waffle.models.Switch` unless ``WAFFLE_SWITCH_MODEL`` names another model.
    """
    defaults = smarter_waffle_switches.switches[switch_name]  # type: ignore[index]
    switch, created = get_waffle_switch_model().objects.get_or_create(
        name=switch_name, defaults={"active": defaults.default, "note": defaults.comment}
    )
    get_cache().set(switch._cache_key(switch_name), switch)  # pylint: disable=protected-access
    if created:
        logger.info(
            "%s.create_missing_switch() created missing switch %s, active=%s", logger_prefix, switch_name, switch.active
        )
    return switch


def switch_is_active(switch_name: str) -> bool:
    """
    Check if a Waffle switch is active, with caching and database readiness checks.

    .. important::

        This is the preferred method for checking Waffle switches in the Smarter codebase.
        It includes caching to optimize performance and handles database readiness to prevent errors.
        Each process remembers a switch's state for :data:`SWITCH_CACHE_SECONDS`.

    **Example**

    .. code-block:: python

        from smarter.lib.django.waffle import SmarterWaffleSwitches, switch_is_active

        if switch_is_active(SmarterWaffleSwitches.API_LOGGING):
            print("API logging is enabled.")

    :param switch_name: The name of the Waffle switch to check.
    :returns: True if the switch is active, False otherwise, including when the app registry or
        the database isn't ready, or the name isn't a :class:`SmarterWaffleSwitches` switch. When
        the cache can't be read, the switch is read from the database (see :func:`switch_from_database`).
    """
    # The remembered state comes first: this runs on every log call of a switched logger.
    # A state is only remembered after the apps and the database were ready.
    cached = cached_switch_state(switch_name)
    if cached is not None:
        return cached

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
    if switch_name not in smarter_waffle_switches.all_set:
        logger.error("%s switch_name '%s' is not a valid SmarterWaffleSwitches attribute", prefix, switch_name)
        return False
    try:
        try:
            switch = get_waffle_switch_model().get(switch_name)
            if not switch.pk:
                switch = create_missing_switch(switch_name)
            is_active = switch.is_active()
        except CACHE_EXCEPTIONS as e:
            # one line, no traceback: Redis being away is an outage to report, not a bug to debug.
            logger.warning("%s the cache failed, reading switch %s from the database: %s", prefix, switch_name, e)
            is_active = switch_from_database(switch_name)
        _switch_cache[switch_name] = (is_active, time.monotonic() + SWITCH_CACHE_SECONDS)
        return is_active
    except (*DB_EXCEPTIONS, AppRegistryNotReady) as e:
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

    A state that this process remembers is returned at once, without the hop to that
    executor, which is a single thread shared by every request.

    :param switch_name: The name of the Waffle switch to check.
    :returns: True if the switch is active, False otherwise.
    """
    cached = cached_switch_state(switch_name)
    if cached is not None:
        return cached
    return await sync_to_async(switch_is_active, thread_sensitive=True)(switch_name)
