"""Test SAMLLMClientBroker's not-found, not-ready and failure branches."""

import os
from unittest.mock import MagicMock, PropertyMock, patch

from smarter.apps.llmclient.manifest.brokers.llmclient import (
    SAMLLMClientBroker,
    SAMLLMClientBrokerError,
)
from smarter.apps.llmclient.models import LLMClient, LLMClientAPIKey
from smarter.lib.manifest.broker import SAMBrokerErrorNotReady
from smarter.lib.manifest.tests.test_broker_base import TestSAMBrokerBaseClass

LIFECYCLE_COMMANDS = ("describe", "delete", "deploy", "undeploy")
MODULE = "smarter.apps.llmclient.manifest.brokers.llmclient"


class TestSAMLLMClientBrokerBranches(TestSAMBrokerBaseClass):
    """Test the SAMLLMClientBroker branches that the happy-path broker tests don't reach."""

    def setUp(self):
        super().setUp()
        self._broker_class = SAMLLMClientBroker
        self._here = os.path.abspath(os.path.dirname(__file__))
        self._manifest_filespec = self.get_data_full_filepath("llm_client.yaml")

    @property
    def SAMBrokerClass(self) -> type[SAMLLMClientBroker]:
        return SAMLLMClientBroker

    @property
    def broker(self) -> SAMLLMClientBroker:
        return super().broker  # type: ignore

    def patch_property(self, name: str, value) -> PropertyMock:
        patcher = patch.object(SAMLLMClientBroker, name, new_callable=PropertyMock, return_value=value)
        mock = patcher.start()
        self.addCleanup(patcher.stop)
        return mock

    def patch_method(self, broker, name: str, **kwargs) -> MagicMock:
        patcher = patch.object(broker, name, **kwargs)
        mock = patcher.start()
        self.addCleanup(patcher.stop)
        return mock

    def test_lifecycle_commands_need_a_name(self):
        """Describe, delete, deploy and undeploy aren't ready without a name."""
        broker = self.broker
        self.patch_property("name", None)
        for command in LIFECYCLE_COMMANDS:
            with self.subTest(command=command), self.assertRaises(SAMBrokerErrorNotReady):
                getattr(broker, command)(self.request)

    def test_lifecycle_commands_need_an_llmclient(self):
        """Describe, delete, deploy and undeploy aren't ready when the LLMClient doesn't exist."""
        broker = self.broker
        self.patch_property("name", "no_such_llmclient")
        self.patch_property("llmclient", None)
        self.patch_method(broker, "verify_no_dependencies")
        for command in LIFECYCLE_COMMANDS:
            with self.subTest(command=command), self.assertRaises(SAMBrokerErrorNotReady):
                getattr(broker, command)(self.request)

    def test_lifecycle_command_failures(self):
        """A failure in describe, delete, deploy or undeploy is reported as SAMLLMClientBrokerError."""
        broker = self.broker
        llmclient = MagicMock(spec=LLMClient)
        llmclient.save.side_effect = RuntimeError("save failed")
        llmclient.delete.side_effect = RuntimeError("delete failed")
        self.patch_property("name", "failing_llmclient")
        self.patch_property("llmclient", llmclient)
        self.patch_method(broker, "verify_no_dependencies")
        self.patch_method(broker, "cache_invalidations")
        self.patch_method(broker, "django_orm_to_manifest_dict", side_effect=RuntimeError("dump failed"))
        for command in LIFECYCLE_COMMANDS:
            with self.subTest(command=command), self.assertRaises(SAMLLMClientBrokerError):
                getattr(broker, command)(self.request)

    def test_deploy_and_undeploy(self):
        """Deploy and undeploy set the LLMClient's deployed flag."""
        broker = self.broker
        llmclient = MagicMock(spec=LLMClient)
        self.patch_property("name", "deployable_llmclient")
        self.patch_property("llmclient", llmclient)
        self.assertEqual(broker.deploy(self.request).status_code, 200)
        self.assertTrue(llmclient.deployed)
        self.assertEqual(broker.undeploy(self.request).status_code, 200)
        self.assertFalse(llmclient.deployed)
        self.assertEqual(llmclient.save.call_count, 2)

    def test_without_an_llmclient(self):
        """Without an LLMClient there are no functions, plugins, api key or manifest dict."""
        broker = self.broker
        self.patch_property("llmclient", None)
        self.assertIsNone(broker.functions)
        self.assertIsNone(broker.plugins)
        self.assertIsNone(broker.django_orm_to_manifest_dict())

    def test_llmclient_api_key_not_found(self):
        """An LLMClient without an api key has none."""
        broker = self.broker
        self.patch_property("llmclient", None)
        self.assertIsNone(broker.llmclient_api_key)

    def test_django_orm_to_manifest_dict_needs_an_account_and_user_profile(self):
        """The ORM-to-manifest conversion needs an account and a user profile."""
        broker = self.broker
        with patch.object(SAMLLMClientBroker, "account", new_callable=PropertyMock, return_value=None):
            with self.assertRaises(SAMBrokerErrorNotReady):
                broker.django_orm_to_manifest_dict()
        with patch.object(SAMLLMClientBroker, "user_profile", new_callable=PropertyMock, return_value=None):
            with self.assertRaises(SAMBrokerErrorNotReady):
                broker.django_orm_to_manifest_dict()

    def test_manifest_required(self):
        """The manifest-to-ORM conversion and apply() need a manifest."""
        broker = self.broker
        self.patch_property("manifest", None)
        with self.assertRaises(SAMBrokerErrorNotReady):
            broker.manifest_to_django_orm()
        with self.assertRaises(SAMBrokerErrorNotReady):
            broker.apply(self.request)

    def test_manifest_of_the_wrong_type(self):
        """A cached manifest that isn't a SAMLLMClient is rejected."""
        broker = self.broker
        broker._manifest = {"kind": "LLMClient"}  # type: ignore[assignment]
        with self.assertRaises(SAMLLMClientBrokerError):
            _ = broker.manifest

    def test_resolvers_need_a_user_profile(self):
        """Guardrails and MCP clients can't be resolved without a user profile."""
        broker = self.broker
        self.patch_property("user_profile", None)
        self.assertIsNone(broker.resolve_guardrail("any"))
        self.assertIsNone(broker.resolve_mcpclient("any"))

    def test_get_serialization_failure(self):
        """A failure to serialize one of the account's LLMClients is reported as SAMLLMClientBrokerError."""
        llmclient = LLMClient.objects.create(
            name=f"test_get_failure_{self.hash_suffix}", user_profile=self.user_profile
        )
        self.addCleanup(LLMClient.objects.filter(pk=llmclient.pk).delete)
        broker = self.broker
        with patch(
            "smarter.apps.llmclient.manifest.brokers.llmclient.LLMClientSerializer", side_effect=RuntimeError("broken")
        ):
            with self.assertRaises(SAMLLMClientBrokerError):
                broker.get(self.request, name=llmclient.name)

    def test_cached_functions_plugins_and_api_key(self):
        broker = self.broker
        broker._functions = ["calculator"]
        broker._plugins = ["a_plugin"]
        api_key = MagicMock()
        broker._llmclient_api_key = api_key
        self.assertEqual(broker.functions, ["calculator"])
        self.assertEqual(broker.plugins, ["a_plugin"])
        self.assertIs(broker.llmclient_api_key, api_key)
        broker._llmclient_api_key = None
        found = MagicMock()
        with patch.object(LLMClientAPIKey.objects, "get", return_value=found):
            self.assertIs(broker.llmclient_api_key, found)

    def test_django_orm_to_manifest_dict_that_is_not_a_dict(self):
        broker = self.broker
        self.patch_property("llmclient", MagicMock(spec=LLMClient))
        with (
            patch(f"{MODULE}.model_to_dict", return_value={}),
            patch.object(SAMLLMClientBroker, "to_camel_case", return_value="not a dict"),
        ):
            with self.assertRaises(SAMLLMClientBrokerError):
                broker.django_orm_to_manifest_dict()

    def test_manifest_from_an_existing_llmclient(self):
        broker = self.broker
        broker._manifest = None
        broker._llmclient = MagicMock(spec=LLMClient)
        self.patch_property("loader", None)
        manifest = MagicMock()
        with patch.object(SAMLLMClientBroker, "django_orm_to_manifest_dict", return_value=manifest):
            self.assertIs(broker.manifest, manifest)

    def test_get_with_an_empty_model_dump(self):
        llmclient = LLMClient.objects.create(name=f"test_get_empty_{self.hash_suffix}", user_profile=self.user_profile)
        self.addCleanup(LLMClient.objects.filter(pk=llmclient.pk).delete)
        with patch(f"{MODULE}.LLMClientSerializer", return_value=MagicMock(data={})):
            with self.assertRaises(SAMLLMClientBrokerError):
                self.broker.get(self.request, name=llmclient.name)

    def test_apply_guards(self):
        """Apply needs a ready broker, a manifest spec, and an LLMClient."""
        broker = self.broker
        with patch.object(SAMLLMClientBroker, "ready", new_callable=PropertyMock, return_value=False):
            with self.assertRaises(SAMBrokerErrorNotReady):
                broker.apply(self.request)
        manifest = MagicMock(spec=None)
        manifest.spec = None
        with patch.object(SAMLLMClientBroker, "manifest", new_callable=PropertyMock, return_value=manifest):
            with self.assertRaises(SAMBrokerErrorNotReady):
                broker.apply(self.request)
        with patch.object(SAMLLMClientBroker, "llmclient", new_callable=PropertyMock, return_value=None):
            with self.assertRaises(SAMLLMClientBrokerError):
                broker.apply(self.request)

    def test_manifest_to_django_orm_config_that_is_not_a_dict(self):
        broker = self.broker
        base_class = next(c for c in SAMLLMClientBroker.__mro__[1:] if "manifest_to_django_orm" in vars(c))
        with (
            patch.object(base_class, "manifest_to_django_orm", return_value={}),
            patch.object(SAMLLMClientBroker, "to_snake_case", return_value="not a dict"),
        ):
            with self.assertRaises(SAMLLMClientBrokerError):
                broker.manifest_to_django_orm()
