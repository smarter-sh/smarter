# pylint: disable=C0302
"""Account DailyBillingRecord model."""

# pylint: disable=missing-class-docstring

import logging

# django stuff
from django.conf import settings
from django.db import models

# our stuff
from smarter.lib.django import waffle
from smarter.lib.django.models import TimestampedModel
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

from .account import Account
from .charge import CHARGE_TYPES, PROVIDERS


# pylint: disable=W0613
def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.ACCOUNT_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


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


__all__ = ["DailyBillingRecord"]
