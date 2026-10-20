"""Test that the deprecated Account UI, :mod:`smarter.apps.account.views.dashboard`, is disabled, and unlinked."""

from http import HTTPStatus

from django.test import Client
from django.urls import reverse

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.account.views.dashboard import ACCOUNT_UI_DEPRECATION_MESSAGE
from smarter.apps.account.views.dashboard.api_keys import APIKeysView, APIKeyView
from smarter.apps.account.views.dashboard.billing.billing import BillingView
from smarter.apps.account.views.dashboard.billing.billing_addresses import (
    BillingAddressesView,
    BillingAddressView,
)
from smarter.apps.account.views.dashboard.billing.payment_methods import (
    PaymentMethodsView,
    PaymentMethodView,
)
from smarter.apps.account.views.dashboard.dashboard import (
    ActivityView,
    LogsView,
    OverviewView,
    StatementsView,
)
from smarter.apps.account.views.dashboard.profile_image import ProfileImageView
from smarter.apps.account.views.dashboard.settings import SettingsView
from smarter.apps.account.views.dashboard.urls import (
    DashboardNamedUrls,
    deprecated_urlpatterns,
    urlpatterns,
)
from smarter.apps.account.views.dashboard.user_profiles import (
    UserProfileSelectView,
    UserProfilesView,
)
from smarter.apps.account.views.dashboard.users import UsersView, UserView
from smarter.apps.dashboard.context_processors import sidebar_context

DEPRECATED_VIEWS = (
    OverviewView,
    ActivityView,
    StatementsView,
    LogsView,
    SettingsView,
    UsersView,
    UserView,
    BillingView,
    BillingAddressesView,
    BillingAddressView,
    PaymentMethodsView,
    PaymentMethodView,
    APIKeysView,
    APIKeyView,
)


class TestDeprecatedAccountUI(TestAccountMixin):
    """The Account UI's urls are disabled, its views are deprecated, and the console no longer links to it."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.addCleanup(self.client.logout)
        self.client.force_login(self.admin_user)

    def test_urls_are_disabled(self):
        """Test that the Account UI's pages are 404s, under both of the paths where the account urls are mounted."""
        for prefix in ("/dashboard/account/", "/account/"):
            for page in ("", "dashboard/", "dashboard/overview/", "dashboard/settings/", "dashboard/billing/"):
                with self.subTest(url=prefix + page):
                    self.assertEqual(self.client.get(prefix + page).status_code, HTTPStatus.NOT_FOUND)

    def test_deprecated_urlpatterns_are_kept(self):
        """Test that the disabled urls are kept, and that only the user menu's urls are still routed."""
        self.assertEqual(
            [pattern.callback.view_class for pattern in urlpatterns],  # type: ignore[attr-defined]
            [ProfileImageView, UserProfilesView, UserProfileSelectView],
        )
        kept = {pattern.callback.view_class for pattern in deprecated_urlpatterns}  # type: ignore[attr-defined]
        self.assertTrue(kept.issuperset({SettingsView, OverviewView, BillingView, APIKeyView, UsersView}))

    def test_profile_image_url_is_routed(self):
        """Test that the user menu's profile image upload still has its url."""
        url = reverse(f"{DashboardNamedUrls.namespace}:{DashboardNamedUrls.ACCOUNT_PROFILE_IMAGE}")
        self.assertNotEqual(self.client.delete(url).status_code, HTTPStatus.NOT_FOUND)

    def test_views_are_deprecated(self):
        """Test that each of the Account UI's views warns that it is deprecated, and the profile image view doesn't."""
        for view_class in DEPRECATED_VIEWS:
            with self.subTest(view=view_class.__name__):
                self.assertEqual(getattr(view_class, "__deprecated__", None), ACCOUNT_UI_DEPRECATION_MESSAGE)
                with self.assertWarnsRegex(DeprecationWarning, "Account UI"):
                    view_class()
        self.assertFalse(hasattr(ProfileImageView, "__deprecated__"))

    def test_console_does_not_link_to_it(self):
        """Test that neither the sidebar nor the user menu links to the Account UI."""
        sidebar_context.invalidate()
        self.addCleanup(sidebar_context.invalidate)
        self.assertNotIn("account", sidebar_context()["sidebar"])
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertNotIn(b"/dashboard/account/dashboard/", response.content)
        self.assertNotIn(b"Account Settings", response.content)
