# pylint: disable=wrong-import-position
"""
Test SAMWebsearchPluginBroker.

.. note::

    **Experimental.** The WebsearchPlugin was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

import os

from django.http import HttpRequest
from pydantic_core import ValidationError

from smarter.apps.connection.tests.factories import secret_factory
from smarter.apps.plugin.manifest.brokers.websearch_plugin import (
    SAMWebsearchPluginBroker,
)
from smarter.apps.plugin.manifest.models.common.plugin.metadata import (
    SAMPluginCommonMetadata,
)
from smarter.apps.plugin.manifest.models.websearch_plugin.model import (
    SAMWebsearchPlugin,
)
from smarter.apps.plugin.manifest.models.websearch_plugin.spec import (
    SAMWebsearchPluginSpec,
)
from smarter.apps.plugin.models import PluginDataWebsearch
from smarter.apps.plugin.plugin.websearch import WebsearchPlugin
from smarter.lib import json, logging
from smarter.lib.manifest.broker import (
    SAMBrokerErrorNotImplemented,
)
from smarter.lib.manifest.loader import SAMLoader
from smarter.lib.manifest.tests.test_broker_base import TestSAMBrokerBaseClass

logger = logging.getLogger(__name__)

API_KEY_SECRET = "test_brave_api_key"
"""The api key Secret named by ./data/websearch-plugin.yaml."""
API_KEY = "test-brave-api-key-value"


# pylint: disable=too-many-public-methods
class TestSmarterWebsearchPluginBroker(TestSAMBrokerBaseClass):
    """
    Test the Smarter SAMWebsearchPluginBroker.

    TestSAMBrokerBaseClass provides common setup for SAM broker tests,
    including SAMLoader and HttpRequest properties.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.api_key_secret = secret_factory(user_profile=cls.user_profile, name=API_KEY_SECRET, value=API_KEY)

    @classmethod
    def tearDownClass(cls):
        try:
            cls.api_key_secret.delete()
        # pylint: disable=W0718
        except Exception:
            pass
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self._broker_class = SAMWebsearchPluginBroker
        self._here = os.path.abspath(os.path.dirname(__file__))
        self._manifest_filespec = self.get_data_full_filepath("websearch-plugin.yaml")

    @property
    def ready(self) -> bool:
        if not super().ready:
            return False
        self.assertIsInstance(self.loader, SAMLoader)
        self.assertIsInstance(self.request, HttpRequest)
        return True

    @property
    def SAMBrokerClass(self) -> type[SAMWebsearchPluginBroker]:
        return SAMWebsearchPluginBroker

    @property
    def broker(self) -> SAMWebsearchPluginBroker:
        return super().broker  # type: ignore

    def test_setup(self):
        """Test that the test setup is correct."""
        self.assertTrue(self.ready)
        self.assertIsInstance(self.SAMBrokerClass(self.request, self.loader), SAMWebsearchPluginBroker)

    def test_is_valid(self):
        """Test that the is_valid property returns True."""
        self.assertTrue(self.broker.is_valid)

    def test_immutability(self):
        """Test that the Pydantic manifest models are immutable."""
        with self.assertRaises(AttributeError):
            self.broker.kind = "NewKind"
        with self.assertRaises(ValidationError):
            self.broker.manifest.metadata.name = "NewManifestName"
        with self.assertRaises(ValidationError):
            self.broker.manifest.spec.websearchData.timeout = 1

    def test_sam_broker_initialization(self):
        """Test that the SAMWebsearchPlugin model can be initialized from the manifest data."""
        SAMWebsearchPlugin(
            apiVersion=self.loader.manifest_api_version,
            kind=self.loader.manifest_kind,
            metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
            spec=SAMWebsearchPluginSpec(**self.loader.manifest_spec),
        )

    def test_broker_initialization(self):
        """Test the broker kind and model classes."""
        broker: SAMWebsearchPluginBroker = self.SAMBrokerClass(self.request, self.loader)
        self.assertEqual(broker.kind, "WebsearchPlugin")
        self.assertIs(broker.ORMModelClass, PluginDataWebsearch)
        self.assertIs(broker.SAMModelClass, SAMWebsearchPlugin)
        self.assertTrue(broker.ready)

    def test_to_json(self):
        """Test that the broker can serialize itself to JSON."""
        self.assertIsInstance(json.loads(json.dumps(self.broker.to_json())), dict)

    def test_manifest_initialization(self):
        """Test that the broker can be initialized from a manifest."""
        self.assertIsInstance(self.SAMBrokerClass(self.request, self.broker.manifest), SAMWebsearchPluginBroker)

    def test_formatted_class_name(self):
        """Test the formatted class name."""
        self.assertIn("SAMWebsearchPluginBroker", self.broker.formatted_class_name)

    def test_manifest_property(self):
        """Test that the manifest property returns a SAMWebsearchPlugin."""
        manifest = self.broker.manifest
        self.assertIsInstance(manifest, SAMWebsearchPlugin)
        self.assertEqual(manifest.spec.websearchData.search.apiKey, API_KEY_SECRET)  # type: ignore[union-attr]

    def test_example_manifest(self):
        """Test the example_manifest() generates a valid manifest response."""
        response = self.broker.example_manifest(self.request)
        self.assertTrue(self.validate_smarter_journaled_json_response_ok(response))
        self.assertTrue(self.validate_example_manifest(response))
        self.assertIsInstance(SAMWebsearchPlugin(**json.loads(response.content)["data"]), SAMWebsearchPlugin)

    def test_get(self):
        """Test the get() method returns a valid manifest response."""
        response = self.broker.get(self.request, **self.kwargs)
        self.assertTrue(self.validate_smarter_journaled_json_response_ok(response))
        self.assertTrue(self.validate_get(response))

    def test_apply(self):
        """Test that apply() stores the configuration, with the api key Secret."""
        response = self.broker.apply(self.request, **self.kwargs)
        self.assertTrue(self.validate_smarter_journaled_json_response_ok(response))
        self.assertTrue(self.validate_apply(response))
        plugin_data = self.broker.plugin.plugin_data
        self.assertIsInstance(plugin_data, PluginDataWebsearch)
        self.assertEqual(plugin_data.search_provider, "brave")
        self.assertEqual(plugin_data.search_api_key, self.api_key_secret)
        self.assertEqual(plugin_data.blocked_domains, ["blocked.example"])

    def test_apply_then_describe(self):
        """Test that describe() renders an applied plugin, with the api key's Secret name, never its value."""
        self.broker.apply(self.request, **self.kwargs)
        broker = self.SAMBrokerClass(self.request, name=self.broker.manifest.metadata.name)
        spec = broker.plugin_websearch_spec_orm2pydantic()
        self.assertIsInstance(spec, SAMWebsearchPluginSpec)
        self.assertEqual(spec.websearchData.search.apiKey, API_KEY_SECRET)  # type: ignore[union-attr]

        response = self.broker.describe(self.request, **self.kwargs)
        self.assertTrue(self.validate_smarter_journaled_json_response_ok(response))
        data = json.loads(response.content)["data"]
        self.assertEqual(data["spec"]["websearchData"]["search"]["apiKey"], API_KEY_SECRET)
        self.assertNotIn(API_KEY, response.content.decode())

    def test_plugin(self):
        """Test that the plugin property returns a ready WebsearchPlugin."""
        plugin = self.broker.plugin
        self.assertIsInstance(plugin, WebsearchPlugin)
        self.assertTrue(plugin.ready)

    def test_describe(self):
        """Test the describe() method returns a valid manifest response."""
        response = self.broker.describe(self.request, **self.kwargs)
        self.assertTrue(self.validate_smarter_journaled_json_response_ok(response))

    def test_deploy(self):
        """Test that deploy() is not implemented."""
        with self.assertRaises(SAMBrokerErrorNotImplemented):
            self.broker.deploy(self.request, **self.kwargs)

    def test_undeploy(self):
        """Test that undeploy() is not implemented."""
        with self.assertRaises(SAMBrokerErrorNotImplemented):
            self.broker.undeploy(self.request, **self.kwargs)

    def test_chat_not_implemented(self):
        """Test that prompt() is not implemented."""
        with self.assertRaises(SAMBrokerErrorNotImplemented):
            self.broker.prompt(self.request, **self.kwargs)

    def test_logs(self):
        """Test that logs() is not implemented."""
        with self.assertRaises(SAMBrokerErrorNotImplemented):
            self.broker.logs(self.request, **self.kwargs)
