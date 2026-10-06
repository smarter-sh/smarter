"""Test the guard and failure branches of the Provider manifest broker, called directly with its properties replaced."""

from contextlib import ExitStack
from unittest.mock import MagicMock, PropertyMock, patch

from django.test import RequestFactory

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.provider.manifest.brokers.provider import (
    SAMProviderBroker,
    SAMProviderBrokerError,
)
from smarter.apps.provider.manifest.models.provider.model import SAMProvider
from smarter.apps.provider.models import Provider
from smarter.lib.manifest.broker import SAMBrokerErrorNotImplemented


class TestProviderBrokerBranches(TestAccountMixin):
    """Test SAMProviderBroker when its provider, manifest, user or params are missing or fail."""

    def setUp(self):
        super().setUp()
        self.provider_name = f"test_provider_broker_branches_{self.hash_suffix}"
        self.request = RequestFactory().get(f"/api/v1/cli/describe/Provider/?name={self.provider_name}")
        self.request.user = self.admin_user

    def broker(self, **properties) -> SAMProviderBroker:
        """A broker for this test's request, whose named properties return the given values."""
        broker = SAMProviderBroker(request=self.request, kind="Provider")
        stack = ExitStack()
        self.addCleanup(stack.close)
        for name, value in properties.items():
            stack.enter_context(patch.object(SAMProviderBroker, name, new_callable=PropertyMock, return_value=value))
        return broker

    def create_provider(self) -> Provider:
        provider = Provider.objects.create(
            name=self.provider_name, user_profile=self.user_profile, base_url="https://api.example.com/v1/"
        )
        self.addCleanup(Provider.objects.filter(pk=provider.pk).delete)
        return provider

    def test_logo_url_of_a_stored_logo(self):
        provider = MagicMock()
        provider.logo.name = "logos/provider.png"
        provider.logo.url = "/media/logos/provider.png"
        self.assertEqual(self.broker(provider=provider).logo_url, "/media/logos/provider.png")

    def test_manifest_to_django_orm_guards(self):
        base_class = next(c for c in SAMProviderBroker.__mro__[1:] if "manifest_to_django_orm" in vars(c))
        with patch.object(base_class, "manifest_to_django_orm", return_value={}):
            broker = self.broker()
            with patch.object(SAMProviderBroker, "manifest", new_callable=PropertyMock, return_value=MagicMock()):
                with self.assertRaises(SAMProviderBrokerError):
                    broker.manifest_to_django_orm()
            manifest = MagicMock(spec=SAMProvider)
            manifest.spec = MagicMock()
            manifest.metadata = MagicMock()
            with (
                patch.object(SAMProviderBroker, "manifest", new_callable=PropertyMock, return_value=manifest),
                patch.object(SAMProviderBroker, "to_snake_case", return_value="not a dict"),
            ):
                with self.assertRaises(SAMProviderBrokerError):
                    broker.manifest_to_django_orm()

    def test_django_orm_to_manifest_dict_needs_a_provider(self):
        with self.assertRaises(SAMProviderBrokerError):
            self.broker(provider=None).django_orm_to_manifest_dict()

    def test_invalid_manifest(self):
        broker = self.broker()
        broker._manifest = "not a manifest"  # type: ignore[assignment]
        with self.assertRaises(SAMProviderBrokerError):
            _ = broker.manifest

    def test_get_by_name_with_a_failed_model_dump(self):
        self.create_provider()
        with patch.object(SAMProviderBroker, "django_orm_to_manifest_dict", return_value=None):
            with self.assertRaises(SAMProviderBrokerError):
                self.broker().get(self.request, name=self.provider_name)

    def test_apply_needs_an_admin(self):
        broker = self.broker()
        for user in (None, MagicMock(is_staff=False)):
            with self.subTest(user=user):
                with patch.object(SAMProviderBroker, "user", new_callable=PropertyMock, return_value=user):
                    with self.assertRaises(SAMProviderBrokerError):
                        broker.apply(self.request)

    def test_prompt_is_not_implemented(self):
        with self.assertRaises(SAMBrokerErrorNotImplemented):
            self.broker().prompt(self.request)

    def test_describe_failure(self):
        self.create_provider()
        with patch.object(SAMProviderBroker, "django_orm_to_manifest_dict", side_effect=RuntimeError("broken")):
            with self.assertRaises(SAMProviderBrokerError):
                self.broker().describe(self.request, name=self.provider_name)

    def test_no_dependencies_without_a_provider(self):
        self.assertEqual(self.broker(provider=None).dependencies(), [])

    def test_delete_guards(self):
        broker = self.broker()
        for user in (None, MagicMock(is_staff=False)):
            with self.subTest(user=user):
                with patch.object(SAMProviderBroker, "user", new_callable=PropertyMock, return_value=user):
                    with self.assertRaises(SAMProviderBrokerError):
                        broker.delete(self.request)
        with patch.object(SAMProviderBroker, "params", new_callable=PropertyMock, return_value="not a dict"):
            with self.assertRaises(SAMBrokerErrorNotImplemented):
                broker.delete(self.request)

    def test_delete_failure(self):
        self.create_provider()
        with (
            patch.object(SAMProviderBroker, "verify_no_dependencies"),
            patch.object(Provider, "delete", side_effect=RuntimeError("database down")),
        ):
            with self.assertRaises(SAMProviderBrokerError):
                self.broker().delete(self.request)
