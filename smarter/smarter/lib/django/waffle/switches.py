"""
SmarterWaffleSwitches - Predefined, centrally managed Waffle switches for the Smarter Platform.
"""

from dataclasses import dataclass


# pylint: disable=C0115
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

    CONNECTION_LOGGING = "log_connection"
    """Enables logging throughout the smarter.app.connection namespace."""

    PROMPT_LOGGING = "log_prompt"
    """Enables logging throughout the smarter.app.prompt namespace."""

    CHATAPP_LOGGING = "log_chatapp"
    """For the React Chat UI component. Enables debug-level javascript console logging inside the browser"""

    CHATBOT_LOGGING = "log_chatbot"
    """Enables logging throughout the smarter.app.chatbot namespace."""

    CHATBOT_HELPER_LOGGING = "log_chatbothelper"
    """Enables logging within the smarter.apps.chatbot.model.ChatBotHelper class."""

    SECRET_LOGGING = "log_secret"
    """Enables logging throughout the smarter.app.secret namespace."""

    VECTORSTORE_LOGGING = "log_vectorstore"
    """Enables logging throughout the smarter.app.vectorstore namespace."""

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
            default=True,
        ),
        ACCOUNT_MIXIN_LOGGING: SmarterWaffleSwitch(
            name=ACCOUNT_MIXIN_LOGGING,
            comment="Enables logging within the smarter.apps.account.mixins.AccountMixin class.",
            default=False,
        ),
        API_LOGGING: SmarterWaffleSwitch(
            name=API_LOGGING,
            comment="Enables logging throughout the smarter.api namespace.",
            default=True,
        ),
        CACHE_LOGGING: SmarterWaffleSwitch(
            name=CACHE_LOGGING,
            comment="Enables detailed logging for caching operations including cache hits, misses, and errors.",
            default=True,
        ),
        PROMPT_LOGGING: SmarterWaffleSwitch(
            name=PROMPT_LOGGING,
            comment="Enables logging throughout the smarter.app.prompt namespace.",
            default=True,
        ),
        CHATAPP_LOGGING: SmarterWaffleSwitch(
            name=CHATAPP_LOGGING,
            comment="For the React Chat UI component. Enables debug-level javascript console logging inside the browser",
            default=True,
        ),
        CHATBOT_LOGGING: SmarterWaffleSwitch(
            name=CHATBOT_LOGGING,
            comment="Enables logging throughout the smarter.app.chatbot namespace.",
            default=True,
        ),
        CONNECTION_LOGGING: SmarterWaffleSwitch(
            name=CONNECTION_LOGGING,
            comment="Enables logging throughout the smarter.app.connection namespace.",
            default=True,
        ),
        SECRET_LOGGING: SmarterWaffleSwitch(
            name=SECRET_LOGGING,
            comment="Enables logging throughout the smarter.app.secret namespace.",
            default=True,
        ),
        VECTORSTORE_LOGGING: SmarterWaffleSwitch(
            name=VECTORSTORE_LOGGING,
            comment="Enables logging throughout the smarter.app.vectorstore namespace.",
            default=True,
        ),
        CHATBOT_HELPER_LOGGING: SmarterWaffleSwitch(
            name=CHATBOT_HELPER_LOGGING,
            comment="Enables logging within the smarter.apps.chatbot.model.ChatBotHelper class.",
            default=True,
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
            default=True,
        ),
        ENABLE_MIDDLEWARE_SECURITY: SmarterWaffleSwitch(
            name=ENABLE_MIDDLEWARE_SECURITY,
            comment="Enables SmarterSecurityMiddleware",
            default=False,
        ),
        ENABLE_REACTAPP_DEBUG_MODE: SmarterWaffleSwitch(
            name=ENABLE_REACTAPP_DEBUG_MODE,
            comment="Enables React app debug mode within the Smarter React Chat component.",
            default=True,
        ),
        ENABLE_NEW_USER_PASSWORD_EMAIL: SmarterWaffleSwitch(
            name=ENABLE_NEW_USER_PASSWORD_EMAIL,
            comment="Enables sending textemail with password to new users.",
            default=False,
        ),
        MANIFEST_LOGGING: SmarterWaffleSwitch(
            name=MANIFEST_LOGGING,
            comment="Enables detailed diagnostic logging for manifest initialization, validation and brokered operations.",
            default=True,
        ),
        MIDDLEWARE_LOGGING: SmarterWaffleSwitch(
            name=MIDDLEWARE_LOGGING,
            comment="Enables detailed diagnostic logging for all middleware operations.",
            default=False,
        ),
        PLUGIN_LOGGING: SmarterWaffleSwitch(
            name=PLUGIN_LOGGING,
            comment="Enables logging throughout the smarter.app.plugin namespace.",
            default=True,
        ),
        PROVIDER_LOGGING: SmarterWaffleSwitch(
            name=PROVIDER_LOGGING,
            comment="Enables logging throughout the smarter.app.provider namespace.",
            default=True,
        ),
        REQUEST_MIXIN_LOGGING: SmarterWaffleSwitch(
            name=REQUEST_MIXIN_LOGGING,
            comment="Enables detailed diagnostic logging for the SmarterRequestMixin class.",
            default=False,
        ),
        RECEIVER_LOGGING: SmarterWaffleSwitch(
            name=RECEIVER_LOGGING,
            comment="Enables logging in all Django signal receivers throughout the Smarter codebase.",
            default=True,
        ),
        TASK_LOGGING: SmarterWaffleSwitch(
            name=TASK_LOGGING,
            comment="Enables logging in all Celery tasks throughout the Smarter codebase.",
            default=True,
        ),
        VALIDATOR_LOGGING: SmarterWaffleSwitch(
            name=VALIDATOR_LOGGING,
            comment="Enables logging in all Django model field validators throughout the Smarter codebase.",
            default=False,
        ),
        VIEW_LOGGING: SmarterWaffleSwitch(
            name=VIEW_LOGGING,
            comment="Enables logging in all Django views throughout the Smarter codebase.",
            default=True,
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

__all__ = ["SmarterWaffleSwitches", "smarter_waffle_switches"]
