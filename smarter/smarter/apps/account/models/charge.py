"""
Account Charge Model and Constants
==================================

This module defines the :class:`Charge` model for tracking periodic billing events associated with user profiles.
It also provides constants for charge types and providers, and emits a signal when a new charge is created.

Classes & Constants
-------------------

- :class:`Charge`: Represents a single billing event for a user profile, including provider, charge type, token usage, and references.
- :data:`CHARGE_TYPES`: List of available charge types (completion, plugin, tool).
- :data:`CHARGE_TYPE_PROMPT_COMPLETION`, :data:`CHARGE_TYPE_PLUGIN`, :data:`CHARGE_TYPE_TOOL`: Charge type constants.

Key Features
------------

- Tracks provider, charge type, token usage, and references for each billing event.
- Emits a signal (`new_charge_created`) when a new charge is created for downstream processing.
- Integrates with Smarter logging and signal systems.

Example
-------

.. code-block:: python

    from smarter.apps.account.models import Charge

    charge = Charge.objects.create(
        charge_type="completion",
        prompt_tokens=100,
        completion_tokens=200,
        total_tokens=300,
    )
"""

# django stuff
from decimal import Decimal

from django.db import models, transaction
from django.db.models import Sum
from django.db.models.functions import (
    ExtractDay,
    ExtractHour,
    ExtractMonth,
    ExtractYear,
)

from smarter.apps.account.signals import new_charge_created

# our stuff
from smarter.lib import logging
from smarter.lib.django.models import TimestampedModel
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.ACCOUNT_LOGGING])


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


class Charge(TimestampedModel):
    """
    Charge model for tracking periodic account billing events.

    A signal is emitted when a new charge is created, enabling downstream billing and analytics workflows.

    Represents a single billing event for a resource.

    :param resource_locator: String. The TimestampedModel.resource_locator of the resource that this charge is associated with.
    :param charge_type: String. The type of charge (e.g., completion, plugin, tool).
    :param prompt_tokens: Integer. Number of prompt tokens used.
    :param completion_tokens: Integer. Number of completion tokens used.
    :param total_tokens: Integer. Total tokens used.

    **Example usage**::

        charge = Charge.objects.create(
            resource_locator=resource_locator,
            charge_type="completion",
            prompt_tokens=100,
            completion_tokens=200,
            total_tokens=300,
        )
    """

    resource_locator = models.CharField(
        max_length=255,
        db_index=True,
        help_text="The TimestampedModel.resource_locator of the resource that this lock is associated with.",
    )
    charge_type = models.CharField(
        max_length=20,
        choices=CHARGE_TYPES,
        default=CHARGE_TYPE_PROMPT_COMPLETION,
    )
    prompt_tokens = models.IntegerField()
    completion_tokens = models.IntegerField()
    total_tokens = models.IntegerField()
    total_cost = models.DecimalField(max_digits=10, decimal_places=8, default=Decimal("0"))

    def save(self, *args, **kwargs):
        is_new = self.pk is None

        super().save(*args, **kwargs)
        if is_new:
            logger.debug(
                "%s.save() New user charge created for %s.",
                logging.formatted_text(__name__ + ".Charge()"),
                self.resource_locator,
            )
            new_charge_created.send(sender=self.__class__, charge=self)

    def __str__(self):
        return f"""{self.resource_locator} - {self.charge_type} - {self.total_tokens} - {self.total_cost}"""


class AggregatedCharges(Charge):
    """
    AggregatedCharges model for tracking aggregated account billing events.

    Represents aggregated billing data for a specific time period.

    :param year: Integer. The year of the aggregated data.
    :param month: Integer. The month of the aggregated data.
    :param day: Integer. The day of the aggregated data.
    :param hour: Integer. The hour of the aggregated data.
    """

    year = models.SmallIntegerField()
    month = models.SmallIntegerField()
    day = models.SmallIntegerField()
    hour = models.SmallIntegerField()


@transaction.atomic
def aggregate_charges() -> int:
    charges = Charge.objects.all()

    aggregates = (
        charges.annotate(
            year=ExtractYear("created"),
            month=ExtractMonth("created"),
            day=ExtractDay("created"),
            hour=ExtractHour("created"),
        )
        .values(
            "resource_locator",
            "charge_type",
            "year",
            "month",
            "day",
            "hour",
        )
        .annotate(
            prompt_tokens=Sum("prompt_tokens"),
            completion_tokens=Sum("completion_tokens"),
            total_tokens=Sum("total_tokens"),
            total_cost=Sum("total_cost"),
        )
    )

    AggregatedCharges.objects.bulk_create(
        [
            AggregatedCharges(
                resource_locator=row["resource_locator"],
                charge_type=row["charge_type"],
                prompt_tokens=row["prompt_tokens"],
                completion_tokens=row["completion_tokens"],
                total_tokens=row["total_tokens"],
                total_cost=row["total_cost"],
                year=row["year"],
                month=row["month"],
                day=row["day"],
                hour=row["hour"],
            )
            for row in aggregates
        ]
    )

    retval = charges.count()
    charges.delete()
    return retval


__all__ = [
    "Charge",
    "AggregatedCharges",
    "CHARGE_TYPES",
    "CHARGE_TYPE_PROMPT_COMPLETION",
    "CHARGE_TYPE_PLUGIN",
    "CHARGE_TYPE_TOOL",
]
