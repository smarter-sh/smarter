"""URL configuration for the web platform."""

from django.urls import include, path
from django.views.generic.base import RedirectView

from smarter.apps.account import urls as account_urls
from smarter.apps.dashboard.const import namespace
from smarter.apps.dashboard.views.dashboard import (
    ChangeLogView,
    DashboardView,
    EmailAdded,
    NotificationsView,
)
from smarter.apps.dashboard.views.dashboard.api.my_resources import MyResourcesView
from smarter.apps.dashboard.views.dashboard.api.service_health import ServiceHealthView
from smarter.apps.dashboard.views.logs import urls as logs_urls
from smarter.apps.dashboard.views.manifest_drop_zone import ManifestDropZoneView
from smarter.apps.dashboard.views.passthrough import urls as passthrough_urls
from smarter.apps.dashboard.views.profile import urls as profile_urls
from smarter.apps.plugin import urls as plugin_urls
from smarter.common.utils import camel_case_object_name
from smarter.lib import logging

logger = logging.getLogger(__name__)

app_name = namespace


class DashboardReverseNames:
    """
    A class to hold the names of the dashboard views for easy reference throughout the codebase.
    """

    namespace = namespace

    dashboard = namespace
    notifications = camel_case_object_name(NotificationsView)
    changelog = camel_case_object_name(ChangeLogView)
    email_added = camel_case_object_name(EmailAdded)
    manifest_drop_zone = camel_case_object_name(ManifestDropZoneView)
    api_my_resources = camel_case_object_name(MyResourcesView)
    api_service_health = camel_case_object_name(ServiceHealthView)


urlpatterns = [
    path("", DashboardView.as_view(), name=DashboardReverseNames.dashboard),
    path("api/my-resources/", MyResourcesView.as_view(), name=DashboardReverseNames.api_my_resources),
    path("api/service-health/", ServiceHealthView.as_view(), name=DashboardReverseNames.api_service_health),
    path("account/", include(account_urls)),
    path("plugins/", include(plugin_urls)),
    path("help/", RedirectView.as_view(url="/docs/"), name="help"),
    path("support/", RedirectView.as_view(url="/docs/"), name="support"),
    path("changelog/", ChangeLogView.as_view(), name=DashboardReverseNames.changelog),
    path("notifications/", NotificationsView.as_view(), name=DashboardReverseNames.notifications),
    path("email-added/", EmailAdded.as_view(), name=DashboardReverseNames.email_added),
    path("manifest-drop-zone/", ManifestDropZoneView.as_view(), name=DashboardReverseNames.manifest_drop_zone),
    path("logs/", include(logs_urls, namespace=logs_urls.app_name)),
    path("passthrough/", include(passthrough_urls, namespace=passthrough_urls.app_name)),
    path("profile/", include(profile_urls, namespace=profile_urls.app_name)),
]
