# -*- coding: utf-8 -*-
# pylint: disable=wrong-import-position
# pylint: disable=R0801
"""Test providers."""

# python stuff
import os
import sys
import unittest
from pathlib import Path

import yaml
from django.contrib.auth.models import User

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
from smarter.apps.plugin.tests.test_setup import get_test_file_path


HERE = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = str(Path(HERE).parent.parent)
PYTHON_ROOT = str(Path(PROJECT_ROOT).parent)
if PYTHON_ROOT not in sys.path:
    sys.path.append(PYTHON_ROOT)  # noqa: E402


class TestPlugin(unittest.TestCase):
    """Test OpenAI Function Calling hook for refers_to."""

    data: dict
    account: Account
    user: User
    user_profile: UserProfile

    def setUp(self):
        """Set up test fixtures."""
        config_path = get_test_file_path("everlasting-gobstopper.yaml")
        with open(config_path, "r", encoding="utf-8") as file:
            self.data = yaml.safe_load(file)

        self.user, _ = User.objects.get_or_create(username="testuser", password="12345")
        self.account, _ = Account.objects.get_or_create(company_name="Test Account")
        self.user_profile, _ = UserProfile.objects.get_or_create(user=self.user, account=self.account)

        self.data["user"] = self.user
        self.data["account"] = self.account
        self.data["meta_data"]["author"] = self.user_profile.id

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
