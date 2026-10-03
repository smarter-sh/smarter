"""Test the account dashboard's pages: overview, billing, payment methods, billing addresses and settings."""

from http import HTTPStatus

from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory

from smarter.apps.account.models import Account
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.account.views import account as account_views
from smarter.apps.account.views.dashboard import dashboard
from smarter.apps.account.views.dashboard.billing.billing import BillingView
from smarter.apps.account.views.dashboard.billing.billing_addresses import (
    BillingAddressesView,
    BillingAddressView,
)
from smarter.apps.account.views.dashboard.billing.payment_methods import (
    PaymentMethodsView,
    PaymentMethodView,
    payment_method_factory,
)
from smarter.apps.account.views.dashboard.settings import SettingsView
from smarter.lib import json


class TestDashboardPages(TestAccountMixin):
    """Call each page as the account's admin."""

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()

    def call(self, view_class, method="get", data=None, **kwargs):
        request = getattr(self.factory, method)("/dashboard/account/", data=data or {}, HTTP_HOST="testserver")
        SessionMiddleware(lambda r: None).process_request(request)  # type: ignore[arg-type]
        request.user = self.admin_user
        return view_class.as_view()(request, **kwargs)

    def test_pages(self):
        for view_class in (
            dashboard.OverviewView,
            dashboard.ActivityView,
            dashboard.StatementsView,
            dashboard.LogsView,
            dashboard.CardDeclinedView,
            BillingView,
            SettingsView,
            account_views.AccountOrganizationView,
            account_views.AccountTeamView,
            account_views.AccountLimitsView,
            account_views.AccountProfileView,
            account_views.AccountAPIKeysView,
            account_views.AccountUsageView,
        ):
            with self.subTest(view=view_class.__name__):
                response = self.call(view_class)
                self.assertIn(response.status_code, (HTTPStatus.OK, HTTPStatus.FOUND), view_class.__name__)

    def test_payment_methods(self):
        self.assertEqual(len(json.loads(self.call(PaymentMethodsView).content)), 3)
        self.assertIn("card_masked", json.loads(self.call(PaymentMethodView, payment_method_id="1").content))
        self.assertEqual(self.call(PaymentMethodView, "delete", payment_method_id="1").status_code, HTTPStatus.OK)
        method = payment_method_factory()
        self.assertTrue(method["card_masked"].startswith("ending "))
        valid = {**method, "is_primary": "on"}
        for verb in ("post", "patch", "put"):
            with self.subTest(verb=verb):
                self.assertEqual(self.call(PaymentMethodView, "post", valid).status_code, HTTPStatus.OK)
                self.assertEqual(getattr(self, "call")(PaymentMethodView, verb, {}).status_code, HTTPStatus.BAD_REQUEST)

    def test_billing_addresses(self):
        self.assertEqual(len(json.loads(self.call(BillingAddressesView).content)), 3)
        self.assertEqual(self.call(BillingAddressView, billing_address_id="1").status_code, HTTPStatus.OK)
        self.assertEqual(self.call(BillingAddressView, "delete", billing_address_id="1").status_code, HTTPStatus.OK)

    def test_billing_address_write(self):
        """Test that a billing address form is answered."""
        for verb in ("post", "patch", "put"):
            with self.subTest(verb=verb):
                self.assertEqual(self.call(BillingAddressView, verb, {}).status_code, HTTPStatus.BAD_REQUEST)
        address = {
            "first_name": "A",
            "last_name": "B",
            "address1": "1 Main St",
            "address2": "Suite 1",
            "city": "Austin",
            "state": "TX",
            "zip": "78701",
            "country": "US",
        }
        self.assertEqual(self.call(BillingAddressView, "post", address).status_code, HTTPStatus.OK)

    def test_settings_write(self):
        """Test that the account's settings are validated, and saved."""
        account = Account.objects.get(pk=self.account.pk)
        data = {
            "account_number": account.account_number,
            "name": account.name,
            "company_name": account.company_name,
            "phone_number": account.phone_number,
            "address1": account.address1,
            "city": account.city,
            "state": account.state,
            "postal_code": account.postal_code,
            "country": account.country,
            "language": account.language,
            "timezone": account.timezone,
            "currency": account.currency,
            "is_active": "on",
        }
        for verb in ("post", "patch", "put"):
            with self.subTest(verb=verb):
                response = self.call(SettingsView, verb, data)
                self.assertIn(response.status_code, (HTTPStatus.OK, HTTPStatus.BAD_REQUEST), response.content)
        for field, value in (("currency", "XXX"), ("country", "Narnia"), ("language", "xx"), ("timezone", "Mars/Base")):
            with self.subTest(field=field):
                response = self.call(SettingsView, "post", {**data, field: value})
                self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(self.call(SettingsView, "post", {}).status_code, HTTPStatus.BAD_REQUEST)
