"""Test the AccountContact model's welcome and Slack invitation emails, in each language of settings.LANGUAGES.

The email is never sent: the infrastructure email service is patched.
"""

from datetime import timedelta
from typing import Optional
from unittest.mock import patch

from django.conf import settings
from django.core import signing
from django.utils import timezone, translation

from smarter.apps.account.const import SLACK_INVITATION_EMAIL_DELAY
from smarter.apps.account.models import (
    Account,
    AccountContact,
    UserProfile,
    unsubscribe_email_address,
    unsubscribe_token,
    unsubscribe_url,
    welcome_email_languages,
)
from smarter.common.conf import smarter_settings
from smarter.common.exceptions import SmarterValueError

from .mixins import TestAccountMixin

MODULE = "smarter.apps.account.models.account_contact"


def other_account(name: str) -> Account:
    """Return a second account, for a contact whose email address is also another account's contact."""
    return Account.objects.create(
        name=name,
        company_name=name,
        is_default_account=False,
        is_active=True,
        phone_number="123-456-789",
        address1="Smarter Way 4U",
        city="Smarter",
        state="WY",
        postal_code="12345",
        country="USA",
    )


# A message of the welcome email's body, in each language.
GREETINGS = {
    "en": "Howdy Jane,",
    "es": "Hola, Jane:",
    "fr": "Bonjour Jane,",
    "pt-br": "Olá, Jane,",
}


class TestAccountContactWelcomeEmail(TestAccountMixin):
    """Test that the welcome email is rendered in the language it is sent in."""

    def setUp(self):
        super().setUp()
        patcher = patch(f"{MODULE}.infrastructure")
        self.infrastructure = patcher.start()
        self.addCleanup(patcher.stop)
        self.email = "test_welcome_language@example.com"
        self.addCleanup(AccountContact.objects.filter(account=self.account, email=self.email).delete)

    def sent(self) -> dict:
        """Return the keyword arguments of the last email sent."""
        return self.infrastructure.email.send_email.call_args.kwargs

    def test_languages_are_settings_languages(self):
        self.assertEqual(welcome_email_languages(), [code for code, _ in settings.LANGUAGES])
        self.assertEqual(sorted(GREETINGS), sorted(welcome_email_languages()))

    def test_every_language(self):
        """Test that each language's email has its own greeting, subject and html lang."""
        contact = AccountContact(account=self.account, email=self.email, first_name="jane", welcomed=True)
        contact.save()
        subjects = set()
        for language, greeting in GREETINGS.items():
            with self.subTest(language=language):
                contact.send_welcome_email(language=language)
                body = self.sent()["body"]
                self.assertIn(greeting, body)
                self.assertIn(f'<html lang="{language}">', body)
                self.assertTrue(self.sent()["html"])
                subjects.add(self.sent()["subject"])
        self.assertEqual(len(subjects), len(GREETINGS))

    def test_default_is_english(self):
        """Test that the email is English by default, whatever language is active."""
        contact = AccountContact(account=self.account, email=self.email, first_name="jane", welcomed=True)
        contact.save()
        with translation.override("es"):
            contact.send_welcome_email()
            self.assertEqual(translation.get_language(), "es")
        self.assertIn(GREETINGS["en"], self.sent()["body"])
        self.assertEqual(self.sent()["subject"], "Welcome to Smarter!")

    def test_new_contact_is_welcomed_in_the_language_of_save(self):
        AccountContact(account=self.account, email=self.email, first_name="jane").save(language="fr")
        self.infrastructure.email.send_email.assert_called_once()
        self.assertIn(GREETINGS["fr"], self.sent()["body"])
        self.assertTrue(AccountContact.objects.get(account=self.account, email=self.email).welcomed)

    def test_unknown_language_is_refused(self):
        contact = AccountContact(account=self.account, email=self.email, welcomed=True)
        contact.save()
        with self.assertRaises(SmarterValueError):
            contact.send_welcome_email(language="xx")
        self.infrastructure.email.send_email.assert_not_called()

    def test_default_is_the_users_preferred_language(self):
        """Test that a contact who is a user of the account is welcomed in their preferred language."""
        UserProfile.objects.filter(pk=self.non_admin_user_profile.pk).update(language="es")
        self.addCleanup(UserProfile.objects.filter(pk=self.non_admin_user_profile.pk).update, language="en")
        email = self.non_admin_user.email
        contact = AccountContact.objects.filter(account=self.account, email=email).first()
        if contact is None:
            contact = AccountContact(account=self.account, email=email, first_name="jane", welcomed=True)
            contact.save()
            self.addCleanup(contact.delete)
        self.assertEqual(contact.preferred_language(), "es")
        contact.send_welcome_email()
        self.assertIn('<html lang="es">', self.sent()["body"])
        # an explicit language wins over the preference.
        contact.send_welcome_email(language="fr")
        self.assertIn('<html lang="fr">', self.sent()["body"])

    def test_contact_who_is_not_a_user_prefers_english(self):
        contact = AccountContact(account=self.account, email=self.email, welcomed=True)
        contact.save()
        self.assertEqual(contact.preferred_language(), settings.LANGUAGE_CODE)


class TestAccountContactEmails(TestAccountMixin):
    """Test welcomed_at, the Slack invitation email, and unsubscribing."""

    def setUp(self):
        super().setUp()
        patcher = patch(f"{MODULE}.infrastructure")
        self.infrastructure = patcher.start()
        self.infrastructure.email.send_email.return_value = True
        self.addCleanup(patcher.stop)
        self.email = f"test_contact_emails_{self.hash_suffix}@example.com"
        self.addCleanup(AccountContact.objects.filter(email__iexact=self.email).delete)

    def sent(self) -> dict:
        """Return the keyword arguments of the last email sent."""
        return self.infrastructure.email.send_email.call_args.kwargs

    def contact(self, **fields) -> AccountContact:
        """Return a saved contact of self.email, who was welcomed without sending an email."""
        fields.setdefault("welcomed", True)
        contact = AccountContact(account=self.account, email=self.email, first_name="jane", **fields)
        contact.save()
        return contact

    def test_welcome_email_records_welcomed_at(self):
        before = timezone.now()
        AccountContact(account=self.account, email=self.email, first_name="jane").save()
        contact = AccountContact.objects.get(account=self.account, email=self.email)
        self.assertTrue(contact.welcomed)
        self.assertGreaterEqual(contact.welcomed_at, before)

    def test_welcome_email_not_sent_records_nothing(self):
        self.infrastructure.email.send_email.return_value = False
        AccountContact(account=self.account, email=self.email, first_name="jane").save()
        contact = AccountContact.objects.get(account=self.account, email=self.email)
        self.assertTrue(contact.welcomed)
        self.assertIsNone(contact.welcomed_at)

    def test_emails_have_an_unsubscribe_link_and_headers(self):
        contact = self.contact()
        url = unsubscribe_url(self.email)
        for send in (contact.send_welcome_email, contact.send_slack_invitation_email):
            with self.subTest(send=send.__name__):
                self.assertTrue(send())
                self.assertIn(url, self.sent()["body"])
                self.assertEqual(self.sent()["headers"]["List-Unsubscribe"], f"<{url}>")
                self.assertEqual(self.sent()["headers"]["List-Unsubscribe-Post"], "List-Unsubscribe=One-Click")

    def test_welcome_email_links_to_the_slack_setting(self):
        self.contact().send_welcome_email()
        self.assertIn(str(smarter_settings.branding_url_slack), self.sent()["body"])

    def test_slack_invitation_in_every_language(self):
        contact = self.contact()
        subjects = set()
        for language, greeting in GREETINGS.items():
            with self.subTest(language=language):
                self.assertTrue(contact.send_slack_invitation_email(language=language))
                body = self.sent()["body"]
                self.assertIn(greeting, body)
                self.assertIn(f'<html lang="{language}">', body)
                self.assertIn(str(smarter_settings.branding_url_slack), body)
                self.assertTrue(self.sent()["html"])
                subjects.add(self.sent()["subject"])
        self.assertEqual(len(subjects), len(GREETINGS))
        self.assertIn("Join the Smarter community on Slack", subjects)

    def test_slack_invitation_records_every_contact_of_the_address(self):
        """Test that slack_invited_at is set on the address's contacts of every account, in any case."""
        account = other_account(f"test_slack_invitation_{self.hash_suffix}")
        self.addCleanup(account.delete)
        contact = self.contact()
        other = AccountContact(account=account, email=self.email.upper(), first_name="jane", welcomed=True)
        other.save()
        self.assertTrue(contact.send_slack_invitation_email())
        for row in AccountContact.objects.filter(email__iexact=self.email):
            self.assertIsNotNone(row.slack_invited_at)

    def test_slack_invitation_unknown_language_is_refused(self):
        with self.assertRaises(SmarterValueError):
            self.contact().send_slack_invitation_email(language="xx")
        self.infrastructure.email.send_email.assert_not_called()

    def test_test_contact_is_sent_quietly(self):
        self.contact(is_test=True).send_slack_invitation_email()
        self.assertTrue(self.sent()["quiet"])

    def test_unsubscribe(self):
        contact = self.contact()
        self.assertIsNone(AccountContact.unsubscribed_at_of(self.email))
        self.assertEqual(AccountContact.unsubscribe(self.email.upper()), 1)
        self.assertIsNotNone(AccountContact.objects.get(pk=contact.pk).unsubscribed_at)
        self.assertIsNotNone(AccountContact.unsubscribed_at_of(self.email))
        # unsubscribing again changes nothing.
        self.assertEqual(AccountContact.unsubscribe(self.email), 0)

    def test_unsubscribed_address_is_sent_nothing(self):
        contact = self.contact()
        AccountContact.unsubscribe(self.email)
        self.assertFalse(contact.send_welcome_email())
        self.assertFalse(contact.send_slack_invitation_email())
        self.infrastructure.email.send_email.assert_not_called()
        self.assertIsNone(AccountContact.objects.get(pk=contact.pk).slack_invited_at)

    def test_new_contact_of_an_unsubscribed_address_is_unsubscribed(self):
        """Test that a contact added later, e.g. in another account, inherits the address's opt-out."""
        self.contact()
        AccountContact.unsubscribe(self.email)
        account = other_account(f"test_unsubscribed_{self.hash_suffix}")
        self.addCleanup(account.delete)
        AccountContact(account=account, email=self.email, first_name="jane").save()
        new = AccountContact.objects.get(account=account, email=self.email)
        self.assertIsNotNone(new.unsubscribed_at)
        self.assertIsNone(new.welcomed_at)
        self.infrastructure.email.send_email.assert_not_called()

    def test_unsubscribe_token(self):
        token = unsubscribe_token(f" {self.email.upper()} ")
        self.assertEqual(unsubscribe_email_address(token), self.email)
        with self.assertRaises(signing.BadSignature):
            unsubscribe_email_address(token[:-2] + "xx")
        # a value signed with another salt is not a token.
        with self.assertRaises(signing.BadSignature):
            unsubscribe_email_address(signing.dumps(self.email))

    def test_unsubscribe_url(self):
        url = unsubscribe_url(self.email)
        self.assertTrue(url.startswith(smarter_settings.environment_url.rstrip("/")))
        self.assertIn(f"/account/unsubscribe/{unsubscribe_token(self.email)}/", url)


class TestDueSlackInvitations(TestAccountMixin):
    """Test which contacts are due the Slack invitation, and the hourly sender."""

    def setUp(self):
        super().setUp()
        patcher = patch(f"{MODULE}.infrastructure")
        self.infrastructure = patcher.start()
        self.infrastructure.email.send_email.return_value = True
        self.addCleanup(patcher.stop)
        self.prefix = f"test_due_{self.hash_suffix}"
        self.addCleanup(AccountContact.objects.filter(email__startswith=self.prefix).delete)
        self.now = timezone.now()
        self.long_ago = self.now - SLACK_INVITATION_EMAIL_DELAY - timedelta(minutes=1)

    def contact(self, name: str, account: Optional[Account] = None, **fields) -> AccountContact:
        fields.setdefault("welcomed_at", self.long_ago)
        contact = AccountContact(
            account=account or self.account, email=f"{self.prefix}_{name}@example.com", welcomed=True, **fields
        )
        contact.save()
        return contact

    def due(self) -> set[str]:
        """Return the names of this test's contacts that are due."""
        return {
            contact.email.split("@")[0].removeprefix(f"{self.prefix}_")
            for contact in AccountContact.due_slack_invitations(self.now).filter(email__startswith=self.prefix)
        }

    def recipients(self) -> list[str]:
        """Return the addresses of this test's contacts that were sent an email."""
        return [
            call.kwargs["to"]
            for call in self.infrastructure.email.send_email.call_args_list
            if call.kwargs["to"].startswith(self.prefix)
        ]

    def test_due(self):
        self.contact("due")
        self.contact("recent", welcomed_at=self.now - SLACK_INVITATION_EMAIL_DELAY + timedelta(minutes=1))
        self.contact("legacy", welcomed_at=None)
        self.contact("invited", slack_invited_at=self.now)
        self.contact("unsubscribed", unsubscribed_at=self.now)
        self.contact("test", is_test=True)
        self.assertEqual(self.due(), {"due"})

    def test_send_one_email_per_address(self):
        account = other_account(f"test_due_{self.hash_suffix}")
        self.addCleanup(account.delete)
        first = self.contact("jane")
        self.contact("jane", account=account)
        self.contact("recent", welcomed_at=self.now)
        AccountContact.send_slack_invitation_emails()
        self.assertEqual(self.recipients(), [first.email])
        for row in AccountContact.objects.filter(email=first.email):
            self.assertIsNotNone(row.slack_invited_at)
        # the next run sends nothing more.
        AccountContact.send_slack_invitation_emails()
        self.assertEqual(self.recipients(), [first.email])

    def test_failed_email_is_released(self):
        """Test that an email that isn't sent leaves the address due, for the next run."""
        contact = self.contact("jane")
        self.infrastructure.email.send_email.return_value = False
        AccountContact.send_slack_invitation_emails()
        self.assertIsNone(AccountContact.objects.get(pk=contact.pk).slack_invited_at)
        self.assertEqual(self.due(), {"jane"})

    def test_error_is_released(self):
        contact = self.contact("jane")
        self.infrastructure.email.send_email.side_effect = RuntimeError("smtp down")
        with self.assertRaises(RuntimeError):
            AccountContact.send_slack_invitation_emails()
        self.assertIsNone(AccountContact.objects.get(pk=contact.pk).slack_invited_at)

    def test_claimed_address_is_skipped(self):
        """Test that an address that another run claimed after this one listed it is not sent twice."""
        contact = self.contact("jane")
        due = list(AccountContact.due_slack_invitations(self.now).filter(pk=contact.pk))
        AccountContact.objects.filter(pk=contact.pk).update(slack_invited_at=self.now)
        with patch.object(AccountContact, "due_slack_invitations", return_value=due):
            self.assertEqual(AccountContact.send_slack_invitation_emails(), 0)
        self.assertEqual(self.recipients(), [])
