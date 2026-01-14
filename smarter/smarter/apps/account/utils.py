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
from typing import Any, Optional

from django.contrib.auth.models import AnonymousUser

from smarter.apps.account.models import (
    Account,
    Secret,
    User,
    UserProfile,
    get_resolved_user,
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
    Lazy instantiations of cached objects for the smarter account.
    """

    def __init__(self):
        self._smarter_account = None
        self._smarter_admin = None
        self._smarter_admin_user_profile = None
        self._admin_user = None

    @property
    def smarter_account(self) -> Account:
        if not self._smarter_account:
            try:
                self._smarter_account = Account.objects.get(account_number=SMARTER_ACCOUNT_NUMBER)
            except Account.DoesNotExist as e:
                raise SmarterConfigurationError("Smarter account does not exist") from e
        return self._smarter_account

    @property
    def smarter_admin(self) -> User:
        if not self._smarter_admin:
            try:
                user = User.objects.filter(userprofile__account=self.smarter_account, is_superuser=True).first()
            except User.DoesNotExist as e:
                raise SmarterConfigurationError("No superuser found for smarter account") from e
            if not user:
                raise SmarterConfigurationError("No superuser found for smarter account")
            self._smarter_admin = user
        return self._smarter_admin

    @property
    def smarter_admin_user_profile(self) -> UserProfile:
        if not self._smarter_admin_user_profile:
            try:
                user_profile = UserProfile.objects.filter(account=self.smarter_account, user__is_superuser=True).first()
            except UserProfile.DoesNotExist as e:
                raise SmarterConfigurationError("No superuser user profile found for smarter account") from e
            if not user_profile:
                raise SmarterConfigurationError("No superuser user profile found for smarter account")
            self._smarter_admin_user_profile = user_profile
        return self._smarter_admin_user_profile

    @property
    def admin_user(self) -> User:
        if not self._admin_user:
            try:
                self._admin_user = User.objects.get(username=SMARTER_ADMIN_USERNAME, is_superuser=True)
            except User.DoesNotExist as e:
                raise SmarterConfigurationError("No staff user found for smarter account") from e
        return self._admin_user


smarter_cached_objects = SmarterCachedObjects()


def get_cached_secret(name: str, user_profile: UserProfile, invalidate: bool = False) -> Optional[Secret]:
    """
    Retrieve a Secret instance by its name and associated UserProfile, using in-memory caching.

    :param name: String. The name of the secret to retrieve.
    :param user_profile: UserProfile instance. The user profile associated with the secret.
    :param invalidate: Boolean, optional. If True, invalidates the cache before fetching.
    :returns: Secret instance if found, otherwise None.

    .. warning::

           If no secret exists for the given name and user profile, None is returned and a warning is logged.
    .. tip::
           Use ``invalidate=True`` after updating secret data to ensure cache consistency.

    **Example usage**::
        # Retrieve secret by name and user profile
        secret = get_cached_secret("my_secret", user_profile)

        # Invalidate cache before fetching
        secret = get_cached_secret("my_secret", user_profile, invalidate=True)
    """

    @cache_results()
    def _in_memory_secret(name: str, user_profile_id: int) -> Optional[Secret]:
        """
        In-memory cache for secret objects by name and user profile ID.
        """
        logger.debug(
            "%s.get_cached_secret() retrieving and caching secret %s for user_profile %s",
            HERE,
            name,
            user_profile_id,
        )
        try:
            secret = Secret.objects.get(name=name, user_profile_id=user_profile_id)
        except Secret.DoesNotExist:
            logger.warning(
                "%s.get_cached_secret() secret with name %s does not exist for user_profile %s",
                HERE,
                name,
                user_profile_id,
            )
            return None
        return secret

    return (
        _in_memory_secret(name, user_profile.id)
        if not invalidate
        else _in_memory_secret.invalidate(name, user_profile.id)
    )


def get_cached_secret_by_pk(secret_pk: int, user_profile: UserProfile, invalidate: bool = False) -> Optional[Secret]:
    """
    Retrieve a Secret instance by its primary key and associated UserProfile, using in-memory caching.

    :param secret_pk: Integer. The primary key of the secret to retrieve.
    :param user_profile: UserProfile instance. The user profile associated with the secret.
    :param invalidate: Boolean, optional. If True, invalidates the cache before fetching.
    :returns: Secret instance if found, otherwise None.

    .. warning::

           If no secret exists for the given primary key and user profile, None is returned and a warning is logged.
    .. tip::
              Use ``invalidate=True`` after updating secret data to ensure cache consistency.

    **Example usage**::
        # Retrieve secret by primary key and user profile
        secret = get_cached_secret_by_pk(123, user_profile)

        # Invalidate cache before fetching
        secret = get_cached_secret_by_pk(123, user_profile, invalidate=True)

    """

    @cache_results()
    def _in_memory_secret_by_pk(secret_pk: int, user_profile_id: int) -> Optional[Secret]:
        """
        In-memory cache for secret objects by primary key and user profile ID.
        """
        logger.debug(
            "%s.get_cached_secret_by_pk() retrieving and caching secret PK %s for user profile ID %s",
            HERE,
            secret_pk,
            user_profile_id,
        )
        try:
            secret = Secret.objects.get(pk=secret_pk, user_profile_id=user_profile_id)
        except Secret.DoesNotExist:
            logger.warning(
                "%s.get_cached_secret_by_pk() secret with PK %s does not exist for user profile ID %s",
                HERE,
                secret_pk,
                user_profile_id,
            )
            return None
        return secret

    return (
        _in_memory_secret_by_pk(secret_pk, user_profile.id)
        if not invalidate
        else _in_memory_secret_by_pk.invalidate(secret_pk, user_profile.id)
    )


def get_cached_account(
    account_id: Optional[int] = None, account_number: Optional[str] = None, invalidate: bool = False
) -> Optional[Account]:
    """
    Retrieve an Account instance by its ID or account number, using in-memory and Redis-based caching.

    :param account_id: Integer, optional. The primary key of the account to retrieve.
    :param account_number: String, optional. The unique account number to retrieve.
    :param invalidate: Boolean, optional. If True, invalidates the cache before fetching.

    :returns: Account instance if found, otherwise None.

    .. note::

       If both ``account_id`` and ``account_number`` are provided, ``account_id`` takes precedence.

    .. attention::

       If the account does not exist, None is returned and a warning is logged.

    **Example usage**::

        # Retrieve by account ID
        account = get_cached_account(account_id=42)

        # Retrieve by account number
        account = get_cached_account(account_number="3141-5926-5359")

        # Invalidate cache before fetching
        account = get_cached_account(account_id=42, invalidate=True)
    """

    @cache_results()
    def _get_cached_account_by_id(account_id) -> Optional[Account]:
        """
        In-memory cache for account objects by ID.
        """
        logger.debug("%s.get_cached_account() retrieving and caching account %s", HERE, account_id)
        try:
            account = Account.objects.get(id=account_id)
        except Account.DoesNotExist:
            logger.warning("%s.get_cached_account() account with ID %s does not exist", HERE, account_id)
            return None
        return account

    @cache_results()
    def _get_cached_account_by_account_number(account_number) -> Optional[Account]:
        """
        In-memory cache for account objects by account number.
        """
        logger.debug("%s.get_cached_account() retrieving and caching account %s", HERE, account_number)
        try:
            account = Account.objects.get(account_number=account_number)
        except Account.DoesNotExist:
            logger.warning("%s.get_cached_account() account with number %s does not exist", HERE, account_number)
            return None
        return account

    if account_id:
        return (
            _get_cached_account_by_id(account_id)
            if not invalidate
            else _get_cached_account_by_id.invalidate(account_id)
        )

    if account_number == SMARTER_ACCOUNT_NUMBER:
        return get_cached_smarter_account()

    if account_number:
        return (
            _get_cached_account_by_account_number(account_number)
            if not invalidate
            else _get_cached_account_by_account_number.invalidate(account_number)
        )


def get_cached_smarter_account() -> Optional[Account]:
    """
    Retrieve the special "smarter" account instance, using caching for performance.

    :param invalidate: Boolean, optional. If True, invalidates the cache before fetching.
    :returns: The smarter Account instance if found, otherwise None.

    .. note::

           The smarter account is identified by the constant ``SMARTER_ACCOUNT_NUMBER`` and is used for platform-level operations.

    .. attention::

           If the smarter account does not exist or is misconfigured, None is returned.

    **Example usage**::

        # Get the smarter account
        smarter_account = get_cached_smarter_account()

        # Invalidate cache before fetching
        smarter_account = get_cached_smarter_account(invalidate=True)
    """
    return smarter_cached_objects.smarter_account


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
    def _get_default_account():
        accounts = Account.objects.filter(is_default_account=True)
        if not accounts.exists():
            logger.warning("%s.get_cached_default_account() no default account found", HERE)
            return None
        if accounts.count() > 1:
            logger.warning("%s.get_cached_default_account() multiple default accounts found", HERE)
        account = accounts.first()
        logger.debug("%s.get_cached_default_account() retrieving and caching default account %s", HERE, account)
        return account

    return _get_default_account() if not invalidate else _get_default_account.invalidate()


def get_cached_account_for_user(user, invalidate: bool = False) -> Optional[Account]:
    if not user:
        return None

    if isinstance(user, AnonymousUser):
        return None

    username = getattr(user, "username")
    if username == SMARTER_ADMIN_USERNAME:
        return smarter_cached_objects.smarter_account

    user_id = getattr(user, "id", None)
    if not user_id:
        logger.warning("%s.get_cached_account_for_user() user has no ID: %s", HERE, user)
        return None

    @cache_results()
    def get_cached_account_for_user_by_id(user_id):
        """
        In-memory cache for user accounts.
        """
        user_profiles = UserProfile.objects.filter(user_id=user_id)
        for user_profile in user_profiles:
            if user_profile.account.is_default_account and waffle.switch_is_active(SmarterWaffleSwitches.CACHE_LOGGING):
                logger.debug(
                    "%s.get_cached_account_for_user() retrieving and caching default account %s for user %s",
                    HERE,
                    user_profile.account,
                    user,
                )
                return user_profile.account
        # If no default account is found, return the first account
        user_profile = user_profiles.first()
        if not user_profile:
            logger.warning("%s.get_cached_account_for_user_by_id() no UserProfile found for user ID %s", HERE, user_id)
            return None
        account = user_profile.account
        logger.debug(
            "%s.get_cached_account_for_user_by_id() retrieving and caching default account %s for user ID %s",
            HERE,
            account,
            user_id,
        )
        return account

    return (
        get_cached_account_for_user_by_id(user_id)
        if not invalidate
        else get_cached_account_for_user_by_id.invalidate(user_id)
    )


def get_cached_user_profile(
    user: User, account: Optional[Account] = None, invalidate: bool = False
) -> Optional[UserProfile]:
    """
    Locate the UserProfile for a given user and account, using caching for performance.

    :param user: User instance. The user whose profile should be located.
    :param account: Account instance, optional. If not provided, the user's account is determined automatically.
    :param invalidate: Boolean, optional. If True, invalidates the cache before fetching.
    :returns: UserProfile instance if found, otherwise None.

    .. note::

           If ``account`` is not provided, it is resolved using the user's associated account.

    .. warning::

           If no account or user profile is found, None is returned and a warning is logged.

    .. tip::

           Use ``invalidate=True`` after updating user or account data to ensure cache consistency.

    **Example usage**::

        # Locate user profile for a user
        profile = get_cached_user_profile(user)

        # Locate user profile for a user and specific account
        profile = get_cached_user_profile(user, account=account)

        # Invalidate cache before fetching
        profile = get_cached_user_profile(user, account=account, invalidate=True)
    """

    @cache_results()
    def get_cached_user_profile_by_user_and_account(user_id: int, account_id: int) -> Optional[UserProfile]:

        try:
            return UserProfile.objects.get(user_id=user_id, account_id=account_id)
        except UserProfile.DoesNotExist:
            logger.warning(
                "%s.get_cached_user_profile() user profile does not exist for user_id: %s and account: %s",
                HERE,
                user_id,
                account,
            )
            return None

    account = account or get_cached_account_for_user(user, invalidate=invalidate)
    if not account:
        logger.warning("%s.get_cached_user_profile() no account found for user: %s", HERE, user)
        return None

    # pylint: disable=W0212
    resolved_user = get_resolved_user(user)
    if isinstance(resolved_user, User) and isinstance(account, Account):
        return (
            get_cached_user_profile_by_user_and_account(resolved_user.id, account.id)
            if not invalidate
            else get_cached_user_profile_by_user_and_account.invalidate(resolved_user.id, account.id)
        )

    logger.warning("%s.get_cached_user_profile() user_profile is not resolvable: %s", HERE, user)
    return None


def get_cached_user_for_user_id(user_id: int, invalidate: bool = False) -> Optional[User]:
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
        user = get_cached_user_for_user_id(123)

        # Invalidate cache before fetching
        user = get_cached_user_for_user_id(123, invalidate=True)
    """

    @cache_results()
    def _in_memory_user(user_id) -> Optional[User]:
        """
        In-memory cache for user objects.
        """
        try:
            user = User.objects.get(id=user_id)
            logger.debug("%s.get_cached_user_for_user_id() retrieving and caching user %s", HERE, user)
            return user  # type: ignore[return-value]
        except User.DoesNotExist:
            logger.error("%s.get_cached_user_for_user_id() user with ID %s does not exist", HERE, user_id)

    user = _in_memory_user(user_id) if not invalidate else _in_memory_user.invalidate(user_id)
    return user


def get_cached_user_for_username(username: str, invalidate: bool = False) -> Optional[User]:
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
    def _in_memory_user_by_username(username) -> Optional[User]:
        """
        In-memory cache for user objects by username.
        """
        try:
            user = User.objects.get(username=username)
            logger.debug("%s.get_cached_user_for_username() retrieving and caching user %s", HERE, user)
            return user  # type: ignore[return-value]
        except User.DoesNotExist:
            logger.debug("%s.get_cached_user_for_username() user with username %s does not exist", HERE, username)

    if username == SMARTER_ADMIN_USERNAME:
        return smarter_cached_objects.admin_user

    user = _in_memory_user_by_username(username) if not invalidate else _in_memory_user_by_username.invalidate(username)
    if user:
        logger.debug("%s.get_cached_user_for_username() retrieving and caching user %s", HERE, user)
    return user


def get_cached_admin_user_for_account(account: Account, invalidate: bool = False) -> Optional[User]:
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
        admin_user = get_cached_admin_user_for_account(account)

        # Invalidate cache before fetching
        admin_user = get_cached_admin_user_for_account(account, invalidate=True)
    """
    if not isinstance(account, Account):
        raise SmarterValueError("Account is required")

    @cache_results()
    def _admin_user_for_account_number(account_number: str) -> User:
        # reinstantiate the account
        account = Account.objects.get(account_number=account_number)
        if not account:
            raise SmarterConfigurationError(
                f"Failed to retrieve account with number {account_number}. Please ensure the account exists and is configured correctly."
            )
        console_prefix = formatted_text(f"{__name__}.get_cached_admin_user_for_account()")
        user_profile = UserProfile.objects.filter(account=account, user__is_staff=True).order_by("pk").first()
        if user_profile:
            logger.debug(
                "%s found and cached admin UserProfile %s for account %s", console_prefix, user_profile, account
            )
            return user_profile.user
        else:
            # Create a new admin user and UserProfile
            random_email = f"{uuid.uuid4().hex[:8]}@mail.com"
            if account and isinstance(account.account_number, str):
                admin_user = User.objects.create_user(username=account.account_number, email=random_email, is_staff=True)  # type: ignore[arg-type]
                logger.debug("%s created new admin User %s for account %s", console_prefix, admin_user, account)
                user_profile = UserProfile.objects.create(name=admin_user.username, user=admin_user, account=account)
                logger.debug("%s created new admin UserProfile for user %s", console_prefix, user_profile)
        if not user_profile:
            logger.debug("%s failed to query nor create admin UserProfile for account %s", console_prefix, account)
            raise SmarterConfigurationError("Failed to create admin UserProfile")
        return user_profile.user if user_profile else None  # type: ignore[return-value]

    return (
        _admin_user_for_account_number(account.account_number)
        if not invalidate
        else _admin_user_for_account_number.invalidate(account.account_number)
    )


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


def account_number_from_url(url: str, invalidate: bool = False) -> Optional[str]:
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

    @cache_results()
    def _account_number_from_url(url: str) -> Optional[str]:
        match = SMARTER_ACCOUNT_NUMBER_PATTERN.search(url)
        retval = match.group(0) if match else None
        if retval is not None:
            logger.debug("account_number_from_url() extracted and cached account number %s from URL %s", retval, url)
        return retval

    return _account_number_from_url(url) if not invalidate else _account_number_from_url.invalidate(url)


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
    users = User.objects.filter(userprofile__account=account)
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
    return user_profiles  # type: ignore[list-item,return-value]


def cache_invalidate(user: Optional[User] = None, account: Optional[Account] = None):
    """
    Invalidate all cache entries for the specified user and/or account.

    :param user: User instance, optional. The user whose cache entries should be invalidated.
    :param account: Account instance, optional. The account whose cache entries should be invalidated.

    .. important::

           At least one of ``user`` or ``account`` must be provided. If neither is given, an exception is raised.

    .. warning::

           If the user or account cannot be resolved, cache invalidation will not occur and a warning is logged.

    .. tip::

           Use this function after updating user or account data to ensure cache consistency across the platform.

    **Example usage**::

        # Invalidate cache for a user
        cache_invalidate(user=user)

        # Invalidate cache for an account
        cache_invalidate(account=account)

        # Invalidate cache for both user and account
        cache_invalidate(user=user, account=account)
    """
    logger.debug("%s.cache_invalidate() called with user: %s account: %s", HERE, user, account)
    resolved_user = get_resolved_user(user) if user else None

    if not isinstance(resolved_user, User) and not isinstance(account, Account):
        raise SmarterValueError("either user or account is required")

    if not isinstance(resolved_user, User) and isinstance(account, Account):
        resolved_user = get_cached_admin_user_for_account(account, invalidate=True)
    else:
        user_profile = UserProfile.objects.filter(user=resolved_user).first()
        if not user_profile:
            # this can happen during new platform bootstrap initialization, so just log a warning and return
            logger.warning("%s.cache_invalidate() no UserProfile found for user: %s", HERE, resolved_user)
            return
        account = user_profile.account

    logger.debug("%s.cache_invalidate() invalidating cache for user: %s account: %s", HERE, resolved_user, account)

    if not isinstance(account, Account):
        raise SmarterValueError(f"could not resolve account {account} for user {user}")

    if isinstance(account, Account):
        get_cached_account(account_id=account.id, invalidate=True)
        get_cached_admin_user_for_account(account=account, invalidate=True)

    if isinstance(resolved_user, User):
        get_cached_account_for_user(user=resolved_user, invalidate=True)
        get_cached_user_profile(user=resolved_user, account=account, invalidate=True)
        get_cached_user_for_user_id(user_id=resolved_user.id, invalidate=True)
        get_cached_user_for_username(username=resolved_user.username, invalidate=True)
