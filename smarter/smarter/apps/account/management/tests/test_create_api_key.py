"""Test the create_api_key management command."""

import re

from django.core.management.base import CommandError

from smarter.common.utils import to_snake_case
from smarter.lib.drf.models import SmarterAuthToken

from .base import CommandTestBase


class TestCreateApiKey(CommandTestBase):
    def setUp(self):
        super().setUp()
        self.addCleanup(SmarterAuthToken.objects.filter(user_profile__account=self.account).delete)

    def test_by_username(self):
        output = self.run_command("create_api_key", username=self.admin_user.username, description="d")
        self.assertIn("API key:", output)
        self.assertTrue(
            # API key names are stored in snake_case.
            SmarterAuthToken.objects.filter(
                name=to_snake_case(f"{self.account.account_number}.{self.admin_user.username}")
            ).exists()
        )

    def test_by_account_number(self):
        output = self.run_command("create_api_key", account_number=self.account.account_number)
        self.assertIn("API key:", output)

    def test_by_account_number_and_username(self):
        output = self.run_command(
            "create_api_key", account_number=self.account.account_number, username=self.admin_user.username
        )
        self.assertIn("API key:", output)

    def test_errors(self):
        """Test that missing options, an unknown account, and an unknown user are refused with a message."""
        for options, message in (
            ({}, "Provide an --account_number, a --username, or both."),
            ({"account_number": "0000-0000-0000"}, "There is no account with the account number 0000-0000-0000."),
            ({"username": "no_such_user"}, "There is no user with the username no_such_user."),
            (
                {"account_number": self.account.account_number, "username": self.non_admin_user.username + "x"},
                "There is no user with the username",
            ),
        ):
            with self.subTest(options=options):
                with self.assertRaisesRegex(CommandError, re.escape(message)):
                    self.run_command("create_api_key", **options)
