# -*- coding: utf-8 -*-
"""URL configuration for the web platform."""

from django.urls import path

from smarter.apps.account.views.account import (
    AccountAPIKeysView,
    AccountLimitsView,
    AccountOrganizationView,
    AccountProfileView,
    AccountTeamView,
    AccountUsageView,
    AccountView,
)


urlpatterns = [
    path("", AccountView.as_view(), name="account"),
    path("limits/", AccountLimitsView.as_view(), name="account_limits"),
    path("organization/", AccountOrganizationView.as_view(), name="account_organization"),
    path("profile/", AccountProfileView.as_view(), name="account_profile"),
    path("team/", AccountTeamView.as_view(), name="account_team"),
    path("api-keys/", AccountAPIKeysView.as_view(), name="account_api_keys"),
    path("usage/", AccountUsageView.as_view(), name="account_usage"),
]
