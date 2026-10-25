"""
Smarter caching.

- :func:`cache_results` caches a function's results by its arguments
  (:mod:`smarter.lib.cache.decorators`, configured by :mod:`smarter.lib.cache.conf`).
- :data:`lazy_cache` is Django's cache, imported only once Django is ready
  (:mod:`smarter.lib.cache.lazy_cache`).
"""

from .decorators import cache_results
from .lazy_cache import lazy_cache

__all__ = ["cache_results", "lazy_cache"]
