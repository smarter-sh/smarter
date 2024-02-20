# -*- coding: utf-8 -*-
"""Account models."""
import logging
import random

from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from django.db import models

# our stuff
from smarter.apps.common.model_utils import TimestampedModel

from .signals import new_user_created


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
    address = models.CharField(max_length=255)

    def save(self, *args, **kwargs):
        if self.account_number == "default_value":
            prefix = "1860-6722-"
            prev_instances = Account.objects.all().order_by("-id")
            while True:
                if prev_instances.exists():
                    last_instance = prev_instances.first()
                    last_num = int(last_instance.account_number.split("-")[-1])
                    new_account_number = prefix + str(last_num + 1).zfill(4)
                else:
                    s = "".join(random.sample("0001", 4))
                    new_account_number = prefix + s

                if not Account.objects.filter(account_number=new_account_number).exists():
                    break

            self.account_number = new_account_number
        super().save(*args, **kwargs)

    # pylint: disable=missing-class-docstring
    class Meta:
        verbose_name = "Smarter Account"
        verbose_name_plural = "Smarter Account"

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
