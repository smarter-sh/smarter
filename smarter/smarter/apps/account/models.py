# -*- coding: utf-8 -*-
"""Account models."""
import logging
import random
import uuid
from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone
from knox.auth import TokenAuthentication
from knox.models import AuthToken, AuthTokenManager
from rest_framework.exceptions import AuthenticationFailed

# our stuff
from smarter.common.model_utils import TimestampedModel

from .const import CHARGE_TYPE_PLUGIN, CHARGE_TYPE_PROMPT_COMPLETION, CHARGE_TYPE_TOOL
from .signals import new_charge_created, new_user_created


User = get_user_model()
logger = logging.getLogger(__name__)


class Account(TimestampedModel):
    """Account model."""

    account_number_format = RegexValidator(
        regex=r"^\d{4}-\d{4}-\d{4}", message="Account number must be entered in the format: '9999-9999-9999'."
    )

    account_number = models.CharField(
        validators=[account_number_format], max_length=255, unique=True, default="default_value"
    )
    company_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20)
    address1 = models.CharField(max_length=255)
    address2 = models.CharField(max_length=255)
    city = models.CharField(max_length=255)
    state = models.CharField(max_length=255)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=255)
    language = models.CharField(max_length=255)
    timezone = models.CharField(max_length=255)
    currency = models.CharField(max_length=255)

    def randomized_account_number(self):
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
        while Account.objects.filter(account_number=account_number).exists():
            account_number = account_number_generator()

        return account_number

    def save(self, *args, **kwargs):
        if self.account_number == "default_value":
            self.account_number = self.randomized_account_number()
        super().save(*args, **kwargs)

    # pylint: disable=missing-class-docstring
    class Meta:
        verbose_name = "Account"
        verbose_name_plural = "Accounts"

    def __str__(self):
        return str(self.company_name)


class UserProfile(TimestampedModel):
    """User profile model."""

    # pylint: disable=missing-class-docstring
    class Meta:
        unique_together = (
            "user",
            "account",
        )

    # Add more fields here as needed
    user = models.OneToOneField(User, unique=True, db_index=True, related_name="user_profile", on_delete=models.CASCADE)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="users")

    def save(self, *args, **kwargs):
        is_new = self.pk is None

        if self.user is None or self.account is None:
            raise ValueError("User and Account cannot be null")
        super().save(*args, **kwargs)
        if is_new:
            logger.debug(
                "New user profile created for %s %s. Sending signal.", self.account.company_name, self.user.email
            )
            new_user_created.send(sender=self.__class__, user_profile=self)

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


class APIKeyManager(AuthTokenManager):
    """API Key manager."""

    def create(self, user, expiry=None, description: str = None, is_active: bool = False, **kwargs):
        api_key, token = super().create(user, expiry=expiry, **kwargs)
        api_key.description = description
        api_key.is_active = is_active
        api_key.save()
        return api_key, token


class APIKey(AuthToken):
    """API Key model."""

    objects = APIKeyManager()

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
            raise ValueError("API Keys can only be created for staff users.")
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

    @classmethod
    def validate_token(cls, token_str: str) -> bool:
        """
        Validate a token by authenticating with Django using Knox's TokenAuthentication
        """
        try:
            token_bytes = token_str.encode("utf-8")
            TokenAuthentication().authenticate_credentials(token_bytes)
            return True
        except AuthenticationFailed:
            return False

    def __str__(self):
        return self.identifier


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
            raise ValueError("User and Account cannot be null")

        super().save(*args, **kwargs)
        if is_new:
            logger.debug(
                "New user charge created for %s %s. Sending signal.", self.account.company_name, self.user.email
            )
            new_charge_created.send(sender=self.__class__, charge=self)

    def __str__(self):
        return str(self.id) + " - " + self.model + " - " + self.total_tokens
