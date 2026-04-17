"""URL configuration for the web platform."""

from django.urls import include, path
from django.views.generic.base import RedirectView

from smarter.apps.account import urls as account_urls
from smarter.apps.dashboard import urls_profile
from smarter.apps.plugin import urls as plugin_urls

from .const import namespace
from .views.dashboard import ChangeLogView, DashboardView, EmailAdded, NotificationsView
from .views.server_logs import stream_global_logs

app_name = namespace

urlpatterns = [
    path("", DashboardView.as_view(), name="dashboard"),
    path("account/", include(account_urls)),
    path("plugins/", include(plugin_urls)),
    path("profile/", include(urls_profile)),
    path("help/", RedirectView.as_view(url="/docs/"), name="help"),
    path("support/", RedirectView.as_view(url="/docs/"), name="support"),
    path("changelog/", ChangeLogView.as_view(), name="changelog"),
    path("notifications/", NotificationsView.as_view(), name="notifications"),
    path("email-added/", EmailAdded.as_view(), name="email-added"),
    path("logs/", stream_global_logs, name="stream_global_logs"),
]
