# pylint: disable=C0302
"""Account PaymentMethod model."""

# pylint: disable=missing-class-docstring

import logging

# django stuff
from django.db import models

# our stuff
from smarter.lib.django import waffle
from smarter.lib.django.models import TimestampedModel
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

from .account import Account


# pylint: disable=W0613
def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.ACCOUNT_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class PaymentMethod(TimestampedModel):
    """
    Payment method model.

    .. attention::

        This model is not in use.
    """

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


__all__ = ["PaymentMethod"]
