"""Account models."""

# pylint: disable=missing-class-docstring

import logging
import os
import random
from typing import TYPE_CHECKING, Optional, Union

# 3rd party stuff
from cryptography.fernet import Fernet

# django stuff
from django.conf import settings
from django.contrib.auth.models import AbstractUser, AnonymousUser, User
from django.core.handlers.wsgi import WSGIRequest
from django.core.validators import RegexValidator
from django.db import models
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.functional import SimpleLazyObject

# our stuff
from smarter.common.conf import settings as smarter_settings
from smarter.common.exceptions import SmarterConfigurationError, SmarterValueError
from smarter.common.helpers.email_helpers import email_helper
from smarter.lib.django import waffle
from smarter.lib.django.model_helpers import TimestampedModel
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

from .signals import (
    new_charge_created,
    new_user_created,
    secret_accessed,
    secret_created,
    secret_edited,
)


HERE = os.path.abspath(os.path.dirname(__file__))


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.ACCOUNT_LOGGING) and level >= smarter_settings.log_level


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


CHARGE_TYPE_PROMPT_COMPLETION = "completion"
CHARGE_TYPE_PLUGIN = "plugin"
CHARGE_TYPE_TOOL = "tool"

CHARGE_TYPES = [
    (CHARGE_TYPE_PROMPT_COMPLETION, "Prompt Completion"),
    (CHARGE_TYPE_PLUGIN, "Plugin"),
    (CHARGE_TYPE_TOOL, "Tool"),
]

PROVIDER_OPENAI = "openai"
PROVIDER_METAAI = "metaai"
PROVIDER_GOOGLEAI = "googleai"

PROVIDERS = [
    (PROVIDER_OPENAI, "OpenAI"),
    (PROVIDER_METAAI, "Meta AI"),
    (PROVIDER_GOOGLEAI, "Google AI"),
]


def welcome_email_context(first_name: str) -> dict:
    """
    Return the context for the welcome email template.
    templates/account/email/welcome.html
    """

    first_name = first_name.capitalize()
    return {
        "base_url": smarter_settings.environment_url,
        "first_name": first_name,
        "corporate_name": settings.SMARTER_BRANDING_CORPORATE_NAME,
        "support_phone": settings.SMARTER_BRANDING_SUPPORT_PHONE_NUMBER,
        "support_email": settings.SMARTER_BRANDING_SUPPORT_EMAIL,
        "contact_address": settings.SMARTER_BRANDING_ADDRESS,
        "contact_url": settings.SMARTER_BRANDING_CONTACT,
        "office_hours": settings.SMARTER_BRANDING_SUPPORT_HOURS,
        "facebook_url": settings.SMARTER_BRANDING_URL_FACEBOOK,
        "twitter_url": settings.SMARTER_BRANDING_URL_TWITTER,
        "linkedin_url": settings.SMARTER_BRANDING_URL_LINKEDIN,
    }


if TYPE_CHECKING:
    try:
        from django.contrib.auth.models import _AnyUser
    except ImportError:
        _AnyUser = object  # fallback for Sphinx/type checkers


def get_resolved_user(
    user: "Union[User, AbstractUser, AnonymousUser, SimpleLazyObject, _AnyUser]",
) -> Optional[Union[User, AbstractUser, AnonymousUser]]:
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
    logger.info("get_resolved_user() called for user type: %s", type(user))
    if user is None:
        return None

    # this is the expected case
    if isinstance(user, Union[User, AnonymousUser, AbstractUser]):
        return user

    # these are manageable edge cases
    # --------------------------------

    # pylint: disable=W0212
    if isinstance(user, SimpleLazyObject):
        return user._wrapped
    # Allow unittest.mock.MagicMock or Mock for testing
    if hasattr(user, "__class__") and user.__class__.__name__ in ("MagicMock", "Mock"):
        return user  # type: ignore[return-value]
    raise SmarterConfigurationError(
        f"Unexpected user type: {type(user)}. Expected Django User, AnonymousUser, SimpleLazyObject, or a test mock."
    )


class Account(TimestampedModel):
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
    is_default_account = models.BooleanField(default=False)
    company_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=50, blank=True, null=True)
    address1 = models.CharField(max_length=255, blank=True, null=True)
    address2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=255, blank=True, null=True)
    state = models.CharField(max_length=255, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(max_length=255, default="USA", blank=True, null=True)
    language = models.CharField(max_length=255, default="EN", blank=True, null=True)
    timezone = models.CharField(max_length=255, blank=True, null=True)
    currency = models.CharField(max_length=255, default="USD", blank=True, null=True)
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

    # pylint: disable=missing-class-docstring
    class Meta:
        verbose_name = "Account"
        verbose_name_plural = "Accounts"

    def __str__(self):
        return str(self.account_number) + " - " + str(self.company_name)


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
    is_primary = models.BooleanField(default=False)
    is_test = models.BooleanField(default=False)
    welcomed = models.BooleanField(default=False)

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
        contact = cls.get_primary_contact(account)
        if contact:
            contact.send_email(subject=subject, body=body, html=html, from_email=from_email)
        else:
            logger.error("No primary contact found for account %s", account)

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


class UserProfile(TimestampedModel):
    """
    UserProfile model for associating Django users with Smarter accounts.

    Establishes a link between a Django User and an Account, enabling centralized management of billing, identity, and resource ownership.

    :param user: ForeignKey to :class:`django.contrib.auth.models.User`. The user associated with this profile.
    :param account: ForeignKey to :class:`Account`. The related Smarter account.
    :param is_test: Boolean. Indicates if this profile is for testing purposes.

    .. important::

        The combination of `user` and `account` must be unique. Duplicate profiles for the same user and account are not allowed.

    **Example usage**::

        from smarter.apps.account.models import UserProfile
        profile = UserProfile.objects.create(user=user, account=account)
        profile.add_to_account_contacts(is_primary=True)

    """

    # pylint: disable=missing-class-docstring
    class Meta:
        unique_together = (
            "user",
            "account",
        )

    # Add more fields here as needed
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="user_profile",
    )
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="users")
    is_test = models.BooleanField(default=False)

    def add_to_account_contacts(self, is_primary: bool = False):
        """
        Add the user to the account's contact list.

        Creates or updates an `AccountContact` entry for the user, ensuring their email and name are registered with the account.
        Optionally sets the contact as primary.

        :param is_primary: Boolean. If True, marks the contact as the primary contact for the account. Defaults to False.

        .. important::

            Ensures every user associated with an account is also listed as a contact, supporting notifications and account management.

        **Example usage**::

            profile.add_to_account_contacts(is_primary=True)

        .. seealso::

            :class:`AccountContact`
        """
        account_contact, _ = AccountContact.objects.get_or_create(
            account=self.account,
            email=self.user.email,
            is_test=self.is_test,
            first_name=self.user.first_name or "account",
            last_name=self.user.last_name or "contact",
        )
        if account_contact.is_primary != is_primary:
            account_contact.is_primary = is_primary
            account_contact.save()

    def save(self, *args, **kwargs):
        """
        Save the UserProfile instance and ensure account contacts are updated.

        This method validates that both `user` and `account` are set, saves the profile, and, if newly created,
        adds the user to the account's contact list. It also emits a signal for new user creation.

        :param args: Positional arguments passed to the parent save method.
        :param kwargs: Keyword arguments passed to the parent save method.

        .. note::

            On first save, ensures at least one primary contact exists for the account.

        **Example usage**::

            profile.save()

        """
        is_new = self.pk is None

        if self.user is None or self.account is None:
            raise SmarterValueError("User and Account cannot be null")
        super().save(*args, **kwargs)
        if is_new:
            # ensure that at least one person is on the account contact list
            is_primary = AccountContact.objects.filter(account=self.account, is_primary=True).count() == 0
            self.add_to_account_contacts(is_primary=is_primary)

            logger.debug(
                "New user profile created for %s %s. Sending signal.", self.account.company_name, self.user.email
            )
            new_user_created.send(sender=self.__class__, user_profile=self)

    @classmethod
    def admin_for_account(cls, account: Account) -> User:
        """
        Return the designated user for the given account.

        This method finds the first staff user associated with the account. If no staff user exists, it returns the first available user.
        If the account has no users, an admin user is created and returned.

        :param account: Instance of :class:`Account`. The account for which to find the designated user.
        :returns: :class:`django.contrib.auth.models.User`
            The designated user for the account.

        .. attention::

            If no staff or regular users exist for the account, an admin user is automatically created. You must set the password manually.

        .. error::

            Logs an error if no admin or user is found for the account.

        **Example usage**::

            user = UserProfile.admin_for_account(account)

        .. seealso::

            :class:`UserProfile`
        """
        admins = cls.objects.filter(account=account, user__is_staff=True).order_by("user__id")
        if admins.exists():
            return admins.first().user  # type: ignore[return-value]

        logger.error("No admin found for account %s", account)

        users = cls.objects.filter(account=account).order_by("user__id")
        if users.exists():
            user = users.first().user  # type: ignore[return-value]
            return user

        logger.error("No user for account %s", account)
        admin_user = cls.objects.get_or_create(username="admin")
        user_profile = cls.objects.create(user=admin_user, account=account)
        logger.warning("Created admin user for account %s. Use manage.py to set the password", account)
        return user_profile.user

    def __str__(self):
        return str(self.account.company_name) + "-" + str(self.user.email or self.user.username)


class PaymentMethod(TimestampedModel):
    """Payment method model."""

    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="payment_methods")
    name = models.CharField(max_length=255)
    stripe_id = models.CharField(max_length=255)
    card_type = models.CharField(max_length=255)
    card_last_4 = models.CharField(max_length=4)
    card_exp_month = models.CharField(max_length=2)
    card_exp_year = models.CharField(max_length=4)
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return str(self.card_type) + " " + str(self.card_last_4)


class LLMPrices(TimestampedModel):
    """
    LLMPrices model for managing markup factors in account billing.

    Stores provider/model-specific price markups, enabling proportional billing across all accounts based on their usage.

    :param charge_type: String. The type of charge (e.g., completion, plugin, tool).
    :param provider: String. The LLM provider (e.g., OpenAI, Meta AI).
    :param model: String. The model name.
    :param price: Decimal. The markup price to apply.

    .. note::

        Markup factors are used to calculate each account's share of provider costs.

    **Example usage**::

        # Calculate account charge for provider/model usage
        markup = LLMPrices.objects.get(provider="openai", model="gpt-4").price
        account_charge = provider_cost * markup * account_usage_ratio

    .. seealso::

        :class:`Account`, :class:`Charge`
    """

    charge_type = models.CharField(max_length=20)
    provider = models.CharField(max_length=255)
    model = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=6)

    class Meta:
        unique_together = ("charge_type", "provider", "model")

    def __str__(self):
        return f"{self.charge_type} - {self.provider} - {self.model} - {self.price}"


class Charge(TimestampedModel):
    """
    Charge model for tracking periodic account billing events.

    Represents a single billing event for an account and user, including provider, charge type, token usage, and reference details.

    :param account: ForeignKey to :class:`Account`. The account being billed.
    :param user: ForeignKey to :class:`django.contrib.auth.models.User`. The user associated with the charge.
    :param session_key: String. Optional session identifier for the charge.
    :param provider: String. The LLM provider (e.g., OpenAI).
    :param charge_type: String. The type of charge (e.g., completion, plugin, tool).
    :param prompt_tokens: Integer. Number of prompt tokens used.
    :param completion_tokens: Integer. Number of completion tokens used.
    :param total_tokens: Integer. Total tokens used.
    :param model: String. The model name.
    :param reference: String. Reference identifier for the charge.

    .. note::

        A signal is emitted when a new charge is created, enabling downstream billing and analytics workflows.

    **Example usage**::

        charge = Charge.objects.create(
            account=account,
            user=user,
            provider="openai",
            charge_type="completion",
            prompt_tokens=100,
            completion_tokens=200,
            total_tokens=300,
            model="gpt-4",
            reference="invoice-123"
        )

    .. seealso::

        :class:`Account`, :class:`LLMPrices`
    """

    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="charge", null=False, blank=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="charge", null=False, blank=False
    )
    session_key = models.CharField(max_length=255, null=True, blank=True)
    provider = models.CharField(
        max_length=255,
        choices=PROVIDERS,
        default=PROVIDER_OPENAI,
    )
    charge_type = models.CharField(
        max_length=20,
        choices=CHARGE_TYPES,
        default=CHARGE_TYPE_PROMPT_COMPLETION,
    )
    prompt_tokens = models.IntegerField()
    completion_tokens = models.IntegerField()
    total_tokens = models.IntegerField()
    model = models.CharField(max_length=255)
    reference = models.CharField(max_length=255)

    def save(self, *args, **kwargs):
        is_new = self.pk is None

        super().save(*args, **kwargs)
        if is_new:
            logger.debug(
                "New user charge created for %s %s. Sending signal.", self.account.company_name, self.user.email
            )
            new_charge_created.send(sender=self.__class__, charge=self)

    def __str__(self):
        return f"""{self.account.account_number} - {self.user.email} - {self.provider} - {self.charge_type} - {self.total_tokens}"""


class DailyBillingRecord(TimestampedModel):
    """
    DailyBillingRecord model for aggregating daily account charges.

    Tracks daily usage and billing data for each account, user, provider, and charge type, enabling efficient reporting and analytics.

    :param account: ForeignKey to :class:`Account`. The account being billed.
    :param user: ForeignKey to :class:`django.contrib.auth.models.User`. The user associated with the record.
    :param provider: String. The LLM provider (e.g., OpenAI).
    :param date: Date. The billing date for the record.
    :param charge_type: String. The type of charge (e.g., completion, plugin, tool).
    :param prompt_tokens: Integer. Number of prompt tokens used.
    :param completion_tokens: Integer. Number of completion tokens used.
    :param total_tokens: Integer. Total tokens used.

    **Example usage**::

        record = DailyBillingRecord.objects.create(
            account=account,
            user=user,
            provider="openai",
            date=date.today(),
            charge_type="completion",
            prompt_tokens=100,
            completion_tokens=200,
            total_tokens=300
        )

    .. seealso::

        :class:`Charge`, :class:`Account`
    """

    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="daily_billing_records")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="daily_billing_records")
    provider = models.CharField(
        max_length=255,
        choices=PROVIDERS,
    )
    date = models.DateField()
    charge_type = models.CharField(
        max_length=20,
        choices=CHARGE_TYPES,
    )
    prompt_tokens = models.IntegerField()
    completion_tokens = models.IntegerField()
    total_tokens = models.IntegerField()

    class Meta:
        unique_together = ("account", "user", "provider", "date")

    def __str__(self):
        return (
            f"{self.account.account_number} - {self.user.email} - {self.provider} - {self.date} - {self.total_tokens}"
        )


class Secret(TimestampedModel):
    """
    Secret model for securely storing and managing sensitive account-level information.

    Usage::

        # Encrypt a secret value before saving it
        secret_value = Secret.encrypt("my-sensitive-api-key")

        # Create a new secret
        secret = Secret(
            name="API Key",
            user_profile=user_profile_instance,
            encrypted_value=secret_value
        )
        secret.save()

        # Retrieve and decrypt a secret
        retrieved_secret = Secret.objects.get(id=secret.id)
        decrypted_value = retrieved_secret.get_secret()

    .. note::

        The `value` field is transient and only used during runtime. It is not stored in the database
        to ensure sensitive data is only saved in encrypted form.
    """

    class Meta:
        verbose_name = "Secret"
        verbose_name_plural = "Secrets"
        unique_together = ("user_profile", "name")

    last_accessed = models.DateTimeField(
        blank=True, editable=False, null=True, help_text="Timestamp of the last time the secret was accessed."
    )
    expires_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Timestamp indicating when the secret expires. If null, the secret does not expire.",
    )
    user_profile = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="secrets",
        help_text="Reference to the UserProfile associated with this secret.",
    )
    name = models.CharField(
        max_length=255, help_text="Name of the secret in camelCase, e.g., 'apiKey', no special characters."
    )
    description = models.TextField(blank=True, null=True, help_text="Optional description of the secret.")
    encrypted_value = models.BinaryField(help_text="Read-only encrypted representation of the secret's value.")

    def save(self, *args, **kwargs):
        """
        Encrypt and persist the secret value for this instance.

        This method encrypts the transient `value` field and stores the result in `encrypted_value`.
        It validates that both `name` and `encrypted_value` are present and that the value is a string.

        :param args: Positional arguments passed to the parent save method.
        :param kwargs: Keyword arguments passed to the parent save method.

        :raises: :class:`SmarterValueError` if `name` or `encrypted_value` is missing.

        .. important::

            Only the encrypted value is stored in the database; the plaintext value is never persisted.


        .. note::

            Emits a signal on creation or edit for audit and notification purposes.

        **Example usage**::

            secret = Secret(
                name="apiKey",
                user_profile=user_profile,
                encrypted_value=Secret.encrypt("my-api-key")
            )
            secret.save()

        """
        is_new = self.pk is None
        if not self.name or not self.encrypted_value:
            raise SmarterValueError(
                f"Name and encrypted_value are required fields. Got name: {self.name}, encrypted_value: {self.encrypted_value}"
            )
        super().save(*args, **kwargs)
        if is_new:
            secret_created.send(sender=self.__class__, secret=self)
        else:
            secret_edited.send(sender=self.__class__, secret=self)

    def get_secret(self, update_last_accessed=True) -> Optional[str]:
        """
        Decrypt and return the original secret value.

        Optionally updates the `last_accessed` timestamp and emits an access signal. If decryption fails, raises a :class:`SmarterValueError`.

        :param update_last_accessed: Boolean. If True, updates the `last_accessed` timestamp. Defaults to True.
        :returns: Optional[str]
            The decrypted secret value, or None if not set.

        :raises: :class:`SmarterValueError` if decryption fails.

        .. note::

            Accessing the secret updates its last accessed time for audit purposes.

        **Example usage**::

            secret_value = secret.get_secret(update_last_accessed=True)

        """
        try:
            if update_last_accessed:
                self.last_accessed = timezone.now()
                self.save(update_fields=["last_accessed"])
            secret_accessed.send(sender=self.__class__, secret=self, user_profile=self.user_profile)
            fernet = self.get_fernet()
            if self.encrypted_value:
                return fernet.decrypt(self.encrypted_value).decode()
            return None
        except Exception as e:
            raise SmarterValueError(f"Failed to decrypt the secret: {str(e)}") from e

    def is_expired(self) -> bool:
        """
        Determine whether the secret has expired based on its `expires_at` timestamp.

        :returns: bool
            True if the current time is past the expiration timestamp; False otherwise.

        .. note::

            If `expires_at` is not set, the secret is considered non-expiring.

        **Example usage**::

            if secret.is_expired():
                print("This secret is no longer valid.")

        """
        if not self.expires_at:
            return False
        expiration = timezone.make_aware(self.expires_at) if timezone.is_naive(self.expires_at) else self.expires_at
        return timezone.now() > expiration

    def has_permissions(self, request: WSGIRequest) -> bool:
        """
        Check if the authenticated user in the given request has permission to manage this secret.

        :param request: :class:`django.core.handlers.wsgi.WSGIRequest`
            The HTTP request containing the user to check.

        :returns: bool

            True if the user is authenticated and is either staff or superuser; False otherwise.

        .. attention::

            Only users with staff or superuser status are permitted to manage secrets.

        .. warning::

            If the request does not contain a valid user, or the user lacks required privileges, permission is denied.

        **Example usage**::

            if secret.has_permissions(request):
                # Allow secret management
                pass

        .. seealso::

            :meth:`get_resolved_user` -- Resolves the user from the request.
        """
        if not hasattr(request, "user"):
            return False
        user = get_resolved_user(request.user)
        if not isinstance(user, User):
            return False
        if not hasattr(user, "is_authenticated") or not user.is_authenticated:
            return False
        if not hasattr(user, "is_staff") or not hasattr(user, "is_superuser"):
            return False
        return user.is_staff or user.is_superuser

    def __str__(self):
        return str(self.name) or "no name" + " - " + str(self.user_profile) or "no user profile"

    @classmethod
    def encrypt(cls, value: str) -> bytes:
        """
        Encrypt a string value using Fernet symmetric encryption.

        :param value: str
            The plaintext string to encrypt.

        :returns: bytes
            The encrypted value as bytes.

        :raises: :class:`SmarterValueError`
            If the input value is not a non-empty string.

        .. attention::

            The original plaintext value is not stored or persisted; only the encrypted bytes are returned.

        .. caution::

            Always clear or avoid storing the plaintext value after encryption to prevent accidental exposure.

        **Example usage**::

            encrypted = Secret.encrypt("my-api-key")
            # Store `encrypted` in the database, never the plaintext

        .. seealso::

            :meth:`get_fernet` -- Returns the Fernet encryption object.

        """
        if not value or not isinstance(value, str):
            raise SmarterValueError("Value must be a non-empty string")

        fernet = cls.get_fernet()
        retval = fernet.encrypt(value.encode())
        return retval

    @classmethod
    def get_fernet(cls) -> Fernet:
        """
        Return a Fernet encryption object for secure value encryption and decryption.

        :returns: :class:`cryptography.fernet.Fernet`
            A Fernet instance initialized with the configured encryption key.

        :raises: :class:`SmarterConfigurationError`
            If the encryption key is missing from settings.

        .. important::

            The encryption key must be set in ``smarter.common.conf.settings.fernet_encryption_key``.
            Without a valid key, secrets cannot be encrypted or decrypted.

        **Example usage**::

            fernet = Secret.get_fernet()
            encrypted = fernet.encrypt(b"my-value")
            decrypted = fernet.decrypt(encrypted)

        .. seealso::

            :meth:`encrypt` -- Uses the Fernet object to encrypt values.

        """
        encryption_key = smarter_settings.fernet_encryption_key
        if not encryption_key:
            raise SmarterConfigurationError(
                "Encryption key not found in settings. Please set smarter.common.conf.settings.fernet_encryption_key"
            )
        fernet = Fernet(encryption_key)
        return fernet
