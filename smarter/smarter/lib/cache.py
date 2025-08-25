"""chatbot utils"""

import hashlib
import logging
import pickle
from functools import wraps
from typing import Optional

from django.core.cache import cache
from django.http import HttpRequest

from smarter.common.const import SMARTER_DEFAULT_CACHE_TIMEOUT
from smarter.common.helpers.console_helpers import (
    formatted_text,
    formatted_text_green,
    formatted_text_red,
)
from smarter.common.utils import smarter_build_absolute_uri
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches


logger = logging.getLogger(__name__)
logger_prefix = formatted_text("@cache_results()")


class CacheSentinel:
    """
    A sentinel object to represent a cache entry that is None or a cache miss.
    """

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return f"<CacheSentinel: {hashlib.sha256(pickle.dumps(self.name)).hexdigest()[:32]}>"

    def __str__(self):
        return self.name


CACHE_NONE_SENTINEL = 'CacheSentinel("CACHE_NONE")'
CACHE_MISS_SENTINEL = CacheSentinel("CACHE_MISS")


def cache_results(timeout=SMARTER_DEFAULT_CACHE_TIMEOUT, logging_enabled=True):
    """
    Caches the result of a function based on its arguments.
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
            # unpickled_cache_key = unpickle_key_data(key_data)

            cached_result = cache.get(cache_key, CACHE_MISS_SENTINEL)
            if cached_result is not CACHE_MISS_SENTINEL:
                # We have a cache hit
                result = (
                    None if isinstance(cached_result, str) and cached_result == CACHE_NONE_SENTINEL else cached_result
                )
                if logging_enabled and waffle.switch_is_active(SmarterWaffleSwitches.CACHE_LOGGING):
                    logger.info(
                        "%s cache hit for %s: %s",
                        formatted_text_green("@cache_results()"),
                        cache_key,
                        "None" if result is None else result,
                    )
            else:
                # Cache miss - call the function
                result = func(*args, **kwargs)
                cache_value = CACHE_NONE_SENTINEL if result is None else result
                cache.set(cache_key, cache_value, timeout)
                if logging_enabled and waffle.switch_is_active(SmarterWaffleSwitches.CACHE_LOGGING):
                    logger.info(
                        "%s cache miss for %s, caching result: %s",
                        formatted_text_red("@cache_results()"),
                        cache_key,
                        "None" if result is None else result,
                    )
            return result

        def invalidate(*args, **kwargs):
            key_data = generate_key_data(func, args, kwargs)
            if key_data is None:
                return
            cache_key = generate_cache_key(func, key_data)
            cache.delete(cache_key)
            if logging_enabled and waffle.switch_is_active(SmarterWaffleSwitches.CACHE_LOGGING):
                logger.info(
                    "%s invalidated cache entry for %s",
                    formatted_text_red("@cache_results()"),
                    cache_key,
                )

        wrapper.invalidate = invalidate  # type: ignore[attr-defined]
        return wrapper

    return decorator


def cache_request(timeout=SMARTER_DEFAULT_CACHE_TIMEOUT, logging_enabled=True):
    """
    Caches the result of a function based on the request URI and user identifier.
    Associates a Smarter user account number with the cache key if the user is authenticated.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(request: HttpRequest, *args, **kwargs):
            if request is None or not isinstance(request, HttpRequest):
                logger.warning(
                    "%s.cache_request() received an invalid request object: %s",
                    logger_prefix,
                    type(request).__name__,
                )
                return func(request, *args, **kwargs)
            url = smarter_build_absolute_uri(request)
            user_identifier = (
                request.user.username if hasattr(request, "user") and request.user.is_authenticated else "anonymous"  # type: ignore[union-attr,attr-defined]
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
