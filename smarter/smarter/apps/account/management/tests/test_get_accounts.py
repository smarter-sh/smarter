"""Test the get_accounts management command."""

from unittest.mock import patch

from django.core.exceptions import ValidationError

from .base import CommandTestBase


class TestGetAccounts(CommandTestBase):
    def test_all_and_filtered(self):
        with patch("builtins.print") as mock_print:
            self.run_command("get_accounts")
            self.run_command("get_accounts", self.account.name)
        filtered = mock_print.call_args_list[-1].args[0]
        self.assertEqual(
            [
                account["accountNumber"] if "accountNumber" in account else account["account_number"]
                for account in filtered
            ],
            [self.account.account_number],
        )

    def test_invalid_regex(self):
        with self.assertRaises(ValidationError):
            self.run_command("get_accounts", "[unclosed")
