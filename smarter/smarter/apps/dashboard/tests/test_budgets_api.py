# pylint: disable=wrong-import-position
"""Test the budget versus actual API end points."""

from decimal import Decimal

from django.test import Client
from django.urls import reverse

from smarter.apps.account.models import Budget, Charge, ChargeTypes
from smarter.apps.account.models.budget import get_resource_lock_message
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.dashboard.views.views.api.urls import DashboardApiReverseNames

from ..const import namespace


class TestBudgetsApi(TestAccountMixin):
    """Test BudgetsView and BudgetSeriesView."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.client.force_login(self.non_admin_user)
        self.locator = self.non_admin_user_profile.record_locator
        self.budget = Budget.objects.create(name=f"test_budgets_api_{self.hash_suffix}", periodic_limit=Decimal("4.00"))
        self.budget.attach(self.non_admin_user_profile)
        self.charge = Charge.objects.create(
            resource_locator=self.locator,
            charge_type=ChargeTypes.PROMPT_COMPLETION.value,
            prompt_tokens=10,
            completion_tokens=10,
            total_tokens=20,
            total_cost=Decimal("1.00"),
        )

    def tearDown(self):
        self.client.logout()
        self.budget.delete()
        self.charge.delete()
        get_resource_lock_message.invalidate(self.locator)
        super().tearDown()

    def url(self, name: str, **kwargs) -> str:
        return reverse(f"{namespace}:{DashboardApiReverseNames.namespace}:{name}", kwargs=kwargs or None)

    def test_budgets(self):
        """Test that a user sees the status of their own budget."""
        response = self.client.post(self.url(DashboardApiReverseNames.budgets))
        self.assertEqual(response.status_code, 200)
        (status,) = (row for row in response.json() if row["budget"] == self.budget.name)
        self.assertEqual(status["periodic_actual"], 1.0)
        self.assertEqual(status["periodic_percent"], 25.0)
        self.assertFalse(status["is_locked"])

    def test_series(self):
        """Test the budget versus actual series of the user's own resource, and that others' are not found."""
        response = self.client.post(
            self.url(DashboardApiReverseNames.budget_series, resource_locator=self.locator) + "?periods=3"
        )
        self.assertEqual(response.status_code, 200)
        (data,) = response.json()
        self.assertEqual(data["series"][-1]["actual"], 1.0)
        self.assertEqual(data["series"][-1]["budget"], 4.0)

        response = self.client.post(
            self.url(DashboardApiReverseNames.budget_series, resource_locator=self.account.record_locator)
        )
        self.assertEqual(response.status_code, 404)
