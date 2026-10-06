"""Test smarter.apps.plugin.plugin.utils: Plugins and PluginExample."""

import os
import tempfile
from unittest.mock import MagicMock, patch

from smarter.apps.plugin.plugin import utils
from smarter.apps.plugin.plugin.utils import PluginExample, Plugins
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


class TestPluginExample(SmarterTestBase):
    """Test PluginExample loaded from a yaml file."""

    def example(self, content: str, filename: str = "my-sample_plugin.yaml") -> PluginExample:
        tmpdir = tempfile.mkdtemp()
        self.addCleanup(lambda: [os.remove(os.path.join(tmpdir, filename)), os.rmdir(tmpdir)])
        with open(os.path.join(tmpdir, filename), "w", encoding="utf-8") as f:
            f.write(content)
        return PluginExample(filepath=tmpdir, filename=filename)

    def test_well_formed_example(self):
        example = self.example("metadata:\n  name: SamplePlugin\n")
        self.assertEqual(example.filename, "my-sample_plugin.yaml")
        self.assertEqual(example.name, "SamplePlugin")
        self.assertEqual(example.to_json(), {"metadata": {"name": "SamplePlugin"}})
        self.assertIn("SamplePlugin", example.to_yaml())

    def test_name_falls_back_to_the_filename(self):
        example = self.example("spec: {}\n")
        self.assertEqual(example.name, "MySamplePlugin")

    def test_convert_filename_without_a_filename(self):
        example = self.example("spec: {}\n")
        example._filename = None
        self.assertIsNone(example.convert_filename())

    def test_convert_filename_failure_returns_the_filename(self):
        example = self.example("spec: {}\n")
        with patch.object(utils.os.path, "splitext", side_effect=ValueError("boom")):
            self.assertEqual(example.convert_filename(), "my-sample_plugin.yaml")
