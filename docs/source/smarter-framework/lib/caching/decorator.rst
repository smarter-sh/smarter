@cache_results() Decorator
==================================

Smarter's cache decorator is fundamental to the framework's caching strategy. It provides a simple
one-size-fits-all solution for caching the results of any function based on its input parameters.
`@cache_results()` is designed to be low-overhead and easy to implement. It includes built-in
support for cache invalidation.

Usage examples::

  .. code-block:: python

    from smarter.lib.cache import cache_results

    @cache_results(timeout=600)
    def expensive_function(x, y, *args, **kwargs):
        # Perform expensive computation ...
        result = "some very expensive computational result"
        return result

    result = expensive_function(1, 2)

    # Invalidate the cache for specific input parameters
    expensive_function.invalidate(1, 2)

.. literalinclude:: ../../../../../smarter/smarter/lib/cache.py
   :language: python
   :lines: 295-
   :caption: Smarter cache_results() decorator implementation
