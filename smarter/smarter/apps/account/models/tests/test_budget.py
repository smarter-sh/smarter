# pylint: disable=wrong-import-position
"""Test Budget, ResourceConstraint, ResourceLock and charge_authorization()."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from django.utils import timezone as django_timezone

from smarter.apps.account.models import (
    AggregatedCharges,
    Budget,
    BudgetAction,
    BudgetPeriod,
    BudgetUnit,
    Charge,
    ChargeTypes,
    LLMPrices,
    ResourceConstraint,
    ResourceLock,
    SmarterBudgetExceeded,
    charge_authorization,
    evaluate_budgets,
    get_actuals,
)
from smarter.apps.account.models.budget import (
    add_periods,
    get_resource_lock_message,
    period_start,
    resolve_resource,
)
from smarter.apps.account.signals import (
    budget_exceeded,
    budget_released,
    budget_warning,
)
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.dashboard.views.views.api.budgets import is_visible
from smarter.lib import logging

logger = logging.getLogger(__name__)


class TestBudget(TestAccountMixin):
    """Test the enforcement of budgets."""

    logger_prefix = logging.formatted_text(f"{__name__}.TestBudget()")

    def setUp(self):
        super().setUp()
        self.locator = f"testbudgetresource-{self.hash_suffix}-{self._testMethodName}"
        self.signals: dict[str, list[dict]] = {"warning": [], "exceeded": [], "released": []}

        def receiver_for(name):
            def receiver(sender, **kwargs):
                self.signals[name].append(kwargs)

            return receiver

        self._receivers = {name: receiver_for(name) for name in self.signals}
        budget_warning.connect(self._receivers["warning"])
        budget_exceeded.connect(self._receivers["exceeded"])
        budget_released.connect(self._receivers["released"])

    def tearDown(self):
        budget_warning.disconnect(self._receivers["warning"])
        budget_exceeded.disconnect(self._receivers["exceeded"])
        budget_released.disconnect(self._receivers["released"])
        Budget.objects.filter(name__startswith=f"test_budget_{self.hash_suffix}").delete()
        Charge.objects.filter(resource_locator=self.locator).delete()
        AggregatedCharges.objects.filter(resource_locator=self.locator).delete()
        get_resource_lock_message.invalidate(self.locator)
        super().tearDown()

    def budget(self, **kwargs) -> Budget:
        """Create a budget that tearDown() deletes."""
        name = f"test_budget_{self.hash_suffix}_{len(Budget.objects.filter(name__startswith='test_budget_'))}"
        return Budget.objects.create(name=name, **kwargs)

    def charge(self, cost: str = "0", tokens: int = 0, created_at=None) -> Charge:
        """Create a charge for the test resource."""
        charge = Charge.objects.create(
            resource_locator=self.locator,
            charge_type=ChargeTypes.PROMPT_COMPLETION.value,
            prompt_tokens=tokens,
            completion_tokens=0,
            total_tokens=tokens,
            total_cost=Decimal(cost),
        )
        if created_at:
            Charge.objects.filter(pk=charge.pk).update(created_at=created_at)
        return charge

    def assertLocked(self, locator: str = "", message: str = ""):
        with self.assertRaises(SmarterBudgetExceeded) as cm:
            charge_authorization(locator or self.locator, "test")
        if message:
            self.assertEqual(cm.exception.message, message)
        return cm.exception

    # -------------------------------------------------------------------------
    # periods and actuals
    # -------------------------------------------------------------------------
    def test_periods(self):
        """Test the beginnings of billing periods, and adding periods."""
        when = datetime(2026, 1, 31, 13, 45, tzinfo=timezone.utc)  # a Saturday
        self.assertEqual(period_start(BudgetPeriod.HOUR, when), datetime(2026, 1, 31, 13, tzinfo=timezone.utc))
        self.assertEqual(period_start(BudgetPeriod.DAY, when), datetime(2026, 1, 31, tzinfo=timezone.utc))
        self.assertEqual(period_start(BudgetPeriod.WEEK, when), datetime(2026, 1, 26, tzinfo=timezone.utc))
        self.assertEqual(period_start(BudgetPeriod.MONTH, when), datetime(2026, 1, 1, tzinfo=timezone.utc))
        month = datetime(2026, 11, 1, tzinfo=timezone.utc)
        self.assertEqual(add_periods(BudgetPeriod.MONTH, month, 2), datetime(2027, 1, 1, tzinfo=timezone.utc))
        self.assertEqual(add_periods(BudgetPeriod.MONTH, month, -11), datetime(2025, 12, 1, tzinfo=timezone.utc))
        self.assertEqual(add_periods(BudgetPeriod.WEEK, month, 1), datetime(2026, 11, 8, tzinfo=timezone.utc))

    def test_get_actuals(self):
        """Test that actuals add charges and aggregated charges, within the period."""
        now = django_timezone.now()
        self.charge(cost="1.50", tokens=100)
        self.charge(cost="2.00", tokens=10, created_at=now - timedelta(days=3))
        two_hours_ago = now - timedelta(hours=2)
        AggregatedCharges.objects.create(
            year=two_hours_ago.year,
            month=two_hours_ago.month,
            day=two_hours_ago.day,
            hour=two_hours_ago.hour,
            resource_locator=self.locator,
            charge_type=ChargeTypes.PROMPT_COMPLETION.value,
            records=4,
            prompt_tokens=1000,
            completion_tokens=0,
            total_tokens=1000,
            total_cost=Decimal("0.25"),
        )
        actuals = get_actuals(self.locator, now - timedelta(days=1))
        self.assertEqual(actuals.total_cost, Decimal("1.75"))
        self.assertEqual(actuals.total_tokens, 1100)
        self.assertEqual(actuals.records, 5)
        self.assertEqual(get_actuals(self.locator).total_cost, Decimal("3.75"))
        self.assertEqual(get_actuals(self.locator, now - timedelta(hours=1)).total_cost, Decimal("1.50"))

    def test_llm_prices_cost_of(self):
        """Test that LLMPrices prices tokens in USD per million, and that an unknown model costs nothing."""
        model = f"test-model-{self.hash_suffix}"
        LLMPrices.objects.create(
            charge_type=ChargeTypes.PROMPT_COMPLETION.value, provider="openai", model=model, price=Decimal("2.5")
        )
        self.addCleanup(LLMPrices.objects.filter(model=model).delete)
        self.assertEqual(
            LLMPrices.cost_of(ChargeTypes.PROMPT_COMPLETION.value, "OpenAI", model, 200000), Decimal("0.5")
        )
        self.assertEqual(LLMPrices.cost_of(ChargeTypes.PROMPT_COMPLETION.value, "openai", "nope", 200000), 0)
        self.assertEqual(LLMPrices.cost_of(ChargeTypes.PROMPT_COMPLETION.value, None, None, 200000), 0)

    # -------------------------------------------------------------------------
    # enforcement
    # -------------------------------------------------------------------------
    def test_periodic_limit(self):
        """Test the warning, the lock, and its release when the budget is raised."""
        budget = self.budget(periodic_limit=Decimal("1.00"), message="Your allowance is used up.")
        budget.attach(self.locator)
        self.assertTrue(charge_authorization(self.locator))

        self.charge(cost="0.50")
        self.assertEqual(self.signals["warning"], [])
        self.charge(cost="0.35")
        self.assertEqual(len(self.signals["warning"]), 1)
        self.charge(cost="0.01")
        self.assertEqual(len(self.signals["warning"]), 1, "the warning is sent once per period")
        self.assertTrue(charge_authorization(self.locator))

        self.charge(cost="0.20")
        lock = ResourceLock.objects.get(resource_locator=self.locator)
        self.assertEqual(lock.expiration_date, ResourceConstraint.objects.get(budget=budget).current_period()[1])
        self.assertIn("monthly limit of $1.00", lock.reason)
        self.assertEqual(len(self.signals["exceeded"]), 1)
        self.assertLocked(message="Your allowance is used up.")

        self.charge(cost="0.20")
        self.assertEqual(len(self.signals["exceeded"]), 1, "exceeded is sent once per lock")
        self.assertEqual(ResourceLock.objects.filter(resource_locator=self.locator).count(), 1)

        budget.periodic_limit = Decimal("5.00")
        budget.save()
        self.assertFalse(ResourceLock.objects.filter(resource_locator=self.locator).exists())
        self.assertEqual(len(self.signals["released"]), 1)
        self.assertTrue(charge_authorization(self.locator))

    def test_tokens_and_absolute_limit(self):
        """Test a budget of tokens over the life of the resource, which does not expire with the period."""
        budget = self.budget(unit=BudgetUnit.TOKENS, absolute_limit=Decimal(1000))
        self.charge(tokens=600, created_at=django_timezone.now() - timedelta(days=60))
        budget.attach(self.locator, start_date=django_timezone.now() - timedelta(days=90))
        self.charge(tokens=500)
        lock = ResourceLock.objects.get(resource_locator=self.locator)
        self.assertIsNone(lock.expiration_date)
        self.assertIn("1,000 tokens", self.assertLocked().message)

    def test_charges_before_start_date_do_not_count(self):
        """Test that a budget counts only the charges from when it was attached."""
        self.charge(cost="10.00", created_at=django_timezone.now() - timedelta(minutes=5))
        budget = self.budget(period=BudgetPeriod.DAY, periodic_limit=Decimal("1.00"))
        budget.attach(self.locator)
        self.assertTrue(charge_authorization(self.locator))

    def test_warn_only(self):
        """Test that a budget that only warns sends budget_exceeded, once, but does not lock."""
        budget = self.budget(periodic_limit=Decimal("1.00"), action=BudgetAction.WARN)
        budget.attach(self.locator)
        self.charge(cost="2.00")
        self.charge(cost="2.00")
        self.assertFalse(ResourceLock.objects.filter(resource_locator=self.locator).exists())
        self.assertEqual(len(self.signals["exceeded"]), 1)
        self.assertIsNone(self.signals["exceeded"][0]["lock"])
        self.assertTrue(charge_authorization(self.locator))

    def test_duration(self):
        """Test that a budget no longer applies when its duration ends, and its lock ends with it."""
        budget = self.budget(period=BudgetPeriod.DAY, duration=2, periodic_limit=Decimal("1.00"))
        (constraint,) = budget.attach(self.locator, start_date=django_timezone.now() - timedelta(days=1))
        self.charge(cost="2.00")
        lock = ResourceLock.objects.get(resource_locator=self.locator)
        self.assertEqual(lock.expiration_date, constraint.expires_at)
        self.assertLocked()

        ResourceConstraint.objects.filter(pk=constraint.pk).update(start_date=django_timezone.now() - timedelta(days=3))
        constraint.refresh_from_db()
        self.assertTrue(constraint.is_expired())
        self.assertIsNone(constraint.evaluate())
        self.assertFalse(ResourceLock.objects.filter(resource_locator=self.locator).exists())
        self.charge(cost="2.00")
        self.assertTrue(charge_authorization(self.locator))

    def test_detach_and_inactive(self):
        """Test that detaching a budget, or deactivating it, removes the lock."""
        budget = self.budget(periodic_limit=Decimal("1.00"))
        (constraint,) = budget.attach(self.locator)
        self.charge(cost="2.00")
        self.assertLocked()

        constraint.is_active = False
        constraint.save()
        self.assertTrue(charge_authorization(self.locator))

        budget.attach(self.locator)
        self.assertLocked()

        self.assertEqual(budget.detach(self.locator), 1)
        self.assertTrue(charge_authorization(self.locator))

    def test_evaluate_budgets_removes_expired_locks(self):
        """Test that the hourly task removes locks whose billing period has ended."""
        budget = self.budget(period=BudgetPeriod.HOUR, periodic_limit=Decimal("1.00"))
        (constraint,) = budget.attach(self.locator)
        ResourceLock.objects.create(
            resource_constraint=constraint,
            resource_locator=self.locator,
            expiration_date=django_timezone.now() - timedelta(minutes=1),
            reason="last hour",
        )
        # an expired lock refuses nothing, even before the task removes it.
        self.assertTrue(charge_authorization(self.locator))
        evaluate_budgets()
        self.assertFalse(ResourceLock.objects.filter(resource_locator=self.locator).exists())

    def test_attach_to_user(self):
        """Test that a budget attached to a User is attached to their UserProfile."""
        budget = self.budget(periodic_limit=Decimal("1.00"))
        constraints = budget.attach(self.non_admin_user)
        self.assertEqual([c.resource_locator for c in constraints], [self.non_admin_user_profile.record_locator])
        budget.attach(self.account)
        self.assertEqual(
            set(budget.constraints.values_list("resource_locator", flat=True)),  # type: ignore[attr-defined]
            {self.non_admin_user_profile.record_locator, self.account.record_locator},
        )

    # -------------------------------------------------------------------------
    # budget vs actual
    # -------------------------------------------------------------------------
    def test_status_and_series(self):
        """Test the budget versus the actual spending."""
        budget = self.budget(period=BudgetPeriod.DAY, periodic_limit=Decimal("10.00"), absolute_limit=Decimal("100"))
        (constraint,) = budget.attach(self.locator, start_date=django_timezone.now() - timedelta(days=2, hours=1))
        self.charge(cost="3.00", created_at=django_timezone.now() - timedelta(days=1))
        self.charge(cost="2.00")

        status = constraint.status()
        self.assertEqual(status["periodic_actual"], Decimal("2.00"))
        self.assertEqual(status["periodic_percent"], 20.0)
        self.assertEqual(status["absolute_actual"], Decimal("5.00"))
        self.assertFalse(status["is_locked"])

        series = constraint.series(periods=7)
        self.assertEqual(len(series), 3, "the series begins with the period of the start date")
        self.assertEqual([row["actual"] for row in series], [Decimal("0"), Decimal("3.00"), Decimal("2.00")])
        self.assertTrue(all(row["budget"] == Decimal("10.00") for row in series))

    def test_resolve_resource_and_visibility(self):
        """Test that record locators resolve to their resource, and who may see a resource's budgets."""
        self.assertEqual(resolve_resource(self.account.record_locator), self.account)
        self.assertIsNone(resolve_resource("nosuchmodel-abc"))
        self.assertTrue(is_visible(self.non_admin_user_profile, self.non_admin_user_profile.record_locator))
        self.assertFalse(is_visible(self.non_admin_user_profile, self.account.record_locator))
        self.assertFalse(is_visible(self.non_admin_user_profile, self.locator))
        self.assertTrue(is_visible(self.user_profile, self.locator), "superusers see every budget")
