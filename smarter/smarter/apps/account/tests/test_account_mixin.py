"""
Test api/v1/ base class.

We have somewhere in the neighborhood of 75 api endpoints to test, so we want
ensure that:
- our setUp and tearDown methods are as efficient as possible.
- we are authenticating our http requests properly and consistently.
"""

from smarter.apps.account.mixins import AccountMixin
from smarter.apps.account.models import Account, User, UserProfile
from smarter.apps.account.tests.factories import mortal_user_factory
from smarter.apps.account.utils import (
    get_cached_admin_user_for_account,
    get_cached_user_profile,
)
from smarter.common.exceptions import SmarterBusinessRuleViolation
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestAccountMixin(SmarterTestBase):
    """Test AccountMixin."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.mortal_user, cls.account, cls.user_profile = mortal_user_factory()
        cls.admin_user = get_cached_admin_user_for_account(cls.account)
        cls.other_user, cls.other_account, cls.other_user_profile = mortal_user_factory()

    @classmethod
    def tearDownClass(cls) -> None:
        super().tearDownClass()
        instance = cls()
        # tear down the user, account, and user_profile
        try:
            if instance.user_profile:
                instance.user_profile.delete()
        except UserProfile.DoesNotExist:
            pass
        try:
            if instance.mortal_user:
                instance.mortal_user.delete()
        except User.DoesNotExist:
            pass

        # tear down the admin user
        try:
            up = get_cached_user_profile(user=cls.admin_user)
            if up:
                up.delete()
        except UserProfile.DoesNotExist:
            pass
        try:
            if cls.admin_user:
                cls.admin_user.delete()
        except User.DoesNotExist:
            pass

        try:
            if instance.account:
                instance.account.delete()
        except Account.DoesNotExist:
            pass
        # tear down the other user, account, and user_profile
        try:
            if instance.other_user_profile:
                instance.other_user_profile.delete()
        except UserProfile.DoesNotExist:
            pass
        try:
            if instance.other_user:
                instance.other_user.delete()
        except User.DoesNotExist:
            pass
        try:
            if instance.other_account:
                instance.other_account.delete()
        except Account.DoesNotExist:
            pass

    def test_initializations(self) -> None:
        """Test instantiation with all arguments."""
        # verify that the user, account, and user_profile are what we think they are
        instance = AccountMixin(user=self.mortal_user, account=self.account)
        self.assertEqual(instance.user, self.mortal_user)
        self.assertEqual(instance.account, self.account)
        self.assertEqual(instance.user_profile, self.user_profile)

        # ditto for the other user, account, and user_profile
        other_instance = AccountMixin(user=self.other_user, account=self.other_account)
        self.assertEqual(other_instance.user, self.other_user)
        self.assertEqual(other_instance.account, self.other_account)
        self.assertEqual(other_instance.user_profile, self.other_user_profile)

        # verify that the user, account are different from the other_user, other_account
        self.assertNotEqual(self.mortal_user, self.other_user)
        self.assertNotEqual(self.account, self.other_account)
        self.assertNotEqual(self.user_profile, self.other_user_profile)
        self.assertNotEqual(instance.user, other_instance.user)
        self.assertNotEqual(instance.account, other_instance.account)
        self.assertNotEqual(instance.user_profile, other_instance.user_profile)

        # verify that the admin user is what we think it is and that it's profile is cached
        # and that it's associated with the same account as user.
        self.assertIsNotNone(self.admin_user)
        admin_user_profile = get_cached_user_profile(user=self.admin_user, account=self.account)
        self.assertIsNotNone(admin_user_profile)
        if not isinstance(admin_user_profile, UserProfile):
            self.fail("Admin user profile should not be None")
        self.assertEqual(admin_user_profile.user, self.admin_user)
        self.assertEqual(admin_user_profile.account, self.account)

    def test_get_cached_admin_user_for_account(self) -> None:
        """Test get_cached_admin_user_for_account."""
        admin_user = get_cached_admin_user_for_account(self.account)
        self.assertIsNotNone(admin_user)
        self.assertEqual(admin_user, self.admin_user)

    def test_get_cached_user_profile(self) -> None:
        """Test get_cached_user_profile."""
        user_profile = get_cached_user_profile(user=self.mortal_user, account=self.account)
        self.assertIsNotNone(user_profile)
        self.assertEqual(user_profile, self.user_profile)

        # get the profile without providing an account
        user_profile = get_cached_user_profile(user=self.mortal_user)
        self.assertIsNotNone(user_profile)
        self.assertEqual(user_profile, self.user_profile)

        # get the admin user profile
        user_profile = get_cached_user_profile(user=self.admin_user)
        self.assertIsNotNone(user_profile)
        self.assertEqual(user_profile.user, self.admin_user)  # type: ignore[return-value]

    def test_empty_initialization(self) -> None:
        """Test instantiation with no arguments."""
        instance = AccountMixin()
        self.assertIsNone(instance.user)
        self.assertIsNone(instance.account)
        self.assertIsNone(instance.user_profile)

    def test_user_initialization(self) -> None:
        """
        Test instantiation with a user. Mixin should set account and
        user_profile based on the user.
        """
        instance = AccountMixin(user=self.mortal_user)
        self.assertEqual(instance.user, self.mortal_user)
        self.assertEqual(instance.account, self.account)
        self.assertEqual(instance.user_profile, self.user_profile)

    def test_unset_user(self) -> None:
        """Test setting user to None."""
        instance = AccountMixin(user=self.mortal_user)
        self.assertEqual(instance.user, self.mortal_user)
        # force lazy instantiations of account and user_profile.
        self.assertEqual(instance.account, self.account)
        self.assertEqual(instance.user_profile, self.user_profile)

        # unset the user but leave the account unchanged.
        # should reinitialize with the admin user.
        instance.user = None
        self.assertIsNone(instance.account)
        self.assertIsNone(instance.user_profile)

        # unset both the user and account.
        # should unset everything.
        instance.user = None
        instance.account = None
        self.assertIsNone(instance.user)
        self.assertIsNone(instance.account)
        self.assertIsNone(instance.user_profile)

    def test_unset_account(self) -> None:
        """Test setting account to None."""
        instance = AccountMixin(user=self.mortal_user)
        self.assertEqual(instance.user, self.mortal_user)
        self.assertEqual(instance.account, self.account)
        self.assertEqual(instance.user_profile, self.user_profile)

        # should unset the account, but leave the user unchanged.
        # should reinitialize the account and user_profile based on the user.
        instance.account = None
        self.assertEqual(instance.user, self.mortal_user)
        self.assertEqual(instance.account, self.account)
        self.assertIsNotNone(instance.user_profile)
        self.assertEqual(instance.user_profile, self.user_profile)

    def test_unset_user_profile(self) -> None:
        """Test setting user_profile to None."""
        instance = AccountMixin(user=self.mortal_user)
        self.assertEqual(instance.user, self.mortal_user)
        self.assertEqual(instance.account, self.account)
        self.assertEqual(instance.user_profile, self.user_profile)

        # .1) unset the user_profile, but leave the user and account unchanged.
        # should reinitialize the user_profile based on the user.
        instance.user_profile = None
        self.assertEqual(instance.user, self.mortal_user)
        self.assertEqual(instance.account, self.account)
        self.assertEqual(instance.user_profile, self.user_profile)

        # .2) unset the user_profile and user, but leave the account unchanged.
        instance.user_profile = None
        instance.account = None

        # ensure that user is still set.
        self.assertEqual(instance.user, self.mortal_user)

        # should reinitialize the account and user_profile based on the user.
        self.assertEqual(instance.account, self.account)
        self.assertEqual(instance.user_profile, self.user_profile)

        # .3) unset the user_profile and account, but leave the user unchanged.
        instance.user_profile = None
        instance.account = None

        # ensure that account is still set.
        self.assertIsNotNone(instance.account)

    def test_set_account(self) -> None:
        """
        Test setting account. Should set the admin user and user_profile
        """
        instance = AccountMixin(account=self.account)
        self.assertIsNotNone(self.account)
        self.assertIsNotNone(instance.account)
        self.assertEqual(instance.account, self.account)

        # verify that neither the user nor the user_profile are set.
        self.assertIsNone(instance.user)
        self.assertIsNone(instance.user_profile)

    def test_invalid_user_assignment(self) -> None:
        """Test setting an invalid user."""
        instance = AccountMixin(account=self.account)
        with self.assertRaises(SmarterBusinessRuleViolation):
            instance.user = self.other_user

    def test_invalid_account_assignment(self) -> None:
        """Test setting an invalid account."""
        instance = AccountMixin(user=self.mortal_user)

        # verify that the user and account are what we think they are
        self.assertEqual(instance.user, self.mortal_user)
        self.assertEqual(instance.account, self.account)

        # ensure that the other account is not the same as the base account
        self.assertNotEqual(self.account, self.other_account)

        # try to set the account to the other account which
        # should raise an exception.
        with self.assertRaises(SmarterBusinessRuleViolation):
            instance.account = self.other_account

    def test_account_number(self) -> None:
        """Test account_number."""
        instance = AccountMixin(account_number=self.account.account_number)
        self.assertIsNotNone(instance.account)
        self.assertEqual(instance.account, self.account)
        self.assertEqual(instance.account_number, self.account.account_number)

        instance.account = None
        self.assertIsNone(instance.account)

    def unset_account_number(self) -> None:
        """Test setting account_number to None."""
        instance = AccountMixin(account_number=self.account.account_number)
        self.assertIsNotNone(instance.account)
        self.assertEqual(instance.account, self.account)
        self.assertEqual(instance.account_number, self.account.account_number)

        instance.account_number = None
        self.assertIsNone(instance.account)
        self.assertIsNone(instance.account_number)
