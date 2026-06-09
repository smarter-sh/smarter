"""
Smarter caching.
"""

from .decorators import cache_results
from .lazy_cache import lazy_cache

__all__ = ["decorators", "lazy_cache"]
