"""Test the UserProfile model's language preference, and active_language()."""

from django.conf import settings
from django.utils import translation

from smarter.apps.account.models import UserProfile, active_language

from .factories import admin_user_factory
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
        choices = UserProfile._meta.get_field("language").choices
        assert choices is not None
        self.assertEqual(list(choices), list(settings.LANGUAGES))


class TestUserProfileMultipleAccounts(TestAccountMixin):
    """Test get_cached_object() for a user with one UserProfile in each of two accounts."""

    def test_newest_profile_without_warning(self):
        """A second account's profile is the default, and is not logged as a WARNING."""
        other_user, other_account, other_profile = admin_user_factory()
        second_profile = UserProfile.objects.create(user=self.non_admin_user, account=other_account, is_test=True)
        try:
            with self.assertNoLogs("smarter.apps.account.models.user_profile", level="WARNING"):
                profile = UserProfile.get_cached_object(user=self.non_admin_user, invalidate=True)
            self.assertEqual(profile, second_profile)
        finally:
            # Not factory_account_teardown(): it also deletes every is_test profile, this class's fixtures too.
            second_profile.delete()
            other_profile.delete()
            other_user.delete()
            other_account.delete()
            UserProfile.get_cached_object(user=self.non_admin_user, invalidate=True)
