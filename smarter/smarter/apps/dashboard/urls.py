# -*- coding: utf-8 -*-
"""URL configuration for the web platform."""

from django.urls import include, path

from .views.account import (
    account,
    account_limits,
    account_organization,
    account_profile,
    account_team,
)
from .views.authentication import LogoutView, login_redirector
from .views.dashboard import (
    APIKeysView,
    DashboardView,
    DocumentationView,
    NotificationsView,
    PlatformHelpView,
    PluginsView,
    UsageView,
)
from .views.profile import language, profile, sign_out


urlpatterns = [
    path("", DashboardView.as_view(), name="dashboard"),
    path("login/", login_redirector, name="login_redirector"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("api-auth/logout/", LogoutView.as_view(), name="api_logout"),
    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    path("api-keys/", APIKeysView.as_view(), name="api_keys"),
    path("plugins/", PluginsView.as_view(), name="plugins"),
    path("usage/", UsageView.as_view(), name="usage"),
    path("notifications/", NotificationsView.as_view(), name="notifications"),
    path("account/", account, name="account"),
    path("account/limits/", account_limits, name="account_limits"),
    path("account/organization/", account_organization, name="account_organization"),
    path("account/profile/", account_profile, name="account_profile"),
    path("account/team/", account_team, name="account_team"),
    path("documentation/", DocumentationView.as_view(), name="documentation"),
    path("help/", PlatformHelpView.as_view(), name="help"),
    path("profile/", profile, name="profile"),
    path("language/", language, name="language"),
    path("sign-out/", sign_out, name="sign_out"),
]
