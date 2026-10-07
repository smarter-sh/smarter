"""Test :class:`smarter.apps.llmclient.models.LLMClientPlugin`, the plugins of an LLMClient."""

import copy
from unittest import mock

import yaml

from smarter.apps.llmclient.models import LLMClient, LLMClientPlugin
from smarter.apps.plugin.models import PluginDataSql, PluginMeta
from smarter.apps.plugin.tests.base_classes import PluginAppTestBase


class TestLLMClientPlugin(PluginAppTestBase):
    """Test an LLMClient's plugins, with the class fixture static_plugin."""

    def setUp(self):
        super().setUp()
        self.llmclient = LLMClient.objects.create(
            name=f"test_llmclient_plugin_{self.hash_suffix}", user_profile=self.user_profile
        )
        self.addCleanup(self.llmclient.delete)
        self.llmclient_plugin = LLMClientPlugin.objects.create(
            llmclient=self.llmclient, plugin_meta=self.static_plugin.plugin_meta
        )

    def test_str(self):
        self.assertIn(self.static_plugin.plugin_meta.name, str(self.llmclient_plugin))

    def test_plugin(self):
        """Test that the LLMClientPlugin's plugin is the plugin of its PluginMeta."""
        plugin = self.llmclient_plugin.plugin
        self.assertEqual(plugin.plugin_meta.pk, self.static_plugin.plugin_meta.pk)
        self.assertIsNone(LLMClientPlugin(plugin_meta=self.static_plugin.plugin_meta).plugin)

    def test_plugins(self):
        plugins = LLMClientPlugin.plugins(self.llmclient)
        self.assertEqual([plugin.name for plugin in plugins], [self.static_plugin.name])
        self.assertEqual(LLMClientPlugin.plugins(None), [])
        data = LLMClientPlugin.plugins_json(self.llmclient)
        self.assertEqual(len(data), 1)
        self.assertIsInstance(data[0], dict)

    def test_plugins_skips_plugin_that_fails_to_load(self):
        """A plugin that raises while loading is logged and skipped rather than failing the LLMClient.

        This is the shape of a Sql plugin whose PluginDataSql row was cascade-deleted with its SqlConnection.
        """
        with (
            mock.patch(
                "smarter.apps.llmclient.models.llmclient_plugin.PluginController",
                side_effect=PluginDataSql.DoesNotExist("No PluginDataSql found for plugin_id: 0"),
            ),
            self.assertLogs("smarter.apps.llmclient.models.llmclient_plugin", level="ERROR") as logs,
        ):
            self.assertEqual(LLMClientPlugin.plugins(self.llmclient), [])
        self.assertIn(self.static_plugin.plugin_meta.name, logs.output[0])
        self.assertIn("failed to load", logs.output[0])

    def test_plugins_skips_plugin_that_does_not_load(self):
        """A controller that yields no plugin is logged and skipped."""
        controller = mock.MagicMock(plugin=None)
        with (
            mock.patch("smarter.apps.llmclient.models.llmclient_plugin.PluginController", return_value=controller),
            self.assertLogs("smarter.apps.llmclient.models.llmclient_plugin", level="ERROR") as logs,
        ):
            self.assertEqual(LLMClientPlugin.plugins(self.llmclient), [])
        self.assertIn("did not load", logs.output[0])

    def test_get_cached_objects(self):
        for invalidate in (True, False):
            plugins = LLMClientPlugin.get_cached_objects(invalidate=invalidate, llmclient=self.llmclient)
            self.assertEqual([p.pk for p in plugins], [self.llmclient_plugin.pk])
        self.assertIsNotNone(LLMClientPlugin.get_cached_objects())

    def test_load(self):
        """Test that a plugin manifest is loaded, which creates the plugin, and added to the LLMClient."""
        name = f"test_llmclient_plugin_load_{self.hash_suffix}"
        self.addCleanup(PluginMeta.objects.filter(name=name).delete)
        manifest = copy.deepcopy(self.static_plugin_yaml)
        manifest["metadata"]["name"] = name
        llmclient_plugin = LLMClientPlugin.load(self.llmclient, yaml.dump(manifest))
        self.assertEqual(llmclient_plugin.plugin_meta.name, name)
        self.assertIsNone(LLMClientPlugin.load(None, yaml.dump(manifest)))
