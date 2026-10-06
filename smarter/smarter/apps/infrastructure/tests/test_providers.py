"""Test the provider registry, :mod:`smarter.apps.infrastructure.providers`, the facade, and the in-memory provider."""

from unittest.mock import patch

from smarter.apps.infrastructure import providers
from smarter.apps.infrastructure.const import CloudProviders
from smarter.apps.infrastructure.exceptions import (
    InfrastructureConfigurationError,
    InfrastructureNotReadyError,
)
from smarter.apps.infrastructure.providers import (
    configure_provider,
    get_provider,
    register_provider,
    registered_providers,
)
from smarter.apps.infrastructure.providers.aws import AWSProvider
from smarter.apps.infrastructure.providers.memory import InMemoryProvider
from smarter.apps.infrastructure.services import infrastructure
from smarter.apps.infrastructure.signals import (
    infrastructure_authenticated,
    infrastructure_authentication_failed,
)

from .base import InfrastructureTestBase

PROVIDERS = "smarter.apps.infrastructure.providers"


class TestProviderRegistry(InfrastructureTestBase):
    """Test that smarter_settings.cloud_provider selects a registered provider."""

    def setUp(self):
        super().setUp()
        configure_provider(None)

    def test_registered_providers(self):
        self.assertIn(CloudProviders.AWS, registered_providers())
        self.assertIn(CloudProviders.MEMORY, registered_providers())

    def test_selected_by_setting(self):
        with patch(f"{PROVIDERS}.smarter_settings") as settings:
            settings.cloud_provider = "memory"
            provider = get_provider()
            self.assertIsInstance(provider, InMemoryProvider)
            self.assertIs(get_provider(), provider)
        configure_provider(None)
        with patch(f"{PROVIDERS}.smarter_settings") as settings:
            settings.cloud_provider = "aws"
            self.assertIsInstance(get_provider(), AWSProvider)

    def test_unsupported_provider(self):
        with patch(f"{PROVIDERS}.smarter_settings") as settings:
            settings.cloud_provider = "azure"
            with self.assertRaises(InfrastructureConfigurationError) as context:
                get_provider()
        self.assertIn("azure", str(context.exception))

    def test_register_provider(self):
        """A new cloud is a new registered provider, not a change to the platform."""
        register_provider("test-cloud", InMemoryProvider)
        self.addCleanup(providers._registry.pop, "test-cloud", None)  # pylint: disable=protected-access
        with patch(f"{PROVIDERS}.smarter_settings") as settings:
            settings.cloud_provider = "test-cloud"
            self.assertIsInstance(get_provider(), InMemoryProvider)

    def test_configure_provider(self):
        provider = InMemoryProvider()
        configure_provider(lambda: provider)
        self.assertIs(get_provider(), provider)
        self.assertIs(infrastructure.provider, provider)


class TestFacade(InfrastructureTestBase):
    """Test that the facade gives the configured provider's services."""

    def test_services(self):
        self.assertIs(infrastructure.provider, self.provider)
        self.assertTrue(infrastructure.ready)
        self.assertIs(infrastructure.dns, self.provider.dns)
        self.assertIs(infrastructure.certificates, self.provider.certificates)
        self.assertIs(infrastructure.kubernetes.provider, self.provider)
        self.provider.ready = False
        self.assertFalse(infrastructure.ready)


class TestInMemoryProvider(InfrastructureTestBase):
    """Test the in-memory provider, and the authentication signals of every provider."""

    def test_identity(self):
        self.assertEqual(self.provider.name, CloudProviders.MEMORY)
        self.assertEqual(self.provider.account_id, "000000000000")
        self.assertEqual(self.provider.sdk_version, "memory")
        self.assertEqual(self.provider.get_kubernetes_cluster_info()["status"], "ACTIVE")
        self.assertTrue(self.provider.update_kubeconfig())
        self.assertEqual(str(self.provider), "memory.provider")

    def test_not_ready(self):
        self.provider.ready = False
        self.assertIsNone(self.provider.identity)
        self.assertIsNone(self.provider.account_id)
        self.assertFalse(self.provider.update_kubeconfig())
        with self.assertRaises(InfrastructureNotReadyError):
            self.provider.get_kubernetes_cluster_info()

    def test_authentication_signals_on_change(self):
        """Authentication is announced when it changes, rather than on every check."""
        events = self.capture(infrastructure_authenticated, infrastructure_authentication_failed)
        provider = InMemoryProvider()
        for _ in range(3):
            self.assertTrue(provider.ready)
        provider.ready = False
        for _ in range(3):
            self.assertFalse(provider.ready)
        provider.ready = True
        self.assertTrue(provider.ready)
        self.assertEqual(
            [signal for signal, _ in events],
            [infrastructure_authenticated, infrastructure_authentication_failed, infrastructure_authenticated],
        )
        self.assertEqual(self.sent(events, infrastructure_authenticated)[0]["identity"]["Account"], "000000000000")
