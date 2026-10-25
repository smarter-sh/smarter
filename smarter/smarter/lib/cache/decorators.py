"""
Smarter.lib.cache.cache_results
===============================

This module provides the ``@cache_results`` decorator and related utilities
for persistent, argument-based function result caching in the Smarter framework.

**Key Features:**

- Deterministic cache key generation based on the function's module, qualified
  name, and arguments bound to its signature.
- Persistent caching using Smarter's Redis-backed cache infrastructure
  (via ``lazy_cache``), supporting application restarts and multi-instance deployments.
- Handles serialization of arguments for robust cache key creation, with
  fallback to an uncached call for arguments that can't be serialized.
- Special handling for functions returning ``None`` using a sentinel value to distinguish
  between cached ``None`` and cache misses.
- Decorates both regular and ``async`` functions, and classmethods.
- Within one process, concurrent callers that miss the same key wait for the
  first one to compute it, rather than all computing it.
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
import inspect
import threading
import weakref
from functools import wraps
from typing import Callable, Optional

from asgiref.sync import sync_to_async

from smarter.common.conf import smarter_settings
from smarter.common.helpers.console_helpers import SmarterFormattedTextColorCodes
from smarter.lib import json, logging

from .cache_sentinel import CACHE_MISS_SENTINEL, CACHE_NONE_SENTINEL
from .lazy_cache import lazy_cache

logger = logging.getLogger(__name__)
logger_prefix_normal = f"{logging.formatted_text(__name__)}.@cache_results()"
logger_prefix_green = logging.formatted_text(
    f"{__name__}.@cache_results()", SmarterFormattedTextColorCodes.REGULAR_GREEN
)
logger_prefix_red = logging.formatted_text(f"{__name__}.@cache_results()", SmarterFormattedTextColorCodes.DARK_RED)
logger_prefix_gray = logging.formatted_text(f"{__name__}.@cache_results()", SmarterFormattedTextColorCodes.LIGHT_GRAY)

# One lock per cache key that is being computed right now. Entries disappear once
# no thread holds or waits on their lock, so the dict stays small.
_key_locks: "weakref.WeakValueDictionary[str, threading.RLock]" = weakref.WeakValueDictionary()
_key_locks_guard = threading.Lock()


def _lock_for(computed_cache_key: str):
    """
    Return the lock that serializes computing one cache key in this process.

    The lock is reentrant, so a decorated function that ends up calling itself
    with the same arguments recurses as it would without the decorator, rather
    than deadlock.

    :param computed_cache_key: The cache key being computed.
    :type computed_cache_key: str
    :return: The lock for that key.
    :rtype: threading.RLock
    """
    with _key_locks_guard:
        lock = _key_locks.get(computed_cache_key)
        if lock is None:
            lock = threading.RLock()
            _key_locks[computed_cache_key] = lock
        return lock


def _normalize(obj: object, context: str = "") -> object:
    """
    Convert an argument into a JSON-serializable value that is the same for equal arguments.

    Dicts and lists are kept as JSON objects and arrays, so that ``{"a": 1}``
    and ``[("a", 1)]`` don't share a key. Sets are sorted, because their
    iteration order changes from one process to the next, and are tagged so
    that they don't share a key with a list. A class, e.g. the ``cls`` of a
    classmethod, is identified by its module and qualified name.

    :param obj: An argument of the decorated function.
    :type obj: object
    :param context: The decorated function's qualified name, named in
        :func:`smarter.lib.json.dumps_cache_key`'s fallback warning.
    :type context: str
    :return: The normalized value.
    :rtype: object
    """
    if isinstance(obj, dict):
        return {key: _normalize(value, context) for key, value in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_normalize(item, context) for item in obj]
    if isinstance(obj, (set, frozenset)):
        items = [_normalize(item, context) for item in obj]
        return {"__set__": sorted(items, key=lambda item: json.dumps_cache_key(item, context=context))}
    if isinstance(obj, type):
        return {"__class__": f"{obj.__module__}.{obj.__qualname__}"}
    return obj


def _generate_key_data(func: Callable, args: tuple[object, ...], kwargs: dict[str, object]) -> Optional[bytes]:
    """
    Serialize the function's qualified name and its bound arguments into bytes for hashing.

    The arguments are bound to the function's signature, so that ``f(1, b=2)``,
    ``f(a=1, b=2)`` and ``f(1)`` (when ``b`` defaults to 2) produce the same
    key. Otherwise a function and its ``invalidate()`` could silently compute
    different keys depending on how each was called.

    :param func: The function for which to generate the key.
    :param args: The positional arguments passed to the function.
    :param kwargs: The keyword arguments passed to the function.
    :return: The key data as bytes, or ``None`` if the arguments can't be serialized.
    :rtype: Optional[bytes]
    """
    try:
        bound = inspect.signature(func).bind(*args, **kwargs)
        bound.apply_defaults()
        args, kwargs = (), dict(bound.arguments)
    except (TypeError, ValueError):
        pass
    try:
        context = func.__qualname__
        key_data = [context, _normalize(args, context), _normalize(kwargs, context)]
        return json.dumps_cache_key(key_data, context=context).encode("utf-8")
    except (TypeError, ValueError, RecursionError) as e:
        logger.error("%s Failed to JSON serialize key data for %s: %s", logger_prefix_normal, func.__qualname__, e)
        return None


def _generate_cache_key(func: Callable, key_data: bytes) -> str:
    """
    Generate a deterministic cache key from the module name, qualified function name and a 32-character hash of the key data.

    :param func: The function for which to generate the key.
    :param key_data: The raw key data as bytes.
    :return: The generated cache key as a string.
    :rtype: str
    """
    return f"{func.__module__}.{func.__qualname__}()_" + hashlib.sha256(key_data).hexdigest()[:32]


def _reject_instance_methods(func: Callable) -> None:
    """
    Refuse to decorate an instance method.

    ``self`` would be part of the cache key, and an instance is serialized as
    ``str(self)``, so two different objects with the same string, e.g. two
    model rows with the same name, would share one cache entry. A classmethod's
    ``cls`` is fine: it is identified by its module and qualified name.

    :param func: The function being decorated.
    :type func: Callable
    :raises TypeError: If the function's first parameter is ``self``.
    """
    try:
        parameters = list(inspect.signature(func).parameters)
    except (TypeError, ValueError):
        return
    if parameters and parameters[0] == "self":
        raise TypeError(
            f"@cache_results can't decorate the instance method {func.__qualname__}(), because self would be "
            "part of its cache key. Decorate a function of plain values (ids, names, flags) instead."
        )


def cache_results(timeout=smarter_settings.cache_expiration, cache_key: Optional[str] = None, logging_enabled=False):
    """
    A decorator that caches the result of a function based on the arguments passed to it.

    .. important::

        This decorator is intended for expensive and long-lasting, persistable
        caching scenarios such as Django ORM reads, where the results of the
        decorated function should endure application restarts and deployments.
        Every call serializes and hashes its arguments, and makes a round trip
        to Redis, so this decorator could be counter-productive for caching
        scenarios that are better served by in-memory caching of short-lived results.

    When the decorated function is called, the decorator first checks if a cached
    result exists for the given arguments. If a cached result is found, it is
    returned immediately. If not, the original function is called, its result
    is cached, and then returned. Smarter's cache infrastructure is based on
    Redis and runs as a remote service that survives application restarts and
    deployments, and that natively serves multiple application server instances.

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

        *For this reason, a decorated function that is called before Django's
        apps are ready runs uncached.*

    **How It works:**

    A cache key is created by building a string of the module name + the
    function's qualified name (e.g. ``LLMClient.get_for_user.<locals>._get``),
    and then appending a 32-character hash of its arguments, bound to its
    signature and serialized. This ensures that each unique set of arguments
    maps to a unique but repeatable cache key. Technically speaking, there is
    a statistical non-zero probability of hash collisions, but, the risk of
    this happening is *EXTREMELY* low.

    Arguments that can't be serialized are not cached: the function is called
    directly, and an error is logged. Arguments should be plain values (str,
    int, bool, tuples). Keys are serialized by
    :func:`smarter.lib.json.dumps_cache_key`, which encodes datetimes, Decimals
    and UUIDs, but serializes any other object as ``str(obj)`` and logs a
    warning that names the function and the argument's type. For the same
    reason, instance methods can't be decorated. Classmethods can.

    Within one process, concurrent callers that miss the same key wait for the
    first one to compute and cache it. Callers in other processes don't wait.
    ``async`` functions are cached too, without this wait.

    :param timeout: The cache timeout in seconds. Defaults to ``smarter_settings.cache_expiration``.
    :type timeout: int
    :param cache_key: An optional pre-computed cache key to use instead of
        generating one from the function arguments. This marginally increases
        performance by skipping the cache key generation step, but should only
        be used if you are certain that the provided cache key is unique and
        correctly represents the function arguments. Defaults to ``None``.
    :type cache_key: Optional[str]
    :param logging_enabled: Whether to log cache hits, misses and
        invalidations, as when the ``CACHE_LOGGING`` waffle switch is on.
        Results are never logged, only their type. Defaults to ``False``.
    :type logging_enabled: bool
    :return: The decorated function with caching applied.
    :rtype: Callable
    :raises TypeError: If the decorated function is an instance method.

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
        _reject_instance_methods(func)
        qualname = func.__qualname__

        def compute_cache_key(args: tuple, kwargs: dict) -> Optional[str]:
            """Return the cache key for these arguments, or None when they can't be cached."""
            if cache_key:
                return cache_key
            key_data = _generate_key_data(func, args, kwargs)
            if key_data is None:
                return None
            return _generate_cache_key(func, key_data)

        def log_enabled() -> bool:
            return logging_enabled or lazy_cache.cache_logging

        def lookup(computed_cache_key: str, args: tuple, kwargs: dict) -> tuple[bool, object]:
            """Return (True, result) on a cache hit, and (False, None) on a miss."""
            cached_result = lazy_cache.get(computed_cache_key, CACHE_MISS_SENTINEL)
            if cached_result is CACHE_MISS_SENTINEL:
                return False, None
            # cache hit, hooray!
            result = None if isinstance(cached_result, str) and cached_result == CACHE_NONE_SENTINEL else cached_result
            if log_enabled():
                if lazy_cache.verbose_logging:
                    logger.info(
                        "%s cache hit for %s: %s (%s) args: %s kwargs: %s",
                        logger_prefix_green,
                        qualname,
                        computed_cache_key,
                        type(result).__name__,
                        args,
                        kwargs,
                    )
                else:
                    logger.info(
                        "%s cache hit for %s: %s (%s)",
                        logger_prefix_green,
                        qualname,
                        computed_cache_key,
                        type(result).__name__,
                    )
            return True, result

        def store(computed_cache_key: str, result: object, args: tuple, kwargs: dict) -> None:
            """Cache a freshly computed result."""
            cache_value = CACHE_NONE_SENTINEL if result is None else result
            lazy_cache.set(computed_cache_key, cache_value, timeout)
            if log_enabled():
                if lazy_cache.verbose_logging:
                    logger.info(
                        "%s caching %s for %s: %s, with timeout %s args: %s kwargs: %s",
                        logger_prefix_red,
                        type(result).__name__,
                        qualname,
                        computed_cache_key,
                        timeout,
                        args,
                        kwargs,
                    )
                else:
                    logger.info(
                        "%s caching %s for %s: %s, with timeout %s",
                        logger_prefix_red,
                        type(result).__name__,
                        qualname,
                        computed_cache_key,
                        timeout,
                    )

        def cache_not_ready() -> bool:
            """Whether the cache can't be used yet, so that this call must skip it."""
            if not lazy_cache.ready:
                logger.debug(
                    "%s %s() called before Django's apps are ready. Calling it uncached.",
                    logger_prefix_normal,
                    qualname,
                )
                return True
            return False

        if inspect.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                """
                Caches the result of the decorated ``async`` function based on its arguments.

                See :func:`cache_results`. The cache is read and written in a
                worker thread, so that the event loop doesn't block on Redis.

                :param args: Positional arguments passed to the decorated function.
                :type args: tuple
                :param kwargs: Keyword arguments passed to the decorated function.
                :type kwargs: dict
                :return: The result of the decorated function, either from cache or freshly computed.
                :rtype: Any
                """
                computed_cache_key = compute_cache_key(args, kwargs)
                # a None key means the arguments couldn't be serialized. _generate_key_data() logged why.
                if computed_cache_key is None or cache_not_ready():
                    return await func(*args, **kwargs)
                hit, result = await sync_to_async(lookup)(computed_cache_key, args, kwargs)
                if hit:
                    return result
                result = await func(*args, **kwargs)
                await sync_to_async(store)(computed_cache_key, result, args, kwargs)
                return result

            wrapper = async_wrapper
        else:

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                """
                Caches the result of the decorated function based on its arguments.

                This function is the core of the :func:`cache_results` decorator. When you decorate a function with
                :func:`cache_results`, calls to that function are intercepted by this wrapper, which manages
                caching transparently.

                **How it works:**

                1. **Cache Key Generation:**
                    The wrapper binds the arguments to the function's signature and serializes them, with the
                    function's qualified name, to create a unique and repeatable cache key.

                2. **Cache Lookup:**
                    The wrapper checks if a result for this key is already stored in the cache. If so, it returns
                    the cached value. This is called a *cache hit*.

                3. **Cache Miss Handling:**
                    If no cached value is found (a *cache miss*), the wrapper takes this process's lock for the
                    key, checks the cache again in case another thread just filled it, and otherwise calls the
                    original function and stores its result.

                4. **Handling None Results:**
                    If the function returns ``None``, a special sentinel value is cached to distinguish between a
                    cached ``None`` and a true cache miss.

                5. **Logging (Optional):**
                    If logging is enabled, the wrapper logs cache hits and misses, with the type of the result
                    but never the result itself.

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

                :param args: Positional arguments passed to the decorated function.
                :type args: tuple
                :param kwargs: Keyword arguments passed to the decorated function.
                :type kwargs: dict
                :return: The result of the decorated function, either from cache or freshly computed.
                :rtype: Any
                """
                computed_cache_key = compute_cache_key(args, kwargs)
                # a None key means the arguments couldn't be serialized. _generate_key_data() logged why.
                if computed_cache_key is None or cache_not_ready():
                    return func(*args, **kwargs)
                hit, result = lookup(computed_cache_key, args, kwargs)
                if hit:
                    return result
                # Cache miss, boo! Compute it once, while other threads that miss the same key wait.
                with _lock_for(computed_cache_key):
                    hit, result = lookup(computed_cache_key, args, kwargs)
                    if hit:
                        return result
                    result = func(*args, **kwargs)
                    store(computed_cache_key, result, args, kwargs)
                    return result

            wrapper = sync_wrapper

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
            # the decorator's own cache_key, unless the caller passes one. (Assigning to
            # cache_key here would shadow the decorator's, so that it could never be invalidated.)
            explicit_cache_key = kwargs.pop("cache_key", None) or cache_key
            invalidate_prefix = (
                logger_prefix_gray
                + "."
                + logging.formatted_text(qualname + "().invalidate()", SmarterFormattedTextColorCodes.LIGHT_GRAY)
            )
            logger.debug("%s called with args: %s kwargs: %s", invalidate_prefix, args, kwargs)
            if not lazy_cache.ready:
                # nothing can have been cached yet.
                return
            if explicit_cache_key:
                computed_cache_key = explicit_cache_key
            else:
                key_data: Optional[bytes] = _generate_key_data(func, args, kwargs)
                if key_data is None:
                    return
                computed_cache_key = _generate_cache_key(func, key_data)
            # one read, rather than has_key() and then get(): an entry that expires, or is evicted,
            # between the two would be reported as an invalidated None.
            cached_value = lazy_cache.get(computed_cache_key, CACHE_MISS_SENTINEL)
            if cached_value is not CACHE_MISS_SENTINEL:
                lazy_cache.delete(computed_cache_key)
                # like cache hits, invalidations are logged only when cache logging is on: applying one
                # manifest invalidates a dozen keys.
                log = logger.info if log_enabled() else logger.debug
                log(
                    "%s invalidated %s - %s",
                    invalidate_prefix,
                    (
                        "None"
                        if isinstance(cached_value, str) and cached_value == CACHE_NONE_SENTINEL
                        else type(cached_value).__name__
                    ),
                    computed_cache_key,
                )
            else:
                logger.debug(
                    "%s no cache entry found for %s (nothing to invalidate)", invalidate_prefix, computed_cache_key
                )

        wrapper.invalidate = invalidate  # type: ignore[attr-defined]
        return wrapper

    return decorator


__all__ = ["cache_results"]
