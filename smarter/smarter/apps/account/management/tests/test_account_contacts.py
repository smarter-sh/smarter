"""Test the add_account_contact and delete_account_contact management commands."""

from smarter.apps.account.models import AccountContact
from smarter.common.exceptions import SmarterValueError

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
        with self.assertRaises(SystemExit):
            self.run_command("add_account_contact", account_number="0000-0000-0000", email="a@example.com")
        with self.assertRaises(SystemExit):
            self.run_command("add_account_contact", company_name="not a company", email="a@example.com")
        self.run_command("delete_account_contact", account_number="0000-0000-0000", email="a@example.com")
        self.run_command("delete_account_contact", company_name="not a company", email="a@example.com")
        self.run_command(
            "delete_account_contact", account_number=self.account.account_number, email="nobody@example.com"
        )
        for command in ("add_account_contact", "delete_account_contact"):
            with self.subTest(command=command):
                with self.assertRaises(SmarterValueError):
                    self.run_command(command, email="a@example.com")
