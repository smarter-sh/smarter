Smarter Caching
=================

The Smarter Framework implements its own, proprietary caching technology,
designed as a one-size-fits-all easy-to-implement solution for caching
function outputs based on their input parameters.

- A general-purpose caching decorator, `@cache_results()`, for caching function results.
- A lazy singleton cache wrapper, `lazy_cache`, around Django's cache framework.
- Class-based Django ORM object and queryset caching.
- Class and signal driven cache invalidation strategy that is built in to the SAM Broker
  architecture, providing highly targeted and efficient cache management.


.. toctree::
    :maxdepth: 2
    :caption: Smarter Caching Architecture

    caching/decorator
    caching/invalidators
    caching/lazy-cache
    caching/class-based-caching
