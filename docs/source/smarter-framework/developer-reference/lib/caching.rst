Smarter Caching
=================

Smarter caches in Redis with :func:`~smarter.lib.cache.cache_results`, which caches a function's
result under a key built from its arguments, and gives the function an ``invalidate()``.

The web console's resource lists build on it: each list api caches its pages per user, the React
lists keep the pages they showed in the browser, and saving or deleting a resource makes its list's
cached pages stale at once. See :doc:`django/listview`.

.. toctree::
   :maxdepth: 1
   :caption: Technical References

   caching/cache_results
   caching/cache_sentinel
   caching/lazy_cache
