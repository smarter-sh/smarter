"""Test the AccountMixin branches that test_mixins.py doesn't: lazy lookups, immutability, ordering and api tokens."""

from smarter.apps.account.mixins import AccountMixin
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.common.exceptions import SmarterBusinessRuleViolation
from smarter.lib.drf.models import SmarterAuthToken


class TestAccountMixinMore(TestAccountMixin):
    """Test AccountMixin."""

    def test_lazy_account_and_profile_from_user(self):
        """Test that the account and user profile are looked up from the user, when first read."""
        mixin = AccountMixin()
        mixin._user = self.non_admin_user  # pylint: disable=protected-access
        self.assertEqual(mixin.account, self.account)
        self.assertEqual(mixin.user_profile, self.non_admin_user_profile)
        self.assertTrue(mixin.am_ready)
        self.assertTrue(mixin.is_authenticated)

    def test_lazy_profile_from_user_and_account(self):
        mixin = AccountMixin()
        mixin._user = self.non_admin_user  # pylint: disable=protected-access
        mixin._account = self.account  # pylint: disable=protected-access
        self.assertEqual(mixin.user_profile, self.non_admin_user_profile)

    def test_user_from_profile(self):
        mixin = AccountMixin()
        mixin._user_profile = self.user_profile  # pylint: disable=protected-access
        self.assertEqual(mixin.user, self.admin_user)

    def test_setters_are_immutable(self):
        """Test that the account, account number and user can't be changed once they are set."""
        mixin = AccountMixin(user=self.admin_user)
        with self.assertRaises(SmarterBusinessRuleViolation):
            mixin.user = self.non_admin_user
        self.assertEqual(mixin.account, self.account)
        with self.assertRaises(SmarterBusinessRuleViolation):
            mixin.account = self.account
        with self.assertRaises(SmarterBusinessRuleViolation):
            mixin.account_number = self.account.account_number

    def test_setters_to_none(self):
        mixin = AccountMixin()
        mixin.user = None
        mixin.account_number = None
        mixin.account = None
        self.assertIsNone(mixin.user_profile)
        self.assertFalse(mixin.is_authenticated)

    def test_account_setter_with_user(self):
        mixin = AccountMixin()
        mixin._user = self.non_admin_user  # pylint: disable=protected-access
        mixin.account = self.account
        self.assertEqual(mixin.user_profile, self.non_admin_user_profile)

    def test_init(self):
        """Test init(), which sets whichever of the user profile, the user and account, the user or the account it is given."""
        for kwargs, expected in (
            ({"user_profile": self.user_profile}, self.user_profile),
            ({"user": self.non_admin_user, "account": self.account}, self.non_admin_user_profile),
            ({"user": self.non_admin_user}, self.non_admin_user_profile),
        ):
            with self.subTest(kwargs=list(kwargs)):
                mixin = AccountMixin()
                mixin.init(**kwargs)
                self.assertEqual(mixin.user_profile, expected)
        mixin = AccountMixin()
        mixin.init(account=self.account)
        self.assertEqual(mixin.account, self.account)

    def test_ordering(self):
        admin = AccountMixin(user_profile=self.user_profile)
        mortal = AccountMixin(user_profile=self.non_admin_user_profile)
        empty, other_empty = AccountMixin(), AccountMixin()
        self.assertEqual(admin < mortal, str(self.user_profile) < str(self.non_admin_user_profile))
        self.assertTrue(admin <= admin)  # pylint: disable=comparison-with-itself
        self.assertTrue(admin >= admin)  # pylint: disable=comparison-with-itself
        self.assertNotEqual(admin > mortal, admin < mortal)
        self.assertTrue(empty < admin)
        self.assertFalse(admin < empty)
        self.assertFalse(empty < other_empty)
        for method in ("__lt__", "__le__", "__gt__", "__ge__"):
            with self.subTest(method=method):
                self.assertIs(getattr(admin, method)("not a mixin"), NotImplemented)

    def test_authenticate(self):
        """Test that a valid api token authenticates its user, and an invalid one doesn't."""
        token, key = SmarterAuthToken.objects.create(  # type: ignore[misc]
            user_profile=self.user_profile, name="test_mixins_more", user=self.admin_user
        )
        self.addCleanup(token.delete)
        mixin = AccountMixin()
        self.assertTrue(mixin.authenticate(key.encode()))
        self.assertEqual(mixin.user, self.admin_user)
        self.assertTrue(mixin.authenticate(key.encode()))  # already authenticated
        self.assertFalse(AccountMixin().authenticate(b"not-a-valid-token"))
