"""
Account Charge Model and Constants
==================================

This module defines the :class:`Charge` model for tracking periodic billing events associated with user profiles.
It also provides constants for charge types and providers, and emits a signal when a new charge is created.

Classes & Constants
-------------------

- :class:`Charge`: Represents a single billing event for a user profile, including provider, charge type, token usage, and references.
- :data:`ChargeTypes`: List of available charge types (completion, plugin, tool, compute).
- :class:`Actuals`, :func:`get_actuals`: what a resource has actually spent in a period of time.

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

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from django.db import models, transaction
from django.db.models import BigIntegerField, Count, ExpressionWrapper, F, Max, Sum
from django.db.models.functions import (
    ExtractDay,
    ExtractHour,
    ExtractMonth,
    ExtractYear,
)
from django.utils import timezone

from smarter.apps.account.signals import new_charge_created
from smarter.lib import logging
from smarter.lib.django.models import TimestampedModel
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.manifest.enum import SmarterEnumAbstract

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.ACCOUNT_LOGGING])


class ChargeTypes(SmarterEnumAbstract):
    """
    Charge types enumeration.

    This enumeration defines the different types of charges that can be associated with user profiles.
    Each charge type corresponds to a specific billing event, such as prompt completion, plugin usage, or tool usage.

    The charge types are:

    - ``PROMPT_COMPLETION``: a prompt completion charge.
    - ``PLUGIN``: a plugin charge.
    - ``TOOL``: a tool charge.
    - ``COMPUTE``: an hour of infrastructure, e.g. the nodes of an LLMHostCompute. It has no tokens.
    """

    PROMPT_COMPLETION = "completion"
    PLUGIN = "plugin"
    TOOL = "tool"
    COMPUTE = "compute"


CHARGE_TYPES = [
    (ChargeTypes.PROMPT_COMPLETION.value, "Prompt Completion"),
    (ChargeTypes.PLUGIN.value, "Plugin"),
    (ChargeTypes.TOOL.value, "Tool"),
    (ChargeTypes.COMPUTE.value, "Compute"),
]


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
        help_text="The TimestampedModel.resource_locator of the resource that this charge is associated with.",
    )
    charge_type = models.CharField(
        max_length=20,
        choices=CHARGE_TYPES,
        default=ChargeTypes.PROMPT_COMPLETION.value,
    )
    prompt_tokens = models.IntegerField()
    completion_tokens = models.IntegerField()
    total_tokens = models.IntegerField()
    total_cost = models.DecimalField(max_digits=18, decimal_places=8, default=Decimal("0"))

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


class AggregatedCharges(TimestampedModel):
    """
    AggregatedCharges model for tracking aggregated account billing events.

    Represents aggregated billing data for a specific time period.

    :param year: Integer. The year of the aggregated data.
    :param month: Integer. The month of the aggregated data.
    :param day: Integer. The day of the aggregated data.
    :param hour: Integer. The hour of the aggregated data.
    """

    # pylint: disable=C0115
    class Meta:
        verbose_name = "Aggregated Charges"
        verbose_name_plural = "Aggregated Charges"

    year = models.SmallIntegerField()
    month = models.SmallIntegerField()
    day = models.SmallIntegerField()
    hour = models.SmallIntegerField()
    resource_locator = models.CharField(
        max_length=255,
        db_index=True,
        help_text="The TimestampedModel.resource_locator of the resource that this charge is associated with.",
    )
    charge_type = models.CharField(
        max_length=20,
        choices=CHARGE_TYPES,
        default=ChargeTypes.PROMPT_COMPLETION.value,
    )
    records = models.IntegerField()
    prompt_tokens = models.IntegerField()
    completion_tokens = models.IntegerField()
    total_tokens = models.IntegerField()
    total_cost = models.DecimalField(max_digits=18, decimal_places=5, default=Decimal("0"))


@transaction.atomic
def aggregate_charges() -> int:
    """
    Aggregates charges and creates corresponding AggregatedCharges entries.

    Runs hourly from Celery Beat.
    """

    def aggregate_open_charges():
        """Aggregates open charges and creates corresponding AggregatedCharges entries."""
        # only the charges that exist now. Charges that Celery workers create while this runs
        # are aggregated next time, rather than deleted without having been aggregated.
        last_id = Charge.objects.aggregate(last_id=Max("id"))["last_id"]
        if last_id is None:
            return 0
        charges = Charge.objects.filter(id__lte=last_id)

        aggregates = (
            charges.annotate(
                year=ExtractYear("created_at"),
                month=ExtractMonth("created_at"),
                day=ExtractDay("created_at"),
                hour=ExtractHour("created_at"),
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
                records=Count("id"),
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
                    records=row["records"],
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

    def aggregate_month_end_charges():
        """
        Aggregates charges from the previous month and creates corresponding AggregatedCharges entries.

        Ensures that all charges from the previous month are captured and stored in
        the AggregatedCharges model for reporting and analysis, rolled up to the
        year, month, and last day of the month.
        """
        start_of_this_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_of_last_month = start_of_this_month - timedelta(microseconds=1)
        start_of_last_month = end_of_last_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        aggregated_charges = AggregatedCharges.objects.filter(
            created_at__gte=start_of_last_month, created_at__lt=end_of_last_month
        )

        aggregates = (
            aggregated_charges.annotate(
                created_year=ExtractYear("created_at"),
                created_month=ExtractMonth("created_at"),
                created_day=ExtractDay("created_at"),
            )
            .values("resource_locator", "charge_type", "created_year", "created_month", "created_day")
            .annotate(
                records=Count("id"),
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
                    records=row["records"],
                    prompt_tokens=row["prompt_tokens"],
                    completion_tokens=row["completion_tokens"],
                    total_tokens=row["total_tokens"],
                    total_cost=row["total_cost"],
                    year=row["created_year"],
                    month=row["created_month"],
                    day=row["created_day"],
                    hour=0,
                )
                for row in aggregates
            ]
        )
        aggregated_charges.delete()

    retval = aggregate_open_charges()
    aggregate_month_end_charges()
    return retval


def _hour_key(when: datetime) -> int:
    """The year, month, day and hour of a datetime as one sortable integer, e.g. 2026100113."""
    when = timezone.localtime(when)
    return when.year * 1000000 + when.month * 10000 + when.day * 100 + when.hour


@dataclass
class Actuals:
    """What a resource has actually spent in a period of time."""

    records: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    total_cost: Decimal = Decimal("0")

    def add(self, row: dict) -> None:
        """Add an aggregate row of Charge or AggregatedCharges sums."""
        self.records += row.get("records") or 0
        self.prompt_tokens += row.get("prompt_tokens") or 0
        self.completion_tokens += row.get("completion_tokens") or 0
        self.total_tokens += row.get("total_tokens") or 0
        self.total_cost += row.get("total_cost") or Decimal("0")


def get_actuals(resource_locator: str, start: Optional[datetime] = None, end: Optional[datetime] = None) -> Actuals:
    """
    What a resource has spent from start up to end, from its charges whether aggregated or not.

    AggregatedCharges have the precision of an hour, so an hour is counted if it begins at or
    after start, and before end. Charges of a previous month are rolled up into days.

    :param resource_locator: The TimestampedModel.record_locator of the resource.
    :param start: The beginning of the period. None means the beginning of time.
    :param end: The end of the period, exclusive. None means now.
    """
    end = end or timezone.now()
    retval = Actuals()
    sums = {
        "records": Count("id"),
        "prompt_tokens": Sum("prompt_tokens"),
        "completion_tokens": Sum("completion_tokens"),
        "total_tokens": Sum("total_tokens"),
        "total_cost": Sum("total_cost"),
    }

    charges = Charge.objects.filter(resource_locator=resource_locator, created_at__lt=end)
    if start:
        charges = charges.filter(created_at__gte=start)
    retval.add(charges.aggregate(**sums))

    aggregated = AggregatedCharges.objects.filter(resource_locator=resource_locator).annotate(
        hour_key=ExpressionWrapper(
            F("year") * 1000000 + F("month") * 10000 + F("day") * 100 + F("hour"), output_field=BigIntegerField()
        )
    )
    aggregated = aggregated.filter(hour_key__lte=_hour_key(end - timedelta(microseconds=1)))
    if start:
        aggregated = aggregated.filter(hour_key__gte=_hour_key(start))
    sums["records"] = Sum("records")
    retval.add(aggregated.aggregate(**sums))
    return retval


__all__ = [
    "Actuals",
    "Charge",
    "AggregatedCharges",
    "ChargeTypes",
    "get_actuals",
]
