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

secret_inializing = Signal()
"""
Signal sent when a secret is initializing.

Arguments:
    secret_name (str): The name of the secret being initialized.
    user_profile (UserProfile): The profile of the user associated with the secret.

Example::

    secret_inializing.send(sender=self.__class__, secret_name=name, user_profile=user_profile)
"""


secret_created = Signal()
"""
Signal sent when a secret is created.

Arguments:
    secret (Secret): The newly created secret instance.

Example::

    secret_created.send(sender=self.__class__, secret=self)
"""


secret_edited = Signal()
"""
Signal sent when a secret is edited.

Arguments:
    secret (Secret): The edited secret instance.

Example::

    secret_edited.send(sender=self.__class__, secret=self)
"""


secret_ready = Signal()
"""
Signal sent when a secret is ready.

Arguments:
    secret (Secret): The secret instance that is ready.

Example::

    secret_ready.send(sender=self.__class__, secret=self)
"""


secret_deleted = Signal()
"""
Signal sent when a secret is deleted.

Arguments:
    secret (Secret): The deleted secret instance.

Example::

    secret_deleted.send(sender=self.__class__, secret=self)
"""

secret_accessed = Signal()
"""
Signal sent when a secret is accessed.

Arguments:
    secret (Secret): The accessed secret instance.
    user_profile (UserProfile): The profile of the user who accessed the secret.

Example::

    secret_accessed.send(sender=self.__class__, secret=self, user_profile=self.user_profile)
"""
