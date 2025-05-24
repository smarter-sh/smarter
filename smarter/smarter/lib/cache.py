"""chatbot utils"""

import hashlib
import logging
import pickle
from functools import wraps
from urllib.parse import urlparse

from django.core.cache import cache
from django.core.handlers.wsgi import WSGIRequest

from smarter.common.const import SMARTER_DEFAULT_CACHE_TIMEOUT, SmarterWaffleSwitches
from smarter.common.helpers.console_helpers import formatted_text, formatted_text_green
from smarter.lib.django import waffle


logger = logging.getLogger(__name__)


def cache_results(timeout=SMARTER_DEFAULT_CACHE_TIMEOUT, logging_enabled=True):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            sorted_kwargs = tuple(sorted(kwargs.items()))
            key_data = pickle.dumps((func.__name__, args, sorted_kwargs))
            cache_key = f"{func.__module__}.{func.__name__}()_" + hashlib.sha256(key_data).hexdigest()[:32]

            result = cache.get(cache_key)
            if result is not None:
                if logging_enabled and waffle.switch_is_active(SmarterWaffleSwitches.CACHE_LOGGING):
                    logger.info("%s cache hit for %s", formatted_text_green("cache_results()"), cache_key)
            else:
                result = func(*args, **kwargs)
                cache.set(cache_key, result, timeout)
                if logging_enabled and waffle.switch_is_active(SmarterWaffleSwitches.CACHE_LOGGING):
                    logger.info("%s caching %s", formatted_text("cache_results()"), cache_key)
            return result

        def invalidate_cache(*args, **kwargs):
            sorted_kwargs = tuple(sorted(kwargs.items()))
            key_data = pickle.dumps((func.__name__, args, sorted_kwargs))
            cache_key = f"{func.__module__}.{func.__name__}()_" + hashlib.sha256(key_data).hexdigest()[:32]  # nosec
            logger.info("%s invalidating %s", formatted_text("@cache_results()"), pickle.loads(key_data))  # nosec
            cache.delete(cache_key)  # nosec
            if logging_enabled and waffle.switch_is_active(SmarterWaffleSwitches.CACHE_LOGGING):
                logger.info("%s invalidated %s", formatted_text("cache_results()"), cache_key)

        wrapper.invalidate_cache = invalidate_cache
        return wrapper

    return decorator


def cache_request(timeout=SMARTER_DEFAULT_CACHE_TIMEOUT, logging_enabled=True):
    """
    Caches the result of a function based on the request URI and user identifier.
    Associates a Smarter user account number with the cache key if the user is authenticated.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(request: WSGIRequest, *args, **kwargs):
            parsed_url = urlparse(request.build_absolute_uri())
            url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
            user_identifier = (
                request.user.username if hasattr(request, "user") and request.user.is_authenticated else "anonymous"
            )
            cache_key = f"{func.__name__}_{url}_{user_identifier}"
            result = cache.get(cache_key)
            if result and logging_enabled and waffle.switch_is_active(SmarterWaffleSwitches.CACHE_LOGGING):
                logger.info("%s cache hit for %s", formatted_text_green("cache_results()"), cache_key)
            else:
                result = func(request, *args, **kwargs)
                cache.set(cache_key, result, timeout)
                if logging_enabled and waffle.switch_is_active(SmarterWaffleSwitches.CACHE_LOGGING):
                    logger.info("%s caching %s", formatted_text("cache_results()"), cache_key)
            return result

        return wrapper

    return decorator
