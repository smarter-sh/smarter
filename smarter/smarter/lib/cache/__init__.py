"""
Smarter's configuration of the cache-results package.

Smarter caches with the cache-results package (https://docs.cache-results.smarter.sh/):
``from cache_results import cache_results, lazy_cache``. The package depends
only on Django. The hooks in :mod:`smarter.lib.cache.hooks`, named by the
``CACHE_RESULTS`` setting in ``smarter/settings/base.py``, connect it to the
parts of Smarter that it can't depend on.
"""
