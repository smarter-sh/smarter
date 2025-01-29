"""Mixin class that provides the account and user properties."""

from smarter.apps.account.models import Account, UserProfile
from smarter.apps.account.utils import account_admin_user, account_for_user
from smarter.common.exceptions import SmarterBusinessRuleViolation
from smarter.lib.django.user import User, UserType
from smarter.lib.django.validators import SmarterValidator


class AccountMixin:
    """
    Mixin class that provides the account and user properties.
    """

    _account: Account = None
    _user: UserType = None
    _user_profile: UserProfile = None

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        account: Account = None,
        user: UserType = None,
        account_number: str = None,
    ):
        self.init()
        if account_number:
            self.account = account or Account.objects.get(account_number=account_number)
        self.user = user

        if self._user and self._account:
            self._user_profile = self.get_user_profile(user=self._user, account=self._account)

    @property
    def account(self) -> Account:
        if self._account:
            return self._account
        if self._user_profile:
            self._account = self.user_profile.account
        elif self._user:
            self._account = account_for_user(self._user)
        return self._account

    @account.setter
    def account(self, account: Account):
        self._account = account
        if account and self._user:
            try:
                self._user_profile = self.get_user_profile(user=self._user, account=self._account)
            except UserProfile.DoesNotExist as e:
                raise SmarterBusinessRuleViolation(
                    f"User {self._user} does not belong to the account {account.account_number}."
                ) from e

    @property
    def user(self) -> UserType:
        if self._user:
            return self._user
        if self._user_profile:
            self._user = self._user_profile.user
        elif self._account:
            self._user = account_admin_user(self.account)
        return self._user

    @user.setter
    def user(self, user: UserType):
        self._user = user
        self._account = account_for_user(user)
        self._user_profile = None

    @property
    def user_profile(self) -> UserProfile:
        if self._user_profile:
            return self._user_profile
        if self._user and self._account:
            self._user_profile = self.get_user_profile(user=self.user, account=self.account)
        elif self._user:
            self._user_profile = self.get_user_profile(user=self.user)
        elif self._account:
            user = account_admin_user(self.account)
            self._user_profile = self.get_user_profile(user=user, account=self.account)
        return self._user_profile

    def get_user_profile(self, user: UserType = None, account: Account = None) -> UserProfile:
        if not user:
            return None
        if not user.is_authenticated:
            return None

        if user and account:
            try:
                return UserProfile.objects.get(user=user, account=account)
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

    def init(self):
        """
        This method initializes the account and user properties.
        """
        self._account = None
        self._user = None
        self._user_profile = None
