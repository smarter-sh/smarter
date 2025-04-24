"""URL configuration for the web platform."""

from django.urls import path
from django.views.generic.base import RedirectView

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
    CardDeclinedView,
    LogsView,
    OverviewView,
    StatementsView,
)
from smarter.apps.account.views.dashboard.secrets import SecretsView, SecretView
from smarter.apps.account.views.dashboard.settings import SettingsView
from smarter.apps.account.views.dashboard.users import UsersView, UserView


urlpatterns = [
    path(
        "",
        RedirectView.as_view(url="/dashboard/account/dashboard/overview/", permanent=False),
        name="dashboard_account_dashboard_overview",
    ),
    path("overview/", OverviewView.as_view(), name="account_overview"),
    path("settings/", SettingsView.as_view(), name="account_settings"),
    path("activity/", ActivityView.as_view(), name="account_activity"),
    path("logs/", LogsView.as_view(), name="account_logs"),
    path("card-declined/", CardDeclinedView.as_view(), name="card_declined"),
    # users
    # -------------------------------------------
    path("users/", UsersView.as_view(), name="account_users"),
    path("users/<int:user_id>/", UserView.as_view(), name="account_user"),
    path("users/new/", UserView.as_view(), name="account_user_new"),
    # billing
    # -------------------------------------------
    path("billing/", BillingView.as_view(), name="account_billing"),
    path("billing/payment-methods/", PaymentMethodsView.as_view(), name="account_billing_payment_methods"),
    path("billing/payment-methods/new/", PaymentMethodView.as_view(), name="account_billing_payment_method_new"),
    path(
        "billing/payment-methods/<str:payment_method_id>/",
        PaymentMethodView.as_view(),
        name="account_billing_payment_method",
    ),
    path("billing/billing-addresses/", BillingAddressesView.as_view(), name="account_billing_addresses"),
    path("billing/billing-addresses/new/", BillingAddressView.as_view(), name="account_billing_address_new"),
    path(
        "billing/billing-addresses/<str:billing_address_id>",
        BillingAddressView.as_view(),
        name="account_billing_address",
    ),
    path("statements/", StatementsView.as_view(), name="account_statements"),
    # api keys
    # -------------------------------------------
    path("api-keys/", APIKeysView.as_view(), name="account_api_keys"),
    path("api-keys/new/", APIKeyView.as_view(), name="account_api_key_new"),
    path("api-keys/<str:key_id>/", APIKeyView.as_view(), name="account_api_key"),
    path("api-keys/<str:key_id>/<str:new_api_key>/", APIKeyView.as_view(), name="account_new_api_key"),
    # secrets
    # -------------------------------------------
    path("secrets/", SecretsView.as_view(), name="account_secrets"),
    path("secrets/new/", SecretView.as_view(), name="account_secret_new"),
    path("secrets/<int:secret_id>/", SecretView.as_view(), name="account_secret"),
]
