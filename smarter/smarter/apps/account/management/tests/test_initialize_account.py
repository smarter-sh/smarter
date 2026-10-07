"""Test the initialize_account management command, whose sub-commands are patched."""

from unittest.mock import patch

from django.contrib.auth.models import User

from .base import CommandTestBase

MODULE = "smarter.apps.account.management.commands.initialize_account"


class TestInitializeAccount(CommandTestBase):
    def setUp(self):
        super().setUp()
        patcher = patch(f"{MODULE}.call_command")
        self.call = patcher.start()
        self.addCleanup(patcher.stop)

    def names(self) -> list[str]:
        return [c.args[0] for c in self.call.call_args_list]

    def options(self, **overrides) -> dict:
        options = {
            "account_number": self.account.account_number,
            "username": self.non_admin_user.username,
            "email": self.non_admin_user.email,
            "password": "a-password",
            "company_name": self.account.company_name,
        }
        options.update(overrides)
        return {k: v for k, v in options.items() if v is not None}

    def test_existing_user(self):
        """Test that an existing user is updated, and the account's examples are loaded."""
        self.addCleanup(User.objects.filter(pk=self.non_admin_user.pk).update, is_superuser=False, is_staff=False)
        self.run_command("initialize_account", **self.options())
        user = User.objects.get(pk=self.non_admin_user.pk)
        self.assertTrue(user.is_superuser)
        self.assertEqual(self.names()[0], "create_account")
        self.assertIn("load_from_github", self.names())
        self.assertIn("create_stackademy", self.names())

    def test_new_user(self):
        self.run_command("initialize_account", **self.options(username=self.unique("newuser"), email="bad email"))
        self.assertIn("create_user", self.names())

    def test_invalid_arguments(self):
        """Test that a missing or invalid argument stops the command before any sub-command."""
        for overrides in (
            {"account_number": None},
            {"account_number": "not-an-account"},
            {"username": None},
            {"username": "bad user!"},
            {"password": None},
            {"company_name": None},
        ):
            with self.subTest(overrides=overrides):
                self.call.reset_mock()
                self.run_command("initialize_account", **self.options(**overrides))
                self.call.assert_not_called()

    def test_initialize_account_without_password(self):
        from smarter.apps.account.management.commands.initialize_account import (  # pylint: disable=import-outside-toplevel
            Command,
        )

        command = Command()
        self.assertFalse(
            command.initialize_account(
                self.account.account_number, self.unique("nouser"), "a@example.com", None, "Company"
            )
        )
        self.assertTrue(
            command.initialize_account(
                self.account.account_number, self.admin_user.username, "a@example.com", None, "Company"
            )
        )

    def test_all(self):
        self.run_command("initialize_account", all=True)
        self.assertIn("create_account", self.names())
