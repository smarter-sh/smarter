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
from smarter.apps.plugin.providers import Plugin
from smarter.apps.plugin.tests.test_setup import get_test_file_path


HERE = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = str(Path(HERE).parent.parent)
PYTHON_ROOT = str(Path(PROJECT_ROOT).parent)
if PYTHON_ROOT not in sys.path:
    sys.path.append(PYTHON_ROOT)  # noqa: E402


class TestPluginProvider(unittest.TestCase):
    """Test OpenAI Function Calling hook for refers_to."""

    plugin_json: dict
    account: Account
    user: User
    user_profile: UserProfile

    def setUp(self):
        """Set up test fixtures."""
        config_path = get_test_file_path("everlasting-gobstopper.yaml")
        with open(config_path, "r", encoding="utf-8") as file:
            self.plugin_json = yaml.safe_load(file)

        self.user, _ = User.objects.get_or_create(username="testuser", password="12345")
        self.account, _ = Account.objects.get_or_create(company_name="Test Account")
        self.user_profile, _ = UserProfile.objects.get_or_create(user=self.user, account=self.account)

        self.plugin_json["user"] = self.user
        self.plugin_json["account"] = self.account
        self.plugin_json["meta_data"]["author"] = self.user_profile.id

    def tearDown(self):
        """Clean up test fixtures."""
        self.user_profile.delete()
        self.user.delete()
        self.account.delete()

    # pylint: disable=broad-exception-caught
    def test_create(self):
        """Test that we can create a plugin using the Plugin."""
        plugin = Plugin.create(self.plugin_json)

        self.assertIsInstance(plugin, PluginMeta)

        plugin_meta = PluginMeta.objects.get(pk=plugin.id)
        self.assertIsNotNone(plugin_meta)
        self.assertEqual(plugin_meta.name, self.plugin_json["meta_data"]["name"])

        plugin_selector = PluginSelector.objects.get(plugin=plugin_meta)
        self.assertIsNotNone(plugin_selector)
        self.assertEqual(plugin_selector.directive, self.plugin_json["selector"]["directive"])

        plugin_prompt = PluginPrompt.objects.get(plugin_id=plugin.id)
        self.assertIsNotNone(plugin_prompt)
        self.assertEqual(plugin_prompt.system_role, self.plugin_json["prompt"]["system_role"])
        self.assertEqual(plugin_prompt.model, self.plugin_json["prompt"]["model"])
        self.assertEqual(plugin_prompt.temperature, self.plugin_json["prompt"]["temperature"])
        self.assertEqual(plugin_prompt.max_tokens, self.plugin_json["prompt"]["max_tokens"])

        plugin_data = PluginData.objects.get(plugin_id=plugin.id)
        self.assertIsNotNone(plugin_data)
        self.assertEqual(plugin_data.description, self.plugin_json["plugin_data"]["description"])
        self.assertEqual(plugin_data.return_data, self.plugin_json["plugin_data"]["return_data"])

    def test_to_json(self):
        """Test that the Plugin generates correct JSON output."""
        plugin = Plugin.create(self.plugin_json)
        plugin_provider = Plugin(plugin.id)
        to_json = plugin_provider.to_json()

        self.assertIsInstance(to_json, dict)
        self.assertEqual(to_json["meta_data"]["name"], self.plugin_json["meta_data"]["name"])
        self.assertEqual(to_json["selector"]["directive"], self.plugin_json["selector"]["directive"])
        self.assertEqual(to_json["prompt"]["system_role"], self.plugin_json["prompt"]["system_role"])
        self.assertEqual(to_json["prompt"]["model"], self.plugin_json["prompt"]["model"])
        self.assertEqual(to_json["prompt"]["temperature"], self.plugin_json["prompt"]["temperature"])
        self.assertEqual(to_json["prompt"]["max_tokens"], self.plugin_json["prompt"]["max_tokens"])

    def test_delete(self):
        """Test that we can delete a plugin using the Plugin."""
        plugin = Plugin.create(self.plugin_json)
        self.plugin_json["plugin_id"] = plugin.id
        Plugin().delete(data=self.plugin_json)

        with self.assertRaises(PluginMeta.DoesNotExist):
            PluginMeta.objects.get(pk=plugin.id)

        with self.assertRaises(PluginSelector.DoesNotExist):
            PluginSelector.objects.get(plugin=plugin)

        with self.assertRaises(PluginPrompt.DoesNotExist):
            PluginPrompt.objects.get(plugin=plugin)

        with self.assertRaises(PluginData.DoesNotExist):
            PluginData.objects.get(plugin=plugin)
