"""Tests for manage.py create_plugin."""

from django.core.management import call_command

from smarter.apps.plugin.tests.base_classes import TestPluginClassBase
from smarter.apps.plugin.tests.test_setup import get_test_file_path


class ManageCommandCreatePluginTestCase(TestPluginClassBase):
    """Tests for manage.py create_plugin."""

    # part of the abstract base class but not used for these tests
    model = None

    def setUp(self):
        """Set up test fixtures."""
        self.file_path = get_test_file_path("everlasting-gobstopper.yaml")
        self.plugin_name = "MYEverlastingSUPERDUPERGobstopper"

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

        call_command("add_plugin_examples", f"{self.admin_user.get_username()}")

    def test_get_plugins(self):

        call_command("get_plugins", f"{self.account.account_number}")
