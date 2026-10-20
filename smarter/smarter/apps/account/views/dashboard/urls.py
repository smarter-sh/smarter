"""
URL configuration for the account dashboard.

The Account UI that these urls served, at ``/dashboard/account/dashboard/`` and
``/account/dashboard/`` (overview, settings, users, activity, logs, billing,
statements and api keys), is deprecated, and its urls are disabled: they are kept
in :data:`deprecated_urlpatterns`, which no urlconf includes. Only the urls of
the user menu, the ``@smarter/dashboard-user-menu`` React app, are still routed:
the profile image that it uploads, and the profiles that its Change Profile item
lists and chooses.
"""

from django.urls import path
from django.views.generic.base import RedirectView

from smarter.apps.account.const import namespace
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
from smarter.apps.account.views.dashboard.user_profiles import (
    UserProfileSelectView,
    UserProfilesView,
)
from smarter.apps.account.views.dashboard.users import UsersView, UserView
from smarter.common.utils import to_snake_case


class DashboardNamedUrls:
    """
    Holds named URL patterns for the account dashboard.

    This class provides constants for all named URL patterns used in the account dashboard views.
    The names follow the convention: 'dashboard_account_<view_name>'.
    These are referenced in Django templates as 'reverse' or 'url' tags.

    .. usage-example::

      .. html::

      <a href="{% url 'dashboard_account_dashboard_overview' %}">Go to Dashboard Overview</a>
    """

    namespace = namespace

    ACCOUNT_ACTIVITY = "dashboard_account_activity"
    ACCOUNT_API_KEYS = "dashboard_account_api_keys"
    ACCOUNT_API_KEY = "dashboard_account_api_key"
    ACCOUNT_API_KEY_NEW = "dashboard_account_api_key_new"
    ACCOUNT_DASHBOARD_OVERVIEW = "dashboard_account_dashboard_overview"
    ACCOUNT_LOGS = "dashboard_account_logs"
    ACCOUNT_PROFILE_IMAGE = "dashboard_account_profile_image"
    ACCOUNT_BILLING = "dashboard_account_billing"
    ACCOUNT_BILLING_PAYMENT_METHODS = "dashboard_account_billing_payment_methods"
    ACCOUNT_BILLING_PAYMENT_METHOD = "dashboard_account_billing_payment_method"
    ACCOUNT_BILLING_PAYMENT_METHOD_NEW = "dashboard_account_billing_payment_method_new"
    ACCOUNT_BILLING_ADDRESSES = "dashboard_account_billing_addresses"
    ACCOUNT_BILLING_ADDRESS = "dashboard_account_billing_address"
    ACCOUNT_BILLING_ADDRESS_NEW = "dashboard_account_billing_address_new"
    ACCOUNT_SETTINGS = "dashboard_account_settings"
    ACCOUNT_STATEMENTS = "dashboard_account_statements"
    ACCOUNT_USERS = "dashboard_account_users"
    ACCOUNT_USER = "dashboard_account_user"
    ACCOUNT_USER_PROFILES = to_snake_case(UserProfilesView.__name__)
    ACCOUNT_USER_PROFILE_SELECT = to_snake_case(UserProfileSelectView.__name__)


urlpatterns = [
    path("profile-image/", ProfileImageView.as_view(), name=DashboardNamedUrls.ACCOUNT_PROFILE_IMAGE),
    path("user-profiles/", UserProfilesView.as_view(), name=DashboardNamedUrls.ACCOUNT_USER_PROFILES),
    path(
        "user-profiles/select/",
        UserProfileSelectView.as_view(),
        name=DashboardNamedUrls.ACCOUNT_USER_PROFILE_SELECT,
    ),
]
"""The account dashboard's urls that are still routed: those of the user menu."""

deprecated_urlpatterns = [
    path(
        "",
        RedirectView.as_view(url="/dashboard/account/dashboard/overview/", permanent=False),
        name=DashboardNamedUrls.ACCOUNT_DASHBOARD_OVERVIEW,
    ),
    path("overview/", OverviewView.as_view(), name=DashboardNamedUrls.ACCOUNT_DASHBOARD_OVERVIEW),
    path("settings/", SettingsView.as_view(), name=DashboardNamedUrls.ACCOUNT_SETTINGS),
    path("activity/", ActivityView.as_view(), name=DashboardNamedUrls.ACCOUNT_ACTIVITY),
    path("logs/", LogsView.as_view(), name=DashboardNamedUrls.ACCOUNT_LOGS),
    # users
    # -------------------------------------------
    path("users/", UsersView.as_view(), name=DashboardNamedUrls.ACCOUNT_USERS),
    path("users/<int:user_id>/", UserView.as_view(), name=DashboardNamedUrls.ACCOUNT_USER),
    path("users/new/", UserView.as_view(), name=DashboardNamedUrls.ACCOUNT_USER),
    # billing
    # -------------------------------------------
    path("billing/", BillingView.as_view(), name=DashboardNamedUrls.ACCOUNT_BILLING),
    path(
        "billing/payment-methods/",
        PaymentMethodsView.as_view(),
        name=DashboardNamedUrls.ACCOUNT_BILLING_PAYMENT_METHODS,
    ),
    path(
        "billing/payment-methods/new/",
        PaymentMethodView.as_view(),
        name=DashboardNamedUrls.ACCOUNT_BILLING_PAYMENT_METHOD_NEW,
    ),
    path(
        "billing/payment-methods/<str:payment_method_id>/",
        PaymentMethodView.as_view(),
        name=DashboardNamedUrls.ACCOUNT_BILLING_PAYMENT_METHOD,
    ),
    path(
        "billing/billing-addresses/", BillingAddressesView.as_view(), name=DashboardNamedUrls.ACCOUNT_BILLING_ADDRESSES
    ),
    path(
        "billing/billing-addresses/new/",
        BillingAddressView.as_view(),
        name=DashboardNamedUrls.ACCOUNT_BILLING_ADDRESS_NEW,
    ),
    path(
        "billing/billing-addresses/<str:billing_address_id>",
        BillingAddressView.as_view(),
        name=DashboardNamedUrls.ACCOUNT_BILLING_ADDRESS,
    ),
    path("statements/", StatementsView.as_view(), name=DashboardNamedUrls.ACCOUNT_STATEMENTS),
    # api keys
    # -------------------------------------------
    path("api-keys/", APIKeysView.as_view(), name=DashboardNamedUrls.ACCOUNT_API_KEYS),
    path("api-keys/new/", APIKeyView.as_view(), name=DashboardNamedUrls.ACCOUNT_API_KEY_NEW),
    path("api-keys/<str:key_id>/", APIKeyView.as_view(), name=DashboardNamedUrls.ACCOUNT_API_KEY),
    path("api-keys/<str:key_id>/<str:new_api_key>/", APIKeyView.as_view(), name=DashboardNamedUrls.ACCOUNT_API_KEY_NEW),
]
"""
The deprecated Account UI's urls.

Disabled: no urlconf includes them. They are kept,
with their views, templates and static assets, until the Account UI is removed.
"""
