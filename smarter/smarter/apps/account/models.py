"""Account models."""

import logging
import os
import random
import uuid
from datetime import datetime, timedelta

from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone
from knox.models import AuthToken, AuthTokenManager

# our stuff
from smarter.common.exceptions import SmarterValueError
from smarter.common.helpers.email_helpers import email_helper
from smarter.lib.django.model_helpers import TimestampedModel
from smarter.lib.django.user import User, UserType
from smarter.lib.django.validators import SmarterValidator

from .const import CHARGE_TYPE_PLUGIN, CHARGE_TYPE_PROMPT_COMPLETION, CHARGE_TYPE_TOOL
from .signals import new_charge_created, new_user_created


HERE = os.path.abspath(os.path.dirname(__file__))
logger = logging.getLogger(__name__)


class Account(TimestampedModel):
    """Account model."""

    account_number_format = RegexValidator(
        regex=SmarterValidator.VALID_ACCOUNT_NUMBER_PATTERN,
        message="Account number must be entered in the format: '9999-9999-9999'.",
    )

    account_number = models.CharField(
        validators=[account_number_format], max_length=255, unique=True, default="default_value"
    )
    company_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=50)
    address1 = models.CharField(max_length=255)
    address2 = models.CharField(max_length=255)
    city = models.CharField(max_length=255)
    state = models.CharField(max_length=255)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=255)
    language = models.CharField(max_length=255)
    timezone = models.CharField(max_length=255)
    currency = models.CharField(max_length=255)

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
        if self.account_number == "default_value":
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
        template_path = os.path.join(HERE, "./assets/html/welcome.html")
        with open(template_path, encoding="utf-8") as welcome_email_template:
            html_template = welcome_email_template.read()

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


class Charge(TimestampedModel):
    """Charge model for periodic account billing."""

    CHARGE_TYPES = [
        (CHARGE_TYPE_PROMPT_COMPLETION, "Prompt Completion"),
        (CHARGE_TYPE_PLUGIN, "Plugin"),
        (CHARGE_TYPE_TOOL, "Tool"),
    ]

    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="charge")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="charge")
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

        if self.user is None or self.account is None:
            raise SmarterValueError("User and Account cannot be null")

        super().save(*args, **kwargs)
        if is_new:
            logger.debug(
                "New user charge created for %s %s. Sending signal.", self.account.company_name, self.user.email
            )
            new_charge_created.send(sender=self.__class__, charge=self)

    def __str__(self):
        return str(self.id) + " - " + self.model + " - " + self.total_tokens


###############################################################################
# API Key Management
###############################################################################
class SmarterAuthTokenManager(AuthTokenManager):
    """API Key manager."""

    # pylint: disable=too-many-arguments
    def create(self, user, expiry=None, description: str = None, account=None, is_active: bool = True, **kwargs):
        auth_token, token = super().create(user, expiry=expiry, **kwargs)
        if not account:
            account = UserProfile.objects.get(user=user).account
        auth_token.account = account
        auth_token.description = description
        auth_token.is_active = is_active
        auth_token.save()
        return auth_token, token


class SmarterAuthToken(AuthToken, TimestampedModel):
    """API Key model."""

    objects = SmarterAuthTokenManager()

    # pylint: disable=C0115
    class Meta:
        verbose_name = "API Key"
        verbose_name_plural = "API Keys"

    key_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="api_keys", blank=True, null=True)
    description = models.CharField(max_length=255, blank=True, null=True)
    last_used_at = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    @property
    def identifier(self):
        return "******" + str(self.digest)[:8]

    def save(self, *args, **kwargs):
        if not self.user.is_staff:
            raise SmarterValueError("API Keys can only be created for staff users.")
        user_profile = UserProfile.objects.get(user=self.user)
        self.account = user_profile.account
        if self.created is None:
            self.created = timezone.now()
        super().save(*args, **kwargs)

    def has_permissions(self, user) -> bool:
        """Determine if the authenticated user has permissions to manage this key."""
        account = UserProfile.objects.get(user=user).account
        return user.is_staff and account == self.account

    def activate(self):
        """Activate the API key."""
        self.is_active = True
        self.save()

    def deactivate(self):
        """Deactivate the API key."""
        self.is_active = False
        self.save()

    def toggle_active(self):
        """Toggle the active status of the API key."""
        self.is_active = not self.is_active
        self.save()

    def accessed(self):
        """Update the last used time."""
        if self.last_used_at is None or (datetime.now() - self.last_used_at) > timedelta(minutes=5):
            self.last_used_at = datetime.now()
            self.save()

    def __str__(self):
        return self.identifier
