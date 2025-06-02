# pylint: disable=wrong-import-position
# pylint: disable=R0801,E1101
"""Test lambda_openai_v2 function."""

from smarter.apps.account.tests.mixins import TestAccountMixin
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

        self.plugin = StaticPlugin(user_profile=self.user_profile, data=plugin_json)

    def tearDown(self):
        """Tear down test fixtures."""
        self.plugin.delete()
        super().tearDown()

    # pylint: disable=broad-exception-caught
    def test_get_additional_info(self):
        """Test default return value of function_calling_plugin()"""
        try:
            inquiry_type = inquiry_type = self.plugin.plugin_data.return_data_keys[0]
            return_data = self.plugin.function_calling_plugin(inquiry_type=inquiry_type)
        except Exception:
            self.fail("function_calling_plugin() raised ExceptionType")

        self.assertTrue(return_data is not None)

    def test_info_tool_factory(self):
        """Test integrity plugin_tool_factory()"""
        itf = self.plugin.custom_tool
        self.assertIsInstance(itf, dict)

        self.assertIsInstance(itf, dict)
        self.assertTrue("type" in itf)
        self.assertTrue("function" in itf)
