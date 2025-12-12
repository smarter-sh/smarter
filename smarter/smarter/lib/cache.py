"""chatbot utils"""

import hashlib
import logging
import pickle
from functools import wraps

from django.http import HttpRequest

from smarter.common.const import SMARTER_DEFAULT_CACHE_TIMEOUT
from smarter.common.helpers.console_helpers import (
    formatted_text,
    formatted_text_green,
    formatted_text_red,
)
from smarter.common.utils import is_authenticated_request, smarter_build_absolute_uri


logger = logging.getLogger(__name__)
logger_prefix = formatted_text("@cache_results()")
logger.info("%s cache module loaded", logger_prefix)


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


class LazyCache:
    """
    A lazy wrapper around Django's cache framework that defers importing the cache
    until an attribute is accessed. This helps avoid premature initialization issues.
    """

    is_ready = False
    cache_logging = False

    def __getattr__(self, name):
        # pylint: disable=import-outside-toplevel
        from django.core.cache import cache

        # Import waffle here to avoid triggering Django cache initialization too early.
        from smarter.lib.django import waffle
        from smarter.lib.django.waffle import SmarterWaffleSwitches

        self.cache_logging = waffle.switch_is_active(SmarterWaffleSwitches.CACHE_LOGGING)

        if not self.is_ready:
            # First access, perform diagnostics to verify how Django initialized the cache
            self.is_ready = True
            logger.info("%s django.core.cache imported.", logger_prefix)

            from django.core.cache import caches
            from django.utils.connection import ConnectionProxy
            from django_redis.cache import RedisCache

            cache.set("test_key", "test_value", timeout=5)
            value = cache.get("test_key")
            if value == "test_value":
                logger.info("Django cache is up and reachable.")
            else:
                logger.error("Django cache is not working as expected.")

            if not isinstance(caches["default"], RedisCache):
                logger.warning(
                    "django.core.cache.caches['default'] was expecting django_redis.cache.RedisCache but found: %s",
                    caches["default"].__class__,
                )

                if isinstance(cache, ConnectionProxy):
                    # diagnostics for misconfigured Django Redis cache
                    logger.error(
                        "Django has silently fallen back to a ConnectionProxy cache. The actual backend is: %s",
                        caches["default"].__class__,
                    )
                else:
                    logger.warning("Was expecting a Redis cache, but found: %s instead.", cache.__class__)
            else:
                logger.info("Cache is a direct instance of: %s", caches["default"].__class__)

        return getattr(cache, name)


lazy_cache = LazyCache()


def cache_results(timeout=SMARTER_DEFAULT_CACHE_TIMEOUT, logging_enabled=True):
    """
    Decorator that caches the result of a function based on its arguments.

    The cache key is generated from the function name, positional arguments, and sorted keyword arguments.
    If the result is already cached, it is returned directly. Otherwise, the function is called and its
    result is cached. The cache key is created by serializing the function name, its positional arguments,
    and its sorted keyword arguments using pickle. This serialized data is then hashed with SHA-256,
    and the first 32 characters of the hash are used as part of the cache key, prefixed by the function’s
    module and name. This ensures that each unique set of arguments generates a unique cache key.
    There is a non-zero probability of hash collisions, but it is *EXTREMELY* low for practical purposes.
    Smarter's cache entries are short-lived, further reducing the risk of collisions impacting functionality.

    :param timeout: The cache timeout in seconds. Defaults to ``SMARTER_DEFAULT_CACHE_TIMEOUT``.
    :type timeout: int
    :param logging_enabled: Whether to enable logging for cache hits and misses. Defaults to ``True``.
    :type logging_enabled: bool
    :return: The decorated function with caching applied.
    :rtype: Callable

    .. note::
        If the function returns ``None``, a sentinel value is cached to distinguish between a cached ``None``
        and a cache miss.

    Usage example::

        @cache_results(timeout=60)
        def expensive_function(x, y):
            return x + y

    The decorator also adds an ``invalidate`` method to the wrapped function, which can be used to
    manually remove the cached result for specific arguments::

        expensive_function.invalidate(1, 2)
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

            cached_result = lazy_cache.get(cache_key, CACHE_MISS_SENTINEL)
            if cached_result is not CACHE_MISS_SENTINEL:
                # We have a cache hit
                result = (
                    None if isinstance(cached_result, str) and cached_result == CACHE_NONE_SENTINEL else cached_result
                )
                if logging_enabled and lazy_cache.cache_logging:
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
                lazy_cache.set(cache_key, cache_value, timeout)
                if logging_enabled and lazy_cache.cache_logging:
                    logger.info(
                        "%s cache miss for %s, caching result: %s with timeout %s",
                        formatted_text_red("@cache_results()"),
                        cache_key,
                        cache_value,
                        timeout,
                    )
            return result

        def invalidate(*args, **kwargs):
            key_data = generate_key_data(func, args, kwargs)
            if key_data is None:
                return
            cache_key = generate_cache_key(func, key_data)
            lazy_cache.delete(cache_key)
            if logging_enabled and lazy_cache.cache_logging:
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
                request.user.username if is_authenticated_request(request) else "anonymous"  # type: ignore[union-attr,attr-defined]
            )
            cache_key = f"{func.__name__}_{url}_{user_identifier}"
            result = lazy_cache.get(cache_key)
            if result and logging_enabled and lazy_cache.cache_logging:
                logger.info("%s cache hit for %s", logger_prefix, cache_key)
            else:
                result = func(request, *args, **kwargs)
                lazy_cache.set(cache_key, result, timeout)
                if logging_enabled and lazy_cache.cache_logging:
                    logger.info("%s caching %s with timeout %s", formatted_text("cache_results()"), cache_key, timeout)
            return result

        return wrapper

    return decorator
