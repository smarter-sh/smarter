"""
Test the aggregate_charges management command.

aggregate_charges() rolls up, and then deletes, every Charge in the database,
so each test runs inside a transaction that is rolled back.
"""

from django.db import transaction

from smarter.apps.account.models import AggregatedCharges, Charge, ChargeTypes

from .base import CommandTestBase


class TestAggregateCharges(CommandTestBase):
    """Test manage.py aggregate_charges."""

    def test_aggregate_charges(self):
        resource_locator = f"test://aggregate_charges/{self.hash_suffix}"
        with transaction.atomic():
            for tokens in (10, 20):
                Charge.objects.create(
                    resource_locator=resource_locator,
                    charge_type=ChargeTypes.PROMPT_COMPLETION.value,
                    prompt_tokens=tokens,
                    completion_tokens=tokens,
                    total_tokens=2 * tokens,
                )
            self.run_command("aggregate_charges")
            aggregated = AggregatedCharges.objects.filter(resource_locator=resource_locator)
            remaining = Charge.objects.filter(resource_locator=resource_locator).count()
            totals = list(aggregated.values_list("records", "prompt_tokens", "total_tokens"))
            transaction.set_rollback(True)

        self.assertEqual(remaining, 0)
        self.assertEqual(totals, [(2, 30, 60)])
        self.assertFalse(AggregatedCharges.objects.filter(resource_locator=resource_locator).exists())
