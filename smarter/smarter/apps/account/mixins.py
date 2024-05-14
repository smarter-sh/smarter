"""Mixin class that provides the account and user properties."""

from smarter.apps.account.models import Account, UserProfile
from smarter.apps.account.utils import account_admin_user
from smarter.lib.django.user import UserType
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
        account_number: str,
    ):
        SmarterValidator.validate_account_number(account_number)
        self._account = Account.objects.get(account_number=account_number)

    @property
    def account(self) -> Account:
        return self._account

    @property
    def user(self) -> UserType:
        if self._user:
            return self._user
        self._user = account_admin_user(self.account)
        return self._user

    @property
    def user_profile(self) -> UserProfile:
        if self._user_profile:
            return self._user_profile
        self._user_profile = UserProfile.objects.get(user=self.user, account=self.account)
        return self._user_profile
