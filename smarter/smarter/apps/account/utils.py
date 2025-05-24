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
from smarter.lib.django.user import UserType, get_resolved_user
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
        logger.info("get_cached_default_account() retrieving and caching default account %s", account)
    except Account.DoesNotExist as e:
        logger.error("get_cached_default_account() no default account found")
        raise SmarterConfigurationError("No default account found.") from e
    except Account.MultipleObjectsReturned as e:
        logger.error("get_cached_default_account() multiple default accounts found")
        raise SmarterConfigurationError("Multiple default accounts found.") from e
    return account


def get_cached_account_for_user(user) -> Account:
    """
    Locates the account for a given user, or None if no account exists.
    """
    if isinstance(user, AnonymousUser):
        return None

    @cache_results()
    def _get_account(user):
        if not user:
            return None
        try:
            user_profiles = UserProfile.objects.filter(user=user)
            if not user_profiles.exists():
                logger.error("get_cached_account_for_user() no UserProfile found for user %s", user)
                return None
            for user_profile in user_profiles:
                if user_profile.account.is_default_account:
                    logger.info(
                        "get_cached_account_for_user() retrieving and caching default account %s for user %s",
                        user_profile.account,
                        user,
                    )
                    return user_profile.account
            # If no default account is found, return the first account
            user_profile = user_profiles.first()
            logger.info(
                "get_cached_default_account() retrieving and caching account %s user %s",
                user_profile.account,
                user_profile.user,
            )
        except UserProfile.DoesNotExist:
            logger.error("get_cached_default_account() no UserProfile found for user %s", user)
            return None
        return user_profile.account

    get_cached_account_for_user.invalidate_cache = _get_account.invalidate_cache

    return _get_account(user)


def get_cached_user_profile(user: UserType, account: Account = None) -> UserProfile:
    """
    Locates the user_profile for a given user, or None.
    """
    try:
        if not user.is_authenticated:
            logger.warning("get_cached_user_profile() user is not authenticated")
            return None
    except AttributeError:
        return None

    account = account or get_cached_account_for_user(user)
    if not account:
        logger.error("get_cached_user_profile() no account found for user %s", user)
        return None

    @cache_results()
    def _get_user_profile(resolved_user, account):
        try:
            user_profile = UserProfile.objects.get(user=resolved_user, account=account)
            logger.info("get_cached_user_profile() retrieving and caching UserProfile %s", user_profile)
            return user_profile
        except UserProfile.DoesNotExist:
            logger.error("get_cached_user_profile() no UserProfile found for user %s", resolved_user)
            return None

    get_cached_user_profile.invalidate_cache = _get_user_profile.invalidate_cache

    # pylint: disable=W0212
    resolved_user = get_resolved_user(user)
    return _get_user_profile(resolved_user, account)


@cache_results()
def get_cached_user_for_user_id(user_id: int) -> AbstractUser:
    """
    Returns the user for the given user_id.
    """
    try:
        user = User.objects.get(id=user_id)
        logger.info("get_cached_user_for_user_id() retrieving and caching user %s", user)
        return user
    except User.DoesNotExist:
        logger.error("get_cached_user_for_user_id() no user found for user_id %s", user_id)
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
    if user_profile:
        logger.info("%s found and cached admin UserProfile %s for account %s", console_prefix, user_profile, account)
        return user_profile.user
    else:
        # Create a new admin user and UserProfile
        random_email = f"{uuid.uuid4().hex[:8]}@mail.com"
        admin_user = User.objects.create_user(username=account.account_number, email=random_email, is_staff=True)
        logger.info("%s created new admin User %s for account %s", console_prefix, admin_user, account)
        user_profile = UserProfile.objects.create(user=admin_user, account=account)
        logger.info("%s created new admin UserProfile for user %s", console_prefix, user_profile)
    if not user_profile:
        logger.error("%s failed to query nor create admin UserProfile for account %s", console_prefix, account)
        raise SmarterConfigurationError("Failed to create admin UserProfile")
    return user_profile.user if user_profile else None


@cache_results()
def get_cached_smarter_admin_user_profile() -> UserProfile:
    """
    Returns the smarter admin user.
    """
    try:
        smarter_account = Account.objects.get(account_number=SMARTER_ACCOUNT_NUMBER)
    except Account.DoesNotExist as e:
        logger.error("get_cached_smarter_admin_user_profile() no smarter account found")
        raise SmarterConfigurationError("No smarter account found.") from e

    try:
        super_user_profile = (
            UserProfile.objects.filter(account=smarter_account, user__is_superuser=True).order_by("pk").first()
        )
        logger.info(
            "get_cached_smarter_admin_user_profile() retrieving and caching super UserProfile %s", super_user_profile
        )
    except UserProfile.DoesNotExist as e:
        logger.error(
            "get_cached_smarter_admin_user_profile() no super UserProfile found for account %s", smarter_account
        )
        raise SmarterConfigurationError("No super UserProfile found.") from e

    try:
        staff_user_profile = (
            UserProfile.objects.filter(account=smarter_account, user__is_staff=True).order_by("pk").first()
        )
        logger.info(
            "get_cached_smarter_admin_user_profile() retrieving and caching staff UserProfile %s", staff_user_profile
        )
    except UserProfile.DoesNotExist as e:
        logger.error(
            "get_cached_smarter_admin_user_profile() no staff UserProfile found for account %s", smarter_account
        )
        raise SmarterConfigurationError("No staff UserProfile found.") from e

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


def get_users_for_account(account: Account) -> list[AbstractUser]:
    """
    Returns a list of users for the given account.
    """
    if not account:
        raise SmarterValueError("Account is required")

    users = User.objects.filter(userprofile__account=account)
    return users


def get_user_profiles_for_account(account: Account) -> list[UserProfile]:
    """
    Returns a list of user profiles for the given account.
    """
    if not account:
        raise SmarterValueError("Account is required")

    user_profiles = UserProfile.objects.filter(account=account)
    return user_profiles
