"""
Test the account app's Celery tasks.

The tasks are called directly, which runs
them synchronously, in this process.
"""

from decimal import Decimal
from unittest.mock import patch

from smarter.apps.account.models import Charge, ChargeTypes
from smarter.apps.account.tasks import (
    aggregate_records,
    create_charge,
    evaluate_budget_constraints,
)
from smarter.lib.unittest.base_classes import SmarterTestBase

MODULE = "smarter.apps.account.tasks"


class TestAccountTasks(SmarterTestBase):
    """Test create_charge, aggregate_records and evaluate_budget_constraints."""

    def setUp(self):
        super().setUp()
        self.resource_locator = f"test://account_tasks/{self.hash_suffix}"
        self.addCleanup(Charge.objects.filter(resource_locator=self.resource_locator).delete)

    def test_create_charge_with_a_known_cost(self):
        create_charge(
            resource_locator=self.resource_locator,
            charge_type=ChargeTypes.PROMPT_COMPLETION.value,
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
            total_cost="0.25",
        )
        charge = Charge.objects.get(resource_locator=self.resource_locator)
        self.assertEqual(charge.total_tokens, 15)
        self.assertEqual(charge.total_cost, Decimal("0.25"))

    def test_create_charge_prices_the_tokens(self):
        with patch(f"{MODULE}.LLMPrices.cost_of", return_value=Decimal("0.5")) as cost_of:
            create_charge(
                resource_locator=self.resource_locator,
                charge_type=ChargeTypes.PROMPT_COMPLETION.value,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                provider="openai",
                model="gpt-4o",
            )
        cost_of.assert_called_once_with(
            charge_type=ChargeTypes.PROMPT_COMPLETION.value, provider="openai", model="gpt-4o", total_tokens=0
        )
        self.assertEqual(Charge.objects.get(resource_locator=self.resource_locator).total_cost, Decimal("0.5"))

    def test_create_charge_logs_errors(self):
        with patch.object(Charge.objects, "create", side_effect=RuntimeError("db down")):
            with self.assertLogs("smarter.apps.account.tasks", level="ERROR"):
                create_charge(resource_locator=self.resource_locator, total_cost=0)
        self.assertFalse(Charge.objects.filter(resource_locator=self.resource_locator).exists())

    def test_aggregate_records(self):
        with patch(f"{MODULE}.aggregate_charges") as aggregate_charges:
            aggregate_records()
        aggregate_charges.assert_called_once_with()

    def test_evaluate_budget_constraints(self):
        with patch(f"{MODULE}.evaluate_budgets", return_value=3) as evaluate_budgets:
            self.assertEqual(evaluate_budget_constraints(), 3)
        evaluate_budgets.assert_called_once_with()
