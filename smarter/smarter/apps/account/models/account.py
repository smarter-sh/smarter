"""Account models."""

import os
import random
from typing import TYPE_CHECKING, Optional, Union

# django stuff
from django.contrib.auth.models import AbstractUser, AnonymousUser, User
from django.core.validators import RegexValidator
from django.db import models
from django.template.loader import render_to_string
from django.test.client import RequestFactory
from django.utils.functional import SimpleLazyObject

import smarter.lib.logging as logging

# our stuff
from smarter.common.conf import smarter_settings
from smarter.common.exceptions import SmarterConfigurationError, SmarterValueError
from smarter.common.helpers.console_helpers import formatted_text
from smarter.common.helpers.email_helpers import email_helper
from smarter.lib.cache import cache_results
from smarter.lib.django import waffle
from smarter.lib.django.models import MetaDataModel, TimestampedModel
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.django.waffle import SmarterWaffleSwitches

if TYPE_CHECKING:
    try:
        from django.contrib.auth.models import _AnyUser

    except ImportError:
        _AnyUser = Union[object]  # fallback for Sphinx/type checkers

HERE = os.path.abspath(os.path.dirname(__file__))
ResolvedUserType = Optional[Union[User, AbstractUser, AnonymousUser]]


logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.ACCOUNT_LOGGING])
verbose_logger = logging.getSmarterLogger(
    __name__,
    any_switches=[SmarterWaffleSwitches.ACCOUNT_LOGGING],
    condition_func=lambda: smarter_settings.verbose_logging,
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
        "%s called for user type: %s", formatted_text(__name__) + ".is_authenticated_user()", type(user)
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
    verbose_logger.debug("%s called for user type: %s", formatted_text(__name__) + ".get_resolved_user()", type(user))
    if user is None:
        return None

    # this is the expected case
    if isinstance(user, Union[User, AnonymousUser, AbstractUser]):
        verbose_logger.debug(
            "%s - user is instance of expected type: %s",
            formatted_text(__name__) + ".get_resolved_user()",
            type(user),
        )
        return user

    # these are manageable edge cases
    # --------------------------------

    # pylint: disable=W0212
    if isinstance(user, SimpleLazyObject):
        verbose_logger.debug(
            "%s - user is instance of SimpleLazyObject, returning wrapped user: %s",
            formatted_text(__name__) + ".get_resolved_user()",
            type(user._wrapped),
        )
        return user._wrapped
    # Allow unittest.mock.MagicMock or Mock for testing
    if hasattr(user, "__class__") and user.__class__.__name__ in ("MagicMock", "Mock"):
        verbose_logger.debug(
            "%s - user is instance of test mock: %s",
            formatted_text(__name__) + ".get_resolved_user()",
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
        if self.pk is not None:
            # check if account_number is being changed on updated, if so raise error.
            orig = Account.objects.get(pk=self.pk)
            if orig.account_number != self.account_number:
                raise SmarterValueError("Account number cannot be changed once set.")
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
    ) -> Optional["Account"]:
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
        logger_prefix = formatted_text(f"{__name__}.{cls.__name__}.get_cached_object()")
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
            except cls.DoesNotExist:
                logger.debug(
                    "%s._get_account_by_number() no Account found for account_number=%s", logger_prefix, account_number
                )
                return None

        @cache_results(cls.cache_expiration)
        def _get_account_by_company_name(company_name: str, class_name: str) -> Optional["Account"]:
            try:
                logger.debug(
                    "%s._get_account_by_company_name() cache miss for company_name=%s", logger_prefix, company_name
                )
                return cls.objects.get(company_name=company_name)
            except cls.DoesNotExist:
                logger.debug(
                    "%s._get_account_by_company_name() no Account found for company_name=%s",
                    logger_prefix,
                    company_name,
                )
                return None

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


class AccountContact(TimestampedModel):
    """
    Model for storing contact information associated with an account.

    Unlike the User model, `AccountContact` allows management of email lists and contact details
    independently from registered users. This is useful for sending communications to non-user contacts,
    or for users who opt out of system emails.

    :param account: ForeignKey to :class:`Account`. The related account.
    :param first_name: String. Contact's first name.
    :param last_name: String. Contact's last name.
    :param email: String. Contact's email address.
    :param phone: String. Contact's phone number (optional).
    :param is_primary: Boolean. Marks this contact as the primary contact for the account.
    :param is_test: Boolean. Indicates if this contact is for testing purposes.
    :param welcomed: Boolean. Indicates if a welcome email has been sent.

    .. note::

        Contacts do not need to be registered users.

    .. tip::

        Use :meth:`send_email_to_account` to broadcast messages to all contacts.

    .. attention::

        Only one primary contact is allowed per account.

    **Example usage**::

        from smarter.apps.account.models import AccountContact
        contact = AccountContact.objects.create(
            account=account,
            first_name="Jane",
            last_name="Doe",
            email="jane@example.com",
            is_primary=True
        )

    .. seealso::

        :class:`Account`, :class:`UserProfile`
    """

    # pylint: disable=missing-class-docstring
    class Meta:
        verbose_name = "Account Contact"
        verbose_name_plural = "Account Contacts"
        unique_together = ("account", "email")

    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="contacts")
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True, null=True)
    is_primary = models.BooleanField(
        default=False,
        help_text="Indicates if this contact is the primary contact for the account. Only one contact can be primary per account.",
    )
    is_test = models.BooleanField(
        default=False, help_text="Indicates if this contact is used for unit testing purposes."
    )
    welcomed = models.BooleanField(
        default=False, help_text="Indicates if a welcome email has been sent to this contact."
    )

    def send_email(self, subject: str, body: str, html: bool = False, from_email: Optional[str] = None):
        """
        Send an email to this account contact.

        This method uses the Smarter email helper to deliver a message to the contact's email address.
        It supports both plain text and HTML emails, and allows customization of the sender address.

        :param subject: String. The email subject line.
        :param body: String. The email body content.
        :param html: Boolean. If True, sends the email as HTML. Defaults to False.
        :param from_email: String or None. Optional sender email address.

        .. note::

            If the contact is marked as a test contact (`is_test=True`), the email is sent quietly.

        .. tip::

            Use this method for direct, transactional communications with account contacts.

        **Example usage**::

            contact.send_email(
                subject="Welcome!",
                body="Hello and welcome to Smarter.",
                html=True,
                from_email="support@smarter.com"
            )

        """

        email_helper.send_email(
            subject=subject, to=self.email, body=body, html=html, from_email=from_email, quiet=self.is_test
        )

    def send_welcome_email(self) -> None:
        """
        Send a personalized welcome email to this account contact.

        This method renders the welcome email template with the contact's first name and sends it as HTML.

        :returns: None

        .. note::

            The welcome email uses the template at ``account/email/welcome.html``.

        .. tip::

            This method is automatically called when a new contact is created and has not yet been welcomed.

        **Example usage**::

            contact.send_welcome_email()

        """
        context = welcome_email_context(first_name=self.first_name)
        html_template = render_to_string("account/email/welcome.html", context)
        logger.debug(
            "%s.send_welcome_email() Sending welcome email to %s",
            formatted_text(__name__ + ".AccountContact.send_welcome_email()"),
            self.email,
        )

        subject = "Welcome to Smarter!"
        body = html_template
        self.send_email(subject=subject, body=body, html=True)

    @classmethod
    def get_primary_contact(cls, account: Account) -> Optional["AccountContact"]:
        """
        Retrieve the primary contact for a given account.

        This method returns the first contact marked as primary for the specified account, or None if no such contact exists.

        :param account: Instance of :class:`Account`. The account to search for a primary contact.
        :returns: Optional[AccountContact]
            The primary contact instance, or None if not found.

        .. tip::

            Use this method to quickly access the main point of contact for notifications or support.

        **Example usage**::

            primary_contact = AccountContact.get_primary_contact(account)
            if primary_contact:
                print(primary_contact.email)

        """
        return cls.objects.filter(account=account, is_primary=True).first()

    # pylint: disable=too-many-arguments
    @classmethod
    def send_email_to_account(
        cls, account: Account, subject: str, body: str, html: bool = False, from_email: Optional[str] = None
    ) -> None:
        """
        Send an email to all contacts associated with a given account.

        This method iterates over all contacts for the specified account and sends the provided message
        to each contact's email address.

        :param account: Instance of :class:`Account`. The account whose contacts will receive the email.
        :param subject: String. The email subject line.
        :param body: String. The email body content.
        :param html: Boolean. If True, sends the email as HTML. Defaults to False.
        :param from_email: String or None. Optional sender email address.

        .. note::

            Contacts marked as test contacts (`is_test=True`) will receive emails quietly.

        .. tip::

            Use this method for account-wide notifications or announcements.

        **Example usage**::

            AccountContact.send_email_to_account(
                account=account,
                subject="System Update",
                body="We have updated our terms of service.",
                html=False
            )

        """
        contacts = cls.objects.filter(account=account)
        for contact in contacts:
            contact.send_email(subject=subject, body=body, html=html, from_email=from_email)

    # pylint: disable=too-many-arguments
    @classmethod
    def send_email_to_primary_contact(
        cls, account: Account, subject: str, body: str, html: bool = False, from_email: Optional[str] = None
    ) -> None:
        """
        Send an email to the primary contact of a given account.

        This method locates the primary contact for the specified account and sends the provided message.
        If no primary contact exists, an error is logged.

        :param account: Instance of :class:`Account`. The account whose primary contact will receive the email.
        :param subject: String. The email subject line.
        :param body: String. The email body content.
        :param html: Boolean. If True, sends the email as HTML. Defaults to False.
        :param from_email: String or None. Optional sender email address.

        .. attention::

            If no primary contact is found, no email is sent and an error is logged.

        .. tip::

            Use this method for urgent or important communications that require a single point of contact.

        **Example usage**::

            AccountContact.send_email_to_primary_contact(
                account=account,
                subject="Urgent: Action Required",
                body="Please review your account settings.",
                html=True
            )

        """
        prefix = formatted_text(__name__ + ".AccountContact.send_email_to_primary_contact()")
        contact = cls.get_primary_contact(account)
        logger.debug(
            "%s.send_email_to_primary_contact() Attempting to send email to primary contact for account %s. Found contact: %s, subject: %s, body: %s, html: %s, from_email: %s",
            prefix,
            account,
            contact,
            subject,
            body,
            html,
            from_email,
        )
        if contact:
            contact.send_email(subject=subject, body=body, html=html, from_email=from_email)
        else:
            logger.error(
                "%s.send_email_to_primary_contact() No primary contact found for account %s",
                prefix,
                account,
            )

    def save(self, *args, **kwargs):
        """
        Save the AccountContact instance, enforcing primary contact uniqueness and sending a welcome email if needed.

        This method ensures that only one primary contact exists per account. If the contact is new and has not
        been welcomed, a welcome email is sent and the `welcomed` flag is updated.

        :param args: Positional arguments passed to the parent save method.
        :param kwargs: Keyword arguments passed to the parent save method.

        .. attention::

            Only one contact per account can be marked as primary. Attempting to save another will raise an error.

        .. note::

            The welcome email is sent automatically for new contacts who have not been welcomed.

        :raises SmarterValueError: If another primary contact already exists for the account.

        **Example usage**::

            contact = AccountContact(account=account, email="jane@example.com", is_primary=True)
            contact.save()  # Ensures uniqueness and sends welcome email if needed

        """
        prefix = formatted_text(__name__ + ".AccountContact.save()")
        logger.debug("%s called with args: %s, kwargs: %s", prefix, args, kwargs)
        if self.is_primary:
            # Check for another primary contact for this account (excluding self if updating)
            qs = AccountContact.objects.filter(account=self.account, is_primary=True)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise SmarterValueError("There is already a primary contact for this account.")

        super().save(*args, **kwargs)
        if not self.welcomed:
            self.send_welcome_email()
            self.welcomed = True
            self.save()

    def __str__(self):
        return self.first_name + " " + self.last_name


__all__ = [
    "Account",
    "AccountContact",
    "is_authenticated_user",
    "get_resolved_user",
    "ResolvedUserType",
]
