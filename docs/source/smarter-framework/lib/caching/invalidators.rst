Caching Invalidators
========================

Smarter's caching architecture provides three distinct mechanisms for cache
invalidation, each designed to address different use cases and scenarios.

Decorated functions
------------------------------

Smarter's `@cache_results()` decorator includes a built-in `invalidate(*args, **kwargs)` method
that can be called with the same arguments as the original function to
invalidate the corresponding cache entry.

.. note::

   Due to the way the `@cache_results()` decorator generates cache keys,
   this is the only means of invalidating cache entries created by the `@cache_results()`.

.. code-block:: python

    from smarter.lib.cache import cache_results

    @cache_results(timeout=600)
    def expensive_function(x, y):
        # Perform expensive computation ...
        result = "some very expensive computational result"
        return result

    expensive_function.invalidate(1, 2)


Django signals
-------------------

Smarter's SAM broker architecture broadcasts a `cache_invalidate`` Django signal
in response to any brokered database write operations. You can create custom behaviors
in response to these signals by connecting your own signal receivers.

.. code-block:: python
   :caption: Receiving the `cache_invalidate` signal in response SAM brokered updates.

    from smarter.apps.account.signals import cache_invalidate

    # apply a manifest
    factory = RequestFactory()
    request = factory.post('/api/v1/apply', data={'version': 'smarter.sh/v1' ...})

    @receiver(cache_invalidate)
    def invalidate_cache_on_account_update(sender, instance, **kwargs):
        user_profile = kwargs.get('user_profile')

        # do other cache invalidation things for this user_profile

SAM Broker
-------------------

Brokers implement a `invalidate_cache()` class method that is invoked
on `apply()` and `delete()` operations. You can invoke this method
directly in order to trigger platform-wide cache invalidations.

.. code-block:: python
   :caption: trigger platform-wide invalidations with a SAM broker.

    from smarter.apps.chatbot.manifest.brokers.chatbot import SAMChatbotBroker

    broker = SAMChatbotBroker(chatbot=chatbot_instance)
    broker.invalidate_cache()

    @receiver(cache_invalidate)
    def invalidate_cache_on_account_update(sender, instance, **kwargs):
        user_profile = kwargs.get('user_profile')

        # do other cache invalidation things for this user_profile
