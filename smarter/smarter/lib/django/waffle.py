"""
This module provides a wrapper around the django-waffle library to
add caching and to handle an init scendario where the database is not ready.
It is used to check if a feature flag (switch) is active.

Warning and Fix Note: waffle is a Django app that relies on database tables. If the database is not ready (e.g., during initial migrations),
attempting to access waffle switches can lead to errors. This module includes checks to ensure the database is ready before accessing waffle switches.
"""

import logging
from functools import wraps

import waffle as waffle_orig
from django.core.cache import cache
from django.db import connections
from django.db.utils import OperationalError, ProgrammingError
from django_redis.exceptions import ConnectionInterrupted
from redis.exceptions import ConnectionError as RedisConnectionError
from waffle.admin import SwitchAdmin


# Also catch MySQLdb.OperationalError for lower-level DB errors
try:
    import MySQLdb

    MySQLdbOperationalError = MySQLdb.OperationalError
except ImportError:
    MySQLdbOperationalError = None

from smarter.common.const import SMARTER_DEFAULT_CACHE_TIMEOUT
from smarter.common.helpers.console_helpers import formatted_text_green


logger = logging.getLogger(__name__)
CACHE_EXPIRATION = 60  # seconds
prefix = formatted_text_green("smarter.lib.django.waffle.switch_is_active()")


class DbState:
    ready = False


db_state = DbState()


class SmarterSwitchAdmin(SwitchAdmin):
    """
    Customized Django Admin console for managing Waffle switches.
    This class restricts access to the module to superusers only.
    """

    ordering = ("name",)

    def has_module_permission(self, request):
        return request.user.is_superuser  # type: ignore[return-value]


class SmarterWaffleSwitches:
    """A class representing the fixed set of Waffle switches for the Smarter API."""

    ACCOUNT_LOGGING = "log_account"
    API_LOGGING = "log_api"
    CACHE_LOGGING = "log_caching"
    PROMPT_LOGGING = "log_prompt"
    CHATAPP_LOGGING = "log_chatapp"
    CHATBOT_LOGGING = "log_chatbot"
    CHATBOT_HELPER_LOGGING = "log_chatbothelper"
    CSRF_SUPPRESS_FOR_CHATBOTS = "disable_csrf_middleware_for_chatbots"
    JOURNAL = "enable_journal"
    MANIFEST_LOGGING = "log_manifest_brokers"
    MIDDLEWARE_LOGGING = "log_middleware"
    PLUGIN_LOGGING = "log_plugin"
    PROVIDER_LOGGING = "log_provider"
    REACTAPP_DEBUG_MODE = "enable_reactapp_debug_mode"
    REQUEST_MIXIN_LOGGING = "log_request_mixin"
    RECEIVER_LOGGING = "log_receivers"
    TASK_LOGGING = "log_tasks"
    VIEW_LOGGING = "log_views"

    @property
    def all(self):
        """Return all switches."""
        return [
            self.ACCOUNT_LOGGING,
            self.API_LOGGING,
            self.CACHE_LOGGING,
            self.PROMPT_LOGGING,
            self.CHATAPP_LOGGING,
            self.CHATBOT_LOGGING,
            self.CHATBOT_HELPER_LOGGING,
            self.CSRF_SUPPRESS_FOR_CHATBOTS,
            self.JOURNAL,
            self.MANIFEST_LOGGING,
            self.MIDDLEWARE_LOGGING,
            self.PLUGIN_LOGGING,
            self.PROVIDER_LOGGING,
            self.REACTAPP_DEBUG_MODE,
            self.REQUEST_MIXIN_LOGGING,
            self.RECEIVER_LOGGING,
            self.TASK_LOGGING,
            self.VIEW_LOGGING,
        ]


def cache_results(timeout=SMARTER_DEFAULT_CACHE_TIMEOUT):

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}_{args}_{kwargs}"
            result = None
            try:
                result = cache.get(cache_key)
            except (RedisConnectionError, ConnectionInterrupted) as e:
                logger.error("Redis connection error while accessing cache: %s", e, exc_info=True)
            # pylint: disable=broad-except
            except Exception as e:
                logger.error("Unexpected error while attempting to access cache: %s", e, exc_info=True)

            if not result:
                result = func(*args, **kwargs)
                try:
                    cache.set(cache_key, result, timeout)
                except (RedisConnectionError, ConnectionInterrupted) as e:
                    logger.error("Redis connection error while setting cache: %s", e, exc_info=True)
                # pylint: disable=broad-except
                except Exception as e:
                    logger.error("Unexpected error while attempting to access cache: %s", e, exc_info=True)
            return result

        def invalidate(*args, **kwargs):
            cache_key = f"{func.__name__}_{args}_{kwargs}"
            cache.delete(cache_key)

        wrapper.invalidate = invalidate  # type: ignore[attr-defined]
        return wrapper

    return decorator


def is_database_ready(alias="default"):

    if db_state.ready:
        return True
    try:
        # Ensure the connection is usable. ie the DB server is up
        connection = connections[alias]
        connection.ensure_connection()
        # Check if the waffle_switch table exists
        if "waffle_switch" not in connection.introspection.table_names():
            return False
        db_state.ready = True
        return db_state.ready
    except OperationalError:
        return False
    except ProgrammingError:
        return False


@cache_results(timeout=CACHE_EXPIRATION)
def switch_is_active(switch_name: str) -> bool:
    if not is_database_ready():
        logger.warning("%s Database not ready, assuming switch %s is inactive.", prefix, switch_name)
        return False
    if not isinstance(switch_name, str):
        logger.error("%s switch_name must be a string, got %s", prefix, type(switch_name).__name__)
        return False
    if switch_name not in SmarterWaffleSwitches().all:
        logger.error("%s switch_name '%s' is not a valid SmarterWaffleSwitches attribute", prefix, switch_name)
        return False
    db_exceptions = tuple(
        t for t in (OperationalError, ProgrammingError, MySQLdbOperationalError) if t is not None
    ) or (Exception,)
    try:
        switch = waffle_orig.get_waffle_switch_model().get(switch_name)
        if switch.is_active():
            logger.info("%s: %s is active and will be cached for %s seconds.", prefix, switch_name, CACHE_EXPIRATION)
        return switch.is_active()
    except db_exceptions as e:
        logger.error("%s Database not ready or switch does not exist: %s", prefix, e, exc_info=True)
        return False
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("%s An error occurred while checking switch %s: %s", prefix, switch_name, e, exc_info=True)
        return False
