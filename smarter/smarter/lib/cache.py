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
logger_prefix = formatted_text("@cache_results()")


def cache_results(timeout=SMARTER_DEFAULT_CACHE_TIMEOUT, logging_enabled=True):
    """
    Caches the result of a function based on its arguments.
    The cache key is generated using a hash of the function name,
    and the string values of its arguments and the sorted key-values.

    note:
    - The cache is invalidated when the function is called with the same arguments and keyword arguments.
    - The cache key is generated using a SHA-256 hash of the function name, arguments, and sorted keyword arguments.
    - The cache is stored in Django's cache framework.
    - The cache key is prefixed with the module name and function name.
    """

    def decorator(func):
        def generate_sorted_kwargs(kwargs):
            """
            Sorts the keyword arguments to ensure consistent cache keys.
            """
            return tuple(sorted(kwargs.items()))

        def generate_key_data(func, args, kwargs):
            """
            Generates a raw cache key based on the function name, arguments, and sorted keyword arguments.
            """
            sorted_kwargs = generate_sorted_kwargs(kwargs)
            try:
                key_data = pickle.dumps((func.__name__, args, sorted_kwargs))
            except pickle.PickleError as e:
                logger.warning("%s Failed to pickle key data: %s", logger_prefix, e)
                return None

            return key_data

        def generate_cache_key(func, key_data):
            """
            Generates a fixed-length cache key based on a hash of key data.
            """
            return f"{func.__module__}.{func.__name__}()_" + hashlib.sha256(key_data).hexdigest()[:32]

        def unpickle_key_data(key_data):
            """
            Unpickles the key data to retrieve the original function name, arguments, and sorted keyword arguments.
            """
            try:
                return pickle.loads(key_data)  # nosec
            # pylint: disable=W0718
            except Exception as e:
                logger.error("%s Failed to unpickle key data: %s", logger_prefix, e)
                return None

        @wraps(func)
        def wrapper(*args, **kwargs):
            """
            Wrapper function that caches the result of the decorated function.
            If the result is already cached, it returns the cached result.
            If the result is not cached, it calls the function and caches the result.
            """
            key_data = generate_key_data(func, args, kwargs)
            # If key_data is None, we cannot generate a cache key, so we call the function directly
            # and return the result without caching.
            # This is a fallback to avoid breaking the application in case of pickling errors.
            if key_data is None:
                logger.error("%s Failed to generate cache key data for %s", logger_prefix, func.__name__)
                return func(*args, **kwargs)
            cache_key = generate_cache_key(func, key_data)
            unpickled_cache_key = unpickle_key_data(key_data)

            result = cache.get(cache_key)
            if result is not None:
                if logging_enabled and waffle.switch_is_active(SmarterWaffleSwitches.CACHE_LOGGING):
                    logger.info("%s cache hit for %s", formatted_text_green("@cache_results()"), unpickled_cache_key)
            else:
                result = func(*args, **kwargs)
                cache.set(cache_key, result, timeout)
                if logging_enabled and waffle.switch_is_active(SmarterWaffleSwitches.CACHE_LOGGING):
                    logger.info("%s caching %s", logger_prefix, unpickled_cache_key)
            return result

        def invalidate_cache(*args, **kwargs):
            """
            Invalidates the cache for the given function and its arguments.
            This is useful for clearing the cache when the underlying data changes."""
            key_data = generate_key_data(func, args, kwargs)
            cache_key = generate_cache_key(func, key_data)
            unpickled_cache_key = unpickle_key_data(key_data)
            result = cache.get(cache_key)
            if result is not None and logging_enabled and waffle.switch_is_active(SmarterWaffleSwitches.CACHE_LOGGING):
                logger.info("%s.invalidate_cache() invalidating %s", logger_prefix, unpickled_cache_key)
            else:
                logger.debug("%s.invalidate_cache() no cache entry found for %s", logger_prefix, unpickled_cache_key)
            cache.delete(cache_key)  # nosec
            if logging_enabled and waffle.switch_is_active(SmarterWaffleSwitches.CACHE_LOGGING):
                logger.info("%s.invalidate_cache() invalidated %s", logger_prefix, cache_key)

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
                logger.info("%s cache hit for %s", logger_prefix, cache_key)
            else:
                result = func(request, *args, **kwargs)
                cache.set(cache_key, result, timeout)
                if logging_enabled and waffle.switch_is_active(SmarterWaffleSwitches.CACHE_LOGGING):
                    logger.info("%s caching %s", formatted_text("cache_results()"), cache_key)
            return result

        return wrapper

    return decorator
