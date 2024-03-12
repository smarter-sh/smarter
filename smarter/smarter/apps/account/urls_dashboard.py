# -*- coding: utf-8 -*-
"""URL configuration for the web platform."""

from django.urls import path

from smarter.apps.account.views.dashboard.billing import BillingView
from smarter.apps.account.views.dashboard.dashboard import (
    ActivityView,
    APIKeysView,
    CardDeclinedView,
    LogsView,
    OverviewView,
    SettingsView,
    StatementsView,
)


urlpatterns = [
    path("overview/", OverviewView.as_view(), name="account_overview"),
    path("settings/", SettingsView.as_view(), name="account_settings"),
    path("activity/", ActivityView.as_view(), name="account_activity"),
    path("billing/", BillingView.as_view(), name="account_billing"),
    path("statements/", StatementsView.as_view(), name="account_statements"),
    path("api-keys/", APIKeysView.as_view(), name="account_api_keys"),
    path("logs/", LogsView.as_view(), name="account_logs"),
    path("card-declined/", CardDeclinedView.as_view(), name="card_declined"),
]
