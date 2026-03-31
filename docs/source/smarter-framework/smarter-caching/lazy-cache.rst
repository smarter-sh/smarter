Smarter LazyCache
========================

Smarter's lazy singleton cache wrapper, ``lazy_cache``, provides a convenient interface
to Django's caching framework that works safely during Django's startup phase as well
as in multi-threaded environments. It gracefully handles common edge cases, such as
unit testing and Django's startup phase.

Usage examples::

  .. code-block:: python

    from smarter.lib.cache import lazy_cache

    # Get the cache instance
    cache = lazy_cache()

    # Set a value in the cache
    cache.set('my_key', 'my_value', timeout=300)

    # Get a value from the cache
    value = cache.get('my_key')

.. literalinclude:: ../../../../smarter/smarter/lib/cache.py
   :language: python
   :lines: 74-302
   :caption: Smarter LazyCache implementation
