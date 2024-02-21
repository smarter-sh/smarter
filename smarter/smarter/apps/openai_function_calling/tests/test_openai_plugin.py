# -*- coding: utf-8 -*-
# pylint: disable=wrong-import-position
# pylint: disable=R0801,E1101
"""Test lambda_openai_v2 function."""

# python stuff
import os
import sys
import unittest
from pathlib import Path

import yaml
from django.contrib.auth.models import User


HERE = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = str(Path(HERE).parent.parent)
PYTHON_ROOT = str(Path(PROJECT_ROOT).parent)
if PYTHON_ROOT not in sys.path:
    sys.path.append(PYTHON_ROOT)  # noqa: E402


from smarter.apps.account.models import Account, UserProfile
from smarter.apps.openai_function_calling.tests.test_setup import get_test_file_path

# pylint: disable=no-name-in-module
from smarter.apps.openai_function_calling.utils import (
    function_calling_plugin,
    plugin_tool_factory,
)
from smarter.apps.plugin.plugin import Plugin


class TestLambdaOpenaiFunctionRefersTo(unittest.TestCase):
    """Test OpenAI Function Calling hook for refers_to."""

    def setUp(self):
        """Set up test fixtures."""
        self.user, _ = User.objects.get_or_create(username="testuser", password="12345")
        self.account, _ = Account.objects.get_or_create(company_name="Test Account")
        self.user_profile, _ = UserProfile.objects.get_or_create(user=self.user, account=self.account)

        config_path = get_test_file_path("plugins/everlasting-gobstopper.yaml")
        with open(config_path, "r", encoding="utf-8") as file:
            plugin_json = yaml.safe_load(file)
        plugin_json["user_profile"] = self.user_profile

        self.plugin = Plugin(data=plugin_json)

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
            # pylint: disable=no-value-for-parameter
            return_data = function_calling_plugin(
                user=self.user, inquiry_type=self.plugin.plugin_data.return_data_keys[0]
            )
        except Exception:
            self.fail("function_calling_plugin() raised ExceptionType")

        self.assertTrue(return_data is not None)

    def test_info_tool_factory(self):
        """Test integrity plugin_tool_factory()"""
        itf = plugin_tool_factory(plugin=self.plugin)
        self.assertIsInstance(itf, dict)

        self.assertIsInstance(itf, dict)
        self.assertTrue("type" in itf)
        self.assertTrue("function" in itf)
