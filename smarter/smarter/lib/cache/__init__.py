"""
Smarter caching.
"""

from .cache_results import cache_results
from .lazy_cache import lazy_cache

__all__ = ["cache_results", "lazy_cache"]
