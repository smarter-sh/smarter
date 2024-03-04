# -*- coding: utf-8 -*-
"""URL configuration for the web platform."""

from django.urls import include, path

from smarter.apps.dashboard.views.authentication import LogoutView

from .views.authentication import LoginRedirectView, LogoutView
from .views.dashboard import (
    ChangeLogView,
    DashboardView,
    DocumentationView,
    NotificationsView,
    PlatformHelpView,
)
from .views.profile import ProfileLanguageView, ProfileView


urlpatterns = [
    path("", DashboardView.as_view(), name="dashboard"),
    path("login/", LoginRedirectView.as_view(), name="login_redirector"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("sign-out/", LogoutView.as_view(), name="sign_out"),
    path("api-auth/logout/", LogoutView.as_view(), name="api_logout"),
    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    path("account/", include("smarter.apps.account.urls")),
    path("plugins/", include("smarter.apps.plugin.urls")),
    path("legal/", include("smarter.apps.dashboard.urls_legal")),
    path("help/", PlatformHelpView.as_view(), name="help"),
    path("support/", PlatformHelpView.as_view(), name="support"),
    path("documentation/", DocumentationView.as_view(), name="documentation"),
    path("docs/", DocumentationView.as_view(), name="docs"),
    path("changelog/", ChangeLogView.as_view(), name="changelog"),
    path("notifications/", NotificationsView.as_view(), name="notifications"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("profile/language/", ProfileLanguageView.as_view(), name="language"),
]
