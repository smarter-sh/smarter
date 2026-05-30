"""
smarter.lib.cache.cache_results
===============================

This module provides the ``@cache_results`` decorator and related utilities
for persistent, argument-based function result caching in the Smarter framework.

**Key Features:**

- Deterministic cache key generation based on function name, arguments, and
  sorted keyword arguments.
- Persistent caching using Smarter's Redis-backed cache infrastructure
  (via ``lazy_cache``), supporting application restarts and multi-instance deployments.
- Handles serialization of arguments for robust cache key creation, with
  fallback for non-serializable data.
- Special handling for functions returning ``None`` using a sentinel value to distinguish
  between cached ``None`` and cache misses.
- Optional logging for cache hits, misses, and invalidations for debugging and transparency.
- Provides an ``invalidate`` method on decorated functions to manually clear cache entries
  for specific arguments.

**Usage Example:**

.. code-block:: python

    from smarter.lib.cache.cache_results import cache_results

    @cache_results(timeout=600)
    def expensive_function(x, y, *args, **kwargs):
        # Perform expensive computation ...
        return x + y

    # Invalidate cache for specific arguments
    expensive_function.invalidate(1, 2)

**Notes:**

- This decorator is intended for expensive, long-lived, persistable caching scenarios
  (e.g., database reads), not for short-lived in-memory caching.
- The cache key generation is robust but not immune to hash collisions
  (statistically extremely rare).
- See the ``cache_results`` decorator docstring for more details on behavior
  and limitations.
"""

import hashlib
from functools import lru_cache, wraps
from typing import Callable, Optional, Union

from smarter.common.conf import smarter_settings
from smarter.lib import json, logging

from .cache_sentinel import CACHE_MISS_SENTINEL, CACHE_NONE_SENTINEL
from .lazy_cache import lazy_cache

logger = logging.getLogger(__name__)
logger_prefix_normal = logging.formatted_text(f"{__name__}.@cache_results()")
logger_prefix_green = logging.formatted_text_green(f"{__name__}.@cache_results()")
logger_prefix_red = logging.formatted_text_red(f"{__name__}.@cache_results()")
logger_prefix_blue = logging.formatted_text_blue(f"{__name__}.@cache_results()")

LRU_CACHE_MAXSIZE = 128
KwargsTupleType = tuple[tuple[str, object], ...]


@lru_cache(maxsize=LRU_CACHE_MAXSIZE)
def _generate_sorted_kwargs_cached(sorted_items: KwargsTupleType) -> KwargsTupleType:
    """
    Returns a tuple of sorted keyword argument items.

    This function is a helper used to ensure that keyword arguments are consistently
    ordered for cache key generation. It is decorated with `functools.lru_cache` to
    optimize repeated calls with the same input, improving performance when generating
    cache keys for functions with identical keyword arguments.

    :param sorted_items: A tuple of keyword argument items (key-value pairs), already sorted.
    :type sorted_items: tuple
    :return: A tuple of sorted keyword argument items.
    :rtype: tuple
    """
    return tuple(sorted(sorted_items))


def _generate_sorted_kwargs(kwargs: dict[str, object]) -> KwargsTupleType:
    """
    Sorts the keyword arguments for consistent generation of sha256 cache key,
    which is created, in part, on the results of this function.


    :param kwargs: The keyword arguments to sort.
    :return: A tuple of sorted keyword argument items.
    :rtype: KwargsTupleType
    """

    def _make_hashable(obj):
        if isinstance(obj, dict):
            return tuple(sorted((k, _make_hashable(v)) for k, v in obj.items()))
        elif isinstance(obj, (list, tuple)):
            return tuple(_make_hashable(x) for x in obj)
        elif isinstance(obj, set):
            return tuple(sorted(_make_hashable(x) for x in obj))
        else:
            return obj

    hashable_items = tuple(sorted((k, _make_hashable(v)) for k, v in kwargs.items()))
    return _generate_sorted_kwargs_cached(hashable_items)


@lru_cache(maxsize=LRU_CACHE_MAXSIZE)
def _json_cache_key_cached(key_tuple: tuple[KwargsTupleType, ...]) -> Union[bytes, None]:
    """
    Serializes the key data to JSON and encodes it as bytes for hashing.

    This function takes a tuple representing cache key data, serializes it to a JSON string
    with sorted keys and compact separators, and encodes the result as UTF-8 bytes.
    This byte representation is suitable for deterministic hashing (e.g., with SHA-256)
    to generate cache keys. If serialization fails due to non-serializable data,
    the function logs an error and returns ``None``.

    :param key_tuple: The tuple containing key data to serialize (typically function name, args, kwargs).
    :type key_tuple: tuple
    :return: The JSON-encoded bytes representation of the key data, or ``None`` if serialization fails.
    :rtype: Optional[bytes]
    """
    try:
        return json.dumps(key_tuple, sort_keys=True, separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError) as e:
        logger.error("%s Failed to JSON serialize key data: %s", logger_prefix_normal, e)
        return None


def _generate_key_data(func: Callable, args: tuple[object, ...], kwargs: dict[str, object]) -> Optional[bytes]:
    """
    Generates a raw cache key based on the function name, arguments,
    and sorted keyword arguments.

    :param func: The function for which to generate the key.
    :param args: The positional arguments passed to the function.
    :param kwargs: The keyword arguments passed to the function.
    :return: The raw key data as bytes.
    :rtype: Optional[bytes]
    """

    sorted_kwargs = _generate_sorted_kwargs(kwargs)
    key_tuple = (func.__name__, args, sorted_kwargs)
    return _json_cache_key_cached(key_tuple)


@lru_cache(maxsize=LRU_CACHE_MAXSIZE)
def _generate_cache_key_cached(func: Callable, key_data: bytes) -> str:
    """
    Generates a deterministic cache key str based on
    the module name, function name and a 32-character hash of
    the complete set of key data.

    :param func: The function for which to generate the key.
    :param key_data: The raw key data as bytes.
    :return: The generated cache key as a string.
    :rtype: str
    """
    return f"{func.__module__}.{func.__name__}()_" + hashlib.sha256(key_data).hexdigest()[:32]


def cache_results(timeout=smarter_settings.cache_expiration, cache_key: Optional[str] = None, logging_enabled=False):
    """
    A decorator that caches the result of a function based on the arguments
    passed to it.

    .. important::

        This decorator is intended for expensive and long-lasting, persistable
        caching scenarios such as Django ORM reads, where the results of the
        decorated function should endure application restarts and deployments.
        This caching decorator itself is using Python function caching in order
        to generate cache keys, which is to say that using this decorator could
        be counter-productive for caching scenarios that are better served by
        in-memory caching of short-lived results.

    When the decorated function is called, the decorator first checks if a cached
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

    :param timeout: The cache timeout in seconds. Defaults to ``smarter_settings.cache_expiration``.
    :type timeout: int
    :param cache_key: An optional pre-computed cache key to use instead of generating one from the function arguments.
    :type cache_key: Optional[str]
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

        expensive_function.invalidate(1, 2)  # Invalidate cache for specific arguments

    """

    def decorator(func: Callable) -> Callable:

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
            if cache_key:
                computed_cache_key = cache_key
            else:
                key_data: Optional[bytes] = _generate_key_data(func, args, kwargs)
                # If key_data is None, we cannot generate a cache key, so we call the function directly
                # and return the result without caching.
                # This is a fallback to avoid breaking the application in case of pickling errors.
                if key_data is None:
                    logger.error("%s Failed to generate cache key data for %s", logger_prefix_normal, func.__name__)
                    return func(*args, **kwargs)
                computed_cache_key = _generate_cache_key_cached(func, key_data)

            # look for a cached result ...
            cached_result = lazy_cache.get(computed_cache_key, CACHE_MISS_SENTINEL)
            if cached_result is not CACHE_MISS_SENTINEL:
                # cache hit, hooray!
                result = (
                    None if isinstance(cached_result, str) and cached_result == CACHE_NONE_SENTINEL else cached_result
                )
                if logging_enabled or lazy_cache.verbose_logging:
                    class_name = kwargs.get("class_name", "")
                    class_name = f"{class_name} - " if class_name else ""
                    logger.info(
                        "%s cache hit for %s%s: %s args: %s kwargs: %s",
                        logger_prefix_green,
                        class_name,
                        computed_cache_key,
                        "None" if result is None else result,
                        args,
                        kwargs,
                    )
                elif logging_enabled or lazy_cache.cache_logging:
                    class_name = kwargs.get("class_name", "")
                    class_name = f"{class_name} - " if class_name else ""
                    logger.info(
                        "%s cache hit for %s: %s args: %s kwargs: %s",
                        logger_prefix_green,
                        class_name,
                        computed_cache_key,
                        args,
                        kwargs,
                    )
            else:
                # Cache miss, boo! Call the function ...
                result = func(*args, **kwargs)
                cache_value = CACHE_NONE_SENTINEL if result is None else result
                lazy_cache.set(computed_cache_key, cache_value, timeout)
                if logging_enabled or lazy_cache.verbose_logging:
                    logger.info(
                        "%s caching %s - %s, with timeout %s args: %s kwargs: %s for %s",
                        logger_prefix_red,
                        type(cache_value).__name__,
                        computed_cache_key,
                        timeout,
                        args,
                        kwargs,
                        cache_value,
                    )
            return result

        def invalidate(*args, **kwargs):
            """
            Invalidates the cached result for the given arguments.
            This method can be called on the decorated function to manually clear
            the cache for specific input parameters.

            Example usage::

                .. code-block:: python

                    @cache_results(timeout=60)
                    def expensive_function(x, y):
                        # Perform expensive computation
                        return x + y

                    # Invalidate cache for specific arguments
                    expensive_function.invalidate(1, 2)

            :param args: Positional arguments for which to invalidate the cache.
            :type args: tuple
            :param kwargs: Keyword arguments for which to invalidate the cache.
            :type kwargs: dict
            """
            cache_key = kwargs.pop("cache_key", None)
            logger.debug(
                "%s -> %s called with args: %s kwargs: %s",
                logger_prefix_blue,
                logging.formatted_text_blue(func.__name__ + "().invalidate()"),
                args,
                kwargs,
            )
            if cache_key:
                computed_cache_key = cache_key
            else:
                key_data: Optional[bytes] = _generate_key_data(func, args, kwargs)
                if key_data is None:
                    return
                computed_cache_key: str = _generate_cache_key_cached(func, key_data)
            if lazy_cache.has_key(computed_cache_key):
                cached_value = lazy_cache.get(computed_cache_key)
                lazy_cache.delete(computed_cache_key)
                logger.info(
                    "%s - invalidated %s - %s",
                    logger_prefix_green + logging.formatted_text_green(func.__name__ + "().invalidate()"),
                    type(cached_value).__name__,
                    computed_cache_key,
                )
            else:
                logger.debug(
                    "%s - no cache entry found for %s (nothing to invalidate)",
                    logger_prefix_red + logging.formatted_text_red(func.__name__ + "().invalidate()"),
                    computed_cache_key,
                )

        wrapper.invalidate = invalidate  # type: ignore[attr-defined]
        return wrapper

    return decorator


__all__ = ["cache_results"]
