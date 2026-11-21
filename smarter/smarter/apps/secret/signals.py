"""
Signals of the secret app.

The Secret model sends ``secret_created``, ``secret_edited`` and ``secret_accessed``, whichever
code saves or reads it. The SecretTransformer, which applies a Secret's manifest, sends the others.
"""

from django.dispatch import Signal

secret_initializing = Signal()
"""
Signal sent when a secret is initializing.

Arguments:
    secret_name (str): The name of the secret being initialized.
    user_profile (UserProfile): The profile of the user associated with the secret.

Example::

    secret_initializing.send(sender=self.__class__, secret_name=name, user_profile=user_profile)
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
    secret_id (int): The deleted secret's id.
    secret_name (str): The deleted secret's name.

Example::

    secret_deleted.send(sender=self.__class__, secret_id=secret_id, secret_name=secret_name)
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

secret_saved = Signal()
"""
Signal sent when a secret is saved.

Arguments:
    secret (Secret): The saved secret instance.
    user_profile (UserProfile): The profile of the user who saved the secret.

Example::

    secret_saved.send(sender=self.__class__, secret=self, user_profile=self.user_profile)
"""

secret_updated = Signal()
"""
Signal sent when a secret is updated.

Arguments:
    secret (Secret): The updated secret instance.
    user_profile (UserProfile): The profile of the user who updated the secret.

Example::

    secret_updated.send(sender=self.__class__, secret=self, user_profile=self.user_profile)
"""

broker_ready = Signal()
"""
Signal sent when a broker achieves a ready state.

Arguments:
    broker: The broker instance that is ready.

Example::

    # a broker sends it once, from its ready property
    self.send_broker_ready(broker_ready)
"""
