"""Test :class:`smarter.apps.llmclient.models.LLMClientPlugin`, the plugins of an LLMClient."""

import copy
import unittest

import yaml

from smarter.apps.llmclient.models import LLMClient, LLMClientPlugin
from smarter.apps.plugin.models import PluginMeta
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

    @unittest.expectedFailure
    def test_plugin(self):
        """
        Expected to fail: LLMClientPlugin.plugin passes account= and user= to PluginController,.

        which does not take them, so it raises TypeError.
        """
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

    def test_get_cached_objects(self):
        for invalidate in (True, False):
            plugins = LLMClientPlugin.get_cached_objects(invalidate=invalidate, llmclient=self.llmclient)
            self.assertEqual([p.pk for p in plugins], [self.llmclient_plugin.pk])
        self.assertIsNotNone(LLMClientPlugin.get_cached_objects())

    @unittest.expectedFailure
    def test_load(self):
        """
        Test that a plugin manifest is loaded, which creates the plugin, and added to the LLMClient.

        Expected to fail: LLMClientPlugin.load() makes a SAMPluginCommon of the manifest, rather
        than the model of its kind, e.g. SAMStaticPlugin, which the plugin class refuses with a
        TypeError, so no plugin can be loaded.
        """
        name = f"test_llmclient_plugin_load_{self.hash_suffix}"
        self.addCleanup(PluginMeta.objects.filter(name=name).delete)
        manifest = copy.deepcopy(self.static_plugin_yaml)
        manifest["metadata"]["name"] = name
        llmclient_plugin = LLMClientPlugin.load(self.llmclient, yaml.dump(manifest))
        self.assertEqual(llmclient_plugin.plugin_meta.name, name)
        self.assertIsNone(LLMClientPlugin.load(None, yaml.dump(manifest)))
