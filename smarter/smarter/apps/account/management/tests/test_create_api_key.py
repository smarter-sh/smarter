"""Test the create_api_key management command."""

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
            SmarterAuthToken.objects.filter(name=f"{self.account.account_number}.{self.admin_user.username}").exists()
        )

    def test_by_account_number(self):
        output = self.run_command("create_api_key", account_number=self.account.account_number)
        self.assertIn("API key:", output)

    def test_by_account_number_and_username(self):
        output = self.run_command(
            "create_api_key", account_number=self.account.account_number, username=self.admin_user.username
        )
        self.assertIn("API key:", output)

    def test_neither(self):
        self.assertNotIn("API key:", self.run_command("create_api_key"))
