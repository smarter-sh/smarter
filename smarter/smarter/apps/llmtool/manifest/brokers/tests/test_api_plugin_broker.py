# pylint: disable=wrong-import-position
"""Test SAMApiPluginBroker."""

import copy
import os

import yaml
from pydantic_core import ValidationError

from smarter.apps.api.utils import apply_manifest
from smarter.apps.connection.models import ApiConnection
from smarter.apps.llmtool.manifest.brokers.api_plugin import SAMApiPluginBroker
from smarter.apps.llmtool.manifest.models.api_plugin.model import SAMApiPlugin
from smarter.apps.llmtool.manifest.models.api_plugin.spec import SAMApiPluginSpec
from smarter.apps.llmtool.models import (
    PluginDataApi,
    PluginMeta,
    PluginPrompt,
    PluginSelector,
)
from smarter.apps.llmtool.plugin.api import ApiPlugin
from smarter.common.exceptions import SmarterValueError
from smarter.lib import json, logging
from smarter.lib.manifest.broker import (
    SAMBrokerErrorNotImplemented,
)
from smarter.lib.manifest.parsing import read_manifest_file
from smarter.lib.typing import required

from .base_classes.connection_base import TestSmarterConnectionBrokerBase
from .base_classes.edge_cases import PluginBrokerEdgeCasesMixin

logger = logging.getSmarterLogger(__name__)
HERE = os.path.abspath(os.path.dirname(__file__))
MANIFEST_PATH_API_CONNECTION = os.path.join(HERE, "data", "api-connection-broker.yaml")
"""ApiConnection manifest whose name matches spec.connection in data/api-plugin.yaml."""


class TestSmarterApiPluginBroker(PluginBrokerEdgeCasesMixin, TestSmarterConnectionBrokerBase):
    """Test the Smarter SAMApiPluginBroker."""

    plugin_class = ApiPlugin
    broker_module = "smarter.apps.llmtool.manifest.brokers.api_plugin"
    apply_builds_plugin = True
    orm_spec_method = "plugin_api_spec_orm2pydantic"
    api_connection: ApiConnection

    @classmethod
    def setUpClass(cls):
        """Create the ApiConnection that the ApiPlugin manifest refers to."""
        super().setUpClass()
        manifest_data = read_manifest_file(MANIFEST_PATH_API_CONNECTION)
        if not apply_manifest(username=cls.admin_user.username, manifest=yaml.safe_dump(manifest_data), verbose=True):
            raise SmarterValueError("Failed to apply the test ApiConnection manifest.")
        manifest_metadata = required(manifest_data["metadata"], "manifest_data.metadata")
        cls.api_connection = ApiConnection.objects.get(
            user_profile=cls.user_profile, name=manifest_metadata.get("name")
        )

    @classmethod
    def tearDownClass(cls):
        """Delete the plugin and the ApiConnection."""
        PluginMeta.objects.filter(user_profile=cls.user_profile, name="api_test").delete()
        cls.api_connection.delete()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self._here = HERE
        self._broker_class = SAMApiPluginBroker
        self._manifest_filespec = self.get_data_full_filepath("api-plugin.yaml")

    @property
    def SAMBrokerClass(self) -> type[SAMApiPluginBroker]:
        return SAMApiPluginBroker

    @property
    def broker(self) -> SAMApiPluginBroker:
        return super().broker  # type: ignore

    def apply_manifest(self):
        """Apply the ApiPlugin manifest and verify the response."""
        response = self.broker.apply(self.request, **self.kwargs)
        self.assertTrue(self.validate_smarter_journaled_json_response_ok(response))
        self.assertTrue(self.validate_apply(response))
        return response

    def test_broker_properties(self):
        """Test the broker's class and descriptive properties."""
        self.assertTrue(self.ready)
        self.assertEqual(self.broker.kind, "ApiPlugin")
        self.assertIs(self.broker.ORMModelClass, PluginDataApi)
        self.assertIs(self.broker.SAMModelClass, SAMApiPlugin)
        self.assertIn("SAMApiPluginBroker", self.broker.formatted_class_name)
        self.assertTrue(self.broker.is_valid)
        self.assertIsInstance(json.loads(json.dumps(self.broker.to_json())), dict)

    def test_manifest(self):
        """Test that the manifest property returns an immutable SAMApiPlugin."""
        manifest = self.broker.manifest
        self.assertIsInstance(manifest, SAMApiPlugin)
        assert manifest is not None
        self.assertEqual(manifest.spec.connection, "test_api_connection")
        with self.assertRaises(ValidationError):
            # a frozen model's field, which mypy refuses to assign; the test checks that it fails at runtime too.
            manifest.metadata.name = "NewManifestName"  # type: ignore[misc]
        self.assertIsInstance(SAMApiPlugin(**manifest.model_dump()), SAMApiPlugin)
        broker = self.SAMBrokerClass(self.request, manifest)
        self.assertIsInstance(broker, SAMApiPluginBroker)

    def test_example_manifest(self):
        """Test the example_manifest() generates a valid manifest response."""
        response = self.broker.example_manifest(self.request)
        self.assertTrue(self.validate_smarter_journaled_json_response_ok(response))
        self.assertTrue(self.validate_example_manifest(response))

    def test_apply(self):
        """Test that apply() persists the plugin, its data and its connection."""
        self.apply_manifest()
        plugin = self.broker.plugin
        self.assertIsInstance(plugin, ApiPlugin)
        assert plugin is not None
        self.assertTrue(plugin.ready)
        manifest = self.broker.manifest
        plugin_meta = self.broker.plugin_meta
        assert manifest is not None
        assert plugin_meta is not None
        self.assertEqual(plugin.name, manifest.metadata.name)
        self.assertEqual(set(manifest.metadata.tags or []), set(plugin_meta.tags_list))

        plugin_data = self.broker.plugin_data
        self.assertIsInstance(plugin_data, PluginDataApi)
        assert plugin_data is not None
        self.assertEqual(plugin_data.endpoint, manifest.spec.apiData.endpoint)
        self.assertEqual(plugin_data.connection, self.api_connection)

    def test_orm2pydantic(self):
        """Test that the persisted plugin converts back to its Pydantic spec."""
        self.apply_manifest()
        spec = self.broker.plugin_api_spec_orm2pydantic()
        self.assertIsInstance(spec, SAMApiPluginSpec)
        manifest = self.broker.manifest
        assert spec is not None
        assert manifest is not None
        self.assertEqual(spec.connection, manifest.spec.connection)
        self.assertEqual(spec.apiData.endpoint, manifest.spec.apiData.endpoint)
        api_data = self.broker.plugin_data_orm2pydantic()
        assert api_data is not None
        self.assertEqual(api_data.endpoint, manifest.spec.apiData.endpoint)
        self.assertEqual(
            {p.name for p in api_data.parameters or []},
            {p.name for p in manifest.spec.apiData.parameters or []},
        )

    def test_get_and_describe(self):
        """Test the get() and describe() methods return valid responses."""
        self.apply_manifest()
        response = self.broker.get(self.request, **self.kwargs)
        self.assertTrue(self.validate_smarter_journaled_json_response_ok(response))
        self.assertTrue(self.validate_get(response))

        response = self.broker.describe(self.request, **self.kwargs)
        self.assertTrue(self.validate_smarter_journaled_json_response_ok(response))
        data = json.loads(response.content.decode())
        self.assertIn("data", data)

    def test_delete(self):
        """Test that delete() removes the plugin."""
        self.apply_manifest()
        broker = self.SAMBrokerClass(self.request, manifest=self.manifest_data)
        response = broker.delete(self.request, **self.kwargs)
        self.assertTrue(self.validate_smarter_journaled_json_response_ok(response))
        self.assertFalse(PluginMeta.objects.filter(user_profile=self.user_profile, name="api_test").exists())

    def renamed_manifest(self, name: str, drop_test_value: str = "") -> dict:
        """
        Return this test's manifest with another name, and optionally without one of its test values.

        A plugin whose parameter has no test value fails to apply: its data doesn't validate.

        :param name: The plugin's name.
        :param drop_test_value: The name of a parameter whose test value to leave out.
        :returns: The manifest, as a dict.
        """
        manifest_data = copy.deepcopy(self.manifest_data)
        manifest_data["metadata"]["name"] = name
        api_data = manifest_data["spec"]["apiData"]
        kept = []
        for test_value in api_data["testValues"]:
            if test_value["name"] != drop_test_value:
                kept.append(test_value)
        api_data["testValues"] = kept
        self.addCleanup(PluginMeta.objects.filter(user_profile=self.user_profile, name=name).delete)
        return manifest_data

    def assert_plugin_is_complete(self, name: str) -> None:
        """Assert that the plugin named ``name`` has its selector, prompt and data, and is ready."""
        plugin_meta = PluginMeta.objects.get(user_profile=self.user_profile, name=name)
        self.assertTrue(PluginSelector.objects.filter(plugin=plugin_meta).exists())
        self.assertTrue(PluginPrompt.objects.filter(plugin=plugin_meta).exists())
        self.assertTrue(PluginDataApi.objects.filter(plugin=plugin_meta).exists())
        plugin = ApiPlugin(plugin_meta=plugin_meta, user_profile=self.user_profile)
        self.assertTrue(plugin.ready)

    def test_failed_apply_leaves_nothing_behind(self):
        """A manifest that fails to apply leaves no PluginMeta, so applying it again, fixed, makes a whole plugin."""
        name = f"api_test_failed_apply_{self.hash_suffix}"
        broken = self.renamed_manifest(name, drop_test_value="limit")
        response = self.SAMBrokerClass(self.request, manifest=broken).apply(self.request)
        self.assertNotEqual(response.status_code, 200)
        self.assertFalse(PluginMeta.objects.filter(user_profile=self.user_profile, name=name).exists())

        fixed = self.renamed_manifest(name)
        response = self.SAMBrokerClass(self.request, manifest=fixed).apply(self.request)
        self.assertTrue(self.validate_smarter_journaled_json_response_ok(response))
        self.assert_plugin_is_complete(name)

    def test_apply_repairs_a_plugin_without_its_selector_and_prompt(self):
        """Applying a manifest restores a selector and prompt that the database lost, even if the cache still has them."""
        name = f"api_test_repair_{self.hash_suffix}"
        manifest_data = self.renamed_manifest(name)
        self.SAMBrokerClass(self.request, manifest=manifest_data).apply(self.request)
        plugin_meta = PluginMeta.objects.get(user_profile=self.user_profile, name=name)
        # cache both rows, then delete them without going through save() or delete(), so that the
        # cache keeps rows that the database no longer has, as a rolled-back apply used to leave it.
        PluginSelector.get_cached_selector_by_plugin(plugin_meta)
        PluginPrompt.get_cached_prompt_by_plugin(plugin_meta)
        PluginSelector.objects.filter(plugin=plugin_meta)._raw_delete(PluginSelector.objects.db)
        PluginPrompt.objects.filter(plugin=plugin_meta)._raw_delete(PluginPrompt.objects.db)

        response = self.SAMBrokerClass(self.request, manifest=manifest_data).apply(self.request)
        self.assertTrue(self.validate_smarter_journaled_json_response_ok(response))
        self.assert_plugin_is_complete(name)

    def test_delete_a_plugin_without_its_selector_and_prompt(self):
        """A plugin that isn't ready, because its selector and prompt are missing, can still be deleted."""
        name = f"api_test_delete_incomplete_{self.hash_suffix}"
        manifest_data = self.renamed_manifest(name)
        self.SAMBrokerClass(self.request, manifest=manifest_data).apply(self.request)
        plugin_meta = PluginMeta.objects.get(user_profile=self.user_profile, name=name)
        PluginSelector.objects.filter(plugin=plugin_meta).delete()
        PluginPrompt.objects.filter(plugin=plugin_meta).delete()

        broker = self.SAMBrokerClass(self.request, manifest=manifest_data)
        response = broker.delete(self.request, **self.kwargs)
        self.assertTrue(self.validate_smarter_journaled_json_response_ok(response))
        self.assertFalse(PluginMeta.objects.filter(pk=plugin_meta.pk).exists())
        self.assertFalse(PluginDataApi.objects.filter(plugin_id=plugin_meta.pk).exists())

    def test_not_implemented(self):
        """Test that deploy(), undeploy(), prompt() and logs() are not implemented."""
        for method in (self.broker.deploy, self.broker.undeploy, self.broker.prompt, self.broker.logs):
            with self.assertRaises(SAMBrokerErrorNotImplemented):
                method(self.request, **self.kwargs)
