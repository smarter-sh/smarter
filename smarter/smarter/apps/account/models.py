# -*- coding: utf-8 -*-
"""Account models."""
from django.conf import settings
from django.db import models

# our stuff
from smarter.apps.common.model_utils import TimestampedModel


User = settings.AUTH_USER_MODEL


class AccountModel(TimestampedModel):
    """Account model."""

    company_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20)
    address = models.CharField(max_length=255)


class UserProfile(TimestampedModel):
    """User profile model."""

    # Add more fields here as needed
    user = models.OneToOneField(User, unique=True, db_index=True, related_name="user_profile", on_delete=models.CASCADE)
    account = models.ForeignKey(AccountModel, on_delete=models.CASCADE, related_name="users")


class PaymentMethodModel(TimestampedModel):
    """Payment method model."""

    account = models.ForeignKey(AccountModel, on_delete=models.CASCADE, related_name="payment_methods")
    stripe_id = models.CharField(max_length=255)
    card_type = models.CharField(max_length=255)
    card_last_4 = models.CharField(max_length=4)
    card_exp_month = models.CharField(max_length=2)
    card_exp_year = models.CharField(max_length=4)
    is_default = models.BooleanField(default=False)
