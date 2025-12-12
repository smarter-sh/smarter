"""
The Smarter Framework implements its own, proprietary caching technology,
designed as a one-size-fits-all easy-to-implement solution for caching
function outputs based on their input parameters.

This module consists of two main components:

- a general-purpose caching decorator, ``@cache_results()``, for caching function results, and
- a lazy singleton cache wrapper, ``lazy_cache``, around Django's cache framework.

Usage examples::

    # work directly with the cache
    from smarter.lib.cache import lazy_cache as cache

    cache.set("my_key", "my_value", timeout=300)
    value = cache.get("my_key")
    print(value)  # Outputs: "my_value"

    # use the caching decorator
    @cache_results(timeout=600)
    def expensive_function(x, y, *args, **kwargs):
        # Perform expensive computation ...
        result = "some very expensive computational result"
        return result

    result = expensive_function(1, 2)
    expensive_function.invalidate(1, 2)

"""

import hashlib
import logging
import pickle
from functools import wraps
from typing import Any, Callable, Optional

from django.http import HttpRequest

from smarter.common.const import SMARTER_DEFAULT_CACHE_TIMEOUT
from smarter.common.helpers.console_helpers import (
    formatted_text,
    formatted_text_green,
    formatted_text_red,
)
from smarter.common.utils import is_authenticated_request, smarter_build_absolute_uri
from smarter.lib.django.waffle import SmarterWaffleSwitches


logger = logging.getLogger(__name__)
logger_prefix = formatted_text("@cache_results()")


class CacheSentinel:
    """
    Sentinel object for cache state representation.

    This class is used to distinguish between different cache states, specifically to represent
    cases where a cache entry is explicitly set to ``None`` or when a cache lookup results in a miss.
    By using a unique sentinel object, the cache logic can reliably differentiate between a value
    that is intentionally ``None`` and a value that is absent from the cache.

    **Usage scenarios:**

    - When a cached function or value may legitimately return ``None``, this sentinel ensures that
      a cached ``None`` is not mistaken for a cache miss.
    - Used internally by caching decorators and cache wrappers to provide robust cache semantics.

    **Example:**

    .. code-block:: python

        sentinel = CacheSentinel("CACHE_MISS")
        cache_value = cache.get(key, sentinel)
        if cache_value is sentinel:
            # Handle cache miss
            ...
        elif cache_value is None:
            # Handle cached None
            ...

    The string representation of the sentinel is the name provided at construction, while the
    ``repr`` includes a hash for uniqueness. This makes it suitable for use as a default value
    in cache lookups and for debugging purposes.
    """

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return f"<CacheSentinel: {hashlib.sha256(pickle.dumps(self.name)).hexdigest()[:32]}>"

    def __str__(self):
        return self.name


CACHE_NONE_SENTINEL = 'CacheSentinel("CACHE_NONE")'
CACHE_MISS_SENTINEL = CacheSentinel("CACHE_MISS")


# pylint: disable=C2801,E1102,W0613
class LazyCache:
    """
    A lazy wrapper around Django's cache framework that defers importing the cache
    until just before it is used for the first time.
    This helps avoid premature initialization issues. See https://docs.djangoproject.com/en/5.2/topics/cache/

    Usage example::

        from smarter.lib.cache import lazy_cache as cache

        cache.set("my_key", "my_value", timeout=300)
        value = cache.get("my_key")
        print(value)  # Outputs: "my_value"

    This class performs diagnostics on first access to verify that the Django cache
    has been initialized correctly, logging relevant information about the cache backend.
    It is intended to be used as a singleton instance named `lazy_cache` (see below).

    It also checks for a Waffle switch to enable or disable cache logging.

    """

    _cache = None
    _waffle = None

    # pylint: disable=C0415
    @property
    def cache(self):
        """
        Lazily import and return Django's cache framework.
        Performs diagnostics on first access to verify that the cache
        has initialized correctly (eg as expected, as per the Django settings).

        .. important::

            This is reason #1 for using ``lazy_cache`` instead of importing Django's cache.
            This delays importing django.core.cache until first access, preventing premature
            initialization issues where Django falls back to a default cache backend unexpectedly.
            When this happens, the fallback cache may not persist data as expected, leading to
            buggy cache misses such as browser session values not being stored.

        :return: The Django cache instance.
        :rtype: django.core.cache.Cache
        """
        if self._cache is None:
            from django.core.cache import cache, caches
            from django_redis.cache import RedisCache

            logger.info("%s django.core.cache imported.", logger_prefix)

            self._cache = cache

            try:
                # perform diagnostics on first access
                cache.set("test_key", "test_value", timeout=5)
                value = cache.get("test_key")
                if value == "test_value":
                    logger.info("Django cache is up and reachable.")
                else:
                    logger.error("Django cache is not working as expected.")
            # pylint: disable=broad-except
            except Exception as e:
                logger.error("Error accessing Django cache: %s", e)

            if not isinstance(caches["default"], RedisCache):
                logger.warning(
                    "django.core.cache.caches['default'] was expecting django_redis.cache.RedisCache but found: %s",
                    caches["default"].__class__,
                )

        return self._cache

    @property
    def waffle(self):
        """
        Lazily import and return the Waffle module. Lookalike function api such as switch_is_active() with identical signatures.

        Provides enhanced, managed Django-waffle wrapper with short-lived Redis-based
        caching and database readiness checks. Used for feature flagging.


        Features:

            - **Caching**: Integrates short-lived Redis-based caching to optimize feature flag (switch) checks.
            - **Database** Readiness Handling: Implements safeguards to prevent errors when the database is not ready.
            - **Feature Flag Management**: Centralized mechanism to check if a feature flag (switch) is active.
            - **Custom Django Admin**: Customized Django Admin class for managing waffle switches.
            - **Fixed Set of Switches**: Defines a fixed set of waffle switches for the Smarter API.

        .. important::

            This is reason #2 for using ``lazy_cache`` instead of importing Waffle directly.
            This delays importing Waffle until first access. Waffle aggressively
            caches its state which can also lead to premature initialization issues
            if imported too early in the Django startup process.

        :return: The Waffle module.
        :rtype: module
        """
        if self._waffle is None:
            from smarter.lib.django import waffle

            self._waffle = waffle

        return self._waffle

    @property
    def cache_logging(self) -> bool:
        """
        Check if cache activity logging (here, inside this module) is enabled via Waffle switch.

        :return: True if cache logging is enabled, False otherwise.
        :rtype: bool
        """
        return self.waffle.switch_is_active(SmarterWaffleSwitches.CACHE_LOGGING)

    def get(self, key: Any, default: Optional[Any] = None):
        """
        Fetch a given key from the cache. If the key does not exist, return default, which itself defaults to None.
        """
        return self.cache.get(key, default)  # type: ignore[return-value]

    def set(self, key: Any, value: Any, timeout: Optional[float] = None, version: Optional[int] = None):
        """
        Set a value in the cache. If timeout is given, use that timeout for the key; otherwise use the default cache timeout.
        """
        return self.cache.set(key, value, timeout=timeout)  # type: ignore[return-value]

    def delete(self, key: Any):
        """
        Delete a value from the cache.
        """
        return self.cache.delete(key)  # type: ignore[return-value]

    def incr(self, key: Any, delta: int = 1):
        """
        Increment a value in the cache.
        """
        return self.cache.incr(key, delta)  # type: ignore[return-value]

    def decr(self, key: Any, delta: int = 1):
        """
        Decrement a value in the cache.
        """
        return self.cache.decr(key, delta)  # type: ignore[return-value]

    def clear(self):
        """
        Clear the entire cache.
        """
        return self.cache.clear()  # type: ignore[return-value]

    def add(self, key: Any, value: Any, timeout: Optional[float] = None, version: Optional[int] = None):
        """
        Add a value to the cache if the key does not already exist.
        """
        return self.cache.add(key, value, timeout=timeout)  # type: ignore[return-value]

    def touch(self, key: Any, timeout: Optional[float] = None, version: Optional[int] = None):
        """
        Update the timeout for a given key in the cache.
        """
        return self.cache.touch(key, timeout=timeout)  # type: ignore[return-value]

    def has_key(self, key: Any, version: Optional[int] = None) -> bool:
        """
        Check if a key exists in the cache.
        """
        return self.cache.has_key(key)  # type: ignore[return-value]

    def get_many(self, keys: list, version: Optional[int] = None) -> dict:
        """
        Fetch multiple keys from the cache.
        """
        return self.cache.get_many(keys)  # type: ignore[return-value]

    def set_many(self, data: dict, timeout: Optional[float] = None, version: Optional[int] = None):
        """
        Set multiple values in the cache.
        """
        return self.cache.set_many(data, timeout=timeout)  # type: ignore[return-value]

    def delete_many(self, keys: list, version: Optional[int] = None):
        """
        Delete multiple keys from the cache.
        """
        return self.cache.delete_many(keys)  # type: ignore[return-value]

    def incr_version(self, key: Any, delta: int = 1, version: Optional[int] = None):
        """
        Increment the version of a key in the cache.
        """
        return self.cache.incr_version(key, delta)  # type: ignore[return-value]

    def decr_version(self, key: Any, delta: int = 1, version: Optional[int] = None):
        """
        Decrement the version of a key in the cache.
        """
        return self.cache.decr_version(key, delta)  # type: ignore[return-value]

    def close(self, **kwargs):
        """
        Close the cache connection.
        """
        return self.cache.close(**kwargs)  # type: ignore[return-value]


lazy_cache = LazyCache()
"""
A singleton instance of LazyCache for accessing Django's cache framework
without risking premature initialization, which can lead to issues
where Django falls back to a default cache backend unexpectedly.
When this happens, the fallback cache may not persist data as expected,
leading to buggy cache misses such as browser session values not being stored.

.. code-block:: python

    # suggest importing like this, in order to clarify
    # that you're importing lazy_cache, which has an api
    # that is identical to that of django.core.cache
    from smarter.lib.cache import lazy_cache as cache

    cache.set("my_key", "my_value", timeout=300)
    value = cache.get("my_key")
    print(value)  # Outputs: "my_value"
"""


def cache_results(timeout=SMARTER_DEFAULT_CACHE_TIMEOUT, logging_enabled=True):
    """
    A decorator that caches the result of a function based on the arguments
    passed to it. When
    the decorated function is called, the decorator first checks if a cached
    result exists for the given arguments. If a cached result is found, it is
    returned immediately. If not, the original function is called, its result
    is cached, and then returned. Smarter's cache infrastructure is based on
    Redis and runs as a remote service that services application restarts,
    deployments, and, it natively services multiple application server instances.

    .. note::

        *One of the challenges with implementing a caching decorator based on Django cache
        regards working around Django's application startup sequence.
        Decorators are imported and applied at module load time,
        which often results in Django's cache
        framework being prematurely imported and initialized while Django itself is still
        running its own application startup process.*

        *This often leads to situations where Django falls back to an
        alternative 'default' memory-based cache backend unexpectedly
        (and silently). When this happens, the fallback cache most likely
        will not persist data as expected, leading to buggy cache misses
        such as users' browser session values not being stored, and cached
        results of this decorator enduring less than specified.*

    **How It works:**

    A cache key is created by building a string of the module name + the function name,
    and then appending a 32-character hash of its serialized positional arguments and sorted keyword pairs.
    This ensures that each unique set of arguments maps to a unique but repeatable cache key.
    Technically speaking, there is a statistical non-zero probability of hash collisions, but,
    the risk of this happening is *EXTREMELY* low.

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

        @cache_results(timeout=600)
        def expensive_function(x, y, *args, **kwargs):
            # Perform expensive computation ...
            result = "some very expensive computational result"
            return result

    The decorator also adds an ``invalidate`` method to the wrapped function, which can be used to
    manually remove the cached result for specific arguments::

        expensive_function.invalidate(1, 2)
    """

    def decorator(func: Callable) -> Callable:

        def generate_sorted_kwargs(kwargs: dict) -> tuple:
            """
            Sorts the keyword arguments for consistent generation of sha256 cache key,
            which is created, in part, on the results of this function.


            :param kwargs: The keyword arguments to sort.
            :return: A tuple of sorted keyword argument items.
            :rtype: tuple

            """
            return tuple(sorted(kwargs.items()))

        def generate_key_data(func: Callable, args: tuple, kwargs: dict) -> Optional[bytes]:
            """
            Generates a raw cache key based on the function name, arguments,
            and sorted keyword arguments.

            :param func: The function for which to generate the key.
            :param args: The positional arguments passed to the function.
            :param kwargs: The keyword arguments passed to the function.
            :return: The raw key data as bytes.
            :rtype: Optional[bytes]
            """
            sorted_kwargs = generate_sorted_kwargs(kwargs)
            try:
                key_data = pickle.dumps((func.__name__, args, sorted_kwargs))
            except pickle.PickleError as e:
                logger.error("%s Failed to pickle key data: %s", logger_prefix, e)
                return None

            return key_data

        def generate_cache_key(func: Callable, key_data: bytes) -> str:
            """
            Generates a deterministic cache key str based on
            the module name, function name and a 32-character hash of
            the complete set of key data.

            Example::

                'smarter.apps.account.utils._get_account_for_user_by_id()_cc3ce8b352a65ac8018943debd10ec9c'

            :param func: The function for which to generate the key.
            :param key_data: The raw key data as bytes.
            :return: The generated cache key as a string.
            :rtype: str
            """
            return f"{func.__module__}.{func.__name__}()_" + hashlib.sha256(key_data).hexdigest()[:32]

        # pylint: disable=unused-variable
        def unpickle_key_data(key_data: bytes) -> Optional[tuple]:
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
            Caches the result of the decorated function based on its arguments.

            This function is the core of the :func:`cache_results` decorator. When you decorate a function with
            :func:`cache_results`, calls to that function are intercepted by this wrapper, which manages
            caching transparently. The wrapper first attempts to retrieve a cached result using a key
            derived from the function's name and arguments. If a cached value is found, it is returned
            immediately, avoiding redundant computation. If not, the original function is called, its result
            is cached, and then returned.

            **How it works:**

            1. **Cache Key Generation:**
                The wrapper serializes the function's name, positional arguments, and sorted keyword arguments
                to create a unique and repeatable cache key. This ensures that each unique set of arguments,
                including combinations and permutations of keyword arguments, maps to a unique cache entry.

            2. **Cache Lookup:**
                The wrapper checks if a result for this key is already stored in the cache. If so, it returns
                the cached value. This is called a *cache hit*.

            3. **Cache Miss Handling:**
                If no cached value is found (a *cache miss*), the original function is called with the provided
                arguments. The result is then stored in the cache for future calls.

            4. **Handling None Results:**
                If the function returns ``None``, a special sentinel value is cached to distinguish between a
                cached ``None`` and a true cache miss.

            5. **Logging (Optional):**
                If logging is enabled, the wrapper logs cache hits, misses, and cache invalidations for
                debugging and transparency.

            **Decorator Usage Example:**

            .. code-block:: python

                    @cache_results(timeout=60)
                    def expensive_function(x, y):
                        # Perform expensive computation
                        return x + y

                    # First call: result is computed and cached
                    result1 = expensive_function(1, 2)

                    # Second call with same arguments: result is returned from cache
                    result2 = expensive_function(1, 2)

            **Why use this pattern?**

            - *Performance*: Avoids repeating expensive computations for the same inputs.
            - *Transparency*: The original function's interface is preserved; users call it as usual.
            - *Extensibility*: The decorator adds an ``invalidate`` method to the wrapped function, allowing
                manual cache clearing for specific arguments.

            :param args: Positional arguments passed to the decorated function.
            :type args: tuple
            :param kwargs: Keyword arguments passed to the decorated function.
            :type kwargs: dict
            :return: The result of the decorated function, either from cache or freshly computed.
            :rtype: Any
            """
            key_data: Optional[bytes] = generate_key_data(func, args, kwargs)
            # If key_data is None, we cannot generate a cache key, so we call the function directly
            # and return the result without caching.
            # This is a fallback to avoid breaking the application in case of pickling errors.
            if key_data is None:
                logger.error("%s Failed to generate cache key data for %s", logger_prefix, func.__name__)
                return func(*args, **kwargs)
            cache_key = generate_cache_key(func, key_data)
            # unpickled_cache_key = unpickle_key_data(key_data)

            # look for a cached result ...
            cached_result = lazy_cache.get(cache_key, CACHE_MISS_SENTINEL)
            if cached_result is not CACHE_MISS_SENTINEL:
                # cache hit, hooray!
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
                # Cache miss, boo! Call the function ...
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
            key_data: Optional[bytes] = generate_key_data(func, args, kwargs)
            if key_data is None:
                return
            cache_key: str = generate_cache_key(func, key_data)
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
    .. deprecated:: v0.10.0

        Use lib.django.view_helpers or another caching decorator instead.
        This decorator will be removed in a future release.

    Caches the result of a function based on the request URI and user identifier.
    Associates a Smarter user account number with the cache key if the user is authenticated.
    """

    def decorator(func):

        @wraps(func)
        def wrapper(request: HttpRequest, *args, **kwargs):
            if request is None or not isinstance(request, HttpRequest):
                logger.error(
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
