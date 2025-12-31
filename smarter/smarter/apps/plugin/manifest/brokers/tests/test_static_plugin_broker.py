# pylint: disable=wrong-import-position
"""Test SAMStaticPluginBroker."""

import logging
import os

from django.http import HttpRequest
from pydantic_core import ValidationError
from taggit.managers import TaggableManager, _TaggableManager

from smarter.apps.plugin.manifest.brokers.static_plugin import SAMStaticPluginBroker
from smarter.apps.plugin.manifest.models.common.plugin.metadata import (
    SAMPluginCommonMetadata,
)
from smarter.apps.plugin.manifest.models.static_plugin.model import SAMStaticPlugin
from smarter.apps.plugin.manifest.models.static_plugin.spec import SAMPluginStaticSpec
from smarter.apps.plugin.models import PluginDataStatic
from smarter.apps.plugin.plugin.static import StaticPlugin
from smarter.lib import json
from smarter.lib.manifest.broker import (
    SAMBrokerErrorNotImplemented,
)
from smarter.lib.manifest.loader import SAMLoader
from smarter.lib.manifest.tests.test_broker_base import TestSAMBrokerBaseClass


logger = logging.getLogger(__name__)


class TestSmarterStaticPluginBroker(TestSAMBrokerBaseClass):
    """
    Test the Smarter SAMStaticPluginBroker.
    TestSAMBrokerBaseClass provides common setup for SAM broker tests,
    including SAMLoader and HttpRequest properties.
    """

    def setUp(self):
        super().setUp()
        self._broker_class = SAMStaticPluginBroker
        self._here = os.path.abspath(os.path.dirname(__file__))
        self._manifest_filespec = self.get_data_full_filepath("static-plugin.yaml")

    @property
    def ready(self) -> bool:
        if not super().ready:
            return False
        self.assertIsInstance(self.loader, SAMLoader)
        self.assertIsInstance(self.loader.json_data, dict)
        self.assertIsInstance(self.loader.yaml_data, str)
        self.assertIsInstance(self.request, HttpRequest)
        return True

    @property
    def SAMBrokerClass(self) -> type[SAMStaticPluginBroker]:
        return SAMStaticPluginBroker

    @property
    def broker(self) -> SAMStaticPluginBroker:
        return super().broker  # type: ignore

    def test_setup(self):
        """
        Test that the test setup is correct.
        1. ready property is True.
        2. non_admin_user_profile is initialized.
        3. loader is an instance of SAMLoader with valid json_data and yaml_data.
        4. request is an instance of HttpRequest.
        5. broker is an instance of SAMStaticPluginBroker.
        """
        self.assertTrue(self.ready)
        self.assertIsNotNone(self.non_admin_user_profile, "Non-admin user profile not initialized in base class setup.")
        self.assertIsInstance(self.loader, SAMLoader)
        self.assertIsInstance(self.loader.json_data, dict)
        self.assertIsInstance(self.loader.yaml_data, str)
        self.assertIsInstance(self.request, HttpRequest)
        self._broker = self.SAMBrokerClass(self.request, self.loader)
        self.assertIsInstance(self.broker, SAMStaticPluginBroker)
        self._broker = self.SAMBrokerClass(self.request, self.loader)
        self.assertIsInstance(self.broker, SAMStaticPluginBroker)
        logger.info(
            "%s.test_setup() SAMStaticPluginBroker initialized successfully for testing.", self.formatted_class_name
        )

    def test_is_valid(self):
        """
        Test that the is_valid property returns True.
        """
        self.assertTrue(self.broker.is_valid)

    def test_immutability(self):
        """
        Test that any property of any Pydantic broker model are immutable.
        """
        with self.assertRaises(AttributeError):
            self.broker.kind = "NewKind"
        with self.assertRaises(ValidationError):
            self.broker.manifest.metadata.name = "NewManifestName"
        with self.assertRaises(ValidationError):
            self.broker.manifest.metadata.annotations = []
        with self.assertRaises(ValidationError):
            self.broker.manifest.metadata.tags = []
        with self.assertRaises(ValidationError):
            self.broker.manifest.spec.prompt.maxTokens = 2048

    def test_ready(self):
        """
        Test that the test setup is correct.
        """
        self.assertTrue(self.ready)

    def test_sam_broker_initialization(self):
        """
        Test that the SAMStaticPlugin model can be initialized from the manifest data.
        """
        metadata = {**self.loader.manifest_metadata}
        logger.info("%s.setUp() loading manifest spec: %s", self.formatted_class_name, self.loader.manifest_spec)
        SAMStaticPlugin(
            apiVersion=self.loader.manifest_api_version,
            kind=self.loader.manifest_kind,
            metadata=SAMPluginCommonMetadata(**metadata),
            spec=SAMPluginStaticSpec(**self.loader.manifest_spec),
        )

    def test_broker_initialization(self):
        """
        Test that the SAMStaticPluginBroker can be initialized from the request and loader.
        1. broker is an instance of SAMStaticPluginBroker.
        2. broker.kind is "Plugin".
        3. broker.model_class is SAMStaticPlugin.
        """
        broker: SAMStaticPluginBroker = self.SAMBrokerClass(self.request, self.loader)
        self.assertIsInstance(broker, SAMStaticPluginBroker)
        self.assertEqual(broker.kind, "Plugin")
        self.assertIsNotNone(broker.model_class)
        self.assertEqual(broker.model_class.__name__, "PluginDataStatic")

    def test_initialization_from_class(self):
        """
        Test that the SAMStaticPluginBroker can be initialized from SAMBrokerClass.
        """
        broker: SAMStaticPluginBroker = self.SAMBrokerClass(self.request, self.loader)
        self.assertIsInstance(broker, SAMStaticPluginBroker)
        self.assertTrue(broker.ready)

    def test_to_json(self):
        """
        Test that SAMStaticPluginBroker can serialize itself to JSON.
        """
        d = json.loads(json.dumps(self.broker.to_json()))
        self.assertIsInstance(d, dict)

    def test_manifest_initialization(self):
        """
        Test that the SAMStaticPluginBroker can be initialized from a manifest.
        """
        broker = self.SAMBrokerClass(self.request, self.broker.manifest)
        self.assertIsInstance(broker, SAMStaticPluginBroker)

    def test_manifest_model_initialization(self):
        """
        Test that the SAMStaticPlugin can be initialized from
        a json dump of the manifest model.
        """
        static_plugin = SAMStaticPlugin(**self.broker.manifest.model_dump())
        self.assertIsInstance(static_plugin, SAMStaticPlugin)

    def test_formatted_class_name(self):
        """
        Test that the formatted_class_name property returns the correct value.
        """
        name = self.broker.formatted_class_name
        self.assertIsInstance(name, str)
        self.assertIn("SAMStaticPluginBroker", name)

    def test_kind_property(self):
        """
        Test that the kind property returns "Plugin".
        """
        self.assertEqual(self.broker.kind, "Plugin")

    def test_manifest_property(self):
        """
        Test that the manifest property returns a SAMStaticPlugin instance.
        """
        try:
            manifest = self.broker.manifest
        # pylint: disable=broad-except
        except Exception as e:
            self.fail(f"manifest property raised: {e}")
        self.assertIsInstance(manifest, SAMStaticPlugin)

    def test_django_orm_to_manifest_dict(self):
        """
        Test that we can convert the Django plugin spec ORM
        to a Pydantic manifest spec.
        """
        manifest_dict = self.broker.plugin_static_spec_orm2pydantic()
        self.assertIsInstance(manifest_dict, SAMPluginStaticSpec)

    def test_example_manifest(self):
        """
        Test the example_manifest() generates a valid manifest response.
        """
        response = self.broker.example_manifest(self.request)
        is_valid_response = self.validate_smarter_journaled_json_response_ok(response)
        self.assertTrue(is_valid_response)
        is_valid_response = self.validate_example_manifest(response)
        self.assertTrue(is_valid_response)

    def test_get(self):
        """
        Test the get() method returns a valid manifest response.
        """
        response = self.broker.get(self.request, **self.kwargs)
        is_valid_response = self.validate_smarter_journaled_json_response_ok(response)
        self.assertTrue(is_valid_response)
        is_valid_response = self.validate_get(response)
        self.assertTrue(is_valid_response)

    def test_apply(self):
        """
        Test the apply() method returns a valid manifest response.
        """
        response = self.broker.apply(self.request, **self.kwargs)
        is_valid_response = self.validate_smarter_journaled_json_response_ok(response)
        self.assertTrue(is_valid_response)
        is_valid_response = self.validate_apply(response)
        self.assertTrue(is_valid_response)

        # self.broker.manifest.metadata.tags is a list of strings.
        # verify that account.tags (TaggableManager) contains the same tags.
        manifest_tags = set(self.broker.manifest.metadata.tags or [])
        django_orm_tags = None
        if isinstance(self.broker.plugin_meta.tags, (TaggableManager, _TaggableManager)):
            django_orm_tags = set(self.broker.plugin_meta.tags.names()) if self.broker.plugin_meta.tags else set()
        elif isinstance(self.broker.plugin_meta.tags, set):
            django_orm_tags = self.broker.plugin_meta.tags
        else:
            self.fail(f"plugin_meta.tags is of unexpected type: {type(self.broker.plugin_meta.tags)}")
        self.assertEqual(manifest_tags, django_orm_tags)

        # self.broker.manifest.metadata.annotations is a list of key-value pairs or None.
        # verify that plugin.annotations (JSONField) contains the same annotations.
        def sort_annotations(annotations):
            return sorted(annotations, key=lambda d: sorted(d.items()))

        manifest_annotations = sort_annotations(self.broker.manifest.metadata.annotations or [])
        plugin_annotations = sort_annotations(self.broker.plugin_meta.annotations or [])
        self.assertEqual(
            manifest_annotations,
            plugin_annotations,
            f"Plugin annotations do not match manifest annotations. manifest: {manifest_annotations}, plugin: {plugin_annotations}",
        )

        self.assertEqual(
            self.broker.manifest.metadata.name,
            getattr(self.broker.plugin, "name", None),
            f"Plugin name does not match manifest name. manifest: {self.broker.manifest.metadata.name}, plugin: {getattr(self.broker.plugin, 'name', None)}",
        )
        self.assertEqual(
            self.broker.manifest.metadata.description or "",
            getattr(self.broker.plugin.plugin_meta, "description", "") or "",
            f"Plugin description does not match manifest description. manifest: {self.broker.manifest.metadata.description}, plugin: {getattr(self.broker.plugin.plugin_meta , 'description', '')}",
        )
        self.assertEqual(
            self.broker.manifest.metadata.version or "",
            getattr(self.broker.plugin.plugin_meta, "version", "") or "",
            f"Plugin version does not match manifest version. manifest: {self.broker.manifest.metadata.version}, plugin: {getattr(self.broker.plugin.plugin_meta, 'version', '')}",
        )

        # plugin spec fields
        self.assertEqual(self.broker.manifest.spec.selector.directive, self.broker.plugin.plugin_selector.directive)
        self.assertEqual(
            self.broker.manifest.spec.selector.searchTerms, self.broker.plugin.plugin_selector.search_terms
        )
        self.assertEqual(self.broker.manifest.spec.prompt.provider, self.broker.plugin.plugin_prompt.provider)
        self.assertEqual(self.broker.manifest.spec.prompt.systemRole, self.broker.plugin.plugin_prompt.system_role)
        self.assertEqual(self.broker.manifest.spec.prompt.model, self.broker.plugin.plugin_prompt.model)
        self.assertEqual(self.broker.manifest.spec.prompt.temperature, self.broker.plugin.plugin_prompt.temperature)
        self.assertEqual(self.broker.manifest.spec.data.description, self.broker.plugin.plugin_data.description)
        self.assertEqual(self.broker.manifest.spec.data.staticData, self.broker.plugin.plugin_data.static_data)

    def test_plugin(self):
        """
        Test that the plugin property returns a StaticPlugin instance.
        """

        plugin = self.broker.plugin
        self.assertIsInstance(plugin, StaticPlugin)
        self.assertTrue(plugin.ready)

    def test_plugin_data(self):
        """
        Test that the plugin data matches the manifest spec.
        """
        plugin_data = self.broker.plugin_data
        self.assertIsInstance(plugin_data, PluginDataStatic)
        self.assertEqual(
            plugin_data.description or "",
            self.broker.manifest.spec.data.description or "",
            "Plugin data description does not match manifest spec description.",
        )
        self.assertEqual(
            plugin_data.static_data or {},
            self.broker.manifest.spec.data.staticData or {},
            "Plugin data staticData does not match manifest spec staticData.",
        )

    def test_describe(self):
        """
        Test the describe() method returns a valid manifest response.
        """
        response = self.broker.describe(self.request, **self.kwargs)
        is_valid_response = self.validate_smarter_journaled_json_response_ok(response)
        self.assertTrue(is_valid_response)
        logger.info("Describe response: %s", response.content.decode())

    def test_delete(self):
        pass

    def test_deploy(self):
        """
        Test that deploy() raises NotImplementedError.
        """
        with self.assertRaises(SAMBrokerErrorNotImplemented):
            self.broker.deploy(self.request, **self.kwargs)

    def test_undeploy(self):
        """
        Test that undeploy() raises NotImplementedError.
        """
        with self.assertRaises(SAMBrokerErrorNotImplemented):
            self.broker.undeploy(self.request, **self.kwargs)

    def test_chat_not_implemented(self):
        """
        Test that chat() raises NotImplementedError.
        """
        with self.assertRaises(SAMBrokerErrorNotImplemented):
            self.broker.chat(self.request, **self.kwargs)

    def test_logs_returns_ok(self):
        """
        Test that logs() raises NotImplementedError.
        """
        with self.assertRaises(SAMBrokerErrorNotImplemented):
            self.broker.logs(self.request, **self.kwargs)
