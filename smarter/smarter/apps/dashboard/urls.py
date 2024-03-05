# -*- coding: utf-8 -*-
"""URL configuration for the web platform."""

from django.urls import include, path

from .views.dashboard import (
    ChangeLogView,
    DashboardView,
    DocumentationView,
    NotificationsView,
    PlatformHelpView,
)


urlpatterns = [
    path("", DashboardView.as_view(), name="dashboard"),
    path("account/", include("smarter.apps.account.urls")),
    path("plugins/", include("smarter.apps.plugin.urls")),
    path("legal/", include("smarter.apps.dashboard.urls_legal")),
    path("docs/", include("smarter.apps.dashboard.urls_docs")),
    path("profile/", include("smarter.apps.dashboard.urls_profile")),
    path("help/", PlatformHelpView.as_view(), name="help"),
    path("support/", PlatformHelpView.as_view(), name="support"),
    path("documentation/", DocumentationView.as_view(), name="documentation"),
    path("docs/", DocumentationView.as_view(), name="docs"),
    path("changelog/", ChangeLogView.as_view(), name="changelog"),
    path("notifications/", NotificationsView.as_view(), name="notifications"),
]
