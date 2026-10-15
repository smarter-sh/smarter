"""Test the guard and failure branches of the Provider manifest broker, called directly with its properties replaced."""

import copy
from contextlib import ExitStack
from unittest.mock import MagicMock, PropertyMock, patch

from django.test import RequestFactory

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.account.utils import smarter_cached_objects
from smarter.apps.llmtool.manifest.models.static_plugin.model import SAMStaticPlugin
from smarter.apps.llmtool.models import PluginMeta, PluginPrompt
from smarter.apps.llmtool.plugin.static import StaticPlugin
from smarter.apps.llmtool.tests.base_classes import get_test_data
from smarter.apps.provider.manifest.brokers.provider import (
    SAMProviderBroker,
    SAMProviderBrokerError,
)
from smarter.apps.provider.manifest.models.provider.model import SAMProvider
from smarter.apps.provider.models import Provider
from smarter.lib.manifest.broker import (
    SAMBrokerError,
    SAMBrokerErrorNotFound,
    SAMBrokerErrorNotImplemented,
    SAMDependencyReference,
)


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

    # -------------------------------------------------------------------------
    # a dependent resource whose stored data no longer validates
    # -------------------------------------------------------------------------
    def create_plugin_with_a_removed_model(self, provider: Provider) -> PluginMeta:
        """A StaticPlugin that uses this provider, and whose stored model is no longer a valid model."""
        name = f"test_provider_broken_plugin_{self.hash_suffix}"
        data = copy.deepcopy(get_test_data("static-plugin.yaml"))
        data["metadata"]["name"] = name
        plugin = StaticPlugin(manifest=SAMStaticPlugin(**data), user_profile=self.user_profile)
        self.assertTrue(plugin.ready)
        self.addCleanup(PluginMeta.objects.filter(name=name, user_profile=self.user_profile).delete)
        plugin_meta = PluginMeta.objects.get(name=name, user_profile=self.user_profile)
        # bypass validation, as when a model is later removed from the list of valid models.
        PluginPrompt.objects.filter(plugin=plugin_meta).update(provider=provider.name, model="gpt-4-turbo")
        PluginPrompt.get_cached_prompt_by_plugin(plugin=plugin_meta, invalidate=True)
        return plugin_meta

    def test_describe_with_a_dependent_that_no_longer_validates(self):
        """A plugin whose stored model is no longer valid neither breaks describe nor allows delete."""
        provider = self.create_provider()
        plugin_meta = self.create_plugin_with_a_removed_model(provider)
        broker = SAMProviderBroker(request=self.request, kind="Provider", name=provider.name)

        dependencies = broker.dependencies()
        self.assertEqual(len(dependencies), 1)
        self.assertIsInstance(dependencies[0], SAMDependencyReference)
        self.assertEqual(dependencies[0].name, plugin_meta.name)
        self.assertEqual(dependencies[0].account, self.account)

        response = broker.describe(self.request, name=provider.name)
        self.assertEqual(response.status_code, 200)
        self.assertIn(plugin_meta.name, response.content.decode())

        with self.assertRaises(SAMBrokerError) as ctx:
            broker.verify_no_dependencies()
        self.assertIn(plugin_meta.name, str(ctx.exception))

    # -------------------------------------------------------------------------
    # describe a provider that another account owns
    # -------------------------------------------------------------------------
    def test_describe_a_built_in_provider(self):
        """A user may describe a built-in Provider, which the Smarter admin's account owns."""
        request = RequestFactory().get("/api/v1/cli/describe/Provider/?name=openai")
        request.user = self.non_admin_user
        broker = SAMProviderBroker(request=request, kind="Provider")
        built_in = Provider.objects.get(name="openai", user_profile=smarter_cached_objects.smarter_admin_user_profile)
        self.assertNotEqual(broker.account, built_in.user_profile.account)
        response = broker.describe(request, name="openai")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(broker.provider, built_in)

    def test_describe_an_unknown_provider(self):
        with self.assertRaises(SAMBrokerErrorNotFound):
            self.broker().describe(self.request, name=f"no_such_provider_{self.hash_suffix}")
