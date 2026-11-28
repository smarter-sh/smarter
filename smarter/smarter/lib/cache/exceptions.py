"""
The errors that mean the cache, Redis, can't be read or written.

:data:`cache_results.lazy_cache` mirrors Django's cache api, so it passes the backend's exceptions straight through.
A caller on a request's path that can do without the cache catches :data:`CACHE_EXCEPTIONS`, logs one warning line
without a traceback, and degrades, e.g. a read becomes a miss and a rate limit lets the request through, rather than
answering 500 while Redis is down (issues #941, #1052, #1091).

This module imports only django-redis and redis, so that modules which :mod:`smarter.lib.logging` imports while it
initializes, e.g. :mod:`smarter.lib.django.waffle.is_active`, can import it.
"""

from django_redis.exceptions import ConnectionInterrupted
from redis.exceptions import RedisError

CACHE_EXCEPTIONS: tuple[type[BaseException], ...] = (ConnectionInterrupted, RedisError)
"""The errors of the cache, Redis, e.g. while it restarts or refuses a connection."""


__all__ = ["CACHE_EXCEPTIONS"]
