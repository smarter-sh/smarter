"""Test the AccountContact model's welcome email, in each language of settings.LANGUAGES.

The email is never sent: the infrastructure email service is patched.
"""

from unittest.mock import patch

from django.conf import settings
from django.utils import translation

from smarter.apps.account.models import (
    AccountContact,
    UserProfile,
    welcome_email_languages,
)
from smarter.common.exceptions import SmarterValueError

from .mixins import TestAccountMixin

MODULE = "smarter.apps.account.models.account_contact"

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
