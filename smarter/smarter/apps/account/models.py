"""Account models."""

# pylint: disable=missing-class-docstring

import logging
import os
import random

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models
from django.template.loader import render_to_string

from smarter.common.conf import settings as smarter_settings

# our stuff
from smarter.common.exceptions import SmarterValueError
from smarter.common.helpers.email_helpers import email_helper
from smarter.lib.django.model_helpers import TimestampedModel
from smarter.lib.django.user import User, UserType
from smarter.lib.django.validators import SmarterValidator

from .signals import new_charge_created, new_user_created


HERE = os.path.abspath(os.path.dirname(__file__))
logger = logging.getLogger(__name__)

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


class Account(TimestampedModel):
    """Account model."""

    account_number_format = RegexValidator(
        regex=SmarterValidator.VALID_ACCOUNT_NUMBER_PATTERN,
        message="Account number must be entered in the format: '9999-9999-9999'.",
    )

    account_number = models.CharField(
        validators=[account_number_format], max_length=255, unique=True, default="9999-9999-9999", blank=True, null=True
    )
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

    @classmethod
    def randomized_account_number(cls):
        """
        Generate a random account number of the format ####-####-####.
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
        if self.account_number == "9999-9999-9999":
            self.account_number = self.randomized_account_number()
        SmarterValidator.validate_account_number(self.account_number)
        super().save(*args, **kwargs)

    @classmethod
    def get_by_account_number(cls, account_number):
        try:
            return cls.objects.get(account_number=account_number)
        except cls.DoesNotExist:
            return None

    # pylint: disable=missing-class-docstring
    class Meta:
        verbose_name = "Account"
        verbose_name_plural = "Accounts"

    def __str__(self):
        return str(self.company_name)


class AccountContact(TimestampedModel):
    """
    Account contact model.

    This model is used to store contact information for an account. The User model obviously has an email field, but
    this model allows us to detach email list management from user management. This is useful for cases where we need
    to send emails to a list of contacts who are not registered Smarter users, or, in cases where an account user
    does not want to receive Smarter system emails.
    """

    # pylint: disable=missing-class-docstring
    class Meta:
        verbose_name = "Account Contact"
        verbose_name_plural = "Account Contacts"

    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="contacts")
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True, null=True)
    is_primary = models.BooleanField(default=False)
    is_test = models.BooleanField(default=False)
    welcomed = models.BooleanField(default=False)

    def send_email(self, subject: str, body: str, html: bool = False, from_email: str = None):

        email_helper.send_email(
            subject=subject, to=self.email, body=body, html=html, from_email=from_email, quiet=self.is_test
        )

    def send_welcome_email(self) -> None:
        """Send a welcome email to the contact."""
        context = welcome_email_context(first_name=self.first_name)
        html_template = render_to_string("accounts/email/welcome.html", context)

        subject = "Welcome to Smarter!"
        body = html_template
        self.send_email(subject=subject, body=body, html=True)

    @classmethod
    def get_primary_contact(cls, account: Account) -> "AccountContact":
        """Get the primary contact for an account."""
        return cls.objects.filter(account=account, is_primary=True).first()

    # pylint: disable=too-many-arguments
    @classmethod
    def send_email_to_account(
        cls, account: Account, subject: str, body: str, html: bool = False, from_email: str = None
    ) -> None:
        """Send an email to all contacts of an account."""
        contacts = cls.objects.filter(account=account)
        for contact in contacts:
            contact.send_email(subject=subject, body=body, html=html, from_email=from_email)

    # pylint: disable=too-many-arguments
    @classmethod
    def send_email_to_primary_contact(
        cls, account: Account, subject: str, body: str, html: bool = False, from_email: str = None
    ) -> None:
        """Send an email to all contacts of an account."""
        contact = cls.get_primary_contact(account)
        contact.send_email(subject=subject, body=body, html=html, from_email=from_email)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_primary:
            # ensure that only one primary contact exists
            AccountContact.objects.filter(account=self.account, is_primary=True).update(is_primary=False)
        if not self.welcomed:
            self.send_welcome_email()
            self.welcomed = True
            self.save()

    def __str__(self):
        return self.first_name + " " + self.last_name


class UserProfile(TimestampedModel):
    """
    User profile model.

    This model creates a relationship between a Django User and an Account, making Account a higher-level entity where we can
    concentrate billing, identity and Smarter resource ownership.
    """

    # pylint: disable=missing-class-docstring
    class Meta:
        unique_together = (
            "user",
            "account",
        )

    # Add more fields here as needed
    user = models.OneToOneField(User, unique=True, db_index=True, related_name="user_profile", on_delete=models.CASCADE)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="users")
    is_test = models.BooleanField(default=False)

    def add_to_account_contacts(self, is_primary: bool = False):
        """Add the user to the account contact list."""
        account_contact, _ = AccountContact.objects.get_or_create(
            account=self.account, email=self.user.email, is_test=self.is_test
        )
        if account_contact.is_primary != is_primary:
            account_contact.is_primary = is_primary
            account_contact.save()

    def save(self, *args, **kwargs):
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
    def admin_for_account(cls, account: Account) -> UserType:
        """Return the designated user for the account."""
        admins = cls.objects.filter(account=account, user__is_staff=True).order_by("user__id")
        if admins.exists():
            return admins.first().user

        logger.error("No admin found for account %s", account)

        users = cls.objects.filter(account=account).order_by("user__id")
        if users.exists():
            user = users.first().user
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
        return self.card_type + " " + self.card_last_4


class LLMPrices(TimestampedModel):
    """
    LLM Price model for account billing.
    Stores markup factors to be used proportionately
    across the universe of billed entities.

    example:
    Provider A bills us $x during a billing period.
    In turn, we bill each Account $x * markup_factor * their proportional
    usage of provider A.
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
    """Charge model for periodic account billing."""

    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="charge", null=False, blank=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="charge", null=False, blank=False)
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
    """Daily billing record model for aggregated charges."""

    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="daily_billing_records")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="daily_billing_records")
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
