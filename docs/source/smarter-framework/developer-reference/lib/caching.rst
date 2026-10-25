Smarter Caching
=================

Smarter caches in Redis with :func:`~cache_results.decorators.cache_results`, which caches a function's
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

The decorator is the standalone package `cache-results <https://pypi.org/project/cache-results/>`__,
which depends only on Django and is published under the MIT license, with its own documentation at
`docs.cache-results.smarter.sh <https://docs.cache-results.smarter.sh/>`__. Smarter installs it from
PyPI, and code imports it as ``from cache_results import cache_results``. Raw ``get()`` and ``set()``
go through the package's :data:`~cache_results.lazy.lazy_cache`, Django's cache imported only
once Django is ready, never through ``django.core.cache``. The ``CACHE_RESULTS`` setting (see
:mod:`cache_results.conf`) names the cache alias, the default timeout, a key prefix and version that can
abandon every cached result at once, the key encoder, and the logging hooks.
:mod:`smarter.lib.cache.hooks` connects them to Smarter: the default timeout is
``smarter_settings.cache_expiration``, logging follows the ``CACHE_LOGGING`` waffle switch, the
key encoder accepts Pydantic models, and the package's :func:`~cache_results.colors.log_prefix`
colors log messages. These hooks stay in Smarter because they need Pydantic, django-waffle and
Smarter's settings, which the package doesn't depend on.

The web console's resource lists build on it: each list api caches its pages per user, the React
lists keep the pages they showed in the browser, and saving or deleting a resource makes its list's
cached pages stale at once. See :doc:`django/listview`.

.. toctree::
   :maxdepth: 1
   :caption: Technical References

   caching/hooks
