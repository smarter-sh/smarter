"""Test the account app's signal receivers."""

from unittest.mock import MagicMock, patch

from django.utils import timezone

from smarter.apps.account.models import Account, User, UserProfile
from smarter.apps.account.receivers import (
    account_post_delete,
    user_logged_in_receiver,
)
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.account.utils import (
    get_cached_user_for_user_id,
    get_cached_user_for_username,
)

CACHE_INVALIDATIONS = "smarter.apps.dashboard.context_processors.cache_invalidations"
RECEIVERS_LOGGER = "smarter.apps.account.receivers.logger"


def logged_text(logger: MagicMock) -> str:
    """
    Return the arguments of every call to a patched logger, as one string.

    :param logger: The patched logger.
    :returns: The arguments, each as a string, joined with spaces.
    """
    arguments = []
    for logger_call in logger.mock_calls:
        for argument in logger_call.args:
            arguments.append(str(argument))
    return " ".join(arguments)


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


class TestUserReceiversLogging(TestAccountMixin):
    """Test that the User receivers log a user by id, never by username, which is often a person's name."""

    def setUp(self):
        super().setUp()
        self.username = f"test_receivers_logging_{self.hash_suffix}"
        self.user = User.objects.create_user(
            username=self.username,
            email=f"{self.username}@example.com",
            password="12345",
        )
        self.addCleanup(User.objects.filter(pk=self.user.pk).delete)

    def test_logged_in(self):
        """A sign-in is logged with the user's id."""
        user_profile = UserProfile.objects.create(name="test", user=self.user, account=self.account)
        self.addCleanup(user_profile.delete)
        with patch(RECEIVERS_LOGGER) as logger:
            user_logged_in_receiver(sender=User, request=None, user=self.user)
        logged = logged_text(logger)
        self.assertIn(str(self.user.pk), logged)
        self.assertNotIn(self.username, logged)

    def test_logged_in_creates_a_profile(self):
        """A sign-up's new UserProfile is logged with the user's id and the account's number."""
        with (
            patch(RECEIVERS_LOGGER) as logger,
            patch("smarter.apps.account.receivers.get_cached_default_account", return_value=self.account),
        ):
            user_logged_in_receiver(sender=User, request=None, user=self.user)
        self.assertTrue(UserProfile.objects.filter(user=self.user, account=self.account).exists())
        logged = logged_text(logger)
        self.assertIn(str(self.user.pk), logged)
        self.assertIn(str(self.account.account_number), logged)
        self.assertNotIn(self.username, logged)

    def test_save_and_delete(self):
        """A User's save and deletion are logged with its id."""
        user_id = self.user.pk
        with patch(RECEIVERS_LOGGER) as logger:
            self.user.first_name = "Changed"
            self.user.save()
            self.user.delete()
        logged = logged_text(logger)
        self.assertIn(str(user_id), logged)
        self.assertNotIn(self.username, logged)


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

    def test_joining_an_account_makes_it_the_default(self):
        """A user who joins another account moves into it at once, and back when they leave it."""
        # pylint: disable=import-outside-toplevel
        from smarter.apps.account.tests.factories import mortal_user_factory

        first = UserProfile.objects.create(name=self.user.username, user=self.user, account=self.account)
        self.addCleanup(UserProfile.objects.filter(pk=first.pk).delete)
        self.assertEqual(UserProfile.get_cached_object(user=self.user), first)

        other_user, other_account, _ = mortal_user_factory()
        self.addCleanup(other_account.delete)
        self.addCleanup(other_user.delete)
        second = UserProfile.objects.create(name=self.user.username, user=self.user, account=other_account)
        self.assertEqual(UserProfile.get_cached_object(user=self.user), second)

        second.delete()
        self.assertEqual(UserProfile.get_cached_object(user=self.user), first)

    def test_save_refreshes_the_cached_profile(self):
        """A UserProfile's save refreshes its cached copies, by user and account, by user, and by pk."""
        user_profile = UserProfile.objects.create(name=self.user.username, user=self.user, account=self.account)
        self.addCleanup(user_profile.delete)
        self.assertFalse(UserProfile.get_cached_object(user=self.user, account=self.account).is_account_admin)
        self.assertFalse(UserProfile.get_cached_object(user=self.user).is_account_admin)
        self.assertFalse(UserProfile.get_cached_object(pk=user_profile.pk).is_account_admin)

        user_profile.is_account_admin = True
        user_profile.save()
        self.assertTrue(UserProfile.get_cached_object(user=self.user, account=self.account).is_account_admin)
        self.assertTrue(UserProfile.get_cached_object(user=self.user).is_account_admin)
        self.assertTrue(UserProfile.get_cached_object(pk=user_profile.pk).is_account_admin)


class TestAccountPostSave(TestAccountMixin):
    """Test that account_post_save() logs the Account without its contact details, which are personal data."""

    def test_contact_details_are_not_logged(self):
        self.account.phone_number = "+1 (555) 010-0199"
        self.account.address1 = "1 Logging Lane"
        self.account.postal_code = "00000"
        company_name = self.account.company_name
        self.addCleanup(Account.objects.filter(pk=self.account.pk).update, company_name=company_name)
        self.addCleanup(setattr, self.account, "company_name", company_name)
        self.account.company_name = "Ada Q. Lovelace"
        with patch(RECEIVERS_LOGGER) as logger:
            self.account.save()
        logged = logged_text(logger)
        self.assertIn(self.account.account_number, logged)
        for value in (self.account.phone_number, self.account.address1, self.account.postal_code, "Lovelace"):
            self.assertNotIn(value, logged)

    def test_delete_does_not_log_the_company_name(self):
        with patch(RECEIVERS_LOGGER) as logger:
            account_post_delete(sender=Account, instance=self.account)
        logged = logged_text(logger)
        self.assertIn(self.account.account_number, logged)
        self.assertNotIn(self.account.company_name, logged)
