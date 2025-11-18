# pylint: disable=wrong-import-position
# pylint: disable=R0801,E1101
"""Test lambda_openai_v2 function."""

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.plugin.manifest.controller import PluginController
from smarter.apps.plugin.plugin.static import StaticPlugin
from smarter.common.utils import get_readonly_yaml_file

from .test_setup import get_test_file_path


class TestStaticPlugin(TestAccountMixin):
    """Test Plugin."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        config_path = get_test_file_path("plugins/everlasting-gobstopper.yaml")
        plugin_json = get_readonly_yaml_file(config_path)
        plugin_json["user_profile"] = self.user_profile

        plugin_controller = PluginController(
            user_profile=self.user_profile,
            account=self.account,
            user=self.user_profile.user,  # type: ignore
            manifest=plugin_json,
        )
        if not plugin_controller or not plugin_controller.plugin:
            raise ValueError("PluginController could not be created or plugin is None")

        if not isinstance(plugin_controller.plugin, StaticPlugin):
            raise ValueError("Expected StaticPlugin but got different plugin type")
        self.plugin: StaticPlugin = plugin_controller.plugin

    def tearDown(self):
        """Tear down test fixtures."""
        self.plugin.delete()
        super().tearDown()

    # pylint: disable=broad-exception-caught
    def test_get_additional_info(self):
        """Test default return value of tool_call_fetch_plugin_response()"""
        if not self.plugin:
            self.fail("self.plugin is None")
        if not self.plugin.plugin_data:
            self.fail("self.plugin.plugin_data is None")
        if not self.plugin.plugin_data.return_data_keys:
            self.fail("self.plugin.plugin_data.return_data_keys is None")
        try:
            inquiry_type = self.plugin.plugin_data.return_data_keys[0]
            function_args = {
                "inquiry_type": inquiry_type,
            }
            return_data = self.plugin.tool_call_fetch_plugin_response(function_args=function_args)
        except Exception:
            self.fail("tool_call_fetch_plugin_response() raised ExceptionType")

        self.assertTrue(return_data is not None)

    def test_info_tool_factory(self):
        """Test integrity plugin_tool_factory()"""
        itf = self.plugin.custom_tool
        self.assertIsInstance(itf, dict)

        self.assertIsInstance(itf, dict)
        self.assertTrue("type" in itf)
        self.assertTrue("function" in itf)
