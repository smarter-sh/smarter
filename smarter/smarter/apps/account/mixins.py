"""Mixin class that provides the account and user properties."""

import logging

from smarter.apps.account.models import Account, UserProfile
from smarter.apps.account.utils import (
    get_cached_account_for_user,
    get_cached_admin_user_for_account,
)
from smarter.common.exceptions import SmarterBusinessRuleViolation
from smarter.lib.django.user import UserType

from .utils import get_cached_account, get_cached_user_profile


logger = logging.getLogger(__name__)


class AccountMixin:
    """
    Mixin class that provides the account and user properties.
    """

    __slots__ = ["_account", "_user", "_user_profile"]

    def __init__(
        self,
        account: Account = None,
        user: UserType = None,
        account_number: str = None,
    ):
        self._account: Account = None
        self._user: UserType = None
        self._user_profile: UserProfile = None
        self.account = account or get_cached_account(account_number=account_number) if account_number else None
        self.user = user

    @property
    def account(self) -> Account:
        """
        Returns the account for the current user. Handle
        lazy instantiation from user or user_profile.
        """
        if self._account:
            return self._account
        if self._user_profile:
            self._account = self.user_profile.account
        elif self._user:
            self._account = get_cached_account_for_user(self._user)
        return self._account

    @account.setter
    def account(self, account: Account):
        self._account = account
        if not self._account:
            # unset the user_profile if the account is unset
            self.user_profile = None
        if account and self._user:
            try:
                self._user_profile = self.get_user_profile(user=self._user, account=self._account)
            except UserProfile.DoesNotExist as e:
                raise SmarterBusinessRuleViolation(
                    f"User {self._user} does not belong to the account {account.account_number}."
                ) from e

    @property
    def account_number(self) -> str:
        return self.account.account_number if self.account else None

    @account_number.setter
    def account_number(self, account_number: str):
        if not account_number:
            self.account = None
            self.user_profile = None
            return
        self.account = get_cached_account(account_number=account_number)

    @property
    def user(self) -> UserType:
        if self._user:
            return self._user
        if self._user_profile:
            self._user = self._user_profile.user
        elif self._account:
            self._user = get_cached_admin_user_for_account(self.account)
            logger.warning("AccountMixin: user not set, using admin user %s for account %s", self._user, self._account)
        return self._user

    @user.setter
    def user(self, user: UserType):
        self._user = user
        if not self._user:
            # unset the user_profile if the user is unset
            self.user_profile = None
            return
        self._account = get_cached_account_for_user(user)
        self._user_profile = None

    @property
    def user_profile(self) -> UserProfile:
        if self._user_profile:
            return self._user_profile
        # note that we have to use property references here in order to trigger
        # the property setters.
        if self.user and self.account:
            self._user_profile = get_cached_user_profile(user=self.user, account=self.account)
        elif self.user:
            self._user_profile = get_cached_user_profile(user=self.user)
        elif self.account:
            user = get_cached_admin_user_for_account(self.account)
            self._user_profile = get_cached_user_profile(user=user, account=self.account)
            logger.warning("AccountMixin: user not set, using admin user %s for account %s", self._user, self._account)
        return self._user_profile

    @user_profile.setter
    def user_profile(self, user_profile: UserProfile):
        self._user_profile = user_profile
        if not self._user_profile:
            return
        self._user = self._user_profile.user
        self._account = self._user_profile.account

    def get_user_profile(self, user: UserType = None, account: Account = None) -> UserProfile:
        if not user:
            return None
        if not user.is_authenticated:
            return None

        if user and account:
            try:
                return get_cached_user_profile(user=user, account=account)
            except UserProfile.DoesNotExist as e:
                raise SmarterBusinessRuleViolation(
                    f"User {user} does not belong to the account {account.account_number}."
                ) from e
            except TypeError:
                # note: we'll only get a UserType if the user is authenticated.
                # Other self._user will be a SimpleLazyObject. The exception that we're trying to avoid is
                # when AccountMixin is used with public views that don't require authentication, in which case
                # self._user will be a SimpleLazyObject and we can't call UserProfile.objects.get(user=self.user)
                #
                # TypeError: Field 'id' expected a number but got <SimpleLazyObject: <django.contrib.auth.models.AnonymousUser object at 0x7fd7f18a78d0>>.
                return None
