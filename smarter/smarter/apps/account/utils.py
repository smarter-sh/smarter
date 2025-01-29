"""Account utilities."""

import re

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser

from smarter.common.const import SMARTER_ACCOUNT_NUMBER
from smarter.lib.cache import cache_results
from smarter.lib.django.user import UserType
from smarter.lib.django.validators import SmarterValidator

from .models import Account, UserProfile


User = get_user_model()

CACHE_TIMEOUT = 60 * 5
SMARTER_ACCOUNT_NUMBER_REGEX = r"\b\d{4}-\d{4}-\d{4}\b"


@cache_results(timeout=CACHE_TIMEOUT)
def account_for_user(user) -> Account:
    """
    Locates the account for a given user, or None if no account exists.
    """
    if isinstance(user, AnonymousUser):
        return None
    try:
        user_profile = UserProfile.objects.get(user=user)
    except UserProfile.DoesNotExist:
        return None
    return user_profile.account


@cache_results(timeout=CACHE_TIMEOUT)
def user_profile_for_user(user) -> Account:
    """
    Locates the user_profile for a given user, or None.
    """
    try:
        return UserProfile.objects.get(user=user)
    except UserProfile.DoesNotExist:
        return None


@cache_results(timeout=CACHE_TIMEOUT)
def user_for_user_id(user_id: int) -> UserType:
    """
    Returns the user for the given user_id.
    """
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return None


@cache_results(timeout=CACHE_TIMEOUT)
def account_admin_user(account: Account) -> UserType:
    """
    Returns the account admin user for the given account.
    """

    user_profile = UserProfile.objects.filter(account=account, user__is_staff=True).order_by("pk").first()
    return user_profile.user if user_profile else None


@cache_results(timeout=CACHE_TIMEOUT)
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


def account_number_from_url(url: str) -> str:
    """
    Extracts the account number from the URL.
    :return: The account number or None if not found.

    example: https://hr.3141-5926-5359.alpha.api.smarter.sh/
    returns '3141-5926-5359'
    """
    if not url:
        return None
    SmarterValidator.validate_url(url)
    pattern = SMARTER_ACCOUNT_NUMBER_REGEX
    match = re.search(pattern, url)
    return match.group(0) if match else None
