"""
This module provides a wrapper around the django-waffle library to
add caching and to handle an init scendario where the database is not ready.
It is used to check if a feature flag (switch) is active.
"""

import logging
from functools import wraps

import waffle as waffle_orig
from django.core.cache import cache
from django.db.utils import OperationalError
from waffle.admin import SwitchAdmin

from smarter.common.const import SMARTER_DEFAULT_CACHE_TIMEOUT
from smarter.common.helpers.console_helpers import formatted_text_green


logger = logging.getLogger(__name__)
CACHE_EXPIRATION = 60  # seconds
prefix = formatted_text_green("smarter.lib.django.waffle.switch_is_active()")


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
            result = cache.get(cache_key)
            if not result:
                result = func(*args, **kwargs)
                cache.set(cache_key, result, timeout)
            return result

        return wrapper

    return decorator


@cache_results(timeout=CACHE_EXPIRATION)
def switch_is_active(switch_name: str) -> bool:
    if not isinstance(switch_name, str):
        logger.error("%s switch_name must be a string, got %s", prefix, type(switch_name).__name__)
        return False
    if switch_name not in SmarterWaffleSwitches().all:
        logger.error("%s switch_name '%s' is not a valid SmarterWaffleSwitches attribute", prefix, switch_name)
        return False
    try:
        switch = waffle_orig.get_waffle_switch_model().get(switch_name)
        if switch.is_active():
            logger.info("%s: %s is active and will be cached for %s seconds.", prefix, switch_name, CACHE_EXPIRATION)
        return switch.is_active()
    except OperationalError as e:
        # Handle the case where the database is not ready
        # or the switch does not exist
        logger.error("%s Database not ready or switch does not exist: %s", prefix, e, exc_info=True)
        return False
    # pylint: disable=W0718
    except Exception as e:
        # Handle any other exceptions
        logger.error("%s An error occurred while checking switch %s: %s", prefix, switch_name, e, exc_info=True)
        return False
