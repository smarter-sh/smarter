# -*- coding: utf-8 -*-
"""URL configuration for the web platform."""

from django.urls import path

from smarter.apps.account.views.dashboard.api_keys import APIKeysView, APIKeyView
from smarter.apps.account.views.dashboard.billing import (
    BillingAddressesView,
    BillingView,
    PaymentMethodsView,
)
from smarter.apps.account.views.dashboard.dashboard import (
    ActivityView,
    CardDeclinedView,
    LogsView,
    OverviewView,
    StatementsView,
)
from smarter.apps.account.views.dashboard.settings import SettingsView
from smarter.apps.account.views.dashboard.users import UsersView, UserView


urlpatterns = [
    path("overview/", OverviewView.as_view(), name="account_overview"),
    path("settings/", SettingsView.as_view(), name="account_settings"),
    path("activity/", ActivityView.as_view(), name="account_activity"),
    path("billing/", BillingView.as_view(), name="account_billing"),
    path("users/", UsersView.as_view(), name="account_users"),
    path("users/<int:user_id>/", UserView.as_view(), name="account_user"),
    path("billing/payment-methods", PaymentMethodsView.as_view(), name="account_billing_payment_methods"),
    path("billing/billing-addresses", BillingAddressesView.as_view(), name="account_billing_addresses"),
    path("statements/", StatementsView.as_view(), name="account_statements"),
    path("api-keys/", APIKeysView.as_view(), name="account_api_keys"),
    path("api-keys/<int:apikey_id>/", APIKeyView.as_view(), name="account_api_key"),
    path("logs/", LogsView.as_view(), name="account_logs"),
    path("card-declined/", CardDeclinedView.as_view(), name="card_declined"),
]
