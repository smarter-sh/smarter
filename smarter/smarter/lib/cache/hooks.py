"""
Smarter.lib.cache.hooks
=======================

Smarter's configuration of the ``@cache_results`` decorator.

The decorator, its keys and its settings (:mod:`smarter.lib.cache.decorators`,
:mod:`smarter.lib.cache.keys` and :mod:`smarter.lib.cache.conf`) depend only
on Django. This module connects them to the rest of Smarter, through the
``CACHE_RESULTS`` setting in ``smarter/settings/base.py``:

- :func:`logging_enabled` and :func:`verbose_logging` follow the
  ``CACHE_LOGGING`` waffle switch and ``smarter_settings.verbose_logging``.
- :func:`log_prefix` colors log messages as the rest of Smarter's logs are:
  green for hits, red for misses, gray for invalidations.
- :class:`SmarterCacheKeyEncoder` also accepts Pydantic urls and models as
  cache key arguments.
"""

from pydantic import BaseModel, HttpUrl

from smarter.common.helpers.console_helpers import SmarterFormattedTextColorCodes
from smarter.lib import logging

from .keys import CacheKeyEncoder
from .lazy_cache import lazy_cache

_EVENT_COLORS = {
    "hit": SmarterFormattedTextColorCodes.REGULAR_GREEN,
    "miss": SmarterFormattedTextColorCodes.DARK_RED,
    "invalidate": SmarterFormattedTextColorCodes.LIGHT_GRAY,
}


def logging_enabled() -> bool:
    """
    Whether to log every cache hit, miss and invalidation: the ``CACHE_LOGGING`` waffle switch.

    :return: True if the switch is on.
    :rtype: bool
    """
    return lazy_cache.cache_logging


def verbose_logging() -> bool:
    """
    Whether cache logs include the arguments: ``CACHE_LOGGING`` and ``smarter_settings.verbose_logging``.

    :return: True if both are on.
    :rtype: bool
    """
    return lazy_cache.verbose_logging


def log_prefix(text: str, event: str) -> str:
    """
    Format the start of a cache log message in Smarter's style.

    :param text: e.g. ``smarter.lib.cache.decorators.@cache_results()``.
    :type text: str
    :param event: ``"hit"``, ``"miss"``, ``"invalidate"`` or ``""``.
    :type event: str
    :return: The formatted text.
    :rtype: str
    """
    color = _EVENT_COLORS.get(event)
    if color is None:
        return logging.formatted_text(text)
    return logging.formatted_text(text, color)


class SmarterCacheKeyEncoder(CacheKeyEncoder):
    """
    Cache key encoder that also accepts Pydantic urls and models.

    A model is identified by its class and its JSON dump, like a dataclass.
    """

    def default(self, o):
        """
        Encode one value that JSON doesn't know.

        :param o: The value.
        :type o: object
        :return: A JSON-serializable representation of ``o``.
        :rtype: object
        :raises smarter.lib.cache.keys.CacheKeyArgumentError: If ``o`` has no safe representation.
        """
        if isinstance(o, HttpUrl):
            return str(o)
        if isinstance(o, BaseModel):
            return {
                "__model__": f"{type(o).__module__}.{type(o).__qualname__}",
                "fields": o.model_dump(mode="json"),
            }
        return super().default(o)


__all__ = ["SmarterCacheKeyEncoder", "log_prefix", "logging_enabled", "verbose_logging"]
