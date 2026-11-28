"""
A stand-in for the cache, Redis, while it can't be reached, for tests of the code that degrades without it.

Patch a module's ``lazy_cache`` (or a throttle's ``cache``) with :func:`unreachable_cache`, and every call raises
the error that django-redis raises during an outage:

.. code-block:: python

    from smarter.lib.unittest.cache_outage import unreachable_cache

    with patch("smarter.lib.django.static_storage.lazy_cache", unreachable_cache()):
        self.assertFalse(is_uploaded(name))

See issue #1091 and :data:`smarter.lib.cache.exceptions.CACHE_EXCEPTIONS`.
"""

from unittest.mock import MagicMock

from django_redis.exceptions import ConnectionInterrupted
from redis.exceptions import TimeoutError as RedisTimeoutError

CACHE_METHODS = ("get", "set", "add", "incr", "delete", "touch", "get_many", "set_many", "delete_many")
"""The cache's methods that read or write Redis, each of which raises in :func:`unreachable_cache`."""


def cache_outage_error() -> ConnectionInterrupted:
    """
    Return the error that django-redis raises when Redis can't be reached, as seen in prod.

    :returns: A ``ConnectionInterrupted`` caused by a redis ``TimeoutError``.
    """
    cause = RedisTimeoutError("Timeout connecting to server")
    error = ConnectionInterrupted(connection=None)
    error.__cause__ = cause
    return error


def unreachable_cache() -> MagicMock:
    """
    Return a cache whose every read and write raises :func:`cache_outage_error`.

    :returns: A mock with the methods of Django's cache api.
    """
    cache = MagicMock()
    for method_name in CACHE_METHODS:
        method = getattr(cache, method_name)
        method.side_effect = cache_outage_error()
    return cache


__all__ = ["CACHE_METHODS", "cache_outage_error", "unreachable_cache"]
