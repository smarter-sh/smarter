"""Tests for manage.py create_plugin."""

import os
import unittest

from django.core.management import call_command

from smarter.apps.account.models import Account, UserProfile
from smarter.apps.plugin.tests.test_setup import get_test_file_path
from smarter.lib.django.user import User


class ManageCommandCreatePluginTestCase(unittest.TestCase):
    """Tests for manage.py create_plugin."""

    def setUp(self):
        """Set up test fixtures."""
        self.file_path = get_test_file_path("everlasting-gobstopper.yaml")
        self.plugin_name = "MYEverlastingSUPERDUPERGobstopper"

        # create a 4-digit random string of alphanumeric characters
        username = "testuser_" + os.urandom(4).hex()
        self.user = User.objects.create(
            username=username, password="12345", is_active=True, is_staff=True, is_superuser=False
        )
        self.account = Account.objects.create(company_name="Test Account")
        self.user_profile = UserProfile.objects.create(user=self.user, account=self.account, is_test=True)

    def tearDown(self):
        """Clean up test fixtures."""
        self.user_profile.delete()
        self.user.delete()
        self.account.delete()

    def test_create_plugin(self):

        call_command(
            "create_plugin", "--account_number", f"{self.account.account_number}", "--file_path", f"{self.file_path}"
        )

    def test_retrieve_plugin(self):

        call_command(
            "create_plugin", "--account_number", f"{self.account.account_number}", "--file_path", f"{self.file_path}"
        )
        call_command("retrieve_plugin", f"{self.account.account_number}", f"{self.plugin_name}")

    def test_update_plugin(self):

        call_command(
            "create_plugin", "--account_number", f"{self.account.account_number}", "--file_path", f"{self.file_path}"
        )
        call_command("update_plugin", f"{self.account.account_number}", f"{self.file_path}")

    def test_delete_plugin(self):

        call_command(
            "create_plugin", "--account_number", f"{self.account.account_number}", "--file_path", f"{self.file_path}"
        )
        call_command("delete_plugin", f"{self.account.account_number}", f"{self.plugin_name}")

    def test_add_plugin_examples(self):

        call_command("add_plugin_examples", f"{self.user.get_username()}")

    def test_get_plugins(self):

        call_command("get_plugins", f"{self.account.account_number}")
