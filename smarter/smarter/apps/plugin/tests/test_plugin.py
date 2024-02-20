# -*- coding: utf-8 -*-
# pylint: disable=wrong-import-position
# pylint: disable=R0801
"""Test providers."""

# python stuff
import json
import os
import unittest
from pathlib import Path

import yaml
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

# our stuff
from smarter.apps.account.models import Account, UserProfile
from smarter.apps.plugin.models import (
    PluginData,
    PluginMeta,
    PluginPrompt,
    PluginSelector,
)
from smarter.apps.plugin.plugin import Plugin
from smarter.apps.plugin.serializers import (
    PluginDataSerializer,
    PluginMetaSerializer,
    PluginPromptSerializer,
    PluginSelectorSerializer,
)
from smarter.apps.plugin.tests.test_setup import PROJECT_ROOT, get_test_file_path
from smarter.apps.plugin.utils import add_example_plugins


class TestPlugin(unittest.TestCase):
    """Test OpenAI Function Calling hook for refers_to."""

    data: dict
    user_profile: UserProfile

    def setUp(self):
        """Set up test fixtures."""
        config_path = get_test_file_path("everlasting-gobstopper.yaml")
        with open(config_path, "r", encoding="utf-8") as file:
            self.data = yaml.safe_load(file)

        self.user, _ = User.objects.get_or_create(username="testuser", password="12345")
        self.account, _ = Account.objects.get_or_create(company_name="Test Account")
        self.user_profile, _ = UserProfile.objects.get_or_create(user=self.user, account=self.account)

        self.data["user_profile"] = self.user_profile

    def tearDown(self):
        """Clean up test fixtures."""
        self.user_profile.delete()
        self.user.delete()
        self.account.delete()

    # pylint: disable=broad-exception-caught
    def test_create(self):
        """Test that we can create a plugin using the Plugin."""
        plugin = Plugin(data=self.data)

        self.assertIsInstance(plugin, Plugin)
        self.assertTrue(plugin.ready)
        self.assertIsInstance(plugin.plugin_meta, PluginMeta)
        self.assertIsInstance(plugin.plugin_selector, PluginSelector)
        self.assertIsInstance(plugin.plugin_prompt, PluginPrompt)
        self.assertIsInstance(plugin.plugin_data, PluginData)
        self.assertIsInstance(plugin.plugin_data_serializer, PluginDataSerializer)
        self.assertIsInstance(plugin.plugin_meta_serializer, PluginMetaSerializer)
        self.assertIsInstance(plugin.plugin_prompt_serializer, PluginPromptSerializer)
        self.assertIsInstance(plugin.plugin_selector_serializer, PluginSelectorSerializer)

        self.assertEqual(plugin.plugin_meta.name, self.data["meta_data"]["name"])
        self.assertEqual(plugin.plugin_selector.directive, self.data["selector"]["directive"])
        self.assertEqual(plugin.plugin_prompt.system_role, self.data["prompt"]["system_role"])
        self.assertEqual(plugin.plugin_prompt.model, self.data["prompt"]["model"])
        self.assertEqual(plugin.plugin_prompt.temperature, self.data["prompt"]["temperature"])
        self.assertEqual(plugin.plugin_prompt.max_tokens, self.data["prompt"]["max_tokens"])
        self.assertEqual(plugin.plugin_data.description, self.data["plugin_data"]["description"])
        self.assertEqual(plugin.plugin_data.return_data, self.data["plugin_data"]["return_data"])

    def test_update(self):
        """Test that we can update a plugin using the Plugin."""
        plugin = Plugin(data=self.data)

        plugin.plugin_meta.name = "New Name"
        plugin.plugin_selector.directive = "New Directive"
        plugin.plugin_prompt.system_role = "New System Role"
        plugin.plugin_prompt.model = "New Model"
        plugin.plugin_prompt.temperature = 0.5
        plugin.plugin_prompt.max_tokens = 100
        plugin.plugin_data.description = "New Description"
        plugin.plugin_data.return_data = "New Return Data"

        plugin.update()

        self.assertEqual(plugin.plugin_meta.name, "New Name")
        self.assertEqual(plugin.plugin_selector.directive, "New Directive")
        self.assertEqual(plugin.plugin_prompt.system_role, "New System Role")
        self.assertEqual(plugin.plugin_prompt.model, "New Model")
        self.assertEqual(plugin.plugin_prompt.temperature, 0.5)
        self.assertEqual(plugin.plugin_prompt.max_tokens, 100)
        self.assertEqual(plugin.plugin_data.description, "New Description")
        self.assertEqual(plugin.plugin_data.return_data, "New Return Data")

    def test_to_json(self):
        """Test that the Plugin generates correct JSON output."""
        plugin = Plugin(data=self.data)
        to_json = plugin.to_json()

        self.assertIsInstance(to_json, dict)
        self.assertEqual(to_json["meta_data"]["name"], self.data["meta_data"]["name"])
        self.assertEqual(to_json["selector"]["directive"], self.data["selector"]["directive"])
        self.assertEqual(to_json["prompt"]["system_role"], self.data["prompt"]["system_role"])
        self.assertEqual(to_json["prompt"]["model"], self.data["prompt"]["model"])
        self.assertEqual(to_json["prompt"]["temperature"], self.data["prompt"]["temperature"])
        self.assertEqual(to_json["prompt"]["max_tokens"], self.data["prompt"]["max_tokens"])

    def test_delete(self):
        """Test that we can delete a plugin using the Plugin."""
        plugin = Plugin(data=self.data)
        plugin_id = plugin.id
        plugin.delete()

        with self.assertRaises(PluginMeta.DoesNotExist):
            PluginMeta.objects.get(pk=plugin_id)

        with self.assertRaises(PluginSelector.DoesNotExist):
            PluginSelector.objects.get(plugin_id=plugin_id)

        with self.assertRaises(PluginPrompt.DoesNotExist):
            PluginPrompt.objects.get(plugin_id=plugin_id)

        with self.assertRaises(PluginData.DoesNotExist):
            PluginData.objects.get(plugin_id=plugin_id)

    def test_add_sample_plugins(self):
        """Test utility function to add sample plugins to a user account."""
        plugins_path = os.path.join(PROJECT_ROOT, "smarter/apps/plugin/data/sample-plugins/")

        # the number of sample plugins in the sample-plugins directory
        sample_plugins_count = sum(1 for _ in Path(plugins_path).rglob("*.yaml"))

        # add the sample plugins to the user account
        add_example_plugins(user_profile=self.user_profile)

        # verify that all of the sample plugins were added to the user account
        plugins = PluginMeta.objects.filter(author=self.user_profile)
        self.assertEqual(len(plugins), sample_plugins_count)

        # verify that all of the sample plugins were correctdly created
        # and are in a ready state.
        for plugin in plugins:
            self.assertTrue(Plugin(plugin_meta=plugin).ready)

    # pylint: disable=too-many-statements
    def test_validation_bad_structure(self):
        """Test that the Plugin raises an error when given bad data."""
        with self.assertRaises(ValidationError):
            Plugin(data={})

        bad_data = self.data.copy()
        bad_data.pop("meta_data")
        with self.assertRaises(ValidationError):
            Plugin(data=bad_data)

        bad_data = self.data.copy()
        bad_data.pop("selector")
        with self.assertRaises(ValidationError):
            Plugin(data=bad_data)

        bad_data = self.data.copy()
        bad_data.pop("prompt")
        with self.assertRaises(ValidationError):
            Plugin(data=bad_data)

        bad_data = self.data.copy()
        bad_data.pop("plugin_data")
        with self.assertRaises(ValidationError):
            Plugin(data=bad_data)

        bad_data = self.data.copy()
        bad_data["meta_data"].pop("name")
        with self.assertRaises(ValidationError):
            Plugin(data=bad_data)

        bad_data = self.data.copy()
        bad_data["selector"].pop("directive")
        with self.assertRaises(ValidationError):
            Plugin(data=bad_data)

        bad_data = self.data.copy()
        bad_data["prompt"].pop("system_role")
        with self.assertRaises(ValidationError):
            Plugin(data=bad_data)

        bad_data = self.data.copy()
        bad_data["prompt"].pop("model")
        with self.assertRaises(ValidationError):
            Plugin(data=bad_data)

        bad_data = self.data.copy()
        bad_data["prompt"].pop("temperature")
        with self.assertRaises(ValidationError):
            Plugin(data=bad_data)

        bad_data = self.data.copy()
        bad_data["prompt"].pop("max_tokens")
        with self.assertRaises(ValidationError):
            Plugin(data=bad_data)

        bad_data = self.data.copy()
        bad_data["plugin_data"].pop("description")
        with self.assertRaises(ValidationError):
            Plugin(data=bad_data)

        bad_data = self.data.copy()
        bad_data["plugin_data"].pop("return_data")
        with self.assertRaises(ValidationError):
            Plugin(data=bad_data)

    def test_validation_bad_data_types(self):
        """Test that the Plugin raises an error when given bad data."""
        bad_data = self.data.copy()
        bad_data["meta_data"]["tags"] = "not a list"
        with self.assertRaises(ValidationError):
            Plugin(data=bad_data)

        bad_data = self.data.copy()
        bad_data["selector"]["search_terms"] = "not a list"
        with self.assertRaises(ValidationError):
            Plugin(data=bad_data)

        bad_data = self.data.copy()
        bad_data["prompt"]["temperature"] = "not a float"
        with self.assertRaises(ValidationError):
            Plugin(data=bad_data)

        bad_data = self.data.copy()
        bad_data["prompt"]["max_tokens"] = "not an int"
        with self.assertRaises(ValidationError):
            Plugin(data=bad_data)

    def test_clone(self):
        """Test that we can clone a plugin using the Plugin."""
        plugin = Plugin(data=self.data)
        clone_id = plugin.clone()
        plugin_clone = Plugin(plugin_id=clone_id)

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
        self.assertEqual(plugin.plugin_data.return_data, plugin_clone.plugin_data.return_data)

        plugin.delete()
        plugin_clone.delete()

    def test_json_serialization(self):
        """Test that the Plugin generates correct JSON output."""
        plugin = Plugin(data=self.data)
        to_json = plugin.to_json()

        # ensure that we can go from json output to a string and back to json without error
        to_json = json.loads(json.dumps(to_json))

        # ensure that the json output still matches the original data
        self.assertIsInstance(to_json, dict)
        self.assertEqual(to_json["meta_data"]["name"], self.data["meta_data"]["name"])
        self.assertEqual(to_json["selector"]["directive"], self.data["selector"]["directive"])
        self.assertEqual(to_json["prompt"]["system_role"], self.data["prompt"]["system_role"])
        self.assertEqual(to_json["prompt"]["model"], self.data["prompt"]["model"])
        self.assertEqual(to_json["prompt"]["temperature"], self.data["prompt"]["temperature"])
        self.assertEqual(to_json["prompt"]["max_tokens"], self.data["prompt"]["max_tokens"])
