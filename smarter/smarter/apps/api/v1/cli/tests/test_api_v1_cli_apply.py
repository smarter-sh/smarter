# pylint: disable=wrong-import-position
"""Test api/v1/cli - Apply"""

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


class TestApiV1CliApply(TestCase):
    """Test api/v1/cli - Apply"""

    def setUp(self):
        """Set up test fixtures."""
        self.path = os.path.join(PYTHON_ROOT, "smarter", "apps", "api", "v1", "cli", "tests", "data")
        self.good_manifest_path = os.path.join(self.path, "good-plugin-manifest.yaml")

        self.account = Account.objects.create(name="Test Account", description="Test Account Description")
        with open(self.good_manifest_path, encoding="utf-8") as file:
            self.good_manifest_text = file.read()

    def test_valid_manifest_apply(self):
        """Test that we get OK responses for post, put, patch, delete when passing a valid manifest"""

        client = Client()
        url = reverse("api_v1_cli_apply_view")
        response = client.post(url, data=self.good_manifest_text)

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
        self.assertIsNone(static_data.get("platformProvider"))
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

    def test_valid_manifest_describe(self):
        """describe - test that we get OK responses on post using a valid manifest"""

        client = Client()
        url = reverse("api_v1_cli_describe_view", kwargs={"kind": "plugin", "name": "CliTestPlugin"})
        response = client.post(url)

        self.assertEqual(response.status_code, 200)

        print(response.content)

    def test_valid_manifest_api_v1_cli_deploy(self):
        """deploy - test that we get OK responses on post using a valid manifest"""

        client = Client()
        url = reverse("api_v1_cli_deploy_view", kwargs={"kind": "chatbot", "name": "example"})
        response = client.post(url, data=self.good_manifest_text)

        self.assertEqual(response.status_code, 200)

    def test_valid_manifest_api_v1_cli_logs(self):
        """logs - test that we get OK responses on post using a valid manifest"""

        client = Client()
        url = reverse("api_v1_cli_logs_kind_name_view", kwargs={"kind": "chatbot", "name": "CliTestPlugin"})
        response = client.post(url)

        self.assertEqual(response.status_code, 200)

    def test_valid_manifest_api_v1_cli_status(self):
        """status - test that we get OK responses on post using a valid manifest"""

        client = Client()
        url = reverse("api_v1_cli_status_view")
        response = client.post(url)

        self.assertEqual(response.status_code, 200)

    def test_valid_manifest_api_v1_cli_manifest(self):
        """manifest - test that we get OK responses on post using a valid manifest"""

        client = Client()
        url = reverse("api_v1_cli_manifest_view", kwargs={"kind": "plugin"})
        response = client.post(url)

        self.assertEqual(response.status_code, 200)

    def test_valid_manifest_api_v1_cli_whoami(self):
        """whoami - test that we get OK responses on post using a valid manifest"""

        client = Client()
        url = reverse("api_v1_cli_whoami_view")
        response = client.post(url)

        self.assertEqual(response.status_code, 200)

    def test_valid_manifest_api_v1_cli_delete(self):
        """delete - test that we get OK responses on post using a valid manifest"""

        client = Client()
        url = reverse("api_v1_cli_delete_view", kwargs={"kind": "chatbot", "name": "CliTestPlugin"})
        response = client.post(url, data=self.good_manifest_text)

        self.assertEqual(response.status_code, 200)
