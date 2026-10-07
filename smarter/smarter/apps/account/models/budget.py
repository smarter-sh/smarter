"""
Budget models.

A :class:`Budget` is a reusable spending limit. Attaching it to a resource creates a
:class:`ResourceConstraint`. The constraint is evaluated each time a charge is created for
the resource, and hourly by Celery Beat. When the resource's spending reaches a limit, the
constraint creates a :class:`ResourceLock`, and :func:`charge_authorization` then refuses
more charges to the resource until the lock is removed: when the billing period ends, when
the budget is raised, or when the budget is detached.

A budget can be attached to anything that has a record locator: a UserProfile, a User (each of
their UserProfiles), an Account, an LLMClient, a Provider, a Proxy, an LLMHostCompute, a plugin,
an MCPClient, and so on. Charges are created for each resource that took part in a request, so a
budget on any of them sees its share of the spending.

Assumed to be always been under the control of
superusers, so no ownership nor permissions are implemented.

Example::

    budget = Budget.objects.create(
        name="student_monthly_allowance",
        period=BudgetPeriod.MONTH,
        periodic_limit=Decimal("10.00"),
        message="You have used this month's AI allowance. It renews on the 1st.",
    )
    budget.attach(user_profile)
"""

from calendar import monthrange
from datetime import datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Optional, Union

from django.apps import apps
from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q
from django.utils import timezone

from smarter.apps.account.signals import (
    budget_exceeded,
    budget_released,
    budget_warning,
    charge_authorized,
    charge_declined,
)
from smarter.common.exceptions import SmarterException, SmarterValueError
from smarter.lib import logging
from smarter.lib.cache import cache_results
from smarter.lib.django.models import MetaDataModel, TimestampedModel
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .charge import Actuals, get_actuals

if TYPE_CHECKING:
    from .user_profile import UserProfile

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.ACCOUNT_LOGGING])

LOCK_CACHE_TIMEOUT = 60  # seconds. Locks also invalidate it when they are created or removed.


class SmarterChargeAuthorizationFailed(SmarterException):
    """Exception raised when a charge authorization fails."""


class SmarterBudgetExceeded(SmarterChargeAuthorizationFailed):
    """
    A budget's resource lock forbids charges to a resource.

    :attr:`message` is meant for the person who made the request, e.g. in the chat window.
    """

    def __init__(self, message: str = "", resource_locator: Optional[str] = None):
        self.resource_locator = resource_locator
        super().__init__(message)


class BudgetPeriod(models.TextChoices):
    """The billing period of a budget's periodic limit."""

    HOUR = "hour", "Hour"
    DAY = "day", "Day"
    WEEK = "week", "Week"
    MONTH = "month", "Month"


class BudgetUnit(models.TextChoices):
    """What a budget's limits measure."""

    COST = "cost", "Cost (USD)"
    TOKENS = "tokens", "Tokens"


class BudgetAction(models.TextChoices):
    """What happens when a budget's limit is reached."""

    BLOCK = "block", "Block further charges"
    WARN = "warn", "Warn only"


def period_start(period: str, when: datetime) -> datetime:
    """The beginning of the period that contains when.

    Weeks begin on Monday.
    """
    when = timezone.localtime(when).replace(minute=0, second=0, microsecond=0)
    if period == BudgetPeriod.HOUR:
        return when
    when = when.replace(hour=0)
    if period == BudgetPeriod.DAY:
        return when
    if period == BudgetPeriod.WEEK:
        return when - timedelta(days=when.weekday())
    if period == BudgetPeriod.MONTH:
        return when.replace(day=1)
    raise SmarterValueError(f"Unknown budget period: {period}")


def add_periods(period: str, start: datetime, periods: int) -> datetime:
    """The beginning of the period that is periods after the one that begins at start."""
    if period == BudgetPeriod.HOUR:
        return start + timedelta(hours=periods)
    if period == BudgetPeriod.DAY:
        return start + timedelta(days=periods)
    if period == BudgetPeriod.WEEK:
        return start + timedelta(weeks=periods)
    if period == BudgetPeriod.MONTH:
        months = start.year * 12 + start.month - 1 + periods
        year, month = divmod(months, 12)
        return start.replace(year=year, month=month + 1, day=min(start.day, monthrange(year, month + 1)[1]))
    raise SmarterValueError(f"Unknown budget period: {period}")


def resource_locators_for(resource: Union[str, User, TimestampedModel]) -> list[str]:
    """
    The record locators that a budget is attached to for a resource.

    A User's charges are created for their UserProfiles, one per account they belong to, so a
    budget attached to a User is attached to each of them.
    """
    if isinstance(resource, str):
        return [resource]
    if isinstance(resource, User):
        # pylint: disable=C0415
        from .user_profile import UserProfile

        return [user_profile.record_locator for user_profile in UserProfile.objects.filter(user=resource)]
    if isinstance(resource, TimestampedModel):
        return [resource.record_locator]
    raise SmarterValueError(f"A budget cannot be attached to {type(resource).__name__}.")


def resolve_resource(resource_locator: str) -> Optional[TimestampedModel]:
    """The model instance of a record locator, e.g. "llmclient-rc2x", or None."""
    prefix = resource_locator.split("-", 1)[0]
    for model in apps.get_models():
        if model.__name__.lower() == prefix and issubclass(model, TimestampedModel):
            return model.get_object_by_locator(resource_locator)
    return None


# pylint: disable=too-many-return-statements
def is_visible(user_profile: "UserProfile", resource_locator: str) -> bool:
    """Whether the user may see the budgets attached to a resource."""
    user = user_profile.user
    if user.is_superuser:
        return True
    if resource_locator == user_profile.record_locator:
        return True
    if resource_locator == user_profile.account.record_locator:
        return user.is_staff
    resource = resolve_resource(resource_locator)
    # pylint: disable=C0415,W0621
    from .user_profile import UserProfile

    if isinstance(resource, UserProfile):
        return user.is_staff and resource.account_id == user_profile.account_id  # type: ignore[attr-defined]
    owner = getattr(resource, "user_profile", None)
    if isinstance(owner, UserProfile):
        if owner.pk == user_profile.pk:
            return True
        return user.is_staff and owner.account_id == user_profile.account_id  # type: ignore[attr-defined]
    return False


class Budget(MetaDataModel):
    """
    A budget is a catalogue of spending limits that can be enforced on a resource, either in a given period of time, or over the life of the resource.

    examples:

        - a per-User budget of $10 per month, with a total limit of $100 for the life of the student.
        - a per-Account budget of $100 per month, with a total limit of $1,000 for the life of the account.
        - a custom project budget of $1000 per month, with a total limit of $10,000 for the life of the project.
        - a customer project budget of $10,000 over the life of the project, with no monthly limit.
        - a per-User throttle of 50,000 tokens per hour.
        - an LLMHostCompute budget of $500 per month of node time.

    A limit of 0 means no limit.
    """

    name = models.CharField(
        max_length=255,
        unique=True,
        help_text="The budget's name, in snake_case. Unique: manifests refer to budgets by name.",
        validators=[SmarterValidator.validate_snake_case, SmarterValidator.validate_no_spaces],
    )
    period = models.CharField(
        max_length=10,
        choices=BudgetPeriod.choices,
        default=BudgetPeriod.MONTH,
        help_text="The billing period of the periodic limit, and of the duration.",
    )
    unit = models.CharField(
        max_length=10,
        choices=BudgetUnit.choices,
        default=BudgetUnit.COST,
        help_text="What the limits measure: cost in USD, or total tokens.",
    )
    duration = models.PositiveIntegerField(
        default=0,
        help_text="The duration of the budget in billing periods, from when it is attached. Afterwards, the budget no longer applies. 0 means no limit.",
    )
    periodic_limit = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="The maximum cost or tokens that can be incurred in a billing period. 0 means no limit.",
    )
    absolute_limit = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="The maximum cost or tokens that can be incurred in total, from when it is attached. 0 means no limit.",
    )
    action = models.CharField(
        max_length=10,
        choices=BudgetAction.choices,
        default=BudgetAction.BLOCK,
        help_text="What happens when a limit is reached: block further charges, or only send the budget_exceeded signal.",
    )
    warning_threshold = models.PositiveSmallIntegerField(
        default=80,
        help_text="The percentage of a limit at which the budget_warning signal is sent, once per billing period. 0 means never.",
    )
    message = models.TextField(
        blank=True,
        default="",
        help_text="What people are told when this budget blocks their request, e.g. in the chat window. Empty means a description of the limit that was reached.",
    )

    def __str__(self):
        return str(self.name)

    def validate(self):
        super().validate()
        if self.periodic_limit < 0 or self.absolute_limit < 0:
            raise SmarterValueError("Budget limits cannot be negative.")
        if self.warning_threshold > 100:
            raise SmarterValueError("Budget warning_threshold is a percentage, from 0 to 100.")

    def format_amount(self, amount: Union[Decimal, int]) -> str:
        """An amount in this budget's unit, e.g. "$10.00" or "50,000 tokens"."""
        if self.unit == BudgetUnit.TOKENS:
            return f"{int(amount):,} tokens"
        return f"${Decimal(amount):,.2f}"

    def attach(
        self, resource: Union[str, User, TimestampedModel], start_date: Optional[datetime] = None
    ) -> list["ResourceConstraint"]:
        """
        Enforce this budget on a resource, from start_date or now.

        Attaching it again reactivates it, and keeps its start date.

        :returns: The resource constraints, one per record locator.
        """
        retval = []
        for resource_locator in resource_locators_for(resource):
            constraint, created = ResourceConstraint.objects.get_or_create(
                budget=self,
                resource_locator=resource_locator,
                defaults={"start_date": start_date or timezone.now()},
            )
            if not created and not constraint.is_active:
                constraint.is_active = True
                constraint.save()
            retval.append(constraint)
        return retval

    def detach(self, resource: Union[str, User, TimestampedModel]) -> int:
        """
        Stop enforcing this budget on a resource, and remove its locks.

        :returns: The number of resource constraints removed.
        """
        constraints = ResourceConstraint.objects.filter(
            budget=self, resource_locator__in=resource_locators_for(resource)
        )
        retval = constraints.count()
        constraints.delete()
        return retval


class ResourceConstraint(TimestampedModel):
    """
    A budget attached to a resource.

    .. note::

        resource_locator intentionally overrides the parent class's
        TimestampedModel.resource_locator field.
    """

    # pylint: disable=C0115
    class Meta:
        unique_together = ("budget", "resource_locator")

    budget = models.ForeignKey(
        Budget,
        on_delete=models.CASCADE,
        null=True,
        related_name="constraints",
        help_text="The budget that is enforced on the resource.",
    )
    resource_locator = models.CharField(
        max_length=255,
        db_index=True,
        help_text="The TimestampedModel.resource_locator of the resource that this constraint is associated with.",
    )
    is_active = models.BooleanField(default=True, help_text="Whether the budget is enforced.")
    start_date = models.DateTimeField(
        default=timezone.now,
        help_text="When the budget began to apply to the resource. The duration and the absolute limit count from here.",
    )
    warned_at = models.DateTimeField(
        null=True, blank=True, help_text="When the budget_warning signal was last sent for this resource."
    )
    exceeded_at = models.DateTimeField(
        null=True, blank=True, help_text="When the budget_exceeded signal was last sent for this resource."
    )

    def __str__(self):
        return f"{self.budget} -> {self.resource_locator}"

    def validate(self):
        super().validate()
        if self.budget_id is None:  # type: ignore[attr-defined]
            raise SmarterValueError("A resource constraint requires a budget.")
        if not self.resource_locator:
            raise SmarterValueError("A resource constraint requires a resource_locator.")

    # -------------------------------------------------------------------------
    # budget vs actual
    # -------------------------------------------------------------------------
    @property
    def expires_at(self) -> Optional[datetime]:
        """When the budget's duration ends, or None if it has none."""
        if not self.budget.duration:  # type: ignore[union-attr]
            return None
        period = self.budget.period  # type: ignore[union-attr]
        return add_periods(period, period_start(period, self.start_date), self.budget.duration)  # type: ignore[union-attr]

    def is_expired(self, now: Optional[datetime] = None) -> bool:
        """Whether the budget's duration has ended, after which the budget no longer applies."""
        expires_at = self.expires_at
        return expires_at is not None and (now or timezone.now()) >= expires_at

    def current_period(self, now: Optional[datetime] = None) -> tuple[datetime, datetime]:
        """The beginning and end of the billing period that contains now."""
        start = period_start(self.budget.period, now or timezone.now())  # type: ignore[union-attr]
        return start, add_periods(self.budget.period, start, 1)  # type: ignore[union-attr]

    def measure(self, actuals: Actuals) -> Decimal:
        """Actual spending in the budget's unit."""
        if self.budget.unit == BudgetUnit.TOKENS:  # type: ignore[union-attr]
            return Decimal(actuals.total_tokens)
        return actuals.total_cost

    def periodic_actual(self, now: Optional[datetime] = None) -> Decimal:
        """Spending in the billing period that contains now, counted from the start date."""
        now = now or timezone.now()
        start, _ = self.current_period(now)
        return self.measure(get_actuals(self.resource_locator, max(start, self.start_date), now))

    def absolute_actual(self, now: Optional[datetime] = None) -> Decimal:
        """Spending since the start date."""
        return self.measure(get_actuals(self.resource_locator, self.start_date, now or timezone.now()))

    def status(self, now: Optional[datetime] = None) -> dict[str, Any]:
        """The budget versus the actual spending, now."""
        now = now or timezone.now()
        budget: Budget = self.budget  # type: ignore[assignment]
        start, end = self.current_period(now)
        periodic_actual = self.periodic_actual(now)
        absolute_actual = self.absolute_actual(now)
        lock = self.locks.first()  # type: ignore[attr-defined]
        return {
            "budget": budget.name,
            "resource_locator": self.resource_locator,
            "is_active": self.is_active,
            "unit": budget.unit,
            "period": budget.period,
            "action": budget.action,
            "start_date": self.start_date,
            "expires_at": self.expires_at,
            "is_expired": self.is_expired(now),
            "period_start": start,
            "period_end": end,
            "periodic_limit": budget.periodic_limit,
            "periodic_actual": periodic_actual,
            "periodic_percent": _percent(periodic_actual, budget.periodic_limit),
            "absolute_limit": budget.absolute_limit,
            "absolute_actual": absolute_actual,
            "absolute_percent": _percent(absolute_actual, budget.absolute_limit),
            "is_locked": lock is not None and not lock.is_expired,
            "lock_reason": lock.reason if lock else None,
        }

    def series(self, periods: int = 12, now: Optional[datetime] = None) -> list[dict[str, Any]]:
        """
        The budget versus the actual spending of each of the last periods billing periods, for charts.

        The first period is not earlier than the one that contains the start date.
        """
        now = now or timezone.now()
        budget: Budget = self.budget  # type: ignore[assignment]
        current, _ = self.current_period(now)
        first = max(add_periods(budget.period, current, 1 - periods), period_start(budget.period, self.start_date))
        retval = []
        start = first
        while start <= current:
            end = add_periods(budget.period, start, 1)
            actuals = get_actuals(self.resource_locator, max(start, self.start_date), min(end, now))
            retval.append(
                {
                    "period_start": start,
                    "period_end": end,
                    "budget": budget.periodic_limit,
                    "actual": self.measure(actuals),
                    "total_tokens": actuals.total_tokens,
                    "total_cost": actuals.total_cost,
                }
            )
            start = end
        return retval

    # -------------------------------------------------------------------------
    # enforcement
    # -------------------------------------------------------------------------
    # pylint: disable=too-many-branches
    def evaluate(self, now: Optional[datetime] = None) -> Optional["ResourceLock"]:
        """
        Compare the actual spending to the budget, and lock or unlock the resource.

        Sends budget_warning when spending reaches the budget's warning threshold, budget_exceeded
        when it reaches a limit, and budget_released when a lock is removed. Each is sent once per
        billing period.

        An inactive budget, or one whose duration has ended, no longer applies: it removes its lock.

        :returns: The resource's lock, if it is locked.
        """
        now = now or timezone.now()
        budget: Budget = self.budget  # type: ignore[assignment]
        lock: Optional[ResourceLock] = self.locks.first()  # type: ignore[attr-defined]
        if not self.is_active or self.is_expired(now):
            if lock:
                lock.delete()
                budget_released.send(sender=self.__class__, resource_constraint=self)
            return None

        period_begins, period_ends = self.current_period(now)
        reason, expiration_date, actual, limit = None, None, Decimal("0"), Decimal("0")
        periodic_actual = self.periodic_actual(now) if budget.periodic_limit else Decimal("0")
        absolute_actual = self.absolute_actual(now) if budget.absolute_limit else Decimal("0")

        if budget.absolute_limit and absolute_actual >= budget.absolute_limit:
            actual, limit = absolute_actual, budget.absolute_limit
            reason = f"Budget {budget.name}: the limit of {budget.format_amount(limit)} has been reached ({budget.format_amount(actual)} since {self.start_date:%Y-%m-%d})."
        elif budget.periodic_limit and periodic_actual >= budget.periodic_limit:
            actual, limit = periodic_actual, budget.periodic_limit
            expiration_date = period_ends
            reason = f"Budget {budget.name}: the {budget.period}ly limit of {budget.format_amount(limit)} has been reached ({budget.format_amount(actual)} this {budget.period}). It renews at {period_ends:%Y-%m-%d %H:%M %Z}."

        expires_at = self.expires_at
        if reason and expires_at:
            # the lock ends no later than the budget does.
            expiration_date = min(expiration_date, expires_at) if expiration_date else expires_at

        if reason and budget.action == BudgetAction.BLOCK:
            if lock is None:
                lock = ResourceLock.objects.create(
                    resource_constraint=self,
                    resource_locator=self.resource_locator,
                    expiration_date=expiration_date,
                    reason=reason,
                )
                self._exceeded(lock, reason, actual, limit, now)
            elif lock.reason != reason or lock.expiration_date != expiration_date:
                lock.reason = reason
                lock.expiration_date = expiration_date
                lock.save()
            return lock

        if lock:
            lock.delete()
            budget_released.send(sender=self.__class__, resource_constraint=self)
        if reason:
            # BudgetAction.WARN
            if self.exceeded_at is None or self.exceeded_at < period_begins:
                self._exceeded(None, reason, actual, limit, now)
            return None

        for actual, limit in ((periodic_actual, budget.periodic_limit), (absolute_actual, budget.absolute_limit)):
            if budget.warning_threshold and limit and actual >= limit * budget.warning_threshold / 100:
                if self.warned_at is None or self.warned_at < period_begins:
                    ResourceConstraint.objects.filter(pk=self.pk).update(warned_at=now)
                    self.warned_at = now
                    budget_warning.send(sender=self.__class__, resource_constraint=self, actual=actual, limit=limit)
                break
        return None

    def _exceeded(
        self, lock: Optional["ResourceLock"], reason: str, actual: Decimal, limit: Decimal, now: datetime
    ) -> None:
        # update() rather than save(), so that the post_save receiver does not evaluate again.
        ResourceConstraint.objects.filter(pk=self.pk).update(exceeded_at=now)
        self.exceeded_at = now
        budget_exceeded.send(
            sender=self.__class__, resource_constraint=self, lock=lock, reason=reason, actual=actual, limit=limit
        )


class ResourceLock(TimestampedModel):
    """
    A mechanism to prevent spending on a resource when its budget constraint has been exceeded.

    The existence of a resource lock indicates that the resource is locked and cannot be used until the lock is
    removed, or it expires.
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
    reason = models.TextField(blank=True, default="", help_text="Which limit was reached.")

    def __str__(self):
        return f"{self.resource_locator}: {self.reason}"

    @property
    def is_expired(self) -> bool:
        """Whether the lock's billing period has ended."""
        return self.expiration_date is not None and self.expiration_date <= timezone.now()

    @property
    def message(self) -> str:
        """What people are told when the lock refuses their request."""
        budget = self.resource_constraint.budget
        return (budget.message if budget else "") or self.reason or "A budget forbids more charges."


def _percent(actual: Decimal, limit: Decimal) -> Optional[float]:
    return round(float(actual / limit * 100), 1) if limit else None


@cache_results(timeout=LOCK_CACHE_TIMEOUT)
def get_resource_lock_message(resource_locator: str) -> Optional[str]:
    """
    The message of a resource's unexpired lock, or None if it is not locked.

    Cached, because it is checked on every request. A lock invalidates it when it is created or removed.
    """
    lock = (
        ResourceLock.objects.filter(resource_locator=resource_locator, resource_constraint__is_active=True)
        .filter(Q(expiration_date__isnull=True) | Q(expiration_date__gt=timezone.now()))
        .select_related("resource_constraint__budget")
        .first()
    )
    return lock.message if lock else None


def charge_authorization(resource_locator: Union[list[str], str], on_behalf_of: Optional[str] = None) -> bool:
    """
    Check if a charge is authorized for the given list of resource locators.

    Call this before doing anything that creates charges, e.g. before calling an LLM.

    :param resource_locator: A list of resource locators or a single resource locator that may be used by the custom implementation.
    :param on_behalf_of: An optional object representing the entity on whose behalf the charge is being authorized.
    :return: True if the charge is authorized.
    :raises SmarterBudgetExceeded: if a budget's resource lock forbids charges to one of them.
    """
    if isinstance(resource_locator, str):
        resource_locator = [resource_locator]

    for resource in resource_locator:
        if not resource:
            continue
        message = get_resource_lock_message(resource)
        if message:
            charge_declined.send(sender=charge_authorization, record_locator=resource, charge=on_behalf_of)
            raise SmarterBudgetExceeded(message, resource_locator=resource)
        charge_authorized.send(sender=charge_authorization, record_locator=resource, charge=on_behalf_of)
    return True


def evaluate_resource_constraints(resource_locator: str, now: Optional[datetime] = None) -> list["ResourceLock"]:
    """
    Evaluate every budget attached to a resource, e.g. after a charge to it is created.

    :returns: The resource's locks.
    """
    retval = []
    for constraint in ResourceConstraint.objects.filter(
        resource_locator=resource_locator, is_active=True
    ).select_related("budget"):
        try:
            lock = constraint.evaluate(now)
            if lock:
                retval.append(lock)
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("evaluate_resource_constraints() failed for %s: %s", constraint, e)
    return retval


def evaluate_budgets(now: Optional[datetime] = None) -> int:
    """
    Remove expired locks, and the locks of inactive constraints, then evaluate every active constraint.

    Runs hourly from Celery Beat, so that budgets roll over at the end of their billing period
    and changes to a budget take effect even if no charge is created.

    :returns: The number of locked resources.
    """
    now = now or timezone.now()
    for lock in ResourceLock.objects.filter(Q(expiration_date__lte=now) | Q(resource_constraint__is_active=False)):
        budget_released.send(sender=ResourceConstraint, resource_constraint=lock.resource_constraint)
        lock.delete()
    retval = 0
    for constraint in ResourceConstraint.objects.filter(is_active=True).select_related("budget"):
        try:
            if constraint.evaluate(now):
                retval += 1
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("evaluate_budgets() failed for %s: %s", constraint, e)
    return retval


__all__ = [
    "Budget",
    "BudgetAction",
    "BudgetPeriod",
    "BudgetUnit",
    "ResourceConstraint",
    "ResourceLock",
    "SmarterBudgetExceeded",
    "SmarterChargeAuthorizationFailed",
    "charge_authorization",
    "evaluate_budgets",
    "evaluate_resource_constraints",
    "get_resource_lock_message",
    "is_visible",
    "resolve_resource",
]
