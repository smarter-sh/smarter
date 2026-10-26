# Smarter cache

Smarter caches with the [cache-results](https://pypi.org/project/cache-results/)
package, installed from PyPI and pinned in `smarter/requirements/`. Its
documentation is at <https://docs.cache-results.smarter.sh/>, and its source is
at <https://github.com/smarter-sh/cache-results>.

```python
from cache_results import cache_results, lazy_cache
```

This folder only holds `hooks.py`, Smarter's configuration of the package.

## Where the code went

The caching code that used to live here moved into cache-results, which
depends only on Django:

| Was here              | Now                                                     |
| --------------------- | ------------------------------------------------------- |
| `decorators.py`       | `cache_results.decorators`, imported as `cache_results` |
| `keys.py`             | `cache_results.keys`                                    |
| `conf.py`             | `cache_results.conf`                                    |
| `cache_sentinel.py`   | `cache_results.sentinels`                               |
| `lazy_cache.py`       | `cache_results.lazy`, imported as `lazy_cache`          |
| `hooks.log_prefix()`  | `cache_results.colors.log_prefix`                       |
| `tests/test_cache.py` | the package's own tests                                 |

Its tests now run in the package, on Python 3.10 to 3.14, Django 4.2 to 6.0,
and against Redis.

## What stays here

`hooks.py` has the hooks that need Pydantic, django-waffle or Smarter's
settings. The package can't depend on those, so the `CACHE_RESULTS` setting in
`smarter/settings/base.py` names them:

- `SmarterCacheKeyEncoder` also accepts Pydantic models and urls as cache key
  arguments.
- `logging_enabled()` follows the `CACHE_LOGGING` waffle switch.
- `verbose_logging()` follows `smarter_settings.verbose_logging`.

## Changing the decorator

Make the change in the cache-results repository (`../cache-results`), and
release it. Then bump the `cache-results==` pin in `smarter/requirements/`.
Don't copy the package's code back into this folder.
