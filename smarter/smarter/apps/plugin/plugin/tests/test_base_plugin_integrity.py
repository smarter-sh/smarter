"""Test PluginBase's integrity checks: ready, save() and name refuse plugin components of the wrong type."""

from unittest.mock import PropertyMock, patch

from smarter.apps.plugin.plugin.base import SmarterPluginError
from smarter.apps.plugin.plugin.sql import SqlPlugin

from .base_classes import PluginTestBase


class TestPluginBaseIntegrity(PluginTestBase):
    """Test that a plugin whose selector, prompt, data or metadata is missing or of the wrong type isn't ready, and can't be saved."""

    def plugin(self) -> SqlPlugin:
        plugin = SqlPlugin(plugin_id=self.sql_plugin.id, user_profile=self.user_profile)
        self.assertTrue(plugin.ready)
        return plugin

    def reset_ready(self, plugin: SqlPlugin) -> None:
        """Ready is a cached_property; forget its value."""
        plugin.__dict__.pop("ready", None)

    def patch_property(self, name: str, value) -> None:
        patcher = patch.object(SqlPlugin, name, new_callable=PropertyMock, return_value=value)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_not_ready_without_a_selector(self):
        plugin = self.plugin()
        self.reset_ready(plugin)
        self.patch_property("plugin_selector", None)
        self.assertFalse(plugin.ready)

    def test_not_ready_without_a_prompt(self):
        plugin = self.plugin()
        self.reset_ready(plugin)
        self.patch_property("plugin_prompt", None)
        self.assertFalse(plugin.ready)

    def test_not_ready_with_plugin_data_of_the_wrong_type(self):
        plugin = self.plugin()
        self.reset_ready(plugin)
        self.patch_property("plugin_data", "not plugin data")
        plugin._plugin_data = "not plugin data"  # type: ignore[assignment]
        self.assertFalse(plugin.ready)

    def test_not_ready_with_plugin_meta_of_the_wrong_type(self):
        plugin = self.plugin()
        self.reset_ready(plugin)
        self.patch_property("plugin_meta", "not a PluginMeta")
        plugin._plugin_meta = "not a PluginMeta"  # type: ignore[assignment]
        self.assertFalse(plugin.ready)
        with self.assertRaises(SmarterPluginError):
            _ = plugin.name

    def test_save_refuses_missing_components(self):
        """Save() raises for each component that is missing."""
        for name in ("plugin_meta", "plugin_selector", "plugin_prompt", "plugin_data"):
            with self.subTest(missing=name):
                plugin = self.plugin()
                with patch.object(SqlPlugin, name, new_callable=PropertyMock, return_value=None):
                    with self.assertRaises(SmarterPluginError):
                        plugin.save()

    def test_to_json_rejects_an_unknown_version(self):
        with self.assertRaises(SmarterPluginError):
            self.plugin().to_json(version="v0")
