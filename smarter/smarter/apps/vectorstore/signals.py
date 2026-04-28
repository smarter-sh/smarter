"""
Signals for the vectorstore app.
"""

from django.dispatch import Signal

load_started = Signal()
"""
Signal sent when vectorstore loading starts.

Arguments:
    sender (type): The sender of the signal, typically the class initiating the load.
    backend (SmarterVectorstoreBackend): The backend being used for loading.
    provider (Provider): The provider associated with the vectorstore.
    user_profile (UserProfile): The profile of the user associated with the load.

Example::

    load_started.send(sender=self.__class__, backend=backend, provider=provider, user_profile=user_profile)
"""

load_success = Signal()
"""
Signal sent when vectorstore loading completes.

Arguments:
    sender (type): The sender of the signal, typically the class initiating the load.
    backend (SmarterVectorstoreBackend): The backend being used for loading.
    provider (Provider): The provider associated with the vectorstore.
    user_profile (UserProfile): The profile of the user associated with the load.

Example::

    load_success.send(sender=self.__class__, backend=backend, provider=provider, user_profile=user_profile)
"""

load_failed = Signal()
"""
Signal sent when vectorstore loading fails.

Arguments:
    sender (type): The sender of the signal, typically the class initiating the load.
    backend (SmarterVectorstoreBackend): The backend being used for loading.
    provider (Provider): The provider associated with the vectorstore.
    user_profile (UserProfile): The profile of the user associated with the load.

Example::

    load_failed.send(sender=self.__class__, backend=backend, provider=provider, user_profile=user_profile)
"""

connected = Signal()
"""
Signal sent when a connection to the vector store backend is established.

Arguments:
    sender (type): The sender of the signal, typically the class initiating the load.
    instance (VectorStoreBackendConnection): The instance of the connection that was established.
    connection (object): The underlying connection object   .

Example::

    connected.send(sender=self.__class__, backend=backend, provider=provider, user_profile=user_profile)
"""
