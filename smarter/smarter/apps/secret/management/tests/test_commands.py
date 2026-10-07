"""
Test the secret app's get_secret and update_secret management commands.

The tests call the commands by name, as ``manage.py`` does, so they also prove that no other app
defines a command with the same name, which would shadow them.
"""

from io import StringIO
from unittest.mock import patch

from django.core.management import call_command, get_commands
from django.utils.crypto import get_random_string

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.secret.management.commands import get_secret, update_secret
from smarter.apps.secret.models import Secret


class TestSecretCommands(TestAccountMixin):
    """Test the secret app's get_secret and update_secret commands."""

    def setUp(self):
        super().setUp()
        self.name = f"test_secret_{get_random_string(8).lower()}"
        self.secret = Secret.objects.create(
            user_profile=self.user_profile, name=self.name, description="d", encrypted_value=Secret.encrypt("first")
        )
        self.addCleanup(Secret.objects.filter(pk=self.secret.pk).delete)

    def run_command(self, module, **options) -> str:
        """Run the command that the module defines, by name, and return its output."""
        out = StringIO()
        call_command(module.__name__.rsplit(".", 1)[1], stdout=out, stderr=out, **options)
        return out.getvalue()

    def get_value(self) -> str:
        self.secret.refresh_from_db()
        return self.secret.get_secret(update_last_accessed=False)

    def test_commands_belong_to_the_secret_app(self):
        """Manage.py runs the secret app's commands: no other app shadows them."""
        commands = get_commands()
        for name in ("get_secret", "update_secret"):
            with self.subTest(command=name):
                self.assertEqual(commands[name], "smarter.apps.secret")

    def test_get_secret(self):
        output = self.run_command(get_secret, name=self.name, username=self.admin_user.username)
        self.assertIn("first", output)

    def test_get_secret_missing_arguments(self):
        self.assertNotIn("first", self.run_command(get_secret))
        self.assertNotIn("first", self.run_command(get_secret, name=self.name))

    def test_get_secret_not_found(self):
        self.assertNotIn("first", self.run_command(get_secret, name=self.name, username="not_a_user"))
        self.assertNotIn("first", self.run_command(get_secret, name="not_a_secret", username=self.admin_user.username))

    def test_get_secret_missing_user_profile(self):
        with patch.object(get_secret.UserProfile, "get_cached_object", return_value=None):
            output = self.run_command(get_secret, name=self.name, username=self.admin_user.username)
        self.assertNotIn("first", output)

    def test_get_secret_decryption_error(self):
        with patch.object(Secret, "get_secret", side_effect=ValueError("bad key")):
            output = self.run_command(get_secret, name=self.name, username=self.admin_user.username)
        self.assertNotIn("first", output)

    def test_update_secret(self):
        self.run_command(update_secret, name=self.name, username=self.admin_user.username, value="second")
        self.assertEqual(self.get_value(), "second")

    def test_update_secret_prompts_for_value(self):
        with patch.object(update_secret.getpass, "getpass", return_value="prompted"):
            self.run_command(update_secret, name=self.name, username=self.admin_user.username)
        self.assertEqual(self.get_value(), "prompted")

    def test_update_secret_missing_arguments(self):
        self.assertIn("You must provide a name", self.run_command(update_secret, value="x"))
        self.assertIn("No username provided", self.run_command(update_secret, name=self.name, value="x"))
        self.assertEqual(self.get_value(), "first")

    def test_update_secret_not_found(self):
        with self.assertRaises(SystemExit):
            self.run_command(update_secret, name=self.name, username="not_a_user", value="x")
        with self.assertRaises(SystemExit):
            self.run_command(update_secret, name="not_a_secret", username=self.admin_user.username, value="x")
        self.assertEqual(self.get_value(), "first")

    def test_update_secret_missing_user_profile(self):
        with patch.object(update_secret.UserProfile, "get_cached_object", return_value=None):
            self.run_command(update_secret, name=self.name, username=self.admin_user.username, value="x")
        self.assertEqual(self.get_value(), "first")

    def test_update_secret_save_error(self):
        with patch.object(Secret, "save", side_effect=RuntimeError("db down")):
            with self.assertRaises(SystemExit):
                self.run_command(update_secret, name=self.name, username=self.admin_user.username, value="x")
        self.assertEqual(self.get_value(), "first")
