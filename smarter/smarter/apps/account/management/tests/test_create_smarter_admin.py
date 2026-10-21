"""Test the create_smarter_admin management command, with a new superuser in the platform's account.

The api key email is never sent: the infrastructure email service is patched.
"""

from unittest.mock import patch

from django.contrib.auth.models import User

from smarter.apps.account import utils as account_utils
from smarter.apps.account.models import UserProfile
from smarter.common.const import SMARTER_ACCOUNT_NUMBER
from smarter.lib.drf.models import SmarterAuthToken

from .base import CommandTestBase

MODULE = "smarter.apps.account.management.commands.create_smarter_admin"


class TestCreateSmarterAdmin(CommandTestBase):
    def setUp(self):
        super().setUp()
        patcher = patch(f"{MODULE}.infrastructure")
        self.infrastructure = patcher.start()
        self.addCleanup(patcher.stop)

    def test_api_key_is_emailed_not_printed(self):
        """Test that a new api key's value is emailed to its owner, without a blind copy, and never printed."""
        username = self.unique("test_smarter_admin")
        email = f"{username}@example.com"
        self.addCleanup(User.objects.filter(username=username).delete)
        self.addCleanup(SmarterAuthToken.objects.filter(user__username=username).delete)
        self.infrastructure.email.send_email.return_value = True
        output = self.run_command("create_smarter_admin", username=username, email=email)
        self.infrastructure.email.send_email.assert_called_once()
        kwargs = self.infrastructure.email.send_email.call_args.kwargs
        self.assertEqual(kwargs["to"], email)
        self.assertFalse(kwargs["bcc_admin"])
        token_key = kwargs["body"].split("API key: ")[1].strip()
        auth_token = SmarterAuthToken.objects.get(user__username=username)
        self.assertTrue(token_key.startswith(auth_token.token_key))
        self.assertIn(str(auth_token.key_id), kwargs["body"])
        self.assertNotIn(token_key, output)

    def test_api_key_email_failure_is_reported(self):
        """Test that an email that can't be sent says how to create another key, without printing this one."""
        username = self.unique("test_smarter_admin")
        self.addCleanup(User.objects.filter(username=username).delete)
        self.addCleanup(SmarterAuthToken.objects.filter(user__username=username).delete)
        self.infrastructure.email.send_email.return_value = False
        output = self.run_command("create_smarter_admin", username=username, email=f"{username}@example.com")
        self.assertIn(f"could not email it to {username}@example.com", output)
        self.assertIn(f"create_api_key --username {username}", output)
        token_key = self.infrastructure.email.send_email.call_args.kwargs["body"].split("API key: ")[1].strip()
        self.assertNotIn(token_key, output)

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

    def test_create_platform_admin_on_a_new_database(self):
        """Test creating the platform's admin user when it doesn't exist yet, as make init does."""
        username = self.unique("test_smarter_admin")
        self.addCleanup(User.objects.filter(username=username).delete)
        self.addCleanup(SmarterAuthToken.objects.filter(user__username=username).delete)
        with (
            patch.object(account_utils, "SMARTER_ADMIN_USERNAME", username),
            patch.object(account_utils.smarter_cached_objects, "_admin_user", None),
        ):
            self.run_command("create_smarter_admin", username=username)
            self.assertEqual(account_utils.smarter_cached_objects.admin_user.username, username)
        self.assertTrue(User.objects.get(username=username).is_superuser)
