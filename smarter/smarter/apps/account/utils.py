"""
Account utilities. Provides simplified and performance-optimized access to account and user data.

Note that this module uses both LRU in-memory caching and a proprietary
implementation of Django ORM caching to optimize performance. in-memory caching
is per-process and short-lived, while the ORM caching is Redis-based and
persisted, and will live for as long as the cache expiration is set in the decorator.

LRU caching is used for frequently accessed in-process data such as User, Account and
UserProfile in cases where we can cache based on simple atomic identifiers like
the primary key id value account.id, user.id, etc.
"""

import logging
import re
import uuid
from functools import lru_cache

from django.contrib.auth.models import AbstractUser, AnonymousUser

from smarter.common.const import SMARTER_ACCOUNT_NUMBER
from smarter.common.exceptions import SmarterConfigurationError, SmarterValueError
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib.cache import cache_results
from smarter.lib.django import waffle
from smarter.lib.django.user import User, UserType, get_resolved_user
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .models import Account, UserProfile


logger = logging.getLogger(__name__)

LRU_CACHE_MAX_SIZE = 128


@cache_results()
def get_cached_account(account_id: int = None, account_number: str = None) -> Account:
    """
    Returns the account for the given account_id or account_number.
    """

    @lru_cache(maxsize=LRU_CACHE_MAX_SIZE)
    def _in_memory_account_by_id(account_id):
        """
        In-memory cache for account objects by ID.
        """
        account = Account.objects.get(id=account_id)
        if waffle.switch_is_active(SmarterWaffleSwitches.CACHE_LOGGING):
            logger.info("_in_memory_account_by_id() retrieving and caching account %s", account)
        return account

    @lru_cache(maxsize=LRU_CACHE_MAX_SIZE)
    def _in_memory_account_by_number(account_number):
        """
        In-memory cache for account objects by account number.
        """
        account = Account.objects.get(account_number=account_number)
        if waffle.switch_is_active(SmarterWaffleSwitches.CACHE_LOGGING):
            logger.info("_in_memory_account_by_number() retrieving and caching account %s", account)
        return account

    if account_id:
        return _in_memory_account_by_id(account_id)

    if account_number:
        return _in_memory_account_by_number(account_number)


@cache_results()
def get_cached_smarter_account() -> Account:
    """
    Returns the smarter account.
    """
    account = get_cached_account(account_number=SMARTER_ACCOUNT_NUMBER)
    return account


@lru_cache(maxsize=LRU_CACHE_MAX_SIZE)
def get_cached_default_account() -> Account:
    """
    Returns the default account.
    """
    account = Account.objects.get(is_default_account=True)
    if waffle.switch_is_active(SmarterWaffleSwitches.CACHE_LOGGING):
        logger.info("get_cached_default_account() retrieving and caching default account %s", account)
    return account


@cache_results()
def _get_account_for_user(user):
    if not user:
        return None

    user_id = getattr(user, "id", None)
    if not user_id:
        if waffle.switch_is_active(SmarterWaffleSwitches.CACHE_LOGGING):
            logger.error("get_cached_account_for_user() user has no ID")
        return None

    @lru_cache(maxsize=LRU_CACHE_MAX_SIZE)
    def _get_account_for_user_by_id(user_id):
        """
        In-memory cache for user accounts.
        """
        user_profiles = UserProfile.objects.filter(user_id=user_id)
        for user_profile in user_profiles:
            if user_profile.account.is_default_account and waffle.switch_is_active(SmarterWaffleSwitches.CACHE_LOGGING):
                logger.info(
                    "get_cached_account_for_user() retrieving and caching default account %s for user %s",
                    user_profile.account,
                    user,
                )
                return user_profile.account
        # If no default account is found, return the first account
        user_profile = user_profiles.first()
        if not user_profile:
            if waffle.switch_is_active(SmarterWaffleSwitches.CACHE_LOGGING):
                logger.error("get_cached_account_for_user_by_id() no UserProfile found for user ID %s", user_id)
            return None
        account = user_profile.account
        if waffle.switch_is_active(SmarterWaffleSwitches.CACHE_LOGGING):
            logger.info(
                "_get_account_for_user_by_id() retrieving and caching default account %s for user ID %s",
                account,
                user_id,
            )
        return account

    return _get_account_for_user_by_id(user_id)


def get_cached_account_for_user(user) -> Account:
    """
    Locates the account for a given user, or None if no account exists.
    """
    if isinstance(user, AnonymousUser):
        return None

    return _get_account_for_user(user)


def _get_cached_user_profile(resolved_user, account):

    @lru_cache(maxsize=LRU_CACHE_MAX_SIZE)
    def _in_memory_user_profile(user_id, account_id):
        user_profile = UserProfile.objects.get(user_id=user_id, account_id=account_id)
        if waffle.switch_is_active(SmarterWaffleSwitches.CACHE_LOGGING):
            logger.info("_in_memory_user_profile() retrieving and caching UserProfile %s", user_profile)
        return user_profile

    user_profile = _in_memory_user_profile(resolved_user.id, account.id)
    if waffle.switch_is_active(SmarterWaffleSwitches.CACHE_LOGGING):
        logger.info("get_cached_user_profile() retrieving and caching UserProfile %s", user_profile)
    return user_profile


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

    # pylint: disable=W0212
    resolved_user = get_resolved_user(user)
    return _get_cached_user_profile(resolved_user, account)


def get_cached_user_for_user_id(user_id: int) -> UserType:
    """
    Returns the user for the given user_id.
    """

    @lru_cache(maxsize=LRU_CACHE_MAX_SIZE)
    def _in_memory_user(user_id) -> UserType:
        """
        In-memory cache for user objects.
        """
        user = User.objects.get(id=user_id)
        if waffle.switch_is_active(SmarterWaffleSwitches.CACHE_LOGGING):
            logger.info("_in_memory_user() retrieving and caching user %s", user)
        return user

    user = _in_memory_user(user_id)
    if waffle.switch_is_active(SmarterWaffleSwitches.CACHE_LOGGING):
        logger.info("get_cached_user_for_user_id() retrieving and caching user %s", user)
    return user


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
        if waffle.switch_is_active(SmarterWaffleSwitches.CACHE_LOGGING):
            logger.info(
                "%s found and cached admin UserProfile %s for account %s", console_prefix, user_profile, account
            )
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

    smarter_account = get_cached_account(account_number=SMARTER_ACCOUNT_NUMBER)
    if not smarter_account:
        raise SmarterConfigurationError(
            "Failed to retrieve smarter account. Please ensure the account exists and is configured correctly."
        )

    @lru_cache(maxsize=LRU_CACHE_MAX_SIZE)
    def _in_memory_smarter_admin_user_profile(smarter_account_id):
        super_user_profile = (
            UserProfile.objects.filter(account_id=smarter_account_id, user__is_superuser=True).order_by("pk").first()
        )
        if super_user_profile:
            if waffle.switch_is_active(SmarterWaffleSwitches.CACHE_LOGGING):
                logger.info(
                    "_in_memory_smarter_admin_user_profile() retrieving and caching superuser UserProfile %s",
                    super_user_profile,
                )
            return super_user_profile

        staff_user_profile = (
            UserProfile.objects.filter(account=smarter_account, user__is_staff=True).order_by("pk").first()
        )
        if staff_user_profile and waffle.switch_is_active(SmarterWaffleSwitches.CACHE_LOGGING):
            logger.info(
                "_in_memory_smarter_admin_user_profile() retrieving and caching staff UserProfile %s",
                staff_user_profile,
            )
            return staff_user_profile

        raise SmarterConfigurationError(
            "Failed to retrieve smarter admin user profile. Please ensure the account has a superuser or staff user."
        )

    return _in_memory_smarter_admin_user_profile(smarter_account.id)


@cache_results()
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
    match = re.search(SmarterValidator.SMARTER_ACCOUNT_NUMBER_REGEX, url)
    retval = match.group(0) if match else None
    if retval is not None and waffle.switch_is_active(SmarterWaffleSwitches.CACHE_LOGGING):
        logger.info("account_number_from_url() extracted and cached account number %s from URL %s", retval, url)
    return retval


def get_users_for_account(account: Account) -> list[UserType]:
    """
    Returns a list of users for the given account.
    """
    if not account:
        raise SmarterValueError("Account is required")
    users = User.objects.filter(userprofile__account=account)
    return list[users]


def get_user_profiles_for_account(account: Account) -> list[UserProfile]:
    """
    Returns a list of user profiles for the given account.
    """
    if not account:
        raise SmarterValueError("Account is required")

    user_profiles = UserProfile.objects.filter(account=account)
    return user_profiles
