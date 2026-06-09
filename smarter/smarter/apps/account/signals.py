"""Signals for account app."""

from django.dispatch import Signal

new_user_created = Signal()
"""
Signal sent when a new user is created.

Arguments:

    user_profile (UserProfile): The profile of the newly created user.

Example::

    new_user_created.send(sender=self.__class__, user_profile=self)
"""

new_charge_created = Signal()
"""
Signal sent when a new charge is created.

Arguments:
    charge (Charge): The newly created charge instance.

Example::

    new_charge_created.send(sender=self.__class__, charge=self)
"""

broker_ready = Signal()
"""
Signal sent when a broker achieves a ready state.

Arguments:
    broker: The broker instance that is ready.

Example::

    broker_ready.send(sender=self.__class__, broker=self)
"""

cache_invalidate = Signal()
"""
Signal sent to trigger cache invalidation.

Arguments:
    None

Example::

    cache_invalidate.send(sender=self.__class__)
"""
