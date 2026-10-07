# pylint: disable=wrong-import-position
"""Test SAMApiPluginBroker."""

import os

from pydantic_core import ValidationError

from smarter.apps.api.utils import apply_manifest
from smarter.apps.connection.models import ApiConnection
from smarter.apps.plugin.manifest.brokers.api_plugin import SAMApiPluginBroker
from smarter.apps.plugin.manifest.models.api_plugin.model import SAMApiPlugin
from smarter.apps.plugin.manifest.models.api_plugin.spec import SAMApiPluginSpec
from smarter.apps.plugin.models import PluginDataApi, PluginMeta
from smarter.apps.plugin.plugin.api import ApiPlugin
from smarter.common.exceptions import SmarterValueError
from smarter.lib import json, logging
from smarter.lib.manifest.broker import (
    SAMBrokerErrorNotImplemented,
)
from smarter.lib.manifest.loader import SAMLoader

from .base_classes.connection_base import TestSmarterConnectionBrokerBase
from .base_classes.edge_cases import PluginBrokerEdgeCasesMixin

logger = logging.getLogger(__name__)
HERE = os.path.abspath(os.path.dirname(__file__))
MANIFEST_PATH_API_CONNECTION = os.path.join(HERE, "data", "api-connection-broker.yaml")
"""ApiConnection manifest whose name matches spec.connection in data/api-plugin.yaml."""


class TestSmarterApiPluginBroker(PluginBrokerEdgeCasesMixin, TestSmarterConnectionBrokerBase):
    """Test the Smarter SAMApiPluginBroker."""

    plugin_class = ApiPlugin
    broker_module = "smarter.apps.plugin.manifest.brokers.api_plugin"
    apply_builds_plugin = True
    orm_spec_method = "plugin_api_spec_orm2pydantic"

    @classmethod
    def setUpClass(cls):
        """Create the ApiConnection that the ApiPlugin manifest refers to."""
        super().setUpClass()
        loader = SAMLoader(file_path=MANIFEST_PATH_API_CONNECTION)
        if not apply_manifest(username=cls.admin_user.username, manifest=loader.yaml_data, verbose=True):
            raise SmarterValueError("Failed to apply the test ApiConnection manifest.")
        cls.api_connection = ApiConnection.objects.get(
            user_profile=cls.user_profile, name=loader.manifest_metadata.get("name")
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
        self.assertEqual(manifest.spec.connection, "test_api_connection")
        with self.assertRaises(ValidationError):
            self.broker.manifest.metadata.name = "NewManifestName"
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
        self.assertTrue(plugin.ready)
        self.assertEqual(plugin.name, self.broker.manifest.metadata.name)
        self.assertEqual(set(self.broker.manifest.metadata.tags or []), set(self.broker.plugin_meta.tags_list))

        plugin_data = self.broker.plugin_data
        self.assertIsInstance(plugin_data, PluginDataApi)
        self.assertEqual(plugin_data.endpoint, self.broker.manifest.spec.apiData.endpoint)
        self.assertEqual(plugin_data.connection, self.api_connection)

    def test_orm2pydantic(self):
        """Test that the persisted plugin converts back to its Pydantic spec."""
        self.apply_manifest()
        spec = self.broker.plugin_api_spec_orm2pydantic()
        self.assertIsInstance(spec, SAMApiPluginSpec)
        self.assertEqual(spec.connection, self.broker.manifest.spec.connection)
        self.assertEqual(spec.apiData.endpoint, self.broker.manifest.spec.apiData.endpoint)
        api_data = self.broker.plugin_data_orm2pydantic()
        self.assertEqual(api_data.endpoint, self.broker.manifest.spec.apiData.endpoint)
        self.assertEqual(
            {p.name for p in api_data.parameters or []},
            {p.name for p in self.broker.manifest.spec.apiData.parameters or []},
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
        broker = self.SAMBrokerClass(self.request, self.loader)
        response = broker.delete(self.request, **self.kwargs)
        self.assertTrue(self.validate_smarter_journaled_json_response_ok(response))
        self.assertFalse(PluginMeta.objects.filter(user_profile=self.user_profile, name="api_test").exists())

    def test_not_implemented(self):
        """Test that deploy(), undeploy(), prompt() and logs() are not implemented."""
        for method in (self.broker.deploy, self.broker.undeploy, self.broker.prompt, self.broker.logs):
            with self.assertRaises(SAMBrokerErrorNotImplemented):
                method(self.request, **self.kwargs)
