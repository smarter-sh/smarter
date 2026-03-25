Class-Based Caching
========================

Smarter's TimestampedModel and MetaDataModel ORM classes include two powerful
class-based cached fetching methods: `get_cached_object(*args, invalidate=False, **kwargs)`
and `get_cached_objects(*args, invalidate=False, **kwargs)`.
These methods provide seamless caching of ORM objects and querysets, with
built-in support for cache invalidation.

Brokers generally use these methods for all fetch operations on ORM objects,
safely providing a significant performance boost. ORM objects and querysets
fetched using these methods reside inside Smarter's invalidation chain,
meaning that these objects are considered "cache safe" as they will be
automatically invalidated by any of Smarter's three cache invalidation
strategies.

.. note::

    Smarter's class-based fetch methods are fully integrated into the
    cache invalidation chain, meaning that related ORM objects and querysets,
    and hard-to-manage cache keys for UI listviews and rendered html templates
    will also be invalidated in a complete and orderly manner.

.. code-block:: python

    # fetch a cached Django ORM object
    self.user_profile = UserProfile.get_cached_object(user=self.user)

    # invalidate the same cache entry
    self.user_profile = UserProfile.get_cached_object(invalidate=True, user=self.user)

    # fetch a cached Django ORM queryset
    chatbots = ChatBot.get_cached_objects(user_profile=self.user_profile)

    # invalidate the same cache entry
    chatbots = ChatBot.get_cached_objects(invalidate=True, user_profile=self.user_profile)
