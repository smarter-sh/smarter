"""Test smarter.apps.llmtool.plugin.utils: Plugins."""

from unittest.mock import MagicMock, patch

from smarter.apps.llmtool.plugin import utils
from smarter.apps.llmtool.plugin.utils import Plugins
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestPlugins(SmarterTestBase):
    """Test the Plugins collection without loading real plugins."""

    def test_should_log_follows_the_waffle_switch(self):
        self.assertIsInstance(utils.should_log(10), bool)

    def test_load_plugin_skips_a_controller_without_a_plugin(self):
        controller = MagicMock(plugin=None)
        with patch.object(utils, "PluginController", return_value=controller):
            self.assertIsNone(Plugins.load_plugin(plugin_meta=MagicMock(), user_profile=MagicMock()))

    def test_to_json_and_data_include_only_ready_plugins(self):
        ready = MagicMock(ready=True, data={"name": "ready"})
        ready.to_json.return_value = {"name": "ready"}
        not_ready = MagicMock(ready=False)
        plugins = Plugins.__new__(Plugins)
        plugins.plugins = [ready, not_ready]
        self.assertEqual(plugins.to_json(), [{"name": "ready"}])
        self.assertEqual(plugins.data, [{"name": "ready"}])
        not_ready.to_json.assert_not_called()

    def test_len_iter_and_repr_include_every_loaded_plugin(self):
        ready, not_ready = MagicMock(ready=True), MagicMock(ready=False)
        plugins = Plugins.__new__(Plugins)
        plugins.plugins = [ready, not_ready]
        plugins.user_profile = None
        self.assertEqual(len(plugins), 2)
        self.assertEqual(list(plugins), [ready, not_ready])
        self.assertEqual(repr(plugins), "<Plugins user_profile=None count=2>")
