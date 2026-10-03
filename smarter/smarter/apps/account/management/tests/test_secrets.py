"""Test the get_secret and update_secret management commands."""

from unittest.mock import patch

from smarter.apps.secret.models import Secret

from .base import CommandTestBase


class TestSecretCommands(CommandTestBase):
    def setUp(self):
        super().setUp()
        self.name = self.unique("test_secret")
        self.secret = Secret.objects.create(
            user_profile=self.user_profile, name=self.name, description="d", encrypted_value=Secret.encrypt("first")
        )
        self.addCleanup(Secret.objects.filter(pk=self.secret.pk).delete)

    def test_get_secret(self):
        output = self.run_command("get_secret", name=self.name, username=self.admin_user.username)
        self.assertIn("first", output)

    def test_update_secret(self):
        self.run_command("update_secret", name=self.name, username=self.admin_user.username, value="second")
        self.secret.refresh_from_db()
        self.assertEqual(self.secret.get_secret(update_last_accessed=False), "second")

    def test_update_secret_prompts_for_value(self):
        with patch("smarter.apps.account.management.commands.update_secret.getpass.getpass", return_value="prompted"):
            self.run_command("update_secret", name=self.name, username=self.admin_user.username)
        self.secret.refresh_from_db()
        self.assertEqual(self.secret.get_secret(update_last_accessed=False), "prompted")

    def test_missing_arguments(self):
        for command in ("get_secret", "update_secret"):
            with self.subTest(command=command):
                self.assertNotIn("first", self.run_command(command))
                self.assertNotIn("first", self.run_command(command, name=self.name))

    def test_get_secret_not_found(self):
        self.assertNotIn("first", self.run_command("get_secret", name=self.name, username="not_a_user"))
        self.assertNotIn(
            "first", self.run_command("get_secret", name="not_a_secret", username=self.admin_user.username)
        )

    def test_update_secret_not_found(self):
        with self.assertRaises(SystemExit):
            self.run_command("update_secret", name=self.name, username="not_a_user", value="x")
        with self.assertRaises(SystemExit):
            self.run_command("update_secret", name="not_a_secret", username=self.admin_user.username, value="x")
