"""
Smarter.lib.cache.lazy_cache
=============================

This module provides a lazy wrapper around Django's cache framework, ensuring
safe and reliable cache access in the Smarter framework.

**Key Features:**

- Defines the ``LazyCache`` class, which defers importing Django's cache until
  first use to avoid premature initialization issues.
- Exports a singleton instance ``lazy_cache`` with an API identical to ``django.core.cache``.
- Integrates diagnostics and logging to verify cache backend health and
  configuration on first access.
- Supports feature flag management via Django-waffle, with lazy import and
  enhanced caching for switch checks.
- Enables verbose and cache activity logging controlled by feature flags and settings.

**Usage Example:**

.. code-block:: python

    from smarter.lib.cache import lazy_cache as cache

    cache.set("my_key", "my_value", timeout=300)
    value = cache.get("my_key")
    print(value)  # Outputs: "my_value"

**Notes:**

- Use ``lazy_cache`` instead of importing Django's cache directly to prevent
  issues where Django falls back to a default, non-persistent cache backend.
- The ``lazy_cache`` instance is intended for use as a singleton throughout
  the application.
- See the ``LazyCache`` class docstring for more details on features and
  implementation.
"""

from functools import cached_property
from typing import Any, Optional

from django.apps import apps

from smarter.common.conf import smarter_settings
from smarter.lib import logging

logger = logging.getLogger(__name__)


# pylint: disable=C2801,E1102,W0613
class LazyCache:
    """
    A lazy wrapper around Django's cache framework that defers importing the cache.

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
            from smarter.common.mixins.helper_mixin import SmarterReadyState

            logger_prefix = logging.formatted_text(f"{__name__}.{LazyCache.__name__}.cache()")
            if apps.ready:
                logger.debug(
                    "%s Django apps are %s. Proceeding to initialize django.core.cache.",
                    logger_prefix,
                    SmarterReadyState.READY,
                )
            else:
                logger.warning(
                    "%s Django cache is being accessed before Django apps are ready. This may lead to premature initialization issues and unexpected cache backend fallbacks.",
                    logger_prefix,
                )
                return None
            from django.core.cache import cache, caches
            from django_redis.cache import RedisCache

            logger.debug("%s initialized django.core.cache.", logger_prefix)
            self._cache = cache

            try:
                # perform diagnostics on first access
                cache.set("test_key", "test_value", timeout=5)
                value = cache.get("test_key")
                if value == "test_value":
                    logger.debug("%s Django cache is %s", logger_prefix, SmarterReadyState.READY)
                else:
                    logger.error("%s Django cache is %s", logger_prefix, SmarterReadyState.NOT_READY)
            # pylint: disable=broad-except
            except Exception as e:
                logger.error("%s Error accessing Django cache: %s", logger_prefix, e)

            if not isinstance(caches["default"], RedisCache):
                logger.warning(
                    "%s django.core.cache.caches['default'] was expecting django_redis.cache.RedisCache but found: %s",
                    logger_prefix,
                    caches["default"].__class__,
                )

        return self._cache

    @property
    def waffle(self):
        """
        Lazily import and return the Waffle module.

        Lookalike function api such as switch_is_active() with identical signatures.

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
            # pylint: disable=import-outside-toplevel
            from smarter.lib.django import waffle

            self._waffle = waffle

        return self._waffle

    @cached_property
    def verbose_logging(self) -> bool:
        """
        Check if verbose logging (here, inside this module) is enabled via Waffle switch.

        :return: True if verbose logging is enabled, False otherwise.
        :rtype: bool
        """

        return self.cache_logging and smarter_settings.verbose_logging

    @cached_property
    def cache_logging(self) -> bool:
        """
        Check if cache activity logging (here, inside this module) is enabled via Waffle switch.

        :return: True if cache logging is enabled, False otherwise.
        :rtype: bool
        """
        from smarter.lib.django.waffle import SmarterWaffleSwitches

        return self.waffle.switch_is_active(SmarterWaffleSwitches.CACHE_LOGGING)

    def get(self, key: Any, default: Optional[Any] = None) -> Any:
        """
        Fetch a given key from the cache.

        If the key does not exist, return default, which itself defaults to None.
        """
        return self.cache.get(key, default)  # type: ignore[return-value]

    def set(self, key: Any, value: Any, timeout: Optional[float] = None, version: Optional[int] = None) -> None:
        """
        Set a value in the cache.

        If timeout is given, use that timeout for the key; otherwise use the default cache timeout.
        """
        return self.cache.set(key, value, timeout=timeout)  # type: ignore[return-value]

    def delete(self, key: Any) -> bool:
        """Delete a value from the cache."""
        return self.cache.delete(key)  # type: ignore[return-value]

    def incr(self, key: Any, delta: int = 1) -> int:
        """Increment a value in the cache."""
        return self.cache.incr(key, delta)  # type: ignore[return-value]

    def decr(self, key: Any, delta: int = 1) -> int:
        """Decrement a value in the cache."""
        return self.cache.decr(key, delta)  # type: ignore[return-value]

    def clear(self) -> None:
        """Clear the entire cache."""
        return self.cache.clear()  # type: ignore[return-value]

    def add(self, key: Any, value: Any, timeout: Optional[float] = None, version: Optional[int] = None) -> bool:
        """Add a value to the cache if the key does not already exist."""
        return self.cache.add(key, value, timeout=timeout)  # type: ignore[return-value]

    def touch(self, key: Any, timeout: Optional[float] = None, version: Optional[int] = None) -> bool:
        """Update the timeout for a given key in the cache."""
        return self.cache.touch(key, timeout=timeout)  # type: ignore[return-value]

    def has_key(self, key: Any, version: Optional[int] = None) -> bool:
        """Check if a key exists in the cache."""
        return self.cache.has_key(key)  # type: ignore[return-value]

    def get_many(self, keys: list, version: Optional[int] = None) -> dict:
        """Fetch multiple keys from the cache."""
        return self.cache.get_many(keys)  # type: ignore[return-value]

    def set_many(self, data: dict, timeout: Optional[float] = None, version: Optional[int] = None) -> list[Any]:
        """Set multiple values in the cache."""
        return self.cache.set_many(data, timeout=timeout)  # type: ignore[return-value]

    def delete_many(self, keys: list, version: Optional[int] = None) -> None:
        """Delete multiple keys from the cache."""
        return self.cache.delete_many(keys)  # type: ignore[return-value]

    def incr_version(self, key: Any, delta: int = 1, version: Optional[int] = None) -> int:
        """Increment the version of a key in the cache."""
        return self.cache.incr_version(key, delta)  # type: ignore[return-value]

    def decr_version(self, key: Any, delta: int = 1, version: Optional[int] = None) -> int:
        """Decrement the version of a key in the cache."""
        return self.cache.decr_version(key, delta)  # type: ignore[return-value]

    def close(self, **kwargs) -> None:
        """Close the cache connection."""
        return self.cache.close(**kwargs)  # type: ignore[return-value]


lazy_cache = LazyCache()
"""
A singleton instance of LazyCache for accessing Django's cache framework.

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


__all__ = ["lazy_cache"]
