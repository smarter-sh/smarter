Smarter Caching
=================

Smarter caches in Redis with :func:`~smarter.lib.cache.cache_results`, which caches a function's
result under a key built from its module, qualified name and arguments, and gives the function an
``invalidate()``. It decorates regular functions, ``async`` functions and classmethods, but refuses
instance methods, because ``self`` would be part of the key. Concurrent callers in one process that
miss the same key wait for the first to compute it, and calls made before Django's apps are ready run
uncached. ``async`` functions read and write the cache without blocking the event loop. Its logs
name the cached function and the type of its result, never the result itself.

Arguments must be plain values: strings, numbers, booleans, ``None``, and lists, tuples, dicts and
sets of them, plus datetimes, Decimals, UUIDs, classes, dataclasses and Pydantic models. Any other
argument, such as a model instance, runs the function uncached and logs an error that names the
function and the argument's type, once per process. Pass the instance's id instead. ``str()`` of an
object is never used as a key: two rows with the same name would share an entry, and an object
without its own ``__str__`` would have a new key in every process.

The decorator, its keys and its settings depend only on Django, and are also maintained as a
standalone package, `cache-results <https://github.com/smarter-sh/cache-results>`__, under the MIT
license. Until Smarter installs that package, its own copy in ``smarter.lib.cache`` is kept in step
with it. The ``CACHE_RESULTS`` setting (see
:doc:`caching/conf`) names the cache alias, the default timeout, a key prefix and version that can
abandon every cached result at once, the key encoder, and the logging hooks.
:mod:`smarter.lib.cache.hooks` connects them to Smarter: the default timeout is
``smarter_settings.cache_expiration``, logging follows the ``CACHE_LOGGING`` waffle switch, and the
key encoder accepts Pydantic models.

The web console's resource lists build on it: each list api caches its pages per user, the React
lists keep the pages they showed in the browser, and saving or deleting a resource makes its list's
cached pages stale at once. See :doc:`django/listview`.

.. toctree::
   :maxdepth: 1
   :caption: Technical References

   caching/cache_results
   caching/keys
   caching/conf
   caching/hooks
   caching/cache_sentinel
   caching/lazy_cache
