"""
Account Models and Utilities
=============================

This module defines the core organization unit for the Smarter platform.
This module provides the model and utility functions for managing accounts in the Smarter platform.
It provides the :class:`Account` model. An account can generically represent any organizational
unit: a company, a course, a team, a department, etc. In the Smarter platform, accounts are used
to group users and resources for RBAC, billing and reporting purposes. This module
also includes helper functions for user resolution and authentication checks.

Classes & Functions
-------------------

- :class:`Account`: Represents a Smarter account, storing company and billing information.
- :func:`is_authenticated_user`: Checks if an object is an authenticated Django user.
- :func:`get_resolved_user`: Resolves a user-like object to a concrete Django user instance.
- :data:`ResolvedUserType`: Type alias for resolved user objects.

Key Features
------------

- Enforces unique, validated account numbers.
- Supports caching for efficient account retrieval.
- Provides utilities for working with Django user objects, including lazy and mock users.
- Integrates with Smarter's logging, configuration, and validation systems.

Example
-------

.. code-block:: python

    from smarter.apps.account.models import Account, get_resolved_user

    account = Account.objects.create(company_name="Acme Corp")
    resolved_user = get_resolved_user(request.user)
    if resolved_user and resolved_user.is_authenticated:
        print(account.account_number)

"""

import os
import random
from typing import TYPE_CHECKING, Optional, Union

from django.contrib.auth.models import AbstractUser, AnonymousUser, User
from django.core.validators import RegexValidator
from django.db import models
from django.test.client import RequestFactory
from django.utils.functional import SimpleLazyObject

from smarter.common.conf import smarter_settings
from smarter.common.const import SMARTER_ACCOUNT_NUMBER
from smarter.common.exceptions import SmarterConfigurationError, SmarterValueError
from smarter.lib import logging
from smarter.lib.cache import cache_results
from smarter.lib.django import waffle
from smarter.lib.django.models import MetaDataModel
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.django.waffle import SmarterWaffleSwitches

if TYPE_CHECKING:
    try:
        from django.contrib.auth.models import _AnyUser

    except ImportError:
        _AnyUser = Union[object]  # fallback for Sphinx/type checkers

HERE = os.path.abspath(os.path.dirname(__file__))
ResolvedUserType = Optional[Union[User, AbstractUser, AnonymousUser]]


def should_log_verbose(level) -> bool:
    return smarter_settings.verbose_logging


logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.ACCOUNT_LOGGING])
verbose_logger = logging.getSmarterLogger(
    __name__,
    any_switches=[SmarterWaffleSwitches.ACCOUNT_LOGGING],
    condition_func=should_log_verbose,
)


def welcome_email_context(first_name: str) -> dict:
    """
    Return the context for the welcome email template.
    templates/account/email/welcome.html
    """
    # pylint: disable=import-outside-toplevel
    from smarter.apps.dashboard.context_processors import branding

    first_name = first_name.capitalize()
    request = RequestFactory().get("/", HTTP_HOST=smarter_settings.environment_platform_domain)
    retval = branding(request=request)
    retval["first_name"] = first_name
    retval["environment_platform_domain"] = smarter_settings.environment_url.rstrip("/")
    retval["send_password_email"] = waffle.switch_is_active(SmarterWaffleSwitches.ENABLE_NEW_USER_PASSWORD_EMAIL)
    return retval


def is_authenticated_user(user: object) -> bool:
    """
    Check if the given user-like object is an authenticated Django user.

    This function attempts to determine if the provided object represents an authenticated user by checking for
    the `is_authenticated` attribute, which is standard for Django's User and AnonymousUser models. It also
    handles edge cases such as lazy objects and test mocks.

    :param user: The user-like object to check.
    :returns: True if the object is an authenticated user, False otherwise.
    """
    verbose_logger.debug(
        "%s called for user type: %s", logging.formatted_text(__name__) + ".is_authenticated_user()", type(user)
    )
    if hasattr(user, "is_authenticated"):
        return bool(user.is_authenticated)  # type: ignore
    return False


def get_resolved_user(
    user: Union[User, AbstractUser, AnonymousUser, SimpleLazyObject, "_AnyUser"],
) -> ResolvedUserType:
    """
    Resolve and return a Django user object from a user-like instance.

    This function maps various Django user subclasses and proxy types (such as `SimpleLazyObject`)
    to a concrete `User`, `AbstractUser`, or `AnonymousUser` instance. It is useful for ensuring
    type safety and correct type annotations when working with user objects in Django.

    :param user: Union[User, AbstractUser, AnonymousUser, SimpleLazyObject, _AnyUser]
        The user-like object to resolve.

    :returns: Optional[Union[User, AbstractUser, AnonymousUser]]
        The resolved user object, or None if input is None.

    :raises SmarterConfigurationError: If the input user type is unexpected.

    .. note::

            Handles edge cases such as lazy objects and test mocks.


    **Example usage**::

        from smarter.apps.account.models import get_resolved_user
        resolved_user = get_resolved_user(request.user)
        if resolved_user and resolved_user.is_authenticated:
            # Safe to access user fields

    .. seealso::

            :class:`django.contrib.auth.models.User`
            :class:`django.utils.functional.SimpleLazyObject`

    """
    verbose_logger.debug(
        "%s called for user type: %s", logging.formatted_text(__name__) + ".get_resolved_user()", type(user)
    )
    if user is None:
        return None

    # this is the expected case
    if isinstance(user, Union[User, AnonymousUser, AbstractUser]):
        verbose_logger.debug(
            "%s - user is instance of expected type: %s",
            logging.formatted_text(__name__) + ".get_resolved_user()",
            type(user),
        )
        return user

    # these are manageable edge cases
    # --------------------------------

    # pylint: disable=W0212
    if isinstance(user, SimpleLazyObject):
        verbose_logger.debug(
            "%s - user is instance of SimpleLazyObject, returning wrapped user: %s",
            logging.formatted_text(__name__) + ".get_resolved_user()",
            type(user._wrapped),
        )
        return user._wrapped
    # Allow unittest.mock.MagicMock or Mock for testing
    if hasattr(user, "__class__") and user.__class__.__name__ in ("MagicMock", "Mock"):
        verbose_logger.debug(
            "%s - user is instance of test mock: %s",
            logging.formatted_text(__name__) + ".get_resolved_user()",
            type(user),
        )
        return user  # type: ignore[return-value]
    raise SmarterConfigurationError(
        f"Unexpected user type: {type(user)}. Expected Django User, AnonymousUser, SimpleLazyObject, or a test mock."
    )


class Account(MetaDataModel):
    """
    Model representing a Smarter account.

    The `Account` model stores company and billing information, and is the central entity for resource ownership,
    billing, and user management in the Smarter platform.

    :param account_number: String. Unique account identifier in the format '9999-9999-9999'.
    :param is_default_account: Boolean. Indicates if this is the default account.
    :param company_name: String. Name of the company.
    :param phone_number: String. Company phone number.
    :param address1: String. Primary address line.
    :param address2: String. Secondary address line.
    :param city: String. City.
    :param state: String. State or region.
    :param postal_code: String. Postal code.
    :param country: String. Country (default: 'USA').
    :param language: String. Language code (default: 'EN').
    :param timezone: String. Timezone.
    :param currency: String. Currency code (default: 'USD').
    :param is_active: Boolean. If False, account is disabled for billing and resource management.

    **Example usage**::

        from smarter.apps.account.models import Account
        account = Account.objects.create(company_name="Acme Corp")
        print(account.account_number)

    .. seealso::

            Related models: :class:`UserProfile`, :class:`AccountContact`, :class:`Charge`
    """

    account_number_format = RegexValidator(
        regex=SmarterValidator.VALID_ACCOUNT_NUMBER_PATTERN,
        message="Account number must be entered in the format: '9999-9999-9999'.",
    )

    account_number = models.CharField(
        validators=[account_number_format], max_length=255, unique=True, default="9999-9999-9999", blank=True, null=True
    )
    is_default_account = models.BooleanField(
        default=False,
        help_text="Indicates if this is the default account for the organization. Only one account should be marked as default.",
    )
    company_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=50, blank=True, null=True)
    address1 = models.CharField(max_length=255, blank=True, null=True)
    address2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=255, blank=True, null=True)
    state = models.CharField(max_length=255, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(max_length=255, default="USA", blank=True, null=True, help_text="ISO 3166 country code.")
    language = models.CharField(
        max_length=255, default="EN", blank=True, null=True, help_text="BCP 47 language tag, e.g., 'en-US'."
    )
    timezone = models.CharField(
        max_length=255, blank=True, null=True, help_text=" IANA timezone name, e.g., 'America/New_York'."
    )
    currency = models.CharField(
        max_length=255, default="USD", blank=True, null=True, help_text="ISO 4217 currency code."
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Indicates whether the account is active. Inactive accounts cannot be used for billing or resource management, nor hosting Provider apis.",
    )

    @classmethod
    def randomized_account_number(cls):
        """
        Generate a random account number in the format ####-####-####.

        This method ensures uniqueness by checking for collisions with existing account numbers.

        :returns: str
            A unique account number string.

        .. note::

            The generated account number is zero-padded and segmented for readability.


        **Example usage**::

            from smarter.apps.account.models import Account
            account_number = Account.randomized_account_number()
            print(account_number)  # e.g., '1234-5678-9012'


        """
        ACCOUNT_NUMBER_SEGMENTS = 3
        ACCOUNT_NUMBER_SEGMENT_LENGTH = 4

        def account_number_generator():
            parts = [
                str(random.randint(0, 9999)).zfill(ACCOUNT_NUMBER_SEGMENT_LENGTH)
                for _ in range(ACCOUNT_NUMBER_SEGMENTS)
            ]
            retval = "-".join(parts)
            return retval

        account_number = account_number_generator()
        while cls.objects.filter(account_number=account_number).exists():
            account_number = account_number_generator()

        return account_number

    def save(self, *args, **kwargs):
        """
        Save the Account instance, ensuring a valid and unique account number.

        If the account number is set to the default value, this method generates a new unique account number.
        It also validates the account number format before saving.

        :param args: Positional arguments passed to the parent save method.
        :param kwargs: Keyword arguments passed to the parent save method.

        :raises SmarterValueError: If the account number is invalid.

        **Example usage**::

            account = Account(company_name="Acme Corp")
            account.save()  # Ensures account_number is unique and valid

        """
        orig = None
        if self.pk is not None:
            # check if account_number is being changed on updated, if so raise error.
            orig = Account.objects.get(pk=self.pk)
            if orig.account_number != self.account_number:
                raise SmarterValueError("Account number is immutable and cannot be changed once set.")
        try:
            Account.objects.get(is_default_account=True)
        except Account.DoesNotExist:
            if orig and orig.is_default_account:
                logger.warning(
                    "%s.save() this save operation will leave the platform with no default account. You should ensure that exactly one account is marked as default.",
                    self.formatted_class_name,
                )
            else:
                logger.warning(
                    "%s.save() No default account found when saving Account instance. Ensure that one account is marked as default.",
                    self.formatted_class_name,
                )

        except Account.MultipleObjectsReturned as e:
            accounts = Account.objects.filter(is_default_account=True)
            logger.error(
                "%s.save() Multiple accounts marked as default: %s. Account IDs: %s. Ensure that only one account is marked as default.",
                self.formatted_class_name,
                accounts,
                [account for account in accounts],
            )
            raise SmarterConfigurationError(
                f"{self.formatted_class_name}.save() Multiple accounts are marked as default: {[account for account in accounts]}. Only one default account is allowed. {e}"
            ) from e
        if self.account_number == "9999-9999-9999":
            self.account_number = self.randomized_account_number()

        SmarterValidator.validate_account_number(self.account_number)
        super().save(*args, **kwargs)

    @classmethod
    def get_by_account_number(cls, account_number):
        """
        Retrieve an Account instance by its account number.

        :param account_number: String. The account number to search for.
        :returns: Optional[Account]
            The Account instance if found, otherwise None.


        """
        try:
            return cls.objects.get(account_number=account_number)
        except cls.DoesNotExist:
            return None

    @classmethod
    def get_cached_object(
        cls,
        *args,
        invalidate: Optional[bool] = False,
        pk: Optional[int] = None,
        name: Optional[str] = None,
        account_number: Optional[str] = None,
        company_name: Optional[str] = None,
        **kwargs,
    ) -> "Account":
        """
        Retrieve an Account instance by account number with caching.

        This method uses caching to optimize retrieval of Account instances by their account number.
        It checks the cache first and falls back to a database query if the cache is missed.

        :param invalidate: If True, invalidate the cache for this query.
        :type invalidate: bool, optional
        :param pk: Optional primary key to search for (ignored if account_number is provided).
        :type pk: int, optional
        :param name: Optional name to search for (ignored if account_number is provided).
        :type name: str, optional
        :param account_number: String. The account number to search for.
        :type account_number: str, optional
        :param company_name: String. The company name to search for (used if account_number is not provided).
        :type company_name: str, optional

        :returns: Optional[Account]
            The Account instance if found, otherwise None.

        .. note::

            Caching can significantly improve performance for frequently accessed accounts.

        **Example usage**::

            account = Account.get_cached_object(account_number="1234-5678-9012")
            if account:
                print(account.company_name)

        """
        logger_prefix = logging.formatted_text(f"{__name__}.{cls.__name__}.get_cached_object()")
        logger.debug(
            "%s called with pk=%s, name=%s, account_number=%s, company_name=%s, invalidate=%s",
            logger_prefix,
            pk,
            name,
            account_number,
            company_name,
            invalidate,
        )

        @cache_results(cls.cache_expiration)
        def _get_account_by_number(account_number: str, class_name: str) -> Optional["Account"]:
            try:
                logger.debug(
                    "%s._get_account_by_number() cache miss for account_number=%s", logger_prefix, account_number
                )
                return cls.objects.get(account_number=account_number)
            except cls.DoesNotExist as e:
                logger.debug(
                    "%s._get_account_by_number() no Account found for account_number=%s", logger_prefix, account_number
                )
                raise cls.DoesNotExist(f"No Account found with account_number={account_number}") from e

        @cache_results(cls.cache_expiration)
        def _get_account_by_company_name(company_name: str, class_name: str) -> Optional["Account"]:
            try:
                logger.debug(
                    "%s._get_account_by_company_name() cache miss for company_name=%s", logger_prefix, company_name
                )
                return cls.objects.get(company_name=company_name)
            except cls.DoesNotExist as e:
                logger.debug(
                    "%s._get_account_by_company_name() no Account found for company_name=%s",
                    logger_prefix,
                    company_name,
                )
                raise cls.DoesNotExist(f"No Account found with company_name={company_name}") from e

        if invalidate:
            _get_account_by_number.invalidate(account_number=account_number, class_name=Account.__name__)
            _get_account_by_company_name.invalidate(company_name=company_name, class_name=Account.__name__)

        if account_number:
            return _get_account_by_number(account_number=account_number, class_name=Account.__name__)

        if company_name:
            return _get_account_by_company_name(company_name=company_name, class_name=Account.__name__)

        return super().get_cached_object(*args, invalidate=invalidate, pk=pk, name=name, **kwargs)  # type: ignore[return-value]

    # pylint: disable=missing-class-docstring
    class Meta:
        verbose_name = "Account"
        verbose_name_plural = "Accounts"

    def __str__(self):
        return str(self.account_number) + " - " + str(self.company_name)

    def __repr__(self) -> str:
        return super().__str__()


__all__ = [
    "Account",
    "is_authenticated_user",
    "get_resolved_user",
    "ResolvedUserType",
]
