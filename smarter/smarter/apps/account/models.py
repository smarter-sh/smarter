# -*- coding: utf-8 -*-
"""Account models."""
from django.contrib.auth import get_user_model
from django.db import models

# our stuff
from smarter.apps.common.model_utils import TimestampedModel


User = get_user_model()


class Account(TimestampedModel):
    """Account model."""

    company_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20)
    address = models.CharField(max_length=255)

    # pylint: disable=missing-class-docstring
    class Meta:
        verbose_name = "Smarter Account"
        verbose_name_plural = "Smarter Account"

    def __str__(self):
        return str(self.company_name)


class UserProfile(TimestampedModel):
    """User profile model."""

    # Add more fields here as needed
    user = models.OneToOneField(User, unique=True, db_index=True, related_name="user_profile", on_delete=models.CASCADE)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="users")

    def save(self, *args, **kwargs):
        if self.user is None or self.account is None:
            raise ValueError("User and Account cannot be null")
        super().save(*args, **kwargs)

    def __str__(self):
        return str(self.account.company_name) + "-" + str(self.user.email or self.user.username)


class PaymentMethodModel(TimestampedModel):
    """Payment method model."""

    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="payment_methods")
    stripe_id = models.CharField(max_length=255)
    card_type = models.CharField(max_length=255)
    card_last_4 = models.CharField(max_length=4)
    card_exp_month = models.CharField(max_length=2)
    card_exp_year = models.CharField(max_length=4)
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return self.card_type + " " + self.card_last_4
