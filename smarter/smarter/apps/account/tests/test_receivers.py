"""Test the account app's signal receivers."""

from unittest.mock import patch

from django.utils import timezone

from smarter.apps.account.models import User, UserProfile
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.account.utils import (
    get_cached_user_for_user_id,
    get_cached_user_for_username,
)

CACHE_INVALIDATIONS = "smarter.apps.dashboard.context_processors.cache_invalidations"


class TestUserPostSave(TestAccountMixin):
    """Test user_post_save(), which invalidates a user's cached objects."""

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(username=f"test_receivers_{self.hash_suffix}", password="12345")
        self.addCleanup(self.user.delete)

    def test_last_login_does_not_invalidate(self):
        """A save of only last_login, as on every token-authenticated request, leaves the caches alone."""
        user_profile = UserProfile.objects.create(name=self.user.username, user=self.user, account=self.account)
        self.addCleanup(user_profile.delete)
        UserProfile.get_cached_object(user=self.user)
        with patch(CACHE_INVALIDATIONS) as cache_invalidations:
            self.user.last_login = timezone.now()
            self.user.save(update_fields=["last_login"])
        cache_invalidations.assert_not_called()

    def test_edit_invalidates_cached_user(self):
        """Any other save invalidates the user's cached copies, by id and by username."""
        get_cached_user_for_user_id(user_id=self.user.pk)
        get_cached_user_for_username(username=self.user.username)

        # a queryset update bypasses save(), so the cached copies are still read.
        User.objects.filter(pk=self.user.pk).update(first_name="Changed")
        self.assertEqual(get_cached_user_for_user_id(user_id=self.user.pk).first_name, "")

        self.user.refresh_from_db()
        self.user.save()
        self.assertEqual(get_cached_user_for_user_id(user_id=self.user.pk).first_name, "Changed")
        self.assertEqual(get_cached_user_for_username(username=self.user.username).first_name, "Changed")

    def test_edit_invalidates_cached_user_profiles(self):
        """A save refreshes the User carried by the UserProfiles cached by user, and by user and account."""
        user_profile = UserProfile.objects.create(name=self.user.username, user=self.user, account=self.account)
        self.addCleanup(user_profile.delete)
        self.assertFalse(UserProfile.get_cached_object(user=self.user).user.is_staff)
        self.assertFalse(UserProfile.get_cached_object(user=self.user, account=self.account).user.is_staff)
        self.assertFalse(UserProfile.get_cached_objects(user=self.user)[0].user.is_staff)

        self.user.is_staff = True
        self.user.save()
        self.assertTrue(UserProfile.get_cached_object(user=self.user).user.is_staff)
        self.assertTrue(UserProfile.get_cached_object(user=self.user, account=self.account).user.is_staff)
        self.assertTrue(UserProfile.get_cached_objects(user=self.user)[0].user.is_staff)


class TestUserProfileReceivers(TestAccountMixin):
    """Test that saving or deleting a UserProfile refreshes its User's cached list of UserProfiles."""

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(username=f"test_profile_receivers_{self.hash_suffix}", password="12345")
        self.addCleanup(self.user.delete)

    def test_new_user_does_not_cache_an_empty_list(self):
        """A UserProfile created after its User appears in the cached list, which permission querysets read."""
        user_profile = UserProfile.objects.create(name=self.user.username, user=self.user, account=self.account)
        self.addCleanup(user_profile.delete)
        self.assertEqual(list(UserProfile.get_cached_objects(user=self.user)), [user_profile])

    def test_save_and_delete_refresh_the_cached_list(self):
        """The cached list follows UserProfiles that are created and deleted after it was cached."""
        self.assertEqual(list(UserProfile.get_cached_objects(user=self.user)), [])
        user_profile = UserProfile.objects.create(name=self.user.username, user=self.user, account=self.account)
        self.assertEqual(list(UserProfile.get_cached_objects(user=self.user)), [user_profile])
        user_profile.delete()
        self.assertEqual(list(UserProfile.get_cached_objects(user=self.user)), [])


class TestAccountPostSave(TestAccountMixin):
    """Test that account_post_save() logs the Account without its contact details, which are personal data."""

    def test_contact_details_are_not_logged(self):
        self.account.phone_number = "+1 (555) 010-0199"
        self.account.address1 = "1 Logging Lane"
        self.account.postal_code = "00000"
        with patch("smarter.apps.account.receivers.logger") as logger:
            self.account.save()
        logged = " ".join(str(arg) for call in logger.mock_calls for arg in call.args)
        self.assertIn(self.account.account_number, logged)
        for value in (self.account.phone_number, self.account.address1, self.account.postal_code):
            self.assertNotIn(value, logged)
