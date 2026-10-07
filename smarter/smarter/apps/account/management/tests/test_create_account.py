"""Test the create_account management command."""

from smarter.apps.account.models import Account

from .base import CommandTestBase


class TestCreateAccount(CommandTestBase):
    def test_create_by_account_number(self):
        """Test that an account is created with an account number, and then updated."""
        account_number = "9999-0000-0001"
        self.addCleanup(Account.objects.filter(account_number=account_number).delete)
        self.run_command("create_account", account_number=account_number, company_name="Test Command Company")
        account = Account.objects.get(account_number=account_number)
        self.assertEqual(account.company_name, "Test Command Company")
        self.assertEqual(account.name, "test_command_company")
        self.run_command("create_account", account_number=account_number, company_name="Renamed Company")
        self.assertEqual(Account.objects.get(account_number=account_number).company_name, "Renamed Company")

    def test_create_by_company_name(self):
        company_name = self.unique("TestCompany")
        self.addCleanup(Account.objects.filter(company_name=company_name).delete)
        self.run_command("create_account", company_name=company_name)
        self.assertTrue(Account.objects.filter(company_name=company_name).exists())
        self.run_command("create_account", company_name=company_name)
        self.assertEqual(Account.objects.filter(company_name=company_name).count(), 1)

    def test_neither(self):
        before = Account.objects.count()
        self.run_command("create_account")
        self.assertEqual(Account.objects.count(), before)
