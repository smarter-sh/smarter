# pylint: disable=wrong-import-position
"""Test the Budget web console: the list view, its API, the delete API and the detail view."""

from decimal import Decimal

from django.test import Client
from django.urls import reverse

from smarter.apps.account.models import Budget, Charge, ChargeTypes
from smarter.apps.account.models.budget import get_resource_lock_message
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.account.views.budget.urls import BudgetReverseNames


def url(name: str, **kwargs) -> str:
    return reverse(f"{BudgetReverseNames.namespace}:{name}", kwargs=kwargs or None)


class TestBudgetConsole(TestAccountMixin):
    """Test the Budget web console views."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.budget = Budget.objects.create(
            name=f"test_budget_console_{self.hash_suffix}", periodic_limit=Decimal("1.00")
        )
        self.addCleanup(Budget.objects.filter(pk=self.budget.pk).delete)
        self.budget.attach(self.non_admin_user_profile)
        self.other = Budget.objects.create(name=f"test_budget_console_other_{self.hash_suffix}")
        self.addCleanup(Budget.objects.filter(pk=self.other.pk).delete)
        locator = self.non_admin_user_profile.record_locator
        charge = Charge.objects.create(
            resource_locator=locator,
            charge_type=ChargeTypes.PROMPT_COMPLETION.value,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            total_cost=Decimal("2.00"),
        )
        self.addCleanup(charge.delete)
        self.addCleanup(get_resource_lock_message.invalidate, locator)

    def tearDown(self):
        self.client.logout()
        super().tearDown()

    def names(self, response) -> list[str]:
        return [budget["name"] for budget in response.json()["objects"]]

    def test_list_view(self):
        """Test that the list view renders the React app's root element."""
        self.client.force_login(self.non_admin_user)
        response = self.client.get(url(BudgetReverseNames.listview))
        self.assertEqual(response.status_code, 200)
        self.assertIn("smarter-budget-list-root", response.content.decode())
        self.assertIn(url(BudgetReverseNames.listview_api), response.content.decode())

    def test_list_api(self):
        """Test that a user sees the budgets attached to them, with their spending, and a superuser sees all."""
        self.client.force_login(self.non_admin_user)
        response = self.client.post(url(BudgetReverseNames.listview_api))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["isSuperuser"])
        self.assertIn(self.budget.name, self.names(response))
        self.assertNotIn(self.other.name, self.names(response))
        (budget,) = (b for b in response.json()["objects"] if b["name"] == self.budget.name)
        (status,) = budget["resourceStatus"]
        self.assertEqual(status["periodicActual"], 2.0)
        self.assertTrue(status["isLocked"])
        self.assertEqual(status["resource"]["kind"], "User")
        self.assertIn("/series/", status["seriesUrl"])
        self.assertEqual(budget["manifestUrl"], url(BudgetReverseNames.detailview, hashed_id=self.budget.hashed_id))

        self.client.force_login(self.admin_user)
        response = self.client.post(url(BudgetReverseNames.listview_api))
        self.assertTrue(response.json()["isSuperuser"])
        self.assertIn(self.other.name, self.names(response))

    def test_delete_api(self):
        """Test that only superusers may delete a budget."""
        self.client.force_login(self.non_admin_user)
        response = self.client.post(url(BudgetReverseNames.listview_api_delete, budget_id=self.other.pk))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Budget.objects.filter(pk=self.other.pk).exists())

        self.client.force_login(self.admin_user)
        response = self.client.post(url(BudgetReverseNames.listview_api_delete, budget_id=self.other.pk))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Budget.objects.filter(pk=self.other.pk).exists())

    def test_detail_view(self):
        """Test that the detail view renders the manifest of a visible budget, and hides the others."""
        self.client.force_login(self.non_admin_user)
        response = self.client.get(url(BudgetReverseNames.detailview, hashed_id=self.budget.hashed_id))
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.budget.name, response.content.decode())
        self.assertIn("periodicLimit", response.content.decode())
        response = self.client.get(url(BudgetReverseNames.detailview, hashed_id=self.other.hashed_id))
        self.assertEqual(response.status_code, 404)

    def test_dashboard_has_budgets_api_url(self):
        """Test that the dashboard gives its React app the budgets API URL, and the sidebar links to Budgets."""
        self.client.force_login(self.non_admin_user)
        response = self.client.get(reverse("dashboard:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertIn('smarter-budgets-api-url="/dashboard/api/budgets/"', response.content.decode())
        self.assertIn(url(BudgetReverseNames.listview), response.content.decode())
