# -*- coding: utf-8 -*-
"""URL configuration for the web platform."""

from django.urls import include, path

from smarter.apps.dashboard.views.authentication import LogoutView

from .views.account import (
    AccountLimitsView,
    AccountOrganizationView,
    AccountProfileView,
    AccountTeamView,
    AccountView,
)
from .views.authentication import LoginRedirectView, LogoutView
from .views.dashboard import (
    APIKeysView,
    DashboardView,
    DocumentationView,
    NotificationsView,
    PlatformHelpView,
    PluginsView,
    UsageView,
)
from .views.profile import ProfileLanguageView, ProfileView


urlpatterns = [
    path("", DashboardView.as_view(), name="dashboard"),
    path("login/", LoginRedirectView.as_view(), name="login_redirector"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("api-auth/logout/", LogoutView.as_view(), name="api_logout"),
    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    path("api-keys/", APIKeysView.as_view(), name="api_keys"),
    path("plugins/", PluginsView.as_view(), name="plugins"),
    path("usage/", UsageView.as_view(), name="usage"),
    path("notifications/", NotificationsView.as_view(), name="notifications"),
    path("account/", AccountView.as_view(), name="account"),
    path("account/limits/", AccountLimitsView.as_view(), name="account_limits"),
    path("account/organization/", AccountOrganizationView.as_view(), name="account_organization"),
    path("account/profile/", AccountProfileView.as_view(), name="account_profile"),
    path("account/team/", AccountTeamView.as_view(), name="account_team"),
    path("documentation/", DocumentationView.as_view(), name="documentation"),
    path("help/", PlatformHelpView.as_view(), name="help"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("profile/language/", ProfileLanguageView.as_view(), name="language"),
    path("sign-out/", LogoutView.as_view(), name="sign_out"),
]
