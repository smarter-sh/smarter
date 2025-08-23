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
from typing import Any, Optional

from django.contrib.auth.models import AnonymousUser

from smarter.apps.account.models import User, get_resolved_user
from smarter.common.const import SMARTER_ACCOUNT_NUMBER
from smarter.common.exceptions import SmarterConfigurationError, SmarterValueError
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib.cache import cache_results
from smarter.lib.django import waffle
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

from .models import Account, UserProfile


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return (
        waffle.switch_is_active(SmarterWaffleSwitches.ACCOUNT_LOGGING)
        or waffle.switch_is_active(SmarterWaffleSwitches.CACHE_LOGGING)
    ) and level >= logging.INFO


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)

LRU_CACHE_MAX_SIZE = 128


def get_cached_account(
    account_id: Optional[int] = None, account_number: Optional[str] = None, invalidate: bool = False
) -> Optional[Account]:
    """
    Returns the account for the given account_id or account_number.
    """

    @cache_results()
    def _in_memory_account_by_id(account_id) -> Optional[Account]:
        """
        In-memory cache for account objects by ID.
        """
        logger.info("_in_memory_account_by_id() retrieving and caching account %s", account_id)
        try:
            account = Account.objects.get(id=account_id)
        except Account.DoesNotExist:
            logger.warning("_in_memory_account_by_id() account with ID %s does not exist", account_id)
            return None
        return account

    @cache_results()
    def _in_memory_account_by_number(account_number) -> Optional[Account]:
        """
        In-memory cache for account objects by account number.
        """
        logger.info("_in_memory_account_by_number() retrieving and caching account %s", account_number)
        try:
            account = Account.objects.get(account_number=account_number)
        except Account.DoesNotExist:
            logger.warning("_in_memory_account_by_number() account with number %s does not exist", account_number)
            return None
        return account

    if account_id:
        return (
            _in_memory_account_by_id(account_id) if not invalidate else _in_memory_account_by_id.invalidate(account_id)
        )

    if account_number:
        return (
            _in_memory_account_by_number(account_number)
            if not invalidate
            else _in_memory_account_by_number.invalidate(account_number)
        )


@cache_results()
def get_cached_smarter_account(invalidate: bool = False) -> Optional[Account]:
    """
    Returns the smarter account.
    """
    account = get_cached_account(account_number=SMARTER_ACCOUNT_NUMBER, invalidate=invalidate)
    return account


def get_cached_default_account(invalidate: bool = False) -> Account:
    """
    Returns the default account.
    """

    @cache_results()
    def _get_default_account():
        account = Account.objects.get(is_default_account=True)
        logger.info("get_cached_default_account() retrieving and caching default account %s", account)
        return account

    return _get_default_account() if not invalidate else _get_default_account.invalidate()


def _get_account_for_user(user, invalidate: bool = False) -> Optional[Account]:
    if not user:
        return None

    user_id = getattr(user, "id", None)
    if not user_id:
        logger.warning("get_cached_account_for_user() user has no ID: %s", user)
        return None

    @cache_results()
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
            logger.warning("get_cached_account_for_user_by_id() no UserProfile found for user ID %s", user_id)
            return None
        account = user_profile.account
        logger.info(
            "_get_account_for_user_by_id() retrieving and caching default account %s for user ID %s",
            account,
            user_id,
        )
        return account

    return _get_account_for_user_by_id(user_id) if not invalidate else _get_account_for_user_by_id.invalidate(user_id)


def get_cached_account_for_user(user: Any, invalidate: bool = False) -> Optional[Account]:
    """
    Locates the account for a given user, or None if no account exists.
    """
    if isinstance(user, AnonymousUser):
        return None
    return _get_account_for_user(user, invalidate=invalidate)


def _get_cached_user_profile(
    resolved_user: User, account: Optional[Account], invalidate: bool = False
) -> Optional[UserProfile]:

    @cache_results()
    def _in_memory_user_profile(user_id, account_id):
        user_profile = UserProfile.objects.get(user_id=user_id, account_id=account_id)
        logger.info("_in_memory_user_profile() retrieving and caching UserProfile %s", user_profile)
        return user_profile

    if resolved_user is None or account is None:
        logger.warning("get_cached_user_profile() cannot initialize with user: %s account: %s", resolved_user, account)
        return None

    return (
        _in_memory_user_profile(resolved_user.id, account.id)
        if not invalidate
        else _in_memory_user_profile.invalidate(resolved_user.id, account.id)
    )


def get_cached_user_profile(
    user: User, account: Optional[Account] = None, invalidate: bool = False
) -> Optional[UserProfile]:
    """
    Locates the user_profile for a given user, or None.
    """
    account = account or get_cached_account_for_user(user, invalidate=invalidate)
    if not account:
        logger.warning("get_cached_user_profile() no account found for user: %s", user)
        return None

    # pylint: disable=W0212
    resolved_user = get_resolved_user(user)
    if isinstance(resolved_user, User):
        return _get_cached_user_profile(resolved_user, account, invalidate=invalidate)
    logger.warning("get_cached_user_profile() user is not resolvable: %s", user)
    return None


def get_cached_user_for_user_id(user_id: int, invalidate: bool = False) -> User:
    """
    Returns the user for the given user_id.
    """

    @cache_results()
    def _in_memory_user(user_id) -> User:
        """
        In-memory cache for user objects.
        """
        user = User.objects.get(id=user_id)
        logger.info("_in_memory_user() retrieving and caching user %s", user)
        return user  # type: ignore[return-value]

    user = _in_memory_user(user_id) if not invalidate else _in_memory_user.invalidate(user_id)
    logger.info("get_cached_user_for_user_id() retrieving and caching user %s", user)
    return user


def get_cached_admin_user_for_account(account: Account, invalidate: bool = False) -> User:
    """
    Returns the account admin user for the given account. If the user does not exist, it will be created.
    """
    if not account:
        raise SmarterValueError("Account is required")

    @cache_results()
    def admin_for_account(account_number: str) -> User:
        account = get_cached_account(account_number=account_number)
        if not account:
            raise SmarterConfigurationError(
                f"Failed to retrieve account with number {account_number}. Please ensure the account exists and is configured correctly."
            )
        console_prefix = formatted_text("get_cached_admin_user_for_account()")
        user_profile = UserProfile.objects.filter(account=account, user__is_staff=True).order_by("pk").first()
        if user_profile:
            logger.info(
                "%s found and cached admin UserProfile %s for account %s", console_prefix, user_profile, account
            )
            return user_profile.user
        else:
            # Create a new admin user and UserProfile
            random_email = f"{uuid.uuid4().hex[:8]}@mail.com"
            if account and isinstance(account.account_number, str):
                admin_user = User.objects.create_user(username=account.account_number, email=random_email, is_staff=True)  # type: ignore[arg-type]
                logger.info("%s created new admin User %s for account %s", console_prefix, admin_user, account)
                user_profile = UserProfile.objects.create(user=admin_user, account=account)
                logger.info("%s created new admin UserProfile for user %s", console_prefix, user_profile)
        if not user_profile:
            logger.error("%s failed to query nor create admin UserProfile for account %s", console_prefix, account)
            raise SmarterConfigurationError("Failed to create admin UserProfile")
        return user_profile.user if user_profile else None  # type: ignore[return-value]

    account_number = account.account_number if isinstance(account, Account) else None
    if not account_number:
        raise SmarterValueError("Account number is required to retrieve admin user")
    return admin_for_account(account_number) if not invalidate else admin_for_account.invalidate(account_number)  # type: ignore[return-value]


def get_cached_smarter_admin_user_profile(invalidate: bool = False) -> UserProfile:
    """
    Returns the smarter admin user.
    """

    smarter_account = get_cached_account(account_number=SMARTER_ACCOUNT_NUMBER)
    if not smarter_account:
        raise SmarterConfigurationError(
            "Failed to retrieve smarter account. Please ensure the account exists and is configured correctly."
        )

    @cache_results()
    def _in_memory_smarter_admin_user_profile(smarter_account_id):
        super_user_profile = (
            UserProfile.objects.filter(account_id=smarter_account_id, user__is_superuser=True).order_by("pk").first()
        )
        if super_user_profile:
            logger.info(
                "_in_memory_smarter_admin_user_profile() retrieving and caching superuser UserProfile %s",
                super_user_profile,
            )
            return super_user_profile

        try:
            staff_user_profile = (
                UserProfile.objects.filter(account=smarter_account, user__is_staff=True).order_by("pk").first()
            )
        except UserProfile.DoesNotExist:
            pass
        if staff_user_profile and waffle.switch_is_active(SmarterWaffleSwitches.CACHE_LOGGING):
            logger.info(
                "_in_memory_smarter_admin_user_profile() retrieving and caching staff UserProfile %s",
                staff_user_profile,
            )
            return staff_user_profile

        raise SmarterConfigurationError(
            "Failed to retrieve smarter admin user profile. Please ensure the account has a superuser or staff user."
        )

    return (
        _in_memory_smarter_admin_user_profile(smarter_account.id)
        if not invalidate
        else _in_memory_smarter_admin_user_profile.invalidate(smarter_account.id)
    )


def account_number_from_url(url: str, invalidate: bool = False) -> Optional[str]:
    """
    Extracts the account number from the URL.
    :return: The account number or None if not found.

    example: https://hr.3141-5926-5359.alpha.api.smarter.sh/
    returns '3141-5926-5359'
    """
    if not url:
        return None

    @cache_results()
    def _account_number_from_url(url: str) -> Optional[str]:
        SmarterValidator.validate_url(url)
        match = re.search(SmarterValidator.SMARTER_ACCOUNT_NUMBER_REGEX, url)
        retval = match.group(0) if match else None
        if retval is not None and waffle.switch_is_active(SmarterWaffleSwitches.CACHE_LOGGING):
            logger.info("account_number_from_url() extracted and cached account number %s from URL %s", retval, url)
        return retval

    return _account_number_from_url(url) if not invalidate else _account_number_from_url.invalidate(url)


def get_users_for_account(account: Account) -> list[User]:
    """
    Returns a list of users for the given account.
    """
    if not account:
        raise SmarterValueError("Account is required")
    users = User.objects.filter(userprofile__account=account)
    return list[users]  # type: ignore[list-item,return-value]


def get_user_profiles_for_account(account: Account) -> Optional[list[UserProfile]]:
    """
    Returns a list of user profiles for the given account.
    """
    if not account:
        raise SmarterValueError("Account is required")

    user_profiles = UserProfile.objects.filter(account=account)
    return user_profiles  # type: ignore[list-item,return-value]


def cache_invalidate(user: Optional[User] = None, account: Optional[Account] = None):
    """
    Invalidates all cache entries for the given user.
    """
    resolved_user = get_resolved_user(user) if user else None

    if not isinstance(resolved_user, User) and not isinstance(account, Account):
        raise SmarterValueError("either user or account is required")

    if not isinstance(resolved_user, User) and isinstance(account, Account):
        resolved_user = get_cached_admin_user_for_account(account, invalidate=True)
    else:
        user_profile = UserProfile.objects.filter(user=resolved_user).first()
        if not user_profile:
            raise SmarterValueError(f"did not find a UserProfile for {resolved_user}")
        account = user_profile.account

    logger.info("cache_invalidate() invalidating cache for user: %s account: %s", resolved_user, account)

    if not isinstance(account, Account):
        raise SmarterValueError(f"could not resolve account {account} for user {user}")

    get_cached_account(account_id=account.id, invalidate=True)
    get_cached_admin_user_for_account(account=account, invalidate=True)

    if isinstance(resolved_user, User):
        get_cached_account_for_user(user=resolved_user, invalidate=True)
        get_cached_user_profile(user=resolved_user, account=account, invalidate=True)
        get_cached_user_for_user_id(user_id=resolved_user.id, invalidate=True)
