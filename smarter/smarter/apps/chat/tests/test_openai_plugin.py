# pylint: disable=wrong-import-position
# pylint: disable=R0801,E1101
"""Test lambda_openai_v2 function."""

# python stuff
import os
import sys
import unittest
from pathlib import Path

from smarter.lib.django.user import User
from smarter.lib.unittest.utils import get_readonly_yaml_file


HERE = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = str(Path(HERE).parent.parent)
PYTHON_ROOT = str(Path(PROJECT_ROOT).parent)
if PYTHON_ROOT not in sys.path:
    sys.path.append(PYTHON_ROOT)  # noqa: E402


from smarter.apps.account.models import Account, UserProfile

# pylint: disable=no-name-in-module
from smarter.apps.plugin.plugin.static import PluginStatic

from .test_setup import get_test_file_path


class TestPlugin(unittest.TestCase):
    """Test Plugin."""

    def setUp(self):
        """Set up test fixtures."""
        username = "testuser_" + os.urandom(4).hex()
        self.user = User.objects.create(username=username, password="12345")
        self.account = Account.objects.create(company_name="Test Account")
        self.user_profile = UserProfile.objects.create(user=self.user, account=self.account, is_test=True)

        config_path = get_test_file_path("plugins/everlasting-gobstopper.yaml")
        plugin_json = get_readonly_yaml_file(config_path)
        plugin_json["user_profile"] = self.user_profile

        self.plugin = PluginStatic(data=plugin_json)

    def tearDown(self):
        """Tear down test fixtures."""
        self.user_profile.delete()
        self.user.delete()
        self.account.delete()
        self.plugin.delete()

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
