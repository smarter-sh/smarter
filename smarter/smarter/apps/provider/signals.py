# pylint: disable=W0613,C0115
"""Signals for Provider app."""

from django.dispatch import Signal

model_verification_requested = Signal()
model_verification_success = Signal()
model_verification_failure = Signal()

provider_verification_requested = Signal()
provider_verification_success = Signal()
provider_verification_failure = Signal()

provider_suspended = Signal()
provider_unsuspended = Signal()

provider_deprecated = Signal()
provider_undeprecated = Signal()

provider_activated = Signal()
provider_deactivated = Signal()

provider_flagged = Signal()
provider_unflagged = Signal()

embed_started = Signal()
"""
Signal sent when embedding starts.

Arguments:
    sender (type): The sender of the signal, typically the class initiating the embedding.
    backend (SmarterVectorstoreBackend): The backend being used for embedding.
    provider (Provider): The provider associated with the vectorstore.
    user_profile (UserProfile): The profile of the user associated with the embedding.

Example::

    embed_started.send(sender=self.__class__, backend=backend, provider=provider, user_profile=user_profile)
"""

embed_success = Signal()
"""
Signal sent when embedding completes successfully.

Arguments:
    sender (type): The sender of the signal, typically the class initiating the embedding.
    backend (SmarterVectorstoreBackend): The backend being used for embedding.
    provider (Provider): The provider associated with the vectorstore.
    user_profile (UserProfile): The profile of the user associated with the embedding.

Example::

    embed_success.send(sender=self.__class__, backend=backend, provider=provider, user_profile=user_profile)
"""

embed_failed = Signal()
"""
Signal sent when embedding fails.

Arguments:
    sender (type): The sender of the signal, typically the class initiating the embedding.
    backend (SmarterVectorstoreBackend): The backend being used for embedding.
    provider (Provider): The provider associated with the vectorstore.
    user_profile (UserProfile): The profile of the user associated with the embedding.

Example::

    embed_failed.send(sender=self.__class__, backend=backend, provider=provider, user_profile=user_profile)
"""
