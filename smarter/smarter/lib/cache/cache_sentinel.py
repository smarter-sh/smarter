"""
smarter.lib.cache.cache_sentinel
================================

This module defines sentinel objects for robust cache state management in the
Smarter framework.

**Key Features:**

- Provides the ``CacheSentinel`` class for distinguishing between explicit
  ``None`` values and cache misses.
- Exports ``CACHE_MISS_SENTINEL`` (a unique object) and ``CACHE_NONE_SENTINEL``
  (a string sentinel) for use in cache decorators and wrappers.
- Ensures reliable cache semantics when cached functions may return ``None`` or
  when differentiating between missing and present-but-None values.

**Usage Example:**

.. code-block:: python

    from smarter.lib.cache.cache_sentinel import CACHE_MISS_SENTINEL
    value = cache.get(key, CACHE_MISS_SENTINEL)
    if value is CACHE_MISS_SENTINEL:
        # Handle cache miss
        ...
    elif value is None:
        # Handle cached None
        ...

See the ``CacheSentinel`` class docstring for more details.
"""

import hashlib
import pickle


class CacheSentinel:
    """
    Sentinel object for cache state representation.

    This class is used to distinguish between different cache states,
    specifically to represent
    cases where a cache entry is explicitly set to ``None`` or when a cache lookup results in a miss.
    By using a unique sentinel object, the cache logic can reliably differentiate between a value
    that is intentionally ``None`` and a value that is absent from the cache.

    **Usage scenarios:**

    - When a cached function or value may legitimately return ``None``, this sentinel ensures that
        a cached ``None`` is not mistaken for a cache miss.
    - Used internally by caching decorators and cache wrappers to provide robust cache semantics.

    **Example:**

    .. code-block:: python

        sentinel = CacheSentinel("CACHE_MISS")
        cache_value = cache.get(key, sentinel)
        if cache_value is sentinel:
            # Handle cache miss
            ...
        elif cache_value is None:
            # Handle cached None
            ...

    The string representation of the sentinel is the name provided at construction, while the
    ``repr`` includes a hash for uniqueness. This makes it suitable for use as a default value
    in cache lookups and for debugging purposes.
    """

    def __init__(self, name):
        self.name = name

    def __str__(self):
        return f"<CacheSentinel: {hashlib.sha256(pickle.dumps(self.name)).hexdigest()[:32]}>"

    def __repr__(self):
        return self.__str__()


CACHE_NONE_SENTINEL = 'CacheSentinel("CACHE_NONE")'
CACHE_MISS_SENTINEL = CacheSentinel("CACHE_MISS")


__all__ = ["CACHE_NONE_SENTINEL", "CACHE_MISS_SENTINEL"]
