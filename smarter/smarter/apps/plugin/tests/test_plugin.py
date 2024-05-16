# pylint: disable=wrong-import-position
# pylint: disable=R0801,W0613
"""Test providers."""

# python stuff
import json
import unittest
from time import sleep

import yaml
from pydantic_core import ValidationError as PydanticValidationError

from smarter.apps.account.models import UserProfile
from smarter.apps.account.tests.factories import admin_user_factory, admin_user_teardown
from smarter.apps.plugin.models import (
    PluginDataStatic,
    PluginMeta,
    PluginPrompt,
    PluginSelector,
)
from smarter.apps.plugin.plugin.base import SmarterPluginError
from smarter.apps.plugin.plugin.static import PluginStatic
from smarter.apps.plugin.plugin.utils import PluginExamples
from smarter.apps.plugin.serializers import (
    PluginDataStaticSerializer,
    PluginMetaSerializer,
    PluginPromptSerializer,
    PluginSelectorSerializer,
)
from smarter.apps.plugin.signals import (
    plugin_called,
    plugin_cloned,
    plugin_created,
    plugin_deleted,
    plugin_ready,
    plugin_selected,
    plugin_updated,
)
from smarter.apps.plugin.tests.test_setup import get_test_file_path
from smarter.apps.plugin.utils import add_example_plugins
from smarter.lib.manifest.loader import SAMLoaderError


# pylint: disable=too-many-public-methods,too-many-instance-attributes
class TestPlugin(unittest.TestCase):
    """Test plugin."""

    data: dict
    user_profile: UserProfile

    _plugin_called = False
    _plugin_cloned = False
    _plugin_created = False
    _plugin_deleted = False
    _plugin_ready = False
    _plugin_selected = False
    _plugin_selected_called = False
    _plugin_updated = False

    def plugin_called_signal_handler(self, *args, **kwargs):
        self._plugin_called = True

    def plugin_cloned_signal_handler(self, *args, **kwargs):
        self._plugin_cloned = True

    def plugin_created_signal_handler(self, *args, **kwargs):
        self._plugin_created = True

    def plugin_deleted_signal_handler(self, *args, **kwargs):
        self._plugin_deleted = True

    def plugin_ready_signal_handler(self, *args, **kwargs):
        self._plugin_ready = True

    def plugin_selected_signal_handler(self, *args, **kwargs):
        self._plugin_selected = True

    def plugin_selected_called_signal_handler(self, *args, **kwargs):
        self._plugin_selected_called = True

    def plugin_updated_signal_handler(self, *args, **kwargs):
        self._plugin_updated = True

    @property
    def signals(self):
        return {
            "plugin_called": self._plugin_called,
            "plugin_cloned": self._plugin_cloned,
            "plugin_created": self._plugin_created,
            "plugin_deleted": self._plugin_deleted,
            "plugin_ready": self._plugin_ready,
            "plugin_selected": self._plugin_selected,
            "plugin_updated": self._plugin_updated,
        }

    def setUp(self):
        """Set up test fixtures."""
        config_path = get_test_file_path("everlasting-gobstopper.yaml")
        with open(config_path, encoding="utf-8") as file:
            self.data = yaml.safe_load(file)
        self.user, self.account, self.user_profile = admin_user_factory()

    def tearDown(self):
        """Clean up test fixtures."""
        admin_user_teardown(self.user, self.account, self.user_profile)

    # pylint: disable=broad-exception-caught
    def test_create(self):
        """Test that we can create a plugin using the PluginStatic."""

        plugin_created.connect(self.plugin_created_signal_handler, dispatch_uid="plugin_created_test_create")
        plugin_ready.connect(self.plugin_ready_signal_handler, dispatch_uid="plugin_ready_test_create")

        plugin = PluginStatic(data=self.data)

        # sleep long enough to eliminate race situation
        # between the asynchronous commit and our assertion
        sleep(1)

        # verify that the signals were sent
        self.assertTrue(self.signals["plugin_created"])
        self.assertTrue(self.signals["plugin_ready"])

        self.assertIsInstance(plugin, PluginStatic)
        self.assertTrue(plugin.ready)
        self.assertIsInstance(plugin.plugin_meta, PluginMeta)
        self.assertIsInstance(plugin.plugin_selector, PluginSelector)
        self.assertIsInstance(plugin.plugin_prompt, PluginPrompt)
        self.assertIsInstance(plugin.plugin_data, PluginDataStatic)
        self.assertIsInstance(plugin.plugin_data_serializer, PluginDataStaticSerializer)
        self.assertIsInstance(plugin.plugin_meta_serializer, PluginMetaSerializer)
        self.assertIsInstance(plugin.plugin_prompt_serializer, PluginPromptSerializer)
        self.assertIsInstance(plugin.plugin_selector_serializer, PluginSelectorSerializer)

        self.assertEqual(plugin.plugin_meta.name, self.data["metadata"]["name"])
        self.assertEqual(plugin.plugin_selector.directive, self.data["spec"]["selector"]["directive"])
        self.assertEqual(plugin.plugin_prompt.system_role, self.data["spec"]["prompt"]["systemRole"])
        self.assertEqual(plugin.plugin_prompt.model, self.data["spec"]["prompt"]["model"])
        self.assertEqual(plugin.plugin_prompt.temperature, self.data["spec"]["prompt"]["temperature"])
        self.assertEqual(plugin.plugin_prompt.max_tokens, self.data["spec"]["prompt"]["maxTokens"])
        self.assertEqual(plugin.plugin_data.description, self.data["spec"]["data"]["description"])
        self.assertEqual(plugin.plugin_data.static_data, self.data["spec"]["data"]["staticData"])

    def test_to_json(self):
        """Test that the PluginStatic generates correct JSON output."""
        plugin_created.connect(self.plugin_created_signal_handler, dispatch_uid="plugin_created_test_to_json")
        plugin_ready.connect(self.plugin_ready_signal_handler, dispatch_uid="plugin_ready_test_to_json")

        plugin = PluginStatic(user_profile=self.user_profile, data=self.data)
        to_json = plugin.to_json()

        # verify that signal was sent
        self.assertTrue(self.signals["plugin_created"])
        self.assertTrue(self.signals["plugin_ready"])

        self.assertIsInstance(to_json, dict)
        self.assertEqual(to_json["metadata"]["name"], self.data["metadata"]["name"])
        self.assertEqual(to_json["spec"]["selector"]["directive"], self.data["spec"]["selector"]["directive"])
        self.assertEqual(to_json["spec"]["prompt"]["systemRole"], self.data["spec"]["prompt"]["systemRole"])
        self.assertEqual(to_json["spec"]["prompt"]["model"], self.data["spec"]["prompt"]["model"])
        self.assertEqual(to_json["spec"]["prompt"]["temperature"], self.data["spec"]["prompt"]["temperature"])
        self.assertEqual(to_json["spec"]["prompt"]["maxTokens"], self.data["spec"]["prompt"]["maxTokens"])

    def test_delete(self):
        """Test that we can delete a plugin using the PluginStatic."""
        plugin_created.connect(self.plugin_created_signal_handler, dispatch_uid="plugin_created_test_delete")
        plugin_updated.connect(self.plugin_updated_signal_handler, dispatch_uid="plugin_updated_test_delete")
        plugin_ready.connect(self.plugin_ready_signal_handler, dispatch_uid="plugin_ready_test_delete")
        plugin_deleted.connect(self.plugin_deleted_signal_handler, dispatch_uid="plugin_deleted_test_delete")

        plugin = PluginStatic(data=self.data)
        plugin_id = plugin.id
        plugin.delete()

        # sleep long enough to eliminate race situation
        # between the asynchronous commit and our assertion
        sleep(1)

        # verify that the signals were sent
        self.assertTrue(self.signals["plugin_created"] or self.signals["plugin_updated"])
        self.assertTrue(self.signals["plugin_ready"])
        self.assertTrue(self.signals["plugin_deleted"])

        with self.assertRaises(PluginMeta.DoesNotExist):
            PluginMeta.objects.get(pk=plugin_id)

        with self.assertRaises(PluginSelector.DoesNotExist):
            PluginSelector.objects.get(plugin_id=plugin_id)

        with self.assertRaises(PluginPrompt.DoesNotExist):
            PluginPrompt.objects.get(plugin_id=plugin_id)

        with self.assertRaises(PluginDataStatic.DoesNotExist):
            PluginDataStatic.objects.get(plugin_id=plugin_id)

    def test_add_sample_plugins(self):
        """Test utility function to add sample plugins to a user account."""

        # add the sample plugins to the user account
        add_example_plugins(user_profile=self.user_profile)

        # verify that all of the sample plugins were added to the user account
        plugins = PluginMeta.objects.filter(account=self.account)
        self.assertEqual(len(plugins), PluginExamples().count())

        # verify that all of the sample plugins were correctdly created
        # and are in a ready state.
        for plugin in plugins:
            self.assertTrue(PluginStatic(plugin_meta=plugin).ready)

    # pylint: disable=too-many-statements
    def test_validation_bad_structure(self):
        """Test that the PluginStatic raises an error when given bad data."""
        with self.assertRaises(SmarterPluginError):
            PluginStatic(data={})

        bad_data = self.data.copy()
        bad_data.pop("metadata")
        with self.assertRaises(SAMLoaderError):
            PluginStatic(data=bad_data)

        bad_data = self.data.copy()
        bad_data["spec"].pop("selector")
        with self.assertRaises(PydanticValidationError):
            PluginStatic(data=bad_data)

        bad_data = self.data.copy()
        bad_data["spec"].pop("prompt")
        with self.assertRaises(PydanticValidationError):
            PluginStatic(data=bad_data)

        bad_data = self.data.copy()
        bad_data["spec"].pop("data")
        with self.assertRaises(SAMLoaderError):
            PluginStatic(data=bad_data)

        bad_data = self.data.copy()
        bad_data["metadata"].pop("name")
        with self.assertRaises(SAMLoaderError):
            PluginStatic(data=bad_data)

    def test_pydantic_validation_errors(self):
        """Test that the PluginStatic raises an error when given bad data."""

        bad_data = self.data.copy()
        print("bad_data", bad_data)
        bad_data["spec"]["selector"].pop("directive")
        with self.assertRaises(PydanticValidationError):
            PluginStatic(data=bad_data)

        bad_data = self.data.copy()
        bad_data["spec"]["prompt"].pop("systemRole")
        with self.assertRaises(PydanticValidationError):
            PluginStatic(data=bad_data)

        bad_data = self.data.copy()
        bad_data["spec"]["prompt"].pop("model")
        with self.assertRaises(PydanticValidationError):
            PluginStatic(data=bad_data)

        bad_data = self.data.copy()
        bad_data["spec"]["prompt"].pop("temperature")
        with self.assertRaises(PydanticValidationError):
            PluginStatic(data=bad_data)

        bad_data = self.data.copy()
        bad_data["spec"]["prompt"].pop("maxTokens")
        with self.assertRaises(PydanticValidationError):
            PluginStatic(data=bad_data)

        bad_data = self.data.copy()
        bad_data["spec"]["data"].pop("description")
        with self.assertRaises(PydanticValidationError):
            PluginStatic(data=bad_data)

        bad_data = self.data.copy()
        bad_data["spec"]["data"].pop("staticData")
        with self.assertRaises(PydanticValidationError):
            PluginStatic(data=bad_data)

    def test_validation_bad_data_types(self):
        """Test that the PluginStatic raises an error when given bad data."""
        bad_data = self.data.copy()
        bad_data["metadata"]["tags"] = "not a list"
        with self.assertRaises(PydanticValidationError):
            PluginStatic(data=bad_data)

        bad_data = self.data.copy()
        bad_data["spec"]["selector"]["searchTerms"] = "not a list"
        with self.assertRaises(PydanticValidationError):
            PluginStatic(data=bad_data)

        bad_data = self.data.copy()
        bad_data["spec"]["prompt"]["temperature"] = "not a float"
        with self.assertRaises(PydanticValidationError):
            PluginStatic(data=bad_data)

        bad_data = self.data.copy()
        bad_data["spec"]["prompt"]["maxTokens"] = "not an int"
        with self.assertRaises(PydanticValidationError):
            PluginStatic(data=bad_data)

    def test_clone(self):
        """Test that we can clone a plugin using the PluginStatic."""
        plugin_ready.connect(self.plugin_ready_signal_handler, dispatch_uid="plugin_ready_test_clone")
        plugin_cloned.connect(self.plugin_cloned_signal_handler, dispatch_uid="plugin_cloned_test_clone")

        plugin = PluginStatic(data=self.data)
        clone_id = plugin.clone()
        plugin_clone = PluginStatic(plugin_id=clone_id)

        # sleep long enough to eliminate race situation
        # between the asynchronous commit and our assertion
        sleep(1)

        # verify that the signals were sent
        self.assertTrue(self.signals["plugin_ready"])
        self.assertTrue(self.signals["plugin_cloned"])

        self.assertNotEqual(plugin.id, plugin_clone.id)
        self.assertNotEqual(plugin.plugin_meta.name, plugin_clone.plugin_meta.name)
        self.assertNotEqual(plugin.plugin_meta.created_at, plugin_clone.plugin_meta.created_at)

        self.assertEqual(plugin.plugin_meta.author, plugin_clone.plugin_meta.author)
        self.assertListEqual(list(plugin.plugin_meta.tags.all()), list(plugin_clone.plugin_meta.tags.all()))

        self.assertEqual(plugin.plugin_selector.directive, plugin_clone.plugin_selector.directive)
        self.assertEqual(plugin.plugin_selector.search_terms, plugin_clone.plugin_selector.search_terms)

        self.assertEqual(plugin.plugin_prompt.system_role, plugin_clone.plugin_prompt.system_role)
        self.assertEqual(plugin.plugin_prompt.model, plugin_clone.plugin_prompt.model)
        self.assertEqual(plugin.plugin_prompt.temperature, plugin_clone.plugin_prompt.temperature)
        self.assertEqual(plugin.plugin_prompt.max_tokens, plugin_clone.plugin_prompt.max_tokens)

        self.assertEqual(plugin.plugin_data.description, plugin_clone.plugin_data.description)
        self.assertEqual(plugin.plugin_data.static_data, plugin_clone.plugin_data.static_data)

        plugin.delete()
        plugin_clone.delete()

    def test_json_serialization(self):
        """Test that the PluginStatic generates correct JSON output."""
        plugin_ready.connect(self.plugin_ready_signal_handler, dispatch_uid="plugin_ready_test_json_serialization")

        plugin = PluginStatic(data=self.data)
        to_json = plugin.to_json()

        # verify that signal was sent
        self.assertTrue(self.signals["plugin_ready"])

        # ensure that we can go from json output to a string and back to json without error
        to_json = json.loads(json.dumps(to_json))

        # ensure that the json output still matches the original data
        self.assertIsInstance(to_json, dict)
        self.assertEqual(to_json["metadata"]["name"], self.data["metadata"]["name"])
        self.assertEqual(to_json["spec"]["selector"]["directive"], self.data["spec"]["selector"]["directive"])
        self.assertEqual(to_json["spec"]["prompt"]["systemRole"], self.data["spec"]["prompt"]["systemRole"])
        self.assertEqual(to_json["spec"]["prompt"]["model"], self.data["spec"]["prompt"]["model"])
        self.assertEqual(to_json["spec"]["prompt"]["temperature"], self.data["spec"]["prompt"]["temperature"])
        self.assertEqual(to_json["spec"]["prompt"]["maxTokens"], self.data["spec"]["prompt"]["maxTokens"])

    def test_plugin_called_signal(self):
        """Test the plugin_called signal."""
        plugin_called.connect(self.plugin_called_signal_handler, dispatch_uid="plugin_called_test_plugin_called_signal")

        plugin = PluginStatic(data=self.data)
        plugin.function_calling_plugin(inquiry_type="sales_promotions")

        self.assertTrue(self.signals["plugin_called"])

    def test_plugin_selected_signal(self):
        """Test the plugin_selected signal."""
        plugin_selected.connect(
            self.plugin_selected_signal_handler, dispatch_uid="plugin_selected_test_plugin_selected_signal"
        )

        messages = [
            {"role": "system", "content": "you are a helpful chatbot."},
            {"role": "user", "content": "have you ever heard of everlasting gobstoppers?"},
        ]

        plugin = PluginStatic(data=self.data)
        plugin.selected(user=self.user, messages=messages)
        self.assertTrue(self.signals["plugin_selected"])

        sleep(1)

        self._plugin_selected = False
        messages = [
            {"role": "system", "content": "you are a helpful chatbot."},
            {"role": "user", "content": "this should return false."},
        ]
        self.assertFalse(self.signals["plugin_selected"])
