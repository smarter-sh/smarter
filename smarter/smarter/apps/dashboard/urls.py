"""URL configuration for the web platform."""

from django.urls import include, path
from django.views.generic.base import RedirectView

from .views.dashboard import ChangeLogView, DashboardView, EmailAdded, NotificationsView


urlpatterns = [
    path("", DashboardView.as_view(), name="dashboard"),
    path("account/", include("smarter.apps.account.urls")),
    path("plugins/", include("smarter.apps.plugin.urls")),
    path("profile/", include("smarter.apps.dashboard.urls_profile")),
    path("help/", RedirectView.as_view(url="/docs/"), name="help"),
    path("support/", RedirectView.as_view(url="/docs/"), name="support"),
    path("changelog/", ChangeLogView.as_view(), name="changelog"),
    path("notifications/", NotificationsView.as_view(), name="notifications"),
    path("email-added/", EmailAdded.as_view(), name="email-added"),
]
