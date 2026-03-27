"""
Account Utilities

This module provides foundational utilities for accessing, managing, and caching account and user data in the Smarter platform. It is the base model for all Django ORM operations in the project, and is designed for both performance and reliability.

Caching Overview
----------------

Two caching strategies are used:

- **LRU In-Memory Caching**:
  Fast, per-process caching for frequently accessed objects such as `User`, `Account`, and `UserProfile`.
  *Scope*: Only available within the current process; short-lived.

- **Redis-Based ORM Caching**:
  Persistent, cross-process caching for Django ORM objects.
  *Scope*: Shared across all processes; cache lifetime is controlled by expiration settings.

"""

import logging
import re
import uuid
from typing import Optional

from smarter.apps.account.models import (
    Account,
    User,
    UserProfile,
)
from smarter.common.const import SMARTER_ACCOUNT_NUMBER, SMARTER_ADMIN_USERNAME
from smarter.common.exceptions import SmarterConfigurationError, SmarterValueError
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib.cache import cache_results
from smarter.lib.django import waffle
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

HERE = formatted_text(__name__)


# pylint: disable=W0613
def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.ACCOUNT_LOGGING) or waffle.switch_is_active(
        SmarterWaffleSwitches.CACHE_LOGGING
    )


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)

LRU_CACHE_MAX_SIZE = 128
SMARTER_ACCOUNT_NUMBER_PATTERN = re.compile(SmarterValidator.SMARTER_ACCOUNT_NUMBER_REGEX)


# commonly fetched objects
# ----------------------------
class SmarterCachedObjects:
    """
    Lazy instantiations of cached objects for the smarter account. This is a
    much-simplified means of caching commonly used objects without having to
    actually decorate every function that fetches them.

    :raises SmarterConfigurationError: If the smarter account or admin user cannot be found.

    .. note::

           This class uses lazy loading to fetch and cache the smarter account
           and admin user only when accessed.
    """

    _smarter_admin_user_profile: Optional[UserProfile] = None
    _admin_user: Optional[User] = None

    @property
    def smarter_account(self) -> Account:
        """
        Retrieve the smarter account instance.

        :returns: Account instance representing the smarter account.
        :raises SmarterConfigurationError: If the smarter account cannot be found.
        """
        retval = Account.get_cached_object(account_number=SMARTER_ACCOUNT_NUMBER)
        if not retval:
            raise SmarterConfigurationError(
                f"Smarter account with account number {SMARTER_ACCOUNT_NUMBER} does not exist."
            )
        return retval

    @property
    def smarter_admin(self) -> User:
        """
        Retrieve the smarter admin user instance.

        :returns: User instance representing the smarter admin.
        :raises SmarterConfigurationError: If the smarter admin user cannot be found.
        """
        return self.smarter_admin_user_profile.user

    @property
    def smarter_admin_user_profile(self) -> UserProfile:
        """
        Retrieve the UserProfile instance for the smarter admin user.
        Lazy loads and caches the UserProfile on first access.
        Subsequent accesses will return the cached UserProfile, with a
        periodic refresh from the database to ensure data consistency.

        :returns: UserProfile instance for the smarter admin user.
        :raises SmarterConfigurationError: If the UserProfile cannot be found.
        """

        @cache_results()
        def _requery_smarter_admin_user_profile(class_name=SmarterCachedObjects.__name__) -> None:
            if self._smarter_admin_user_profile:
                logger.debug(
                    "%s re-queried %s",
                    formatted_text(f"{__name__}.{SmarterCachedObjects.__name__}.smarter_admin_user_profile()"),
                    self._smarter_admin_user_profile,
                )
                self._smarter_admin_user_profile.refresh_from_db()

        if not self._smarter_admin_user_profile:
            try:
                user_profile = UserProfile.objects.filter(account=self.smarter_account, user__is_superuser=True).first()
                self._smarter_admin_user_profile = user_profile
                logger.debug(
                    "%s initialized %s",
                    formatted_text(f"{__name__}.{SmarterCachedObjects.__name__}.smarter_admin_user_profile()"),
                    user_profile,
                )
                return self._smarter_admin_user_profile  # type: ignore[return-value]
            except UserProfile.DoesNotExist as e:
                raise SmarterConfigurationError("No superuser user profile found for smarter account") from e

        _requery_smarter_admin_user_profile(class_name=SmarterCachedObjects.__name__)
        return self._smarter_admin_user_profile  # type: ignore[return-value]

    @property
    def admin_user(self) -> User:
        """
        Retrieve the admin user instance for the smarter account. Lazy
        loads and caches the user on first access. Subsequent accesses
        will return the cached user, with a periodic refresh from the
        database to ensure data consistency.

        :returns: User instance representing the admin user.
        :raises SmarterConfigurationError: If the admin user cannot be found.
        """

        @cache_results()
        def _requery_admin_user(class_name=SmarterCachedObjects.__name__) -> None:
            self._admin_user.refresh_from_db()
            logger.debug(
                "%s re-queried %s",
                formatted_text(f"{__name__}.{SmarterCachedObjects.__name__}.admin_user()"),
                self._admin_user,
            )

        if not self._admin_user:
            try:
                self._admin_user = User.objects.get(username=SMARTER_ADMIN_USERNAME, is_superuser=True)
                logger.debug(
                    "%s initialized %s",
                    formatted_text(f"{__name__}.{SmarterCachedObjects.__name__}.admin_user()"),
                    self._admin_user,
                )
                return self._admin_user
            except User.DoesNotExist as e:
                raise SmarterConfigurationError("No superuser found for smarter account") from e

        _requery_admin_user(class_name=SmarterCachedObjects.__name__)
        return self._admin_user  # type: ignore[return-value]


smarter_cached_objects = SmarterCachedObjects()
"""
smarter_cached_objects = SmarterCachedObjects()
An instance of `SmarterCachedObjects` for accessing commonly used cached objects.
Functions as a singleton for the project.
"""


def get_cached_default_account(invalidate: bool = False) -> Optional[Account]:
    """
    Retrieve the default account instance, using caching for performance.

    :param invalidate: Boolean, optional. If True, invalidates the cache before fetching.
    :returns: The default Account instance.

    .. important::

           The default account is determined by the ``is_default_account=True`` flag in the database.

    .. warning::

           If no default account exists, an exception may be raised.

    **Example usage**::

        # Get the default account
        default_account = get_cached_default_account()

        # Invalidate cache before fetching
        default_account = get_cached_default_account(invalidate=True)
    """

    @cache_results()
    def _get_default_account(class_name=Account.__name__) -> Account:
        accounts = Account.objects.filter(is_default_account=True)
        if not accounts.exists():
            raise SmarterConfigurationError(
                "No default account found. Please ensure an account is marked as the default account."
            )
        if accounts.count() > 1:
            logger.warning("%s.get_cached_default_account() multiple default accounts found", HERE)
        account = accounts.first()
        logger.debug("%s.get_cached_default_account() retrieving and caching default account %s", HERE, account)
        if not account:
            raise SmarterConfigurationError(
                "No default account found. Please ensure an account is marked as the default account."
            )
        return account

    if invalidate:
        _get_default_account.invalidate(class_name=Account.__name__)

    return _get_default_account(class_name=Account.__name__)


def get_cached_account_for_user(invalidate: Optional[bool] = False, user: Optional[User] = None) -> Optional[Account]:
    """
    Locate the Account associated with a given user, using caching for performance.

    :param user: User instance. The user whose account should be located.
    :param invalidate: Boolean, optional. If True, invalidates the cache before fetching.
    :returns: Account instance if found, otherwise None.

    .. warning::
              If no account is found for the user, None is returned and a warning is logged.
    .. tip::
              Use ``invalidate=True`` after updating user or account data to ensure cache consistency.

    **Example usage**::

        # Locate account for a user
        account = get_cached_account_for_user(user)
        # Invalidate cache before fetching
        account = get_cached_account_for_user(user, invalidate=True)

    """
    if not isinstance(user, User):
        logger.warning("%s.get_cached_account_for_user() invalid user type: %s", HERE, type(user))
        return None

    username = getattr(user, "username")
    if username == SMARTER_ADMIN_USERNAME:
        return smarter_cached_objects.smarter_account

    user_id = getattr(user, "id", None)
    if not user_id:
        logger.warning("%s.get_cached_account_for_user() user has no ID: %s", HERE, user)
        return None

    @cache_results()
    def get_cached_account_for_user_by_id(user_id, class_name=UserProfile.__name__):
        """
        In-memory cache for user accounts.
        """
        user_profiles = UserProfile.objects.filter(user_id=user_id)
        for user_profile in user_profiles:
            if user_profile.cached_account.is_default_account and waffle.switch_is_active(
                SmarterWaffleSwitches.CACHE_LOGGING
            ):
                logger.debug(
                    "%s.get_cached_account_for_user() retrieving and caching default account %s for user %s",
                    HERE,
                    user_profile.cached_account,
                    user,
                )
                return user_profile.cached_account
        # If no default account is found, return the first account
        user_profile = user_profiles.first()
        if not user_profile:
            logger.warning("%s.get_cached_account_for_user_by_id() no UserProfile found for user ID %s", HERE, user_id)
            return None
        account = user_profile.cached_account
        logger.debug(
            "%s.get_cached_account_for_user_by_id() retrieving and caching default account %s for user ID %s",
            HERE,
            account,
            user_id,
        )
        return account

    if invalidate:
        get_cached_account_for_user_by_id.invalidate(user_id, class_name=UserProfile.__name__)

    return get_cached_account_for_user_by_id(user_id=user_id, class_name=UserProfile.__name__)


def get_cached_user_for_user_id(invalidate: Optional[bool] = False, user_id: Optional[int] = None) -> Optional[User]:
    """
    Retrieve a User instance by its primary key, using caching for performance.

    :param user_id: Integer. The primary key of the user to retrieve.
    :param invalidate: Boolean, optional. If True, invalidates the cache before fetching.
    :returns: User instance if found, otherwise None.

    .. warning::

           If no user exists for the given ID, None is returned and an error is logged.

    .. tip::

           Use ``invalidate=True`` after updating user data to ensure cache consistency.

    **Example usage**::

        # Retrieve user by ID
        user = get_cached_user_for_user_id(user_id=123)

        # Invalidate cache before fetching
        user = get_cached_user_for_user_id(user_id=123, invalidate=True)
    """

    @cache_results()
    def _get_user(user_id, class_name=User.__name__) -> Optional[User]:
        """
        In-memory cache for user objects.
        """
        try:
            user = User.objects.get(id=user_id)
            logger.debug("%s.get_cached_user_for_user_id() retrieving and caching user %s", HERE, user)
            return user  # type: ignore[return-value]
        except User.DoesNotExist:
            logger.error("%s.get_cached_user_for_user_id() user with ID %s does not exist", HERE, user_id)

    if invalidate:
        _get_user.invalidate(user_id, class_name=User.__name__)

    return _get_user(user_id=user_id, class_name=User.__name__)


def get_cached_user_for_username(invalidate: Optional[bool] = False, username: Optional[str] = None) -> Optional[User]:
    """
    Retrieve a User instance by its username, using caching for performance.

    :param username: String. The username of the user to retrieve.
    :param invalidate: Boolean, optional. If True, invalidates the cache before fetching.
    :returns: User instance if found, otherwise None.

    .. warning::

           If no user exists for the given username, None is returned and an error is logged.

    .. tip::

           Use ``invalidate=True`` after updating user data to ensure cache consistency.

    **Example usage**::

        # Retrieve user by username
        user = get_cached_user_for_username("johndoe")

        # Invalidate cache before fetching
        user = get_cached_user_for_username("johndoe", invalidate=True)
    """

    @cache_results()
    def _in_memory_user_by_username(username, class_name=User.__name__) -> Optional[User]:
        """
        In-memory cache for user objects by username.
        """
        try:
            user = User.objects.get(username=username)
            logger.debug("%s.get_cached_user_for_username() retrieving and caching user %s", HERE, user)
            return user  # type: ignore[return-value]
        except User.DoesNotExist:
            logger.debug("%s.get_cached_user_for_username() user with username %s does not exist", HERE, username)

    if invalidate:
        _in_memory_user_by_username.invalidate(username, class_name=User.__name__)

    if username == SMARTER_ADMIN_USERNAME:
        return smarter_cached_objects.admin_user

    return _in_memory_user_by_username(username, class_name=User.__name__)


def get_cached_admin_user_for_account(
    invalidate: Optional[bool] = False, account: Optional[Account] = None
) -> Optional[User]:
    """
    Retrieve the admin user for a given account, creating one if necessary.

    :param account: Account instance. The account for which to retrieve the admin user.
    :param invalidate: Boolean, optional. If True, invalidates the cache before fetching.
    :returns: User instance representing the account admin.

    .. important::

           If no admin user exists for the account, a new staff user and UserProfile will be created automatically.

    .. warning::

           If the account is missing or misconfigured, an exception is raised.

    .. tip::

           Use ``invalidate=True`` after updating admin user data to ensure cache consistency.

    **Example usage**::

        # Retrieve the admin user for an account
        admin_user = get_cached_admin_user_for_account(account=account)

        # Invalidate cache before fetching
        admin_user = get_cached_admin_user_for_account(invalidate=True, account=account)
    """
    if not isinstance(account, Account):
        raise SmarterValueError("Account is required")

    @cache_results()
    def _admin_user_for_account_number(account_number: str, class_name=User.__name__) -> User:
        # reinstantiate the account
        account = Account.get_cached_object(account_number=account_number)
        if not account:
            raise SmarterConfigurationError(
                f"Failed to retrieve account with number {account_number}. Please ensure the account exists and is configured correctly."
            )
        console_prefix = formatted_text(f"{__name__}.get_cached_admin_user_for_account()")
        user_profile = (
            UserProfile.objects.filter(account=account, user__is_staff=True)
            .select_related("user", "account")
            .order_by("pk")
            .first()
        )
        if user_profile:
            logger.debug(
                "%s found and cached admin UserProfile %s for account %s", console_prefix, user_profile, account
            )
            return user_profile.cached_user  # type: ignore[return-value]
        else:
            raise SmarterConfigurationError(f"No admin user found for account {account}.")

    if invalidate:
        _admin_user_for_account_number.invalidate(account_number=account.account_number, class_name=User.__name__)

    return _admin_user_for_account_number(account_number=account.account_number, class_name=User.__name__)


def get_cached_smarter_admin_user_profile() -> UserProfile:
    """
    Retrieve the admin UserProfile for the smarter account, using caching for performance.

    :param invalidate: Boolean, optional. If True, invalidates the cache before fetching.
    :returns: UserProfile instance for the smarter admin user.

    .. note::

           The smarter admin user is typically a superuser or staff user associated with the platform's main account.

    .. warning::

           If no suitable admin user exists, or the smarter account is misconfigured, an exception is raised.

    .. tip::

           Use ``invalidate=True`` after updating admin user or account data to ensure cache consistency.

    **Example usage**::

        # Retrieve the smarter admin user profile
        admin_profile = get_cached_smarter_admin_user_profile()

        # Invalidate cache before fetching
        admin_profile = get_cached_smarter_admin_user_profile(invalidate=True)
    """
    return smarter_cached_objects.smarter_admin_user_profile


def account_number_from_url(invalidate: Optional[bool] = False, url: Optional[str] = None) -> Optional[str]:
    """
    Extract the account number from a Smarter platform URL, using caching for performance.

    :param url: String. The URL to parse for an account number.
    :param invalidate: Boolean, optional. If True, invalidates the cache before fetching.
    :returns: The extracted account number as a string, or None if not found.

    .. note::

           The function validates the URL format before extraction.

    .. warning::

           If the URL does not contain a valid account number, None is returned.

    .. tip::

           Use ``invalidate=True`` after updating URLs or account number patterns to ensure cache consistency.

    **Example usage**::

        # Extract account number from a URL
        account_number = account_number_from_url("https://hr.3141-5926-5359.alpha.api.example.com/")

        # Result: '3141-5926-5359'

        # Invalidate cache before fetching
        account_number = account_number_from_url("https://hr.3141-5926-5359.alpha.api.example.com/", invalidate=True)
    """
    if not url:
        return None
    if not isinstance(url, str):
        logger.warning("%s.account_number_from_url() invalid URL type: %s", HERE, type(url))
        return None

    @cache_results()
    def _account_number_from_url(url: str, class_name=Account.__name__) -> Optional[str]:
        match = SMARTER_ACCOUNT_NUMBER_PATTERN.search(url)
        retval = match.group(0) if match else None
        if retval is not None:
            logger.debug("account_number_from_url() extracted and cached account number %s from URL %s", retval, url)
        return retval

    if invalidate:
        _account_number_from_url.invalidate(url, class_name=Account.__name__)

    return _account_number_from_url(url, class_name=Account.__name__)


def get_users_for_account(account: Account) -> list[User]:
    """
    Retrieve a list of users associated with a given account.

    :param account: Account instance. The account for which to retrieve users.
    :returns: List of User instances.

    .. important::

           The account parameter is required. If not provided, an exception is raised.

    .. warning::

           If the account has no associated users, an empty list is returned.

    **Example usage**::

        # Get all users for an account
        users = get_users_for_account(account)
    """
    if not account:
        raise SmarterValueError("Account is required")
    users = User.objects.filter(user_profile__account=account)
    return list[users]  # type: ignore[list-item,return-value]


def get_user_profiles_for_account(account: Account) -> Optional[list[UserProfile]]:
    """
    Retrieve a list of user profiles associated with a given account.

    :param account: Account instance. The account for which to retrieve user profiles.
    :returns: List of UserProfile instances, or None if no profiles exist.

    .. important::

           The account parameter is required. If not provided, an exception is raised.

    .. warning::

           If the account has no associated user profiles, None is returned.

    **Example usage**::

        # Get all user profiles for an account
        profiles = get_user_profiles_for_account(account)
    """
    if not account:
        raise SmarterValueError("Account is required")

    user_profiles = UserProfile.objects.filter(account=account)
    return list(user_profiles)


def valid_resource_owners_for_user(user_profile: Optional[UserProfile]) -> list[UserProfile]:
    """
    Get a list of valid owners for the given user profile.

    This function retrieves all user profiles associated with the same account as the provided user profile.
    These profiles are considered valid owners for plugins created by the user.

    :param user_profile: The `UserProfile` instance representing the user.
    :type user_profile: UserProfile

    :return: A list of `UserProfile` instances that are valid plugin owners.
    :rtype: list[UserProfile]

    .. seealso::

        - :class:`UserProfile`

    Example usage:

    .. code-block:: python

        from smarter.apps.account.models import UserProfile
        from smarter.apps.plugin.utils import valid_plugin_owners_for_user

        user_profile = UserProfile.objects.get(user__username="exampleuser")
        owners = valid_plugin_owners_for_user(user_profile)
        print("Valid plugin owners:", [owner.user.username for owner in owners])

    """
    logger.debug("%s.valid_resource_owners_for_user() called with user_profile: %s", HERE, user_profile)

    if not user_profile:
        return [smarter_cached_objects.smarter_admin_user_profile]

    account_admin = get_cached_admin_user_for_account(invalidate=False, account=user_profile.cached_account)

    if not isinstance(account_admin, UserProfile):
        return [user_profile, smarter_cached_objects.smarter_admin_user_profile]
    return [user_profile, account_admin, smarter_cached_objects.smarter_admin_user_profile]


__all__ = [
    "get_cached_default_account",
    "get_cached_account_for_user",
    "get_cached_user_for_user_id",
    "get_cached_user_for_username",
    "get_cached_admin_user_for_account",
    "get_cached_smarter_admin_user_profile",
    "account_number_from_url",
    "get_users_for_account",
    "get_user_profiles_for_account",
    "valid_resource_owners_for_user",
]
