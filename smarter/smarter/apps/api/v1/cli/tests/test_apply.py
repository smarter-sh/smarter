# pylint: disable=wrong-import-position
"""Test Api V1 CLI - Apply."""

import os

from django.test import Client, TestCase
from django.urls import reverse

from smarter.apps.account.models import Account
from smarter.apps.plugin.models import (
    PluginDataStatic,
    PluginMeta,
    PluginPrompt,
    PluginSelector,
)
from smarter.common.const import PYTHON_ROOT


class TestV1CliApply(TestCase):
    """Test Api V1 CLI - Apply"""

    def setUp(self):
        """Set up test fixtures."""
        self.path = os.path.join(PYTHON_ROOT, "smarter", "apps", "api", "v1", "cli", "tests", "data")
        self.good_manifest_path = os.path.join(self.path, "good-plugin-manifest.yaml")

        self.account = Account.objects.create(name="Test Account", description="Test Account Description")
        with open(self.good_manifest_path, encoding="utf-8") as file:
            self.good_manifest_text = file.read()

        self.client = Client()
        self.url = reverse("api_v1_cli_apply_view")

    def test_valid_manifest(self):
        """Test that we get OK responses for post, put, patch, delete when passing a valid manifest"""

        response = self.client.post(self.url, data=self.good_manifest_text)
        self.assertEqual(response.status_code, 200)

        # meta data
        plugin_meta = PluginMeta.objects.get(name="ExampleConfiguration", account=self.account, plugin_class="static")
        self.assertIsNotNone(plugin_meta)
        self.assertEqual(plugin_meta.version, "0.2.0")

        # static data
        plugin_data_static = PluginDataStatic.objects.get(plugin_meta=plugin_meta)
        self.assertIsNotNone(plugin_data_static)
        self.assertTrue(plugin_data_static.description.startswith("an example plugin to integrate with OpenAI"))
        static_data = plugin_data_static.sanitized_return_data
        self.assertTrue(isinstance(static_data, dict))
        self.assertIsNone(static_data.get("platformPprovider"))
        self.assertIsNone(static_data.get("about"))
        self.assertIsNone(static_data.get("links"))

        # prompt data
        plugin_prompt = PluginPrompt.objects.get(plugin_meta=plugin_meta)
        self.assertIsNotNone(plugin_prompt)
        self.assertTrue(
            plugin_prompt.system_role.startswith(
                "Your job is to provide helpful technical information about the OpenAI API Function"
            )
        )
        self.assertEqual(plugin_prompt.model, "gpt-3.5-turbo-1106")
        self.assertEqual(plugin_prompt.temperature, 0.5)
        self.assertEqual(plugin_prompt.max_tokens, 256)

        # selector data
        plugin_selector = PluginSelector.objects.get(plugin_meta=plugin_meta)
        self.assertIsNotNone(plugin_selector)
        self.assertEqual(plugin_selector.directive, "directive")
        self.assertTrue(isinstance(plugin_selector.search_terms, list))
        self.assertTrue("example function calling configuration" in plugin_selector.search_terms)
