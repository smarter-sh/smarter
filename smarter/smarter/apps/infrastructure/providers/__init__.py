"""
The cloud providers, and the one that the platform uses.

``smarter_settings.cloud_provider`` (``SMARTER_CLOUD_PROVIDER``) names the provider, e.g.
``aws``, and :func:`get_provider` returns it. Tests replace it with :func:`configure_provider`:

.. code-block:: python

    from smarter.apps.infrastructure.providers import configure_provider
    from smarter.apps.infrastructure.providers.memory import InMemoryProvider

    configure_provider(InMemoryProvider)
    ...
    configure_provider(None)
"""

from typing import Callable, Optional

from smarter.common.conf import smarter_settings

from ..const import CloudProviders
from ..exceptions import InfrastructureConfigurationError
from .aws import AWSProvider
from .base import CloudProvider
from .memory import InMemoryProvider

ProviderFactory = Callable[[], CloudProvider]

_registry: dict[str, ProviderFactory] = {}
_provider_factory: Optional[ProviderFactory] = None
_provider: Optional[CloudProvider] = None


def register_provider(name: str, factory: ProviderFactory) -> None:
    """
    Register a cloud provider under its name, so that ``smarter_settings.cloud_provider`` can select it.

    :param name: The provider's name, see :class:`~smarter.apps.infrastructure.const.CloudProviders`.
    :param factory: Returns the provider, e.g. its class.
    """
    _registry[str(name)] = factory


def registered_providers() -> list[str]:
    """The names of the registered providers."""
    return sorted(_registry)


def configure_provider(factory: Optional[ProviderFactory]) -> None:
    """
    Use another provider, e.g. a fake in tests.

    :param factory: Returns the provider, or None to restore ``smarter_settings.cloud_provider``.
    """
    global _provider_factory, _provider  # pylint: disable=global-statement
    _provider_factory = factory
    _provider = None


def get_provider() -> CloudProvider:
    """
    Return the cloud provider, which is created once.

    :raises InfrastructureConfigurationError: If ``smarter_settings.cloud_provider`` is not registered.
    """
    global _provider  # pylint: disable=global-statement
    if _provider is None:
        if _provider_factory is not None:
            _provider = _provider_factory()
        else:
            name = str(smarter_settings.cloud_provider)
            factory = _registry.get(name)
            if factory is None:
                raise InfrastructureConfigurationError(
                    f"Cloud provider {name} is not supported. Supported providers: {', '.join(registered_providers())}"
                )
            _provider = factory()
    return _provider


register_provider(CloudProviders.AWS, AWSProvider)
register_provider(CloudProviders.MEMORY, InMemoryProvider)


__all__ = [
    "CloudProvider",
    "configure_provider",
    "get_provider",
    "register_provider",
    "registered_providers",
]
