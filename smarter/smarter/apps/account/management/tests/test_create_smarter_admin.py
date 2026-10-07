"""Test the create_smarter_admin management command, with a new superuser in the platform's account."""

from django.contrib.auth.models import User

from smarter.apps.account.models import UserProfile
from smarter.common.const import SMARTER_ACCOUNT_NUMBER
from smarter.lib.drf.models import SmarterAuthToken

from .base import CommandTestBase


class TestCreateSmarterAdmin(CommandTestBase):
    def test_create_and_update(self):
        username = self.unique("test_smarter_admin")
        self.addCleanup(User.objects.filter(username=username).delete)
        self.addCleanup(SmarterAuthToken.objects.filter(user__username=username).delete)
        self.run_command("create_smarter_admin", username=username, email=f"{username}@example.com")
        user = User.objects.get(username=username)
        self.assertTrue(user.is_superuser and user.is_staff)
        profile = UserProfile.objects.get(user=user)
        self.assertEqual(profile.account.account_number, SMARTER_ACCOUNT_NUMBER)
        self.assertTrue(SmarterAuthToken.objects.filter(user=user).exists())
        # a second run updates the user, but only a new user's password is set.
        self.run_command("create_smarter_admin", username=username, password="new-password")
        self.assertFalse(User.objects.get(username=username).check_password("new-password"))

    def test_rerun_does_not_create_another_api_key(self):
        """Test that a second run doesn't create another api key."""
        username = self.unique("test_smarter_admin")
        self.addCleanup(User.objects.filter(username=username).delete)
        self.addCleanup(SmarterAuthToken.objects.filter(user__username=username).delete)
        self.run_command("create_smarter_admin", username=username)
        self.run_command("create_smarter_admin", username=username)
        self.assertEqual(SmarterAuthToken.objects.filter(user__username=username).count(), 1)
