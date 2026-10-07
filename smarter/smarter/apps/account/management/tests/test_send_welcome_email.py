"""Test the send_welcome_email management command.

The email is never sent: send_welcome_email() is patched.
"""

import unittest
from unittest.mock import patch

from smarter.apps.account.models import AccountContact
from smarter.common.exceptions import SmarterValueError

from .base import CommandTestBase


class TestSendWelcomeEmail(CommandTestBase):
    def setUp(self):
        super().setUp()
        patcher = patch.object(AccountContact, "send_welcome_email")
        self.send = patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(AccountContact.objects.filter(account=self.account, email=self.non_admin_user.email).delete)

    def test_by_username(self):
        self.run_command("send_welcome_email", username=self.non_admin_user.username)
        self.send.assert_called()
        self.assertTrue(AccountContact.objects.filter(account=self.account, email=self.non_admin_user.email).exists())

    def test_by_email(self):
        self.run_command("send_welcome_email", email=self.non_admin_user.email)
        self.send.assert_called()

    def test_existing_contact_is_sent_one_email(self):
        """Test that an existing contact is re-sent the welcome email once."""
        AccountContact.objects.create(
            account=self.account, email=self.non_admin_user.email, first_name="A", last_name="B"
        )
        self.send.reset_mock()
        self.run_command("send_welcome_email", username=self.non_admin_user.username)
        self.send.assert_called_once()

    def test_new_contact_is_sent_one_email(self):
        """Test that a new contact is sent the welcome email once."""
        self.run_command("send_welcome_email", username=self.non_admin_user.username)
        self.send.assert_called_once()

    def test_by_account_and_email(self):
        """Test that a contact who isn't a user is welcomed, with their email and account."""
        email = "test_welcome_contact@example.com"
        self.addCleanup(AccountContact.objects.filter(account=self.account, email=email).delete)
        for options in ({"account_number": self.account.account_number}, {"company_name": self.account.company_name}):
            with self.subTest(options=options):
                self.run_command("send_welcome_email", email=email, **options)
        self.assertTrue(AccountContact.objects.filter(account=self.account, email=email).exists())
        self.assertEqual(self.send.call_count, 2)

    def test_unknown_account(self):
        with self.assertRaises(SystemExit):
            self.run_command("send_welcome_email", account_number="0000-0000-0000", email="a@example.com")

    def test_by_account_without_email_is_refused(self):
        """Test that an account without a username or an email is refused."""
        for options in (
            {"account_number": self.account.account_number},
            {"company_name": self.account.company_name},
            {},
        ):
            with self.subTest(options=options):
                with self.assertRaises(SmarterValueError):
                    self.run_command("send_welcome_email", **options)
        self.send.assert_not_called()
