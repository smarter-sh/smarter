"""Account utilities."""

import logging
import re
import uuid

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser, AnonymousUser

from smarter.common.const import SMARTER_ACCOUNT_NUMBER
from smarter.common.exceptions import SmarterConfigurationError, SmarterValueError
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib.cache import cache_results
from smarter.lib.django.user import UserType
from smarter.lib.django.validators import SmarterValidator

from .models import Account, UserProfile


logger = logging.getLogger(__name__)
User = get_user_model()

SMARTER_ACCOUNT_NUMBER_REGEX = r"\b\d{4}-\d{4}-\d{4}\b"


@cache_results()
def get_cached_account(account_id: int = None, account_number: str = None) -> Account:
    """
    Returns the account for the given account_id or account_number.
    """

    if account_id:
        account = Account.objects.get(id=account_id)
        return account

    if account_number:
        account = Account.objects.get(account_number=account_number)
        return account


def get_cached_smarter_account() -> Account:
    """
    Returns the smarter account.
    """
    account = get_cached_account(account_number=SMARTER_ACCOUNT_NUMBER)
    return account


@cache_results()
def get_cached_default_account() -> Account:
    """
    Returns the default account.
    """
    try:
        account = Account.objects.get(is_default_account=True)
    except Account.DoesNotExist as e:
        raise SmarterConfigurationError("No default account found.") from e
    except Account.MultipleObjectsReturned as e:
        raise SmarterConfigurationError("Multiple default accounts found.") from e
    return account


@cache_results()
def get_cached_account_for_user(user) -> Account:
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


@cache_results()
def get_cached_user_profile(user: UserType, account: Account = None) -> UserProfile:
    """
    Locates the user_profile for a given user, or None.
    """
    try:
        if not user.is_authenticated:
            return None
    except AttributeError:
        # Handle case where user is not an instance of User
        return None
    try:
        user_profile = (
            UserProfile.objects.get(user=user, account=account) if account else UserProfile.objects.get(user=user)
        )
        return user_profile
    except UserProfile.DoesNotExist:
        pass


@cache_results()
def get_cached_user_for_user_id(user_id: int) -> AbstractUser:
    """
    Returns the user for the given user_id.
    """
    try:
        user = User.objects.get(id=user_id)
        return user
    except User.DoesNotExist:
        return None


@cache_results()
def get_cached_admin_user_for_account(account: Account) -> AbstractUser:
    """
    Returns the account admin user for the given account. If the user does not exist, it will be created.
    """
    if not account:
        raise SmarterValueError("Account is required")

    console_prefix = formatted_text("get_cached_admin_user_for_account()")
    user_profile = UserProfile.objects.filter(account=account, user__is_staff=True).order_by("pk").first()
    if not user_profile:
        # Create a new admin user and user profile
        random_email = f"{uuid.uuid4().hex[:8]}@mail.com"
        admin_user = User.objects.create_user(username=account.account_number, email=random_email, is_staff=True)
        user_profile = UserProfile.objects.create(user=admin_user, account=account)
        logger.warning("%s created new admin user profile for user %s", console_prefix, user_profile)
    return user_profile.user if user_profile else None


@cache_results()
def get_cached_smarter_admin_user_profile() -> UserProfile:
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
