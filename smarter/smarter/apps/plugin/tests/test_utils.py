# pylint: disable=wrong-import-position
"""
Test :mod:`smarter.apps.plugin.utils`.

``add_example_plugins()`` applies Secret and Connection manifests with
``manage.py apply_manifest``, and then creates each example plugin with a
PluginController. Both are mocked, so that these tests verify the function's
own logic without creating the examples.
"""

import os
from unittest import mock

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.plugin.plugin.utils import PluginExamples
from smarter.apps.plugin.utils import add_example_plugins, get_plugin_examples_by_name
from smarter.common.exceptions import SmarterValueError
from smarter.lib import logging

logger = logging.getLogger(__name__)

UTILS_MODULE = "smarter.apps.plugin.utils"
EXAMPLE_MANIFESTS_APPLIED = 5
"""The number of Secret and Connection manifests that add_example_plugins() applies."""


class TestPluginUtils(TestAccountMixin):
    """Test add_example_plugins() and get_plugin_examples_by_name()."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.example_names = [example.name for example in PluginExamples().plugins]
        cls.example_files = [
            filename for filename in os.listdir(PluginExamples.PLUGINS_PATH) if filename.endswith(".yaml")
        ]

    # -------------------------------------------------------------------------
    # get_plugin_examples_by_name()
    # -------------------------------------------------------------------------
    def test_get_plugin_examples_by_name(self):
        """Test that get_plugin_examples_by_name() returns the name of every example."""
        names = get_plugin_examples_by_name()
        self.assertIsInstance(names, list)
        self.assertEqual(len(names), len(self.example_files))  # type: ignore[arg-type]
        self.assertIn("everlasting_gobstopper", names)  # type: ignore[arg-type]
        for name in names:  # type: ignore[union-attr]
            self.assertIsInstance(name, str)

    def test_get_plugin_examples_by_name_unique(self):
        """Test that the examples' names are unique, so that none overwrites another."""
        names = get_plugin_examples_by_name()
        self.assertEqual(len(names), len(set(names)))  # type: ignore[arg-type]

    # -------------------------------------------------------------------------
    # add_example_plugins()
    # -------------------------------------------------------------------------
    def test_add_example_plugins_requires_user_profile(self):
        """Test that add_example_plugins() requires a UserProfile."""
        with self.assertRaises(SmarterValueError):
            add_example_plugins(user_profile=None)
        with self.assertRaises(SmarterValueError):
            add_example_plugins(user_profile=self.admin_user)  # type: ignore[arg-type]

    def test_add_example_plugins(self):
        """Test that add_example_plugins() applies the prerequisites, and then creates every example."""
        with (
            mock.patch(f"{UTILS_MODULE}.call_command") as call_command,
            mock.patch(f"{UTILS_MODULE}.PluginController") as plugin_controller,
        ):
            self.assertTrue(add_example_plugins(user_profile=self.user_profile))

        self.assertEqual(call_command.call_count, EXAMPLE_MANIFESTS_APPLIED)
        for call in call_command.call_args_list:
            self.assertEqual(call.args[0], "apply_manifest")
            self.assertEqual(call.kwargs["username"], self.admin_user.username)
            self.assertTrue(os.path.isfile(call.kwargs["filespec"]), call.kwargs["filespec"])

        self.assertEqual(plugin_controller.call_count, len(self.example_files))
        created = [call.kwargs["manifest"]["metadata"]["name"] for call in plugin_controller.call_args_list]
        self.assertCountEqual(created, self.example_names)
        for call in plugin_controller.call_args_list:
            self.assertEqual(call.kwargs["user_profile"], self.user_profile)

    def test_add_example_plugins_apply_failure(self):
        """Test that add_example_plugins() stops if a prerequisite cannot be applied."""
        with (
            mock.patch(f"{UTILS_MODULE}.call_command", side_effect=ValueError("boom")),
            mock.patch(f"{UTILS_MODULE}.PluginController") as plugin_controller,
        ):
            with self.assertRaises(SmarterValueError):
                add_example_plugins(user_profile=self.user_profile)
        plugin_controller.assert_not_called()

    def test_add_example_plugins_skips_failures(self):
        """Test that add_example_plugins() skips an example that cannot be created, and creates the others."""
        failing_name = "everlasting_gobstopper"

        # pylint: disable=W0613
        def controller(user_profile, manifest):
            if manifest["metadata"]["name"] == failing_name:
                raise ValueError("missing prerequisite")
            return mock.MagicMock()

        with (
            mock.patch(f"{UTILS_MODULE}.call_command"),
            mock.patch(f"{UTILS_MODULE}.PluginController", side_effect=controller) as plugin_controller,
        ):
            self.assertFalse(add_example_plugins(user_profile=self.user_profile))
        self.assertEqual(plugin_controller.call_count, len(self.example_files))

    def test_add_example_plugins_invalid_yaml(self):
        """Test that add_example_plugins() rejects an example without a yaml representation."""
        example = mock.MagicMock()
        example.name = "broken_example"
        example.to_yaml.return_value = None
        examples = mock.MagicMock()
        examples.plugins = [example]
        with (
            mock.patch(f"{UTILS_MODULE}.call_command"),
            mock.patch(f"{UTILS_MODULE}.PluginExamples", return_value=examples),
            mock.patch(f"{UTILS_MODULE}.PluginController") as plugin_controller,
        ):
            with self.assertRaises(SmarterValueError):
                add_example_plugins(user_profile=self.user_profile)
        plugin_controller.assert_not_called()
