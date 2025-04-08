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


logger = logging.getLogger(__name__)
CACHE_EXPIRATION = 60  # seconds


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
        logger.error("Database not ready or switch does not exist: %s", e, exc_info=True)
        return False
    # pylint: disable=W0718
    except Exception as e:
        # Handle any other exceptions
        logger.error("An error occurred while checking switch %s: %s", switch_name, e, exc_info=True)
        return False
