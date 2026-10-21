"""Test the add_account_contact and delete_account_contact management commands."""

import re
from unittest.mock import patch

from django.core.management.base import CommandError

from smarter.apps.account.models import AccountContact

from .base import CommandTestBase


class TestAccountContactCommands(CommandTestBase):
    def contact_exists(self, email: str) -> bool:
        return AccountContact.objects.filter(account=self.account, email=email).exists()

    def test_add_and_delete_by_account_number(self):
        email = f"{self.unique()}@example.com"
        self.addCleanup(AccountContact.objects.filter(account=self.account, email=email).delete)
        self.run_command("add_account_contact", account_number=self.account.account_number, email=email)
        self.assertTrue(self.contact_exists(email))
        self.run_command("add_account_contact", account_number=self.account.account_number, email=email)
        self.assertEqual(AccountContact.objects.filter(account=self.account, email=email).count(), 1)
        self.run_command("delete_account_contact", account_number=self.account.account_number, email=email)
        self.assertFalse(self.contact_exists(email))

    def test_add_and_delete_by_company_name_and_username(self):
        email = self.non_admin_user.email
        self.addCleanup(AccountContact.objects.filter(account=self.account, email=email).delete)
        self.run_command(
            "add_account_contact", company_name=self.account.company_name, username=self.non_admin_user.username
        )
        self.assertTrue(self.contact_exists(email))
        self.run_command(
            "delete_account_contact", company_name=self.account.company_name, username=self.non_admin_user.username
        )
        self.assertFalse(self.contact_exists(email))

    def test_errors(self):
        """Test an unknown account, an unknown contact, and no account."""
        for command in ("add_account_contact", "delete_account_contact"):
            for options, message in (
                (
                    {"account_number": "0000-0000-0000", "email": "a@example.com"},
                    "There is no account with the account number 0000-0000-0000.",
                ),
                (
                    {"company_name": "not a company", "email": "a@example.com"},
                    "There is no account with the company name not a company.",
                ),
                ({"email": "a@example.com"}, "Provide an --account_number or a --company_name."),
                ({"account_number": self.account.account_number}, "Provide an --email, or the --username of a user."),
                (
                    {"account_number": self.account.account_number, "username": "no_such_user"},
                    "There is no user with the username no_such_user.",
                ),
            ):
                with self.subTest(command=command, options=options):
                    with self.assertRaisesRegex(CommandError, re.escape(message)):
                        self.run_command(command, **options)
        with self.assertRaisesRegex(CommandError, "nobody@example.com is not a contact of account"):
            self.run_command(
                "delete_account_contact", account_number=self.account.account_number, email="nobody@example.com"
            )

    def test_language(self):
        """Test that a new contact is welcomed in the given language, and an existing one isn't welcomed again."""
        email = f"{self.unique()}@example.com"
        self.addCleanup(AccountContact.objects.filter(account=self.account, email=email).delete)
        with patch.object(AccountContact, "send_welcome_email") as send:
            self.run_command(
                "add_account_contact", account_number=self.account.account_number, email=email, language="fr"
            )
            send.assert_called_once_with(language="fr")
            self.run_command(
                "add_account_contact", account_number=self.account.account_number, email=email, language="fr"
            )
            send.assert_called_once()
            with self.assertRaises(CommandError):
                self.run_command(
                    "add_account_contact", "--language=xx", account_number=self.account.account_number, email=email
                )
