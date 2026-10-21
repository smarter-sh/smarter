"""Test the UserProfile model's language preference, and active_language()."""

from django.conf import settings
from django.utils import translation

from smarter.apps.account.models import UserProfile, active_language

from .mixins import TestAccountMixin


class TestActiveLanguage(TestAccountMixin):
    """Test that active_language() returns a code of settings.LANGUAGES."""

    def test_active_language(self):
        cases = {"en": "en", "es": "es", "es-mx": "es", "fr-ca": "fr", "pt-br": "pt-br", "de": "en"}
        for active, expected in cases.items():
            with self.subTest(active=active):
                with translation.override(active):
                    self.assertEqual(active_language(), expected)

    def test_no_active_language(self):
        with translation.override(None):
            self.assertEqual(active_language(), settings.LANGUAGE_CODE)


class TestUserProfileLanguage(TestAccountMixin):
    """Test that a UserProfile prefers English by default, and only a language of settings.LANGUAGES."""

    def test_default_is_english(self):
        self.assertEqual(UserProfile._meta.get_field("language").default, settings.LANGUAGE_CODE)
        self.assertEqual(self.user_profile.language, settings.LANGUAGE_CODE)

    def test_choices_are_settings_languages(self):
        self.assertEqual(list(UserProfile._meta.get_field("language").choices), list(settings.LANGUAGES))
