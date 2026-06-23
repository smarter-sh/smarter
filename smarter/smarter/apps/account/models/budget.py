"""
Budget model.

Assumed to be always been under the control of
superusers, so no ownership nor permissions are implemented.
"""

from django.db import models

from smarter.lib.cache import cache_results
from smarter.lib.django.models import MetaDataModel, TimestampedModel


class Budget(MetaDataModel):
    """
    A budget is a catalogue of spending limits that can be enforced on a resource, either.

    in a given period of time, or over the life of the resource.

    A billing period is 1 month.

    examples:

        - a per-User budget of $10 per month, with a total limit of $100 for the life of the student.
        - a per-Account budget of $100 per month, with a total limit of $1,000 for the life of the account.
        - a custom project budget of $1000 per month, with a total limit of $10,000 for the life of the project.
        - a customer project budget of $10,000 over the life of the project, with no monthly limit.
    """

    duration = models.PositiveIntegerField(
        default=0,
        help_text="The duration of the budget in billing periods. 0 means no limit.",
    )
    periodic_limit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text="The maximum cost that can be incurred in this budget in a billing period.",
    )
    absolute_limit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text="The maximum cost that can be incurred in this budget in total.",
    )


class ResourceConstraint(TimestampedModel):
    """
    A resource constraint that has been applied to a resource based upon a budget.

    .. note::

        resource_locator intentionally overrides the parent class's
        TimestampedModel.resource_locator field.
    """

    resource_locator = models.CharField(
        max_length=255,
        db_index=True,
        help_text="The TimestampedModel.resource_locator of the resource that this constraint is associated with.",
    )
    duration = models.PositiveIntegerField(
        default=0,
        help_text="The duration of the budget in billing periods. 0 means no limit.",
    )
    periodic_limit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text="The maximum cost that can be incurred in this budget in a billing period.",
    )
    absolute_limit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text="The maximum cost that can be incurred in this budget in total.",
    )


class ResourceLock(TimestampedModel):
    """
    A mechanism to prevent spending on a resource when its.

    budget constraint has been exceeded. The existence of a resource lock indicates that
    the resource is locked and cannot be used until the lock is removed.
    """

    resource_constraint = models.ForeignKey(
        ResourceConstraint,
        on_delete=models.CASCADE,
        related_name="locks",
        help_text="The resource constraint that this lock is associated with.",
    )
    resource_locator = models.CharField(
        max_length=255,
        db_index=True,
        help_text="The TimestampedModel.resource_locator of the resource that this lock is associated with.",
    )
    expiration_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="The date and time when this lock will expire. If null, the lock will not expire until it is manually removed.",
    )


# pylint: disable=W0613
def charge_authorization(resource_locator: list[str]) -> bool:
    """
    Check if a charge is authorized for the given list of resource locators.

    :param resource_locator: A list of resource locators that may be used by the custom implementation.
    :return: True if the charge is authorized, False otherwise.
    """

    @cache_results()
    def _check_authorization(resource_locator: str) -> bool:
        if ResourceLock.objects.filter(resource_locator=resource_locator).exists():
            return False
        return True

    for resource in resource_locator:
        if not _check_authorization(resource):
            return False
    return True


__all__ = ["Budget", "ResourceConstraint", "ResourceLock", "charge_authorization"]
