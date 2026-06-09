"""Unit tests for UserView and UserListView API endpoints."""

from smarter.apps.account import utils
from smarter.apps.account.models import Account, User, UserProfile
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.account.utils import smarter_cached_objects
from smarter.common.const import SMARTER_ACCOUNT_NUMBER, SMARTER_ADMIN_USERNAME
from smarter.common.exceptions import SmarterConfigurationError, SmarterValueError
from smarter.lib import logging
from smarter.lib.unittest.base_classes import SmarterTestBase

logger = logging.getSmarterLogger(__name__)


class TestSmarterCachedObjects(SmarterTestBase):
    """
    Test that smarter_cached_objects returns the expected instances.
    """

    def test_smarter_account(self):
        self.assertIsInstance(smarter_cached_objects.smarter_account, Account)
        self.assertEqual(smarter_cached_objects.smarter_account.account_number, SMARTER_ACCOUNT_NUMBER)

    def test_smarter_admin(self):
        self.assertIsInstance(smarter_cached_objects.smarter_admin, User)
        self.assertEqual(smarter_cached_objects.smarter_admin.username, SMARTER_ADMIN_USERNAME)

    def test_smarter_admin_user_profile(self):
        self.assertIsInstance(smarter_cached_objects.smarter_admin_user_profile, UserProfile)
        self.assertEqual(smarter_cached_objects.smarter_admin_user_profile.user, smarter_cached_objects.smarter_admin)
        self.assertEqual(
            smarter_cached_objects.smarter_admin_user_profile.account, smarter_cached_objects.smarter_account
        )


class TestGetCachedDefaultAccount(TestAccountMixin):
    """
    Test that get_cached_default_account returns the expected default account instance and handles errors properly.
    """

    def test_get_default(self):
        """
        Test that get_cached_default_account returns the default account instance.
        """
        account = utils.get_cached_default_account()
        self.assertIsInstance(account, Account)

    def test_no_default_raises(self):
        """
        Test that get_cached_default_account raises if no default account is configured.
        """
        account = utils.get_cached_default_account(invalidate=True)
        self.assertIsInstance(account, Account)
        account.is_default_account = False
        account.save()
        with self.assertRaises(SmarterConfigurationError):
            utils.get_cached_default_account(invalidate=True)

        # restore the default account for other tests
        account.is_default_account = True
        account.save()

        account_invalidated = utils.get_cached_default_account(invalidate=True)
        self.assertEqual(account, account_invalidated)

        # test that subsequent calls return the cached account without hitting the database
        account_cached = utils.get_cached_default_account()
        self.assertEqual(account, account_cached)

        account_cached = utils.get_cached_default_account()
        self.assertEqual(account, account_cached)


class TestGetCachedAccountForUser(TestAccountMixin):
    """
    Test that get_cached_account_for_user returns the expected account for a given user and handles edge cases.
    """

    def test_get_account_for_user(self):
        account = utils.get_cached_account_for_user(user=self.admin_user, invalidate=True)
        self.assertIsInstance(account, Account)
        self.assertEqual(account, self.account)

        account = utils.get_cached_account_for_user(user=self.admin_user)
        self.assertIsInstance(account, Account)
        self.assertEqual(account, self.account)

    def test_invalid_user_type(self):
        with self.assertRaises(Account.DoesNotExist):
            utils.get_cached_account_for_user(user=object())  # type: ignore


class TestGetCachedUserForUserId(TestAccountMixin):
    """
    Test that get_cached_user_for_user_id returns the expected user for a given user ID and handles edge cases.
    """

    def test_get_user(self):
        user = utils.get_cached_user_for_user_id(user_id=self.non_admin_user.id, invalidate=True)  # type: ignore
        self.assertEqual(user, self.non_admin_user)

        user = utils.get_cached_user_for_user_id(user_id=self.non_admin_user.id)  # type: ignore
        self.assertEqual(user, self.non_admin_user)

    def test_user_not_found(self):
        with self.assertRaises(User.DoesNotExist):
            utils.get_cached_user_for_user_id(user_id=999999)


class TestGetCachedUserForUsername(TestAccountMixin):
    """
    Test that get_cached_user_for_username returns the expected user for a given username and handles edge cases.
    """

    def test_get_user(self):
        username = self.non_admin_user.username
        user = utils.get_cached_user_for_username(username=username, invalidate=True)
        self.assertEqual(user, self.non_admin_user)

        user = utils.get_cached_user_for_username(username=username)
        self.assertEqual(user, self.non_admin_user)

    def test_user_not_found(self):
        with self.assertRaises(User.DoesNotExist):
            utils.get_cached_user_for_username(username="notfound")


class TestGetCachedAdminUserForAccount(TestAccountMixin):
    """
    Test that get_cached_admin_user_for_account returns the expected admin user for a given account and handles edge cases.
    """

    def test_get_admin_user(self):
        admin = utils.get_cached_admin_user_for_account(account=self.account, invalidate=True)
        self.assertEqual(admin, self.admin_user)

        admin = utils.get_cached_admin_user_for_account(account=self.account)
        self.assertEqual(admin, self.admin_user)

    def test_missing_account_raises(self):
        with self.assertRaises(User.DoesNotExist):
            utils.get_cached_admin_user_for_account(account=None)  # type: ignore


class TestAccountNumberFromUrl(SmarterTestBase):
    """
    Test that account_number_from_url correctly extracts account numbers from URLs and handles edge cases.
    """

    def test_valid_url(self):
        url = "https://hr.3141-5926-5359.alpha.api.example.com/"
        acct = utils.account_number_from_url(url=url)
        self.assertEqual(acct, "3141-5926-5359")

    def test_invalid_url(self):
        url = "https://noaccount.example.com/"
        self.assertIsNone(utils.account_number_from_url(url=url))

    def test_none_url(self):
        self.assertIsNone(utils.account_number_from_url(url=None))


class TestGetUsersForAccount(TestAccountMixin):
    """
    Test that get_users_for_account returns the expected list of users for a given account and handles edge cases.
    """

    def test_get_users(self):
        users = utils.get_users_for_account(self.account)
        logger.debug("got users: %s", users)
        self.assertIn(self.admin_user, users)
        self.assertIn(self.non_admin_user, users)
        self.assertEqual(len(users), 2)

    def test_account_required(self):
        with self.assertRaises(SmarterValueError):
            utils.get_users_for_account(None)  # type: ignore


class TestGetUserProfilesForAccount(TestAccountMixin):
    """
    Test that get_user_profiles_for_account returns the expected list of user profiles for a given account and handles edge cases.
    """

    def test_get_profiles(self):
        profiles = utils.get_user_profiles_for_account(self.account)
        self.assertIn(self.user_profile, profiles)
        self.assertIn(self.non_admin_user_profile, profiles)
        self.assertEqual(len(profiles), 2)

    def test_account_required(self):
        with self.assertRaises(SmarterValueError):
            utils.get_user_profiles_for_account(None)  # type: ignore
