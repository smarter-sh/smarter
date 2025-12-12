"""
smarter.lib.django.waffle
------------------------------

Enhanced, managed Django-waffle wrapper with short-lived Redis-based caching
and database readiness checks.

Features:

- Caching: Integrates short-lived Redis-based caching to optimize feature flag (switch) checks.
- Database Readiness Handling: Implements safeguards to prevent errors when the database is not ready.
- Feature Flag Management: Centralized mechanism to check if a feature flag (switch) is active.
- Custom Django Admin: Customized Django Admin class for managing waffle switches.
- Fixed Set of Switches: Defines a fixed set of waffle switches for the Smarter API.

.. important::

    These are managed feature flags; add any new switches to the SmarterWaffleSwitches class. These switches
    are verified duing deployments to ensure that they exist in the database. Missing switches are
    automatically created with a default inactive state.

.. important::

    django-waffle relies on database tables as well as Redis for storing and caching feature flags. If the database is not ready, waffle switch values
    will default to inactive (False) to prevent application errors.

Example:
    .. code-block:: python

        from smarter.lib.django.waffle import switch_is_active

        if switch_is_active(SmarterWaffleSwitches.ACCOUNT_LOGGING):
            print("API logging is enabled.")

Dependencies:

- `django-waffle <https://waffle.readthedocs.io/en/stable/>`_
- `django-redis <https://django-redis.readthedocs.io/en/stable/>`_
- `Redis <https://redis.io/documentation>`_
- `Django <https://docs.djangoproject.com/en/stable/>`_
"""

import logging

import waffle as waffle_orig
from django.db import connections
from django.db.utils import OperationalError, ProgrammingError
from waffle.admin import SwitchAdmin


# Also catch MySQLdb.OperationalError for lower-level DB errors
try:
    import MySQLdb

    MySQLdbOperationalError = MySQLdb.OperationalError
except ImportError:
    MySQLdbOperationalError = None

from smarter.common.helpers.console_helpers import formatted_text_green


logger = logging.getLogger(__name__)
prefix = formatted_text_green("smarter.lib.django.waffle.switch_is_active()")
logger.info(formatted_text_green("smarter.lib.django.waffle module loaded"))


# pylint: disable=C0115
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
        return hasattr(request, "user") and hasattr(request.user, "is_superuser") and request.user.is_superuser  # type: ignore[return-value]


class SmarterWaffleSwitches:
    """
    Enumerated data type for predefined, managed Smarter waffle switches.

    This class defines the fixed set of feature flags (Waffle switches) used by the Smarter Platform.
    Each class attribute represents a unique, centrally managed switch. These switches are
    automatically verified and created (if missing) during deployments, ensuring consistency
    and preventing runtime errors due to missing flags.

    .. note::

        Only switches defined in this class are considered valid for use in the Smarter codebase.
        To add a new feature flag, declare it as a class attribute here.

    Example usage:

        .. code-block:: python

            from smarter.lib.django.waffle import SmarterWaffleSwitches, switch_is_active

            if switch_is_active(SmarterWaffleSwitches.API_LOGGING):
                print("API logging is enabled.")

    """

    ACCOUNT_LOGGING = "log_account"
    """Enables logging throughout the smarter.app.account namespace."""

    API_LOGGING = "log_api"
    """Enables logging throughout the smarter.api namespace."""

    CACHE_LOGGING = "log_caching"
    """Enables detailed logging for caching operations including cache hits, misses, and errors."""

    PROMPT_LOGGING = "log_prompt"
    """Enables logging throughout the smarter.app.prompt namespace."""

    CHATAPP_LOGGING = "log_chatapp"
    """For the React Chat UI component. Enables debug-level javascript console logging inside the browser"""

    CHATBOT_LOGGING = "log_chatbot"
    """Enables logging throughout the smarter.app.chatbot namespace."""

    CHATBOT_HELPER_LOGGING = "log_chatbothelper"
    """Enables logging within the smarter.apps.chatbot.model.ChatBotHelper class."""

    CSRF_SUPPRESS_FOR_CHATBOTS = "disable_csrf_middleware_for_chatbots"
    """Disables CSRF middleware checks for chat completion endpoints."""

    JOURNAL = "enable_journal"
    """Enables the Smarter Journal feature."""

    MANIFEST_LOGGING = "log_manifest_brokers"
    """Enables detailed diagnostic logging for manifest initialization, validation and brokered operations."""

    MIDDLEWARE_LOGGING = "log_middleware"
    """Enables detailed diagnostic logging for all middleware operations."""

    PLUGIN_LOGGING = "log_plugin"
    """Enables logging throughout the smarter.app.plugin namespace."""

    PROVIDER_LOGGING = "log_provider"
    """Enables logging throughout the smarter.app.provider namespace."""

    REACTAPP_DEBUG_MODE = "enable_reactapp_debug_mode"
    """Enables React app debug mode within the Smarter React Chat component."""

    REQUEST_MIXIN_LOGGING = "log_request_mixin"
    """Enables detailed diagnostic logging for the SmarterRequestMixin class."""

    RECEIVER_LOGGING = "log_receivers"
    """Enables logging in all Django signal receivers throughout the Smarter codebase."""

    TASK_LOGGING = "log_tasks"
    """Enables logging in all Celery tasks throughout the Smarter codebase."""

    VIEW_LOGGING = "log_views"
    """Enables logging in all Django views throughout the Smarter codebase."""

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


def is_database_ready(alias="default"):
    """
    Check if the database is ready by verifying the connection and
    the existence of the waffle_switch table.

    :param alias: The database alias to check.
    :return: True if the database is ready, False otherwise.
    """

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


def switch_is_active(switch_name: str) -> bool:
    """
    Check if a Waffle switch is active, with caching and database readiness checks.

    .. important::

        This is the preferred method for checking Waffle switches in the Smarter codebase.
        It includes caching to optimize performance and handles database readiness to prevent errors.

    Example:
        .. code-block:: python

            from smarter.lib.django.waffle import SmarterWaffleSwitches, switch_is_active

            if switch_is_active(SmarterWaffleSwitches.API_LOGGING):
                print("API logging is enabled.")

    :param switch_name: The name of the Waffle switch to check.
    :return: True if the switch is active, False otherwise.
    :rtype: bool
    """
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
        return switch.is_active()
    except db_exceptions as e:
        logger.error("%s Database not ready or switch does not exist: %s", prefix, e, exc_info=True)
        return False
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("%s An error occurred while checking switch %s: %s", prefix, switch_name, e, exc_info=True)
        return False
