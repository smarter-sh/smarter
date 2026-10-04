"""Test the create_user management command.

The new user's password email is never sent: email_helper is patched.
"""

from unittest.mock import patch

from django.contrib.auth.models import User

from smarter.apps.account.models import AccountContact, UserProfile

from .base import CommandTestBase

MODULE = "smarter.apps.account.management.commands.create_user"


class TestCreateUser(CommandTestBase):
    def setUp(self):
        super().setUp()
        self.username = self.unique("test_create_user")
        self.email = f"{self.username}@example.com"
        self.addCleanup(AccountContact.objects.filter(account=self.account, email=self.email).delete)
        self.addCleanup(User.objects.filter(username=self.username).delete)
        patcher = patch(f"{MODULE}.email_helper")
        self.email_helper = patcher.start()
        self.addCleanup(patcher.stop)

    def create(self, **overrides):
        options = {
            "account_number": self.account.account_number,
            "username": self.username,
            "email": self.email,
            "first_name": "Test",
            "last_name": "User",
        }
        options.update(overrides)
        return self.run_command("create_user", **options)

    def test_new_user_with_random_password_and_email(self):
        """Test that a new user gets a random password, which is emailed when the switch is on."""
        with patch(f"{MODULE}.waffle.switch_is_active", return_value=True):
            output = self.create(admin=True)
        self.assertIn("has been set to", output)
        user = User.objects.get(username=self.username)
        self.assertTrue(user.is_staff)
        self.assertTrue(UserProfile.objects.filter(user=user, account=self.account).exists())
        self.assertTrue(AccountContact.objects.filter(account=self.account, email=self.email).exists())
        self.email_helper.send_email.assert_called_once()

    def test_existing_user_is_updated(self):
        self.create(password="first")
        self.create(password="second", first_name="Renamed")
        user = User.objects.get(username=self.username)
        self.assertTrue(user.check_password("second"))
        self.assertEqual(AccountContact.objects.get(account=self.account, email=self.email).first_name, "Renamed")
        self.assertFalse(user.is_staff)

    def test_email_error_is_reported(self):
        self.email_helper.send_email.side_effect = Exception("smtp down")
        with patch(f"{MODULE}.waffle.switch_is_active", return_value=True):
            self.create()
        self.assertTrue(User.objects.filter(username=self.username).exists())

    def test_unknown_account_and_invalid_email(self):
        self.create(account_number="0000-0000-0000")
        self.assertFalse(User.objects.filter(username=self.username).exists())
        self.create(email="not an email")
        self.assertFalse(UserProfile.objects.filter(user__username=self.username).exists())
