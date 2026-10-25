"""
Smarter.lib.cache.decorators
============================

This module provides the ``@cache_results`` decorator, for persistent,
argument-based caching of function results in Django's cache framework.

**Key Features:**

- Deterministic cache keys built from the function's module, qualified name,
  and arguments bound to its signature (see :mod:`smarter.lib.cache.keys`).
- Persistent caching in a Django cache, e.g. Redis, that survives application
  restarts and serves multi-instance deployments.
- Arguments that can't be part of a safe key, such as model instances, run the
  function uncached and log an error, rather than be cached under ``str()``.
- Special handling for functions returning ``None``, using a sentinel value to
  distinguish between a cached ``None`` and a cache miss.
- Decorates both regular and ``async`` functions, and classmethods.
- Within one process, concurrent callers that miss the same key wait for the
  first one to compute it, rather than all computing it.
- Optional logging for cache hits, misses, and invalidations.
- An ``invalidate`` method on decorated functions to clear the entry of
  specific arguments.
- Configured by the ``CACHE_RESULTS`` Django setting (see
  :mod:`smarter.lib.cache.conf`). Nothing in this module depends on the rest
  of Smarter.

**Usage Example:**

.. code-block:: python

    from smarter.lib.cache import cache_results

    @cache_results(timeout=600)
    def expensive_function(x, y, *args, **kwargs):
        # Perform expensive computation ...
        return x + y

    # Invalidate cache for specific arguments
    expensive_function.invalidate(1, 2)

**Notes:**

- This decorator is intended for expensive, long-lived, persistable caching scenarios
  (e.g., database reads), not for short-lived in-memory caching.
- See the ``cache_results`` decorator docstring for more details on behavior
  and limitations.
"""

import inspect
import logging
import threading
import weakref
from functools import wraps
from typing import Callable, Optional

from asgiref.sync import sync_to_async
from django.apps import apps

from .cache_sentinel import CACHE_MISS_SENTINEL, CACHE_NONE_SENTINEL
from .conf import cache_results_settings
from .keys import describe_key_error, make_key

logger = logging.getLogger(__name__)
LOGGER_PREFIX = f"{__name__}.@cache_results()"
"""The unformatted start of every log message.

``CACHE_RESULTS["LOG_PREFIX"]`` formats it.
"""

# One lock per cache key that is being computed right now. Entries disappear once
# no thread holds or waits on their lock, so the dict stays small.
_key_locks: "weakref.WeakValueDictionary[str, threading.RLock]" = weakref.WeakValueDictionary()
_key_locks_guard = threading.Lock()

# (qualified name, reason) pairs whose key failure has been logged as an error in this process.
_key_errors_logged: set[tuple[str, str]] = set()


def _prefix(event: str = "") -> str:
    """
    Return the formatted start of a log message.

    :param event: ``"hit"``, ``"miss"``, ``"invalidate"`` or ``""``.
    :type event: str
    :return: The prefix.
    :rtype: str
    """
    return cache_results_settings.log_prefix(LOGGER_PREFIX, event)


def cache_ready() -> bool:
    """
    Whether the cache can be used yet.

    Decorators run at import time, often while Django is still starting.
    Touching ``django.core.cache`` then can leave it on an unexpected backend,
    such as a local-memory cache that silently persists nothing. So a decorated
    function that is called before Django's apps are ready runs uncached.

    :return: True once Django's apps are ready, False before.
    :rtype: bool
    """
    return apps.ready


def get_cache():
    """
    Return the Django cache that holds cached results, from ``CACHE_RESULTS["CACHE_ALIAS"]``.

    Call it only once :func:`cache_ready` is True.

    :return: The cache.
    :rtype: django.core.cache.backends.base.BaseCache
    """
    from django.core.cache import caches  # pylint: disable=import-outside-toplevel

    return caches[cache_results_settings.cache_alias]


def _has_native_async(cache, method: str) -> bool:
    """
    Whether a cache backend implements an async method itself.

    Django's :class:`~django.core.cache.backends.base.BaseCache` implements
    ``aget()`` and ``aset()`` as ``sync_to_async(..., thread_sensitive=True)``,
    which queues every call behind all other synchronous work on one thread.

    :param cache: The cache.
    :param method: e.g. ``"aget"``.
    :type method: str
    :return: True if the backend overrides Django's default.
    :rtype: bool
    """
    from django.core.cache.backends.base import (  # pylint: disable=import-outside-toplevel
        BaseCache,
    )

    return getattr(type(cache), method, None) is not getattr(BaseCache, method)


async def _aget(key: str, default: object) -> object:
    """
    Read the cache from async code without blocking the event loop.

    Uses the backend's own ``aget()`` when it has one, and otherwise runs the
    synchronous ``get()`` in a worker thread.

    :param key: The cache key.
    :type key: str
    :param default: The value to return on a miss.
    :type default: object
    :return: The cached value, or ``default``.
    :rtype: object
    """
    cache = get_cache()
    if _has_native_async(cache, "aget"):
        return await cache.aget(key, default)
    return await sync_to_async(cache.get, thread_sensitive=False)(key, default)


async def _aset(key: str, value: object, timeout: Optional[float]) -> None:
    """
    Write the cache from async code without blocking the event loop.

    :param key: The cache key.
    :type key: str
    :param value: The value to cache.
    :type value: object
    :param timeout: The timeout in seconds.
    :type timeout: Optional[float]
    """
    cache = get_cache()
    if _has_native_async(cache, "aset"):
        await cache.aset(key, value, timeout)
        return
    await sync_to_async(cache.set, thread_sensitive=False)(key, value, timeout)


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


def _key_for(func: Callable, args: tuple, kwargs: dict, explicit_cache_key: Optional[str]) -> Optional[str]:
    """
    Return the cache key of one call, or ``None`` when its arguments can't be part of a key.

    The first failure for each function and reason is logged as an error, and
    later ones at debug level, so that a hot code path doesn't flood the log.
    Argument values are never logged, only their types.

    :param func: The decorated function.
    :type func: Callable
    :param args: The positional arguments.
    :type args: tuple
    :param kwargs: The keyword arguments.
    :type kwargs: dict
    :param explicit_cache_key: The decorator's or caller's fixed key, if any.
    :type explicit_cache_key: Optional[str]
    :return: The cache key, or ``None``.
    :rtype: Optional[str]
    """
    prefix = cache_results_settings.key_prefix
    if explicit_cache_key:
        return prefix + explicit_cache_key
    try:
        return make_key(func, args, kwargs, encoder=cache_results_settings.key_encoder, prefix=prefix)
    except (TypeError, ValueError, RecursionError) as e:
        reason = describe_key_error(e)
        log = logger.debug
        if (func.__qualname__, reason) not in _key_errors_logged:
            _key_errors_logged.add((func.__qualname__, reason))
            log = logger.error
        log("%s %s() runs uncached: %s", _prefix(), func.__qualname__, reason)
        return None


def _reject_instance_methods(func: Callable) -> None:
    """
    Refuse to decorate an instance method.

    ``self`` would be part of the cache key, and an instance can't be part of a
    safe key, so every call would run uncached. A classmethod's ``cls`` is
    fine: it is identified by its module and qualified name.

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


def cache_results(timeout: Optional[float] = None, cache_key: Optional[str] = None, logging_enabled: bool = False):
    """
    A decorator that caches the result of a function based on the arguments passed to it.

    .. important::

        This decorator is intended for expensive and long-lasting, persistable
        caching scenarios such as Django ORM reads, where the results of the
        decorated function should endure application restarts and deployments.
        Every call serializes and hashes its arguments, and makes a round trip
        to the cache, so this decorator could be counter-productive for caching
        scenarios that are better served by in-memory caching of short-lived results.

    When the decorated function is called, the decorator first checks if a cached
    result exists for the given arguments. If a cached result is found, it is
    returned immediately. If not, the original function is called, its result
    is cached, and then returned. Results are stored in the Django cache named
    by ``CACHE_RESULTS["CACHE_ALIAS"]`` (``"default"`` unless set), which in
    Smarter is Redis: a remote service that survives application restarts and
    deployments, and that natively serves multiple application server instances.

    .. note::

        *Decorators are imported and applied at module load time, which often
        happens while Django is still starting. Initializing Django's cache
        framework then can leave it on an alternative 'default' memory-based
        backend, unexpectedly and silently, so that cached results endure less
        than specified. For this reason, a decorated function that is called
        before Django's apps are ready runs uncached.*

    **How It works:**

    A cache key is created by building a string of the module name + the
    function's qualified name (e.g. ``LLMClient.get_for_user.<locals>._get``),
    and then appending a 32-character hash of its arguments, bound to its
    signature and serialized (see :mod:`smarter.lib.cache.keys`). This ensures
    that each unique set of arguments maps to a unique but repeatable cache
    key. ``CACHE_RESULTS["KEY_PREFIX"]`` and ``["VERSION"]`` start every key.

    Arguments must be plain values: str, int, float, bool, None, and lists,
    tuples, dicts and sets of them, plus datetimes, Decimals, UUIDs, classes and
    dataclasses. ``CACHE_RESULTS["KEY_ENCODER"]`` can add types. Any other
    argument, such as a model instance, runs the function uncached and logs an
    error that names its type, once per process. For the same reason, instance
    methods can't be decorated. Classmethods can.

    A qualified name records where a function is defined, not who calls it. A
    function defined inside a classmethod that subclasses inherit has the same
    qualified name for every subclass, so give it a ``class_name: str =
    cls.__name__`` parameter, or subclasses will share its entries.

    Within one process, concurrent callers that miss the same key wait for the
    first one to compute and cache it. Callers in other processes don't wait.
    ``async`` functions are cached too, without this wait, and read and write
    the cache without blocking the event loop.

    :param timeout: The cache timeout in seconds. ``None`` (the default) means
        ``CACHE_RESULTS["TIMEOUT"]``, or the cache alias's own timeout when
        that isn't set. 0 caches nothing.
    :type timeout: Optional[float]
    :param cache_key: An optional fixed cache key to use instead of
        generating one from the function arguments. Every call then shares one
        entry, whatever its arguments, so use it only for functions whose
        result doesn't depend on them. Defaults to ``None``.
    :type cache_key: Optional[str]
    :param logging_enabled: Whether to log cache hits, misses and
        invalidations, as when ``CACHE_RESULTS["LOGGING_ENABLED"]`` is true.
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

        def resolved_timeout() -> Optional[float]:
            return cache_results_settings.timeout if timeout is None else timeout

        def log_enabled() -> bool:
            return logging_enabled or cache_results_settings.logging_enabled

        def log_hit(computed_cache_key: str, result: object, args: tuple, kwargs: dict) -> None:
            if not log_enabled():
                return
            if cache_results_settings.verbose_logging:
                logger.info(
                    "%s cache hit for %s: %s (%s) args: %s kwargs: %s",
                    _prefix("hit"),
                    qualname,
                    computed_cache_key,
                    type(result).__name__,
                    args,
                    kwargs,
                )
            else:
                logger.info(
                    "%s cache hit for %s: %s (%s)", _prefix("hit"), qualname, computed_cache_key, type(result).__name__
                )

        def log_store(computed_cache_key: str, result: object, args: tuple, kwargs: dict) -> None:
            if not log_enabled():
                return
            if cache_results_settings.verbose_logging:
                logger.info(
                    "%s caching %s for %s: %s, with timeout %s args: %s kwargs: %s",
                    _prefix("miss"),
                    type(result).__name__,
                    qualname,
                    computed_cache_key,
                    resolved_timeout(),
                    args,
                    kwargs,
                )
            else:
                logger.info(
                    "%s caching %s for %s: %s, with timeout %s",
                    _prefix("miss"),
                    type(result).__name__,
                    qualname,
                    computed_cache_key,
                    resolved_timeout(),
                )

        def unwrap(cached_result: object) -> tuple[bool, object]:
            """Return (True, result) on a cache hit, and (False, None) on a miss."""
            if cached_result is CACHE_MISS_SENTINEL:
                return False, None
            # cache hit, hooray!
            return True, (
                None if isinstance(cached_result, str) and cached_result == CACHE_NONE_SENTINEL else cached_result
            )

        def wrap(result: object) -> object:
            return CACHE_NONE_SENTINEL if result is None else result

        def cache_not_ready() -> bool:
            """Whether the cache can't be used yet, so that this call must skip it."""
            if not cache_ready():
                logger.debug("%s %s() called before Django's apps are ready. Calling it uncached.", _prefix(), qualname)
                return True
            return False

        if inspect.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                """
                Caches the result of the decorated ``async`` function based on its arguments.

                See :func:`cache_results`. The cache is read and written with
                the backend's own async methods, or else in a worker thread, so
                that the event loop doesn't block on the cache.

                :param args: Positional arguments passed to the decorated function.
                :type args: tuple
                :param kwargs: Keyword arguments passed to the decorated function.
                :type kwargs: dict
                :return: The result of the decorated function, either from cache or freshly computed.
                :rtype: Any
                """
                computed_cache_key = _key_for(func, args, kwargs, cache_key)
                # a None key means the arguments can't be part of a key. _key_for() logged why.
                if computed_cache_key is None or cache_not_ready():
                    return await func(*args, **kwargs)
                hit, result = unwrap(await _aget(computed_cache_key, CACHE_MISS_SENTINEL))
                # the logging hooks may query the database, e.g. for a feature flag, which Django
                # forbids from async code.
                if hit:
                    await sync_to_async(log_hit)(computed_cache_key, result, args, kwargs)
                    return result
                result = await func(*args, **kwargs)
                await _aset(computed_cache_key, wrap(result), resolved_timeout())
                await sync_to_async(log_store)(computed_cache_key, result, args, kwargs)
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

                :param args: Positional arguments passed to the decorated function.
                :type args: tuple
                :param kwargs: Keyword arguments passed to the decorated function.
                :type kwargs: dict
                :return: The result of the decorated function, either from cache or freshly computed.
                :rtype: Any
                """
                computed_cache_key = _key_for(func, args, kwargs, cache_key)
                # a None key means the arguments can't be part of a key. _key_for() logged why.
                if computed_cache_key is None or cache_not_ready():
                    return func(*args, **kwargs)
                cache = get_cache()
                hit, result = unwrap(cache.get(computed_cache_key, CACHE_MISS_SENTINEL))
                if hit:
                    log_hit(computed_cache_key, result, args, kwargs)
                    return result
                # Cache miss, boo! Compute it once, while other threads that miss the same key wait.
                with _lock_for(computed_cache_key):
                    hit, result = unwrap(cache.get(computed_cache_key, CACHE_MISS_SENTINEL))
                    if hit:
                        log_hit(computed_cache_key, result, args, kwargs)
                        return result
                    result = func(*args, **kwargs)
                    cache.set(computed_cache_key, wrap(result), resolved_timeout())
                    log_store(computed_cache_key, result, args, kwargs)
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
            invalidate_prefix = f"{_prefix('invalidate')}.{qualname}().invalidate()"
            logger.debug("%s called with args: %s kwargs: %s", invalidate_prefix, args, kwargs)
            if not cache_ready():
                # nothing can have been cached yet.
                return
            computed_cache_key = _key_for(func, args, kwargs, explicit_cache_key)
            if computed_cache_key is None:
                return
            cache = get_cache()
            # one read, rather than has_key() and then get(): an entry that expires, or is evicted,
            # between the two would be reported as an invalidated None.
            cached_value = cache.get(computed_cache_key, CACHE_MISS_SENTINEL)
            if cached_value is not CACHE_MISS_SENTINEL:
                cache.delete(computed_cache_key)
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
