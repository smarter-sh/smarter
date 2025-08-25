"""Tests for manage.py create_plugin."""

from logging import getLogger
from typing import Optional

from django.core.management import call_command

from smarter.apps.plugin.tests.base_classes import TestPluginClassBase
from smarter.apps.plugin.tests.test_setup import get_test_file_path


logger = getLogger(__name__)


class ManageCommandCreatePluginTestCase(TestPluginClassBase):
    """Tests for manage.py create_plugin."""

    # part of the abstract base class but not used for these tests
    model: Optional[str] = None

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        super().setUpClass()
        cls.file_path = get_test_file_path("everlasting-gobstopper.yaml")
        cls.plugin_name = "my_everlasting_super_duper_gobbstopper"

    def test_create_plugin(self):
        """Test creating a plugin."""

        call_command(
            "create_plugin",
            "--account_number",
            f"{self.account.account_number}",
            "--username",
            f"{self.admin_user.username}",
            "--file_path",
            f"{self.file_path}",
        )

    def test_retrieve_plugin(self):
        """Test retrieving a plugin."""

        logger.info("test_retrieve_plugin() - creating plugin for account %s", self.account.account_number)
        call_command(
            "create_plugin",
            "--account_number",
            f"{self.account.account_number}",
            "--username",
            f"{self.admin_user.username}",
            "--file_path",
            f"{self.file_path}",
        )
        logger.info("test_retrieve_plugin() - retrieving plugin...")
        call_command(
            "retrieve_plugin",
            "--account_number",
            f"{self.account.account_number}",
            "--username",
            f"{self.admin_user.username}",
            "--name",
            f"{self.plugin_name}",
        )

    def test_update_plugin(self):
        """Test updating a plugin."""

        call_command(
            "create_plugin",
            "--account_number",
            f"{self.account.account_number}",
            "--username",
            f"{self.admin_user.username}",
            "--file_path",
            f"{self.file_path}",
        )
        call_command(
            "update_plugin",
            "--account_number",
            f"{self.account.account_number}",
            "--username",
            f"{self.admin_user.username}",
            "--file_path",
            f"{self.file_path}",
        )

    def test_delete_plugin(self):
        """Test deleting a plugin."""

        call_command(
            "create_plugin",
            "--account_number",
            f"{self.account.account_number}",
            "--username",
            f"{self.admin_user.username}",
            "--file_path",
            f"{self.file_path}",
        )
        call_command(
            "delete_plugin",
            "--account_number",
            f"{self.account.account_number}",
            "--username",
            f"{self.admin_user.username}",
            "--name",
            f"{self.plugin_name}",
        )

    def test_add_plugin_examples(self):
        """Test adding plugin examples."""

        call_command("add_plugin_examples", "--username", f"{self.admin_user.get_username()}")

    def test_get_plugins(self):

        call_command(
            "get_plugins",
            "--account_number",
            f"{self.account.account_number}",
            "--username",
            f"{self.admin_user.username}",
        )
