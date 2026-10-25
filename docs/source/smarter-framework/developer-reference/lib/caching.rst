Smarter Caching
=================

Smarter caches in Redis with :func:`~smarter.lib.cache.cache_results`, which caches a function's
result under a key built from its module, qualified name and arguments, and gives the function an
``invalidate()``. It decorates regular functions, ``async`` functions and classmethods, but refuses
instance methods, because ``self`` would be part of the key. Concurrent callers in one process that
miss the same key wait for the first to compute it, and calls made before Django's apps are ready run
uncached. Its logs name the cached function and the type of its result, never the result itself.

The web console's resource lists build on it: each list api caches its pages per user, the React
lists keep the pages they showed in the browser, and saving or deleting a resource makes its list's
cached pages stale at once. See :doc:`django/listview`.

.. toctree::
   :maxdepth: 1
   :caption: Technical References

   caching/cache_results
   caching/cache_sentinel
   caching/lazy_cache
