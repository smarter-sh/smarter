"""Account utilities."""

from smarter.common.const import SMARTER_ACCOUNT_NUMBER
from smarter.lib.django.user import UserType

from .models import Account, UserProfile


def account_for_user(user) -> Account:
    """
    Locates the account for a given user, or None if no account exists.
    """
    try:
        user_profile = UserProfile.objects.get(user=user)
    except UserProfile.DoesNotExist:
        return None
    return user_profile.account


def account_admin_user(account: Account) -> UserType:
    """
    Returns the account admin user for the given account.
    """

    user_profile = UserProfile.objects.filter(account=account, user__is_staff=True).order_by("pk").first()
    return user_profile.user if user_profile else None


def smarter_admin_user_profile() -> UserProfile:
    """
    Returns the smarter admin user.
    """
    smarter_account = Account.objects.get(account_number=SMARTER_ACCOUNT_NUMBER)
    super_user_profile = (
        UserProfile.objects.filter(account=smarter_account, user__is_superuser=True).order_by("pk").first()
    )
    staff_user_profile = UserProfile.objects.filter(account=smarter_account, user__is_staff=True).order_by("pk").first()

    return super_user_profile or staff_user_profile
