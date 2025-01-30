"""Account utilities."""

import logging
import re

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser

from smarter.common.const import SMARTER_ACCOUNT_NUMBER
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib.cache import cache_results
from smarter.lib.django.user import UserType
from smarter.lib.django.validators import SmarterValidator

from .models import Account, UserProfile


logger = logging.getLogger(__name__)
User = get_user_model()

CACHE_TIMEOUT = 60 * 5
SMARTER_ACCOUNT_NUMBER_REGEX = r"\b\d{4}-\d{4}-\d{4}\b"


@cache_results(timeout=CACHE_TIMEOUT)
def get_cached_account(account_id: int = None, account_number: str = None) -> Account:
    """
    Returns the account for the given account_id or account_number.
    """

    if account_id:
        account = Account.objects.get(id=account_id)
        logger.info("%s caching account %s", formatted_text("get_cached_account()"), account)
        return account

    if account_number:
        account = Account.objects.get(account_number=account_number)
        logger.info("%s caching account %s", formatted_text("get_cached_account()"), account)
        return account


@cache_results(timeout=CACHE_TIMEOUT)
def get_cached_account_for_user(user) -> Account:
    """
    Locates the account for a given user, or None if no account exists.
    """
    if isinstance(user, AnonymousUser):
        return None
    try:
        user_profile = UserProfile.objects.get(user=user)
        logger.info(
            "%s caching user profile for user %s", formatted_text("get_cached_account_for_user()"), user_profile
        )
    except UserProfile.DoesNotExist:
        return None
    return user_profile.account


@cache_results(timeout=CACHE_TIMEOUT)
def get_cached_user_profile(user: UserType, account: Account = None) -> UserProfile:
    """
    Locates the user_profile for a given user, or None.
    """
    if user and user.is_authenticated:
        try:
            user_profile = (
                UserProfile.objects.get(user=user, account=account) if account else UserProfile.objects.get(user=user)
            )
            logger.info(
                "%s caching user profile for user %s", formatted_text("get_cached_user_profile()"), user_profile
            )
            return user_profile
        except UserProfile.DoesNotExist:
            pass
    return None


@cache_results(timeout=CACHE_TIMEOUT)
def get_cached_user_for_user_id(user_id: int) -> UserType:
    """
    Returns the user for the given user_id.
    """
    try:
        user = User.objects.get(id=user_id)
        logger.info("%s caching user %s", formatted_text("get_cached_user_for_user_id()"), user)
        return user
    except User.DoesNotExist:
        return None


@cache_results(timeout=CACHE_TIMEOUT)
def get_cached_admin_user_for_account(account: Account) -> UserType:
    """
    Returns the account admin user for the given account.
    """

    user_profile = UserProfile.objects.filter(account=account, user__is_staff=True).order_by("pk").first()
    logger.info(
        "%s caching user profile for user %s", formatted_text("get_cached_admin_user_for_account()"), user_profile
    )
    return user_profile.user if user_profile else None


@cache_results(timeout=CACHE_TIMEOUT)
def get_cached_smarter_admin_user_profile() -> UserProfile:
    """
    Returns the smarter admin user.
    """
    smarter_account = Account.objects.get(account_number=SMARTER_ACCOUNT_NUMBER)
    super_user_profile = (
        UserProfile.objects.filter(account=smarter_account, user__is_superuser=True).order_by("pk").first()
    )
    staff_user_profile = UserProfile.objects.filter(account=smarter_account, user__is_staff=True).order_by("pk").first()
    logger.info(
        "%s caching user profile for user %s",
        formatted_text("get_cached_smarter_admin_user_profile()"),
        super_user_profile or staff_user_profile,
    )
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
