"""
Smarter.lib.cache.hooks
=======================

Smarter's hooks for the cache-results package.

The package (https://docs.cache-results.smarter.sh/) depends only on Django.
Its ``CACHE_RESULTS`` setting, in ``smarter/settings/base.py``, names these
hooks, which connect it to the parts of Smarter that it can't depend on:

- :func:`logging_enabled` and :func:`verbose_logging` follow the
  ``CACHE_LOGGING`` waffle switch and ``smarter_settings.verbose_logging``.
- :class:`SmarterCacheKeyEncoder` also accepts Pydantic urls and models as
  cache key arguments.

Log messages are colored by the package's own
:func:`cache_results.colors.log_prefix`.
"""

from cache_results import CacheKeyEncoder
from pydantic import BaseModel, HttpUrl

from smarter.common.conf import smarter_settings


def logging_enabled() -> bool:
    """
    Whether to log every cache hit, miss and invalidation: the ``CACHE_LOGGING`` waffle switch.

    :return: True if the switch is on.
    :rtype: bool
    """
    # pylint: disable=import-outside-toplevel
    from smarter.lib.django.waffle import SmarterWaffleSwitches, switch_is_active

    return switch_is_active(SmarterWaffleSwitches.CACHE_LOGGING)


def verbose_logging() -> bool:
    """
    Whether cache logs include the arguments: ``smarter_settings.verbose_logging``.

    The package asks only when :func:`logging_enabled` is True.

    :return: True if verbose logging is on.
    :rtype: bool
    """
    return bool(smarter_settings.verbose_logging)


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
        :raises cache_results.CacheKeyArgumentError: If ``o`` has no safe representation.
        """
        if isinstance(o, HttpUrl):
            return str(o)
        if isinstance(o, BaseModel):
            return {
                "__model__": f"{type(o).__module__}.{type(o).__qualname__}",
                "fields": o.model_dump(mode="json"),
            }
        return super().default(o)


__all__ = ["SmarterCacheKeyEncoder", "logging_enabled", "verbose_logging"]
