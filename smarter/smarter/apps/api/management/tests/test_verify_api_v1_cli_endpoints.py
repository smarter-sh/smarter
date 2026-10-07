"""Test the verify_api_v1_cli_endpoints management command, which applies a verification Plugin manifest."""

from django.contrib.auth.models import User

from smarter.apps.account.models import UserProfile
from smarter.apps.plugin.models import PluginMeta
from smarter.lib.drf.models import SmarterAuthToken

from .base import CommandTestBase

PLUGIN_NAME = "plugin_verification"


class TestVerifyApiV1CliEndpoints(CommandTestBase):
    def setUp(self):
        super().setUp()
        self.addCleanup(PluginMeta.objects.filter(name=PLUGIN_NAME, user_profile__account=self.account).delete)

    def set_staff(self, is_staff: bool):
        """Make the customer a staff user, or not, and refresh the cached user profile that the command reads."""
        User.objects.filter(pk=self.non_admin_user.pk).update(is_staff=is_staff)
        UserProfile.get_cached_object(invalidate=True, account=self.account, user=self.non_admin_user)

    def assert_verified(self, output: str):
        self.assertIn("response:", output)
        self.assertFalse(SmarterAuthToken.objects.filter(name="verify_api:v1:cli:endpoints").exists())

    def test_account_admin(self):
        """Test that the endpoints are verified as the account's admin, with a single-use api key."""
        self.assert_verified(
            self.run_command("verify_api_v1_cli_endpoints", self.account.account_number, self.admin_user.username)
        )

    def test_other_username(self):
        """Test that the endpoints are verified as another staff user of the account, and not as a customer."""
        before = SmarterAuthToken.objects.count()
        self.run_command("verify_api_v1_cli_endpoints", self.account.account_number, self.non_admin_user.username)
        self.assertEqual(SmarterAuthToken.objects.count(), before)
        self.set_staff(True)
        self.addCleanup(self.set_staff, False)
        self.assert_verified(
            self.run_command("verify_api_v1_cli_endpoints", self.account.account_number, self.non_admin_user.username)
        )

    def test_unknown_account_and_user(self):
        before = SmarterAuthToken.objects.count()
        self.run_command("verify_api_v1_cli_endpoints", "0000-0000-0000", self.admin_user.username)
        self.run_command("verify_api_v1_cli_endpoints", self.account.account_number, "not_a_user")
        self.assertEqual(SmarterAuthToken.objects.count(), before)
