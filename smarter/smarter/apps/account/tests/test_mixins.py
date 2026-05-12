"""Unit tests for AccountMixin and related logic in mixins.py."""

from unittest import mock

from rest_framework.exceptions import AuthenticationFailed

from smarter.apps.account.mixins import AccountMixin
from smarter.apps.account.models import Account, UserProfile
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.common.exceptions import SmarterBusinessRuleViolation
from smarter.lib import logging
from smarter.lib.drf.token_authentication import (
    SmarterAnonymousUser,
    SmarterTokenAuthentication,
)

logger = logging.getSmarterLogger(__name__)


class TestAccountMixinInit(TestAccountMixin):
    """
    Test initialization and property resolution of AccountMixin.
    """

    def test_init_with_user(self):
        mixin = AccountMixin(user=self.admin_user)
        self.assertEqual(mixin.user, self.admin_user)
        self.assertIsInstance(mixin.account, Account)
        self.assertIsInstance(mixin.user_profile, UserProfile)
        self.assertTrue(mixin.is_accountmixin_ready)

    def test_init_with_account(self):
        mixin = AccountMixin(account=self.account)
        self.assertEqual(mixin.account, self.account)
        self.assertIsInstance(mixin.account, Account)

    def test_init_with_user_profile(self):
        mixin = AccountMixin(user_profile=self.user_profile)
        self.assertEqual(mixin.user_profile, self.user_profile)
        self.assertEqual(mixin.user, self.user_profile.user)
        self.assertEqual(mixin.account, self.user_profile.account)

    def test_init_with_account_number(self):
        mixin = AccountMixin(account_number=self.account.account_number)
        self.assertEqual(mixin.account.account_number, self.account.account_number)  # type: ignore[union-attr]

    def test_init_with_request_object(self):
        request = mock.Mock()
        request.headers = {"Authorization": ""}
        request.user = self.admin_user
        request.build_absolute_uri.return_value = "http://test/"
        mixin = AccountMixin(request=request)
        self.assertEqual(mixin.user, self.admin_user)


class TestAccountMixinProperties(TestAccountMixin):
    """
    Test property setters and getters for AccountMixin.
    """

    def setUp(self):
        super().setUp()
        self.mixin = AccountMixin(user=self.admin_user)

    def test_account_setter_and_getter(self):
        mixin = AccountMixin()
        mixin.account = self.account
        self.assertEqual(mixin.account, self.account)

    def test_account_number_setter_and_getter(self):
        mixin = AccountMixin()
        mixin.account_number = self.account.account_number
        self.assertEqual(mixin.account.account_number, self.account.account_number)  # type: ignore

        with self.assertRaises(SmarterBusinessRuleViolation):
            self.mixin.account_number = self.account.account_number

        with self.assertRaises(SmarterBusinessRuleViolation):
            self.mixin.account_number = None

    def test_user_setter_and_getter(self):
        with self.assertRaises(SmarterBusinessRuleViolation):
            self.mixin.user = self.non_admin_user

        with self.assertRaises(SmarterBusinessRuleViolation):
            self.mixin.user = None

        mixin = AccountMixin()
        mixin.user = self.admin_user
        self.assertEqual(mixin.user, self.admin_user)
        self.assertEqual(mixin.account, self.account)
        self.assertEqual(mixin.user_profile, self.user_profile)

    def test_user_profile_setter_and_getter(self):
        with self.assertRaises(SmarterBusinessRuleViolation):
            self.mixin.user_profile = self.non_admin_user_profile

        with self.assertRaises(SmarterBusinessRuleViolation):
            self.mixin.user_profile = None

    def test_is_accountmixin_ready(self):
        self.assertTrue(self.mixin.is_accountmixin_ready)
        mixin = AccountMixin()
        self.assertFalse(mixin.is_accountmixin_ready)

    def test_ready_and_ready_state(self):
        self.assertTrue(self.mixin.ready)
        self.assertEqual(self.formatted_state_ready, self.mixin.ready_state)

        mixin = AccountMixin()
        self.assertFalse(mixin.ready)
        self.assertEqual(self.formatted_state_not_ready, mixin.ready_state)

    def test_is_authenticated(self):
        self.assertTrue(self.mixin.is_authenticated)
        mixin = AccountMixin()
        self.assertFalse(mixin.is_authenticated)


class TestAccountMixinMethods(TestAccountMixin):
    """
    Test methods of AccountMixin.
    """

    def setUp(self):
        super().setUp()
        self.mixin = AccountMixin(user=self.admin_user)

    def test_basic_init(self):
        self.assertEqual(self.mixin.user, self.admin_user)
        self.assertIsInstance(self.mixin.account, Account)
        self.assertEqual(self.mixin.account, self.account)
        self.assertIsInstance(self.mixin.user_profile, UserProfile)
        self.assertEqual(self.mixin.user_profile, self.user_profile)

    def test_to_json(self):
        data = self.mixin.to_json()
        logger.debug("to_json: %s", logging.formatted_json(data))
        self.assertTrue(data.get("ready", False))
        self.assertIsInstance(data, dict)
        self.assertIsInstance(data.get("account"), dict)
        self.assertEqual(data["account"]["accountNumber"], self.account.account_number)
        self.assertEqual(data["user"]["username"], self.admin_user.username)
        self.assertIsInstance(data["userProfile"]["user"], dict)

    def test_authenticate_failure(self):
        with mock.patch.object(
            SmarterTokenAuthentication, "authenticate_credentials", side_effect=AuthenticationFailed
        ):
            mixin = AccountMixin()
            result = mixin.authenticate(b"invalidtoken")
            self.assertFalse(result)
            self.assertIsInstance(mixin.user, SmarterAnonymousUser)

    def test_log_account_mixin_ready_status(self):
        # Should not raise
        self.mixin.log_account_mixin_ready_status()
        mixin = AccountMixin()
        mixin.log_account_mixin_ready_status()

    def test_comparisons(self):
        mixin2 = AccountMixin(user=self.non_admin_user)
        self.assertNotEqual(self.mixin, mixin2)
        self.assertTrue(self.mixin != mixin2)
        self.assertTrue(self.mixin == self.mixin)
        self.assertTrue(self.mixin <= self.mixin)
        self.assertTrue(self.mixin >= self.mixin)
        self.assertTrue((self.mixin < mixin2) or (self.mixin > mixin2) or (self.mixin == mixin2))

    def test_hash(self):
        self.assertIsInstance(hash(self.mixin), int)

    def test_str_and_repr(self):
        s = str(self.mixin)
        r = repr(self.mixin)
        self.assertIsInstance(s, str)
        self.assertIsInstance(r, str)
        self.assertIn("user_profile", s)
        self.assertIn("user_profile", r)

    def test_accountmixin_logger_prefix_and_formatted_class_name(self):
        prefix = self.mixin.account_mixin_logger_prefix
        name = self.mixin.formatted_class_name
        self.assertIsInstance(prefix, str)
        self.assertIsInstance(name, str)

    def test_accountmixin_ready_state(self):
        state = self.mixin.accountmixin_ready_state
        self.assertIsInstance(state, str)
        mixin = AccountMixin()
        state2 = mixin.accountmixin_ready_state
        self.assertIsInstance(state2, str)

    def test_set_account_with_invalid_user_profile(self):
        # Should raise if user is not associated with account
        mixin = AccountMixin(user=self.admin_user)
        with self.assertRaises(SmarterBusinessRuleViolation):
            mixin.account = self.non_admin_user_profile.account
