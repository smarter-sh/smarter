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

from smarter.common.const import SMARTER_DEFAULT_CACHE_TIMEOUT
from smarter.common.helpers.console_helpers import formatted_text


logger = logging.getLogger(__name__)
CACHE_EXPIRATION = 60  # seconds
prefix = formatted_text("switch_is_active()")


# Smarter Waffle Switches and Flags
class SmarterWaffleSwitches:
    """A class representing the fixed set of Waffle switches for the Smarter API."""

    ACCOUNT_MIXIN_LOGGING = "account_mixin_logging"
    CACHE_LOGGING = "cache_logging"
    CHAT_LOGGING = "chat_logging"
    CHATAPP_LOGGING = "chatapp_logging"
    CHATBOT_LOGGING = "chatbot_logging"
    CHATBOT_HELPER_LOGGING = "chatbothelper_logging"
    CSRF_SUPPRESS_FOR_CHATBOTS = "csrf_middleware_suppress_for_chatbots"
    JOURNAL = "journal"
    MANIFEST_LOGGING = "manifest_logging"
    MIDDLEWARE_LOGGING = "middleware_logging"
    REACTAPP_DEBUG_MODE = "reactapp_debug_mode"
    REQUEST_MIXIN_LOGGING = "request_mixin_logging"

    @property
    def all(self):
        """Return all switches."""
        return [
            self.ACCOUNT_MIXIN_LOGGING,
            self.CACHE_LOGGING,
            self.CHAT_LOGGING,
            self.CHATAPP_LOGGING,
            self.CHATBOT_LOGGING,
            self.CHATBOT_HELPER_LOGGING,
            self.CSRF_SUPPRESS_FOR_CHATBOTS,
            self.JOURNAL,
            self.MANIFEST_LOGGING,
            self.MIDDLEWARE_LOGGING,
            self.REACTAPP_DEBUG_MODE,
            self.REQUEST_MIXIN_LOGGING,
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
    try:
        switch = waffle_orig.get_waffle_switch_model().get(switch_name)
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
