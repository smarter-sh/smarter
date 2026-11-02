"""Test the send_slack_invitation_email management command.

The email is never sent: the infrastructure email service is patched.
"""

import re
from unittest.mock import patch

from django.core.management.base import CommandError
from django.utils import timezone

from smarter.apps.account.models import AccountContact, UserProfile

from .base import CommandTestBase

MODULE = "smarter.apps.account.models.account_contact"


class TestSendSlackInvitationEmail(CommandTestBase):
    def setUp(self):
        super().setUp()
        patcher = patch(f"{MODULE}.infrastructure")
        self.infrastructure = patcher.start()
        self.infrastructure.email.send_email.return_value = True
        self.addCleanup(patcher.stop)
        self.stranger = f"test_slack_stranger_{self.hash_suffix}@example.com"
        # the user's profile may have added them to the account's contacts: start without a contact.
        AccountContact.objects.filter(email=self.non_admin_user.email).delete()
        self.addCleanup(AccountContact.objects.filter(email=self.non_admin_user.email).delete)

    def sent(self) -> dict:
        """Return the keyword arguments of the last email sent."""
        return self.infrastructure.email.send_email.call_args.kwargs

    def contact(self, **fields) -> AccountContact:
        contact = AccountContact(
            account=self.account, email=self.non_admin_user.email, first_name="Contact", welcomed=True, **fields
        )
        contact.save()
        return contact

    def test_by_username(self):
        """Test that a user who is no contact is sent the email, with their first name."""
        self.run_command("send_slack_invitation_email", username=self.non_admin_user.username)
        self.assertEqual(self.sent()["to"], self.non_admin_user.email)
        self.assertIn(f"{self.non_admin_user.first_name.capitalize()},", self.sent()["body"])

    def test_contact_is_recorded(self):
        contact = self.contact()
        self.run_command("send_slack_invitation_email", email=self.non_admin_user.email)
        self.assertIn("Howdy Contact,", self.sent()["body"])
        self.assertIsNotNone(AccountContact.objects.get(pk=contact.pk).slack_invited_at)

    def test_first_name_overrides_the_contacts(self):
        contact = self.contact()
        self.run_command("send_slack_invitation_email", email=self.non_admin_user.email, first_name="jane")
        self.assertIn("Howdy Jane,", self.sent()["body"])
        self.assertIsNotNone(AccountContact.objects.get(pk=contact.pk).slack_invited_at)

    def test_someone_who_is_not_a_user(self):
        self.run_command("send_slack_invitation_email", email=self.stranger, first_name="jane", language="fr")
        self.assertEqual(self.sent()["to"], self.stranger)
        self.assertIn("Bonjour Jane,", self.sent()["body"])
        self.assertFalse(AccountContact.objects.filter(email=self.stranger).exists())

    def test_users_preferred_language(self):
        UserProfile.objects.filter(pk=self.non_admin_user_profile.pk).update(language="es")
        self.addCleanup(UserProfile.objects.filter(pk=self.non_admin_user_profile.pk).update, language="en")
        self.run_command("send_slack_invitation_email", username=self.non_admin_user.username)
        self.assertIn('<html lang="es">', self.sent()["body"])

    def test_already_invited_is_refused_without_force(self):
        self.contact(slack_invited_at=timezone.now())
        with self.assertRaisesRegex(CommandError, re.escape("Add --force to send it again.")):
            self.run_command("send_slack_invitation_email", email=self.non_admin_user.email)
        self.infrastructure.email.send_email.assert_not_called()
        self.run_command("send_slack_invitation_email", email=self.non_admin_user.email, force=True)
        self.infrastructure.email.send_email.assert_called_once()

    def test_unsubscribed_is_refused(self):
        self.contact(unsubscribed_at=timezone.now())
        for options in ({}, {"force": True}):
            with self.subTest(options=options):
                with self.assertRaisesRegex(CommandError, re.escape("unsubscribed from these emails")):
                    self.run_command("send_slack_invitation_email", email=self.non_admin_user.email, **options)
        self.infrastructure.email.send_email.assert_not_called()

    def test_not_sent_is_an_error(self):
        self.infrastructure.email.send_email.return_value = False
        with self.assertRaisesRegex(CommandError, re.escape("was not sent")):
            self.run_command("send_slack_invitation_email", email=self.stranger)

    def test_nobody_is_refused(self):
        with self.assertRaisesRegex(CommandError, re.escape("Provide a --username, or an --email.")):
            self.run_command("send_slack_invitation_email")

    def test_unknown_username_is_refused(self):
        with self.assertRaises(CommandError):
            self.run_command("send_slack_invitation_email", username="no_such_user")
        self.infrastructure.email.send_email.assert_not_called()

    def test_unknown_language_is_refused(self):
        with self.assertRaises(CommandError):
            self.run_command("send_slack_invitation_email", "--language=xx", email=self.stranger)
        self.infrastructure.email.send_email.assert_not_called()
