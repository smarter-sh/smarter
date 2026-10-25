"""
Smarter.lib.cache.conf
======================

Configuration of the ``@cache_results`` decorator, read from the
``CACHE_RESULTS`` Django setting. Every entry is optional:

.. code-block:: python

    CACHE_RESULTS = {
        # the CACHES alias that holds cached results.
        "CACHE_ALIAS": "default",
        # the default timeout, in seconds, of a decorated function that names none.
        # Unset, it is the cache alias's own TIMEOUT.
        "TIMEOUT": 3600,
        # text that starts every key. Changing it, or VERSION, abandons every cached
        # result at once, without touching anything else in the same cache.
        "KEY_PREFIX": "",
        "VERSION": None,
        # a subclass of smarter.lib.cache.keys.CacheKeyEncoder, to allow more argument types.
        "KEY_ENCODER": "smarter.lib.cache.keys.CacheKeyEncoder",
        # zero-argument callables that return whether to log cache hits, misses and
        # invalidations, and whether those logs include the arguments.
        "LOGGING_ENABLED": None,
        "VERBOSE_LOGGING": None,
        # a callable(text, event) that formats the start of each log message, where
        # event is "hit", "miss", "invalidate" or "".
        "LOG_PREFIX": None,
    }

Callables and classes are given as dotted paths, or as the objects
themselves. Settings are read on every call, so ``override_settings`` works in
tests. This module depends only on Django and the standard library.
"""

from functools import lru_cache
from typing import Callable, Optional, Union, cast

from django.conf import settings
from django.utils.module_loading import import_string

from .keys import CacheKeyEncoder

SETTING_NAME = "CACHE_RESULTS"
"""The name of the Django setting that configures ``@cache_results``."""

LOG_EVENTS = ("hit", "miss", "invalidate", "")
"""The events that a ``LOG_PREFIX`` callable is called with."""


@lru_cache(maxsize=64)
def _import(dotted_path: str) -> object:
    """
    Import an object from its dotted path, once per path.

    :param dotted_path: e.g. ``myproject.cache.MyCacheKeyEncoder``.
    :type dotted_path: str
    :return: The object.
    :rtype: object
    :raises ImportError: If the path can't be imported.
    """
    return import_string(dotted_path)


def _resolve(value: Union[str, object, None]) -> object:
    """
    Return an object given as itself or as a dotted path.

    :param value: The setting's value.
    :type value: Union[str, object, None]
    :return: The object, or ``None``.
    :rtype: object
    """
    if isinstance(value, str):
        return _import(value)
    return value


def _default_log_prefix(text: str, event: str) -> str:
    """
    Return the start of a log message unchanged.

    :param text: e.g. ``smarter.lib.cache.decorators.@cache_results()``.
    :type text: str
    :param event: ``"hit"``, ``"miss"``, ``"invalidate"`` or ``""``.
    :type event: str
    :return: ``text``.
    :rtype: str
    """
    return text


class CacheResultsSettings:
    """
    The ``CACHE_RESULTS`` setting, with its defaults.

    Use the module's :data:`cache_results_settings` instance.
    """

    @property
    def _values(self) -> dict:
        return getattr(settings, SETTING_NAME, None) or {}

    @property
    def cache_alias(self) -> str:
        """
        The ``CACHES`` alias that holds cached results.

        :rtype: str
        """
        return self._values.get("CACHE_ALIAS", "default")

    @property
    def timeout(self) -> Optional[float]:
        """
        The default timeout in seconds, or Django's ``DEFAULT_TIMEOUT`` marker, which means the cache alias's own.

        :rtype: Optional[float]
        """
        # imported here, like every use of django.core.cache in this package: importing it
        # while Django is still starting can leave the cache on the wrong backend.
        from django.core.cache.backends.base import (  # pylint: disable=import-outside-toplevel
            DEFAULT_TIMEOUT,
        )

        # DEFAULT_TIMEOUT is a bare object() that Django's cache methods accept as a timeout,
        # and their signatures declare as Optional[float].
        return cast(Optional[float], self._values.get("TIMEOUT", DEFAULT_TIMEOUT))

    @property
    def key_prefix(self) -> str:
        """
        Text that starts every key: ``KEY_PREFIX``, then ``v<VERSION>:`` when a version is set.

        :rtype: str
        """
        prefix = str(self._values.get("KEY_PREFIX") or "")
        version = self._values.get("VERSION")
        if version is not None:
            prefix += f"v{version}:"
        return prefix

    @property
    def key_encoder(self) -> type[CacheKeyEncoder]:
        """
        The JSON encoder for arguments.

        :rtype: type[CacheKeyEncoder]
        :raises TypeError: If the setting doesn't name a subclass of :class:`CacheKeyEncoder`.
        """
        encoder = _resolve(self._values.get("KEY_ENCODER")) or CacheKeyEncoder
        if not (isinstance(encoder, type) and issubclass(encoder, CacheKeyEncoder)):
            raise TypeError(f"{SETTING_NAME}['KEY_ENCODER'] must be a subclass of CacheKeyEncoder, not {encoder!r}.")
        return encoder

    def _flag(self, name: str) -> bool:
        hook: Optional[Callable[[], bool]] = _resolve(self._values.get(name))  # type: ignore[assignment]
        if hook is None:
            return False
        if callable(hook):
            return bool(hook())
        return bool(hook)

    @property
    def logging_enabled(self) -> bool:
        """
        Whether to log every cache hit, miss and invalidation, from ``LOGGING_ENABLED``.

        :rtype: bool
        """
        return self._flag("LOGGING_ENABLED")

    @property
    def verbose_logging(self) -> bool:
        """
        Whether those logs include the arguments, from ``VERBOSE_LOGGING``.

        :rtype: bool
        """
        return self._flag("VERBOSE_LOGGING")

    def log_prefix(self, text: str, event: str = "") -> str:
        """
        Format the start of a log message with the ``LOG_PREFIX`` callable.

        :param text: The unformatted text.
        :type text: str
        :param event: ``"hit"``, ``"miss"``, ``"invalidate"`` or ``""``.
        :type event: str
        :return: The formatted text.
        :rtype: str
        """
        formatter = _resolve(self._values.get("LOG_PREFIX")) or _default_log_prefix
        return formatter(text, event)  # type: ignore[operator]


cache_results_settings = CacheResultsSettings()
"""The ``CACHE_RESULTS`` setting, with its defaults."""


__all__ = ["CacheResultsSettings", "LOG_EVENTS", "SETTING_NAME", "cache_results_settings"]
