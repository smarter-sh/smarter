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
from dataclasses import dataclass

import waffle as waffle_orig
from django.apps import apps
from django.core.exceptions import AppRegistryNotReady
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
prefix = formatted_text_green(f"{__name__}.switch_is_active()")
cache_prefix = f"{__name__}"


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


@dataclass(frozen=True)
class SmarterWaffleSwitch:
    name: str
    comment: str
    default: bool

    def to_json(self) -> dict[str, str | bool]:
        return {
            "name": self.name,
            "comment": self.comment,
            "default": self.default,
        }


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

    _all: list[str] = []  # Internal list to track all switch names

    ALLOW_API_GET = "allow_api_get"
    """Allows GET requests to the API endpoints, which are normally restricted to POST requests."""

    ACCOUNT_LOGGING = "log_account"
    """Enables logging throughout the smarter.app.account namespace."""

    ACCOUNT_MIXIN_LOGGING = "log_account_mixin"
    """Enables logging within the smarter.apps.account.mixins.AccountMixin class."""

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

    ENABLE_DEBUG_MODE = "enable_debug_mode"
    """Enables debug mode for the entire Smarter application, which may include additional logging and diagnostic information."""

    ENABLE_JOURNAL = "enable_journal"
    """Enables the Smarter Journal feature."""

    ENABLE_OAUTH2 = "enable_oauth2"
    """Enables OAuth2 authentication support."""

    ENABLE_ACCOUNT_REGISTRATION = "enable_account_registration"
    """Enables account registration link."""

    ENABLE_LOGIN_FOOTER_LINKS = "enable_login_footer_links"
    """Enables additional links in the login page footer, such as 'Legal' and 'Contact'."""

    ENABLE_MULTITENANT_AUTHENTICATION = "enable_multitenant_authentication"
    """Enables multi-tenant authentication support for hosted Smarter platforms."""

    ENABLE_MIDDLEWARE_SENSITIVE_FILES = "enable_middleware_block_sensitive_files"
    """Enables SmarterBlockSensitiveFilesMiddleware"""

    ENABLE_MIDDLEWARE_EXCESSIVE_404 = "enable_middleware_block_excessive_404"
    """Enables SmarterBlockExcessive404Middleware"""

    ENABLE_MIDDLEWARE_CORS = "enable_middleware_cors"
    """Enables SmarterCorsMiddleware"""

    ENABLE_MIDDLEWARE_SECURITY = "enable_middleware_security"
    """Enables SmarterSecurityMiddleware"""

    ENABLE_REACTAPP_DEBUG_MODE = "enable_reactapp_debug_mode"
    """Enables React app debug mode within the Smarter React Chat component."""

    ENABLE_NEW_USER_PASSWORD_EMAIL = "enable_new_user_password_email"
    """Enables sending textemail with password to new users."""

    ENABLE_SMARTER_PAGE_CACHING = "enable_smarter_page_caching"
    """Enables the Smarter user-based page caching decorator for user-facing pages to improve performance."""

    MANIFEST_LOGGING = "log_manifest_brokers"
    """Enables detailed diagnostic logging for manifest initialization, validation and brokered operations."""

    MIDDLEWARE_LOGGING = "log_middleware"
    """Enables detailed diagnostic logging for all middleware operations."""

    PLUGIN_LOGGING = "log_plugin"
    """Enables logging throughout the smarter.app.plugin namespace."""

    PROVIDER_LOGGING = "log_provider"
    """Enables logging throughout the smarter.app.provider namespace."""

    REQUEST_MIXIN_LOGGING = "log_request_mixin"
    """Enables detailed diagnostic logging for the SmarterRequestMixin class."""

    RECEIVER_LOGGING = "log_receivers"
    """Enables logging in all Django signal receivers throughout the Smarter codebase."""

    TASK_LOGGING = "log_tasks"
    """Enables logging in all Celery tasks throughout the Smarter codebase."""

    VALIDATOR_LOGGING = "log_validators"
    """Enables logging in all Django model field validators throughout the Smarter codebase."""

    VIEW_LOGGING = "log_views"
    """Enables logging in all Django views throughout the Smarter codebase."""

    switches = {
        ALLOW_API_GET: SmarterWaffleSwitch(
            name=ALLOW_API_GET,
            comment="Allows GET requests to the API endpoints, which are normally restricted to POST requests.",
            default=False,
        ),
        ACCOUNT_LOGGING: SmarterWaffleSwitch(
            name=ACCOUNT_LOGGING,
            comment="Enables logging throughout the smarter.app.account namespace.",
            default=False,
        ),
        ACCOUNT_MIXIN_LOGGING: SmarterWaffleSwitch(
            name=ACCOUNT_MIXIN_LOGGING,
            comment="Enables logging within the smarter.apps.account.mixins.AccountMixin class.",
            default=False,
        ),
        API_LOGGING: SmarterWaffleSwitch(
            name=API_LOGGING,
            comment="Enables logging throughout the smarter.api namespace.",
            default=False,
        ),
        CACHE_LOGGING: SmarterWaffleSwitch(
            name=CACHE_LOGGING,
            comment="Enables detailed logging for caching operations including cache hits, misses, and errors.",
            default=False,
        ),
        PROMPT_LOGGING: SmarterWaffleSwitch(
            name=PROMPT_LOGGING,
            comment="Enables logging throughout the smarter.app.prompt namespace.",
            default=False,
        ),
        CHATAPP_LOGGING: SmarterWaffleSwitch(
            name=CHATAPP_LOGGING,
            comment="For the React Chat UI component. Enables debug-level javascript console logging inside the browser",
            default=False,
        ),
        CHATBOT_LOGGING: SmarterWaffleSwitch(
            name=CHATBOT_LOGGING,
            comment="Enables logging throughout the smarter.app.chatbot namespace.",
            default=False,
        ),
        CHATBOT_HELPER_LOGGING: SmarterWaffleSwitch(
            name=CHATBOT_HELPER_LOGGING,
            comment="Enables logging within the smarter.apps.chatbot.model.ChatBotHelper class.",
            default=False,
        ),
        CSRF_SUPPRESS_FOR_CHATBOTS: SmarterWaffleSwitch(
            name=CSRF_SUPPRESS_FOR_CHATBOTS,
            comment="Disables CSRF middleware checks for chat completion endpoints.",
            default=False,
        ),
        ENABLE_DEBUG_MODE: SmarterWaffleSwitch(
            name=ENABLE_DEBUG_MODE,
            comment="Enables debug mode for the entire Smarter application, which may include additional logging and diagnostic information.",
            default=False,
        ),
        ENABLE_JOURNAL: SmarterWaffleSwitch(
            name=ENABLE_JOURNAL,
            comment="Enables the Smarter Journal feature.",
            default=False,
        ),
        ENABLE_OAUTH2: SmarterWaffleSwitch(
            name=ENABLE_OAUTH2,
            comment="Enables OAuth2 authentication support.",
            default=False,
        ),
        ENABLE_SMARTER_PAGE_CACHING: SmarterWaffleSwitch(
            name="enable_smarter_page_caching",
            comment="Enables the Smarter user-based page caching decorator for user-facing pages to improve performance.",
            default=True,
        ),
        ENABLE_ACCOUNT_REGISTRATION: SmarterWaffleSwitch(
            name=ENABLE_ACCOUNT_REGISTRATION,
            comment="Enables account registration link.",
            default=False,
        ),
        ENABLE_LOGIN_FOOTER_LINKS: SmarterWaffleSwitch(
            name=ENABLE_LOGIN_FOOTER_LINKS,
            comment="Enables additional links in the login page footer, such as 'Legal' and 'Contact'.",
            default=False,
        ),
        ENABLE_MULTITENANT_AUTHENTICATION: SmarterWaffleSwitch(
            name=ENABLE_MULTITENANT_AUTHENTICATION,
            comment="Enables multi-tenant authentication support for hosted Smarter platforms.",
            default=False,
        ),
        ENABLE_MIDDLEWARE_SENSITIVE_FILES: SmarterWaffleSwitch(
            name=ENABLE_MIDDLEWARE_SENSITIVE_FILES,
            comment="Enables SmarterBlockSensitiveFilesMiddleware",
            default=False,
        ),
        ENABLE_MIDDLEWARE_EXCESSIVE_404: SmarterWaffleSwitch(
            name=ENABLE_MIDDLEWARE_EXCESSIVE_404,
            comment="Enables SmarterBlockExcessive404Middleware",
            default=False,
        ),
        ENABLE_MIDDLEWARE_CORS: SmarterWaffleSwitch(
            name=ENABLE_MIDDLEWARE_CORS,
            comment="Enables SmarterCorsMiddleware",
            default=False,
        ),
        ENABLE_MIDDLEWARE_SECURITY: SmarterWaffleSwitch(
            name=ENABLE_MIDDLEWARE_SECURITY,
            comment="Enables SmarterSecurityMiddleware",
            default=False,
        ),
        ENABLE_REACTAPP_DEBUG_MODE: SmarterWaffleSwitch(
            name=ENABLE_REACTAPP_DEBUG_MODE,
            comment="Enables React app debug mode within the Smarter React Chat component.",
            default=False,
        ),
        ENABLE_NEW_USER_PASSWORD_EMAIL: SmarterWaffleSwitch(
            name=ENABLE_NEW_USER_PASSWORD_EMAIL,
            comment="Enables sending textemail with password to new users.",
            default=False,
        ),
        MANIFEST_LOGGING: SmarterWaffleSwitch(
            name=MANIFEST_LOGGING,
            comment="Enables detailed diagnostic logging for manifest initialization, validation and brokered operations.",
            default=False,
        ),
        MIDDLEWARE_LOGGING: SmarterWaffleSwitch(
            name=MIDDLEWARE_LOGGING,
            comment="Enables detailed diagnostic logging for all middleware operations.",
            default=False,
        ),
        PLUGIN_LOGGING: SmarterWaffleSwitch(
            name=PLUGIN_LOGGING,
            comment="Enables logging throughout the smarter.app.plugin namespace.",
            default=False,
        ),
        PROVIDER_LOGGING: SmarterWaffleSwitch(
            name=PROVIDER_LOGGING,
            comment="Enables logging throughout the smarter.app.provider namespace.",
            default=False,
        ),
        REQUEST_MIXIN_LOGGING: SmarterWaffleSwitch(
            name=REQUEST_MIXIN_LOGGING,
            comment="Enables detailed diagnostic logging for the SmarterRequestMixin class.",
            default=False,
        ),
        RECEIVER_LOGGING: SmarterWaffleSwitch(
            name=RECEIVER_LOGGING,
            comment="Enables logging in all Django signal receivers throughout the Smarter codebase.",
            default=False,
        ),
        TASK_LOGGING: SmarterWaffleSwitch(
            name=TASK_LOGGING,
            comment="Enables logging in all Celery tasks throughout the Smarter codebase.",
            default=False,
        ),
        VALIDATOR_LOGGING: SmarterWaffleSwitch(
            name=VALIDATOR_LOGGING,
            comment="Enables logging in all Django model field validators throughout the Smarter codebase.",
            default=False,
        ),
        VIEW_LOGGING: SmarterWaffleSwitch(
            name=VIEW_LOGGING,
            comment="Enables logging in all Django views throughout the Smarter codebase.",
            default=False,
        ),
    }

    @property
    def all(self):
        """Return all switches."""
        if not self._all:
            self._all = [
                getattr(self, attr) for attr in dir(self) if attr.isupper() and isinstance(getattr(self, attr), str)
            ]
        return self._all


smarter_waffle_switches = SmarterWaffleSwitches()
"""
Singleton instance of SmarterWaffleSwitches to be used throughout the codebase.
"""


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
    # Prevent model access before Django app registry is ready
    if not apps.ready:
        logger.warning("%s App registry not ready, assuming switch %s is inactive.", prefix, switch_name)
        return False

    try:
        if not is_database_ready():
            logger.warning("%s Database not ready, assuming switch %s is inactive.", prefix, switch_name)
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
        switch = waffle_orig.get_waffle_switch_model().get(switch_name)
        return switch.is_active()
    except (*db_exceptions, AppRegistryNotReady) as e:
        logger.error(
            "%s Database not ready, App Registry not ready, or switch does not exist: %s", prefix, e, exc_info=True
        )
        return False
