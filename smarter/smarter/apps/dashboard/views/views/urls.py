"""URL configuration for the web platform."""

from django.urls import include, path
from django.views.generic.base import RedirectView

from smarter.apps.account import urls as account_urls
from smarter.apps.dashboard.const import namespace
from smarter.apps.dashboard.views.views import (
    ChangeLogView,
    DashboardView,
    EmailAdded,
    NotificationsView,
)
from smarter.apps.dashboard.views.views.api import urls as dashboard_api_urls
from smarter.apps.dashboard.views.views.api.my_resources import MyResourcesView
from smarter.apps.dashboard.views.views.api.service_health import ServiceHealthView
from smarter.apps.plugin import urls as plugin_urls
from smarter.common.conf import smarter_settings
from smarter.common.utils import to_snake_case
from smarter.lib import logging

logger = logging.getLogger(__name__)


class DashboardReverseNames:
    """A class to hold the names of the dashboard views for easy reference throughout the codebase."""

    namespace = namespace

    dashboard = namespace
    notifications = to_snake_case(NotificationsView.__name__)
    changelog = to_snake_case(ChangeLogView.__name__)
    email_added = to_snake_case(EmailAdded.__name__)
    api_my_resources = to_snake_case(MyResourcesView.__name__)
    api_service_health = to_snake_case(ServiceHealthView.__name__)


urlpatterns = [
    path("", DashboardView.as_view(), name=DashboardReverseNames.dashboard),
    path("api/", include(dashboard_api_urls, namespace=dashboard_api_urls.app_name)),
    path("account/", include(account_urls)),
    path("plugins/", include(plugin_urls)),
    path("help/", RedirectView.as_view(url="/docs/"), name="help"),
    path("support/", RedirectView.as_view(url="/docs/"), name="support"),
    path("changelog/", ChangeLogView.as_view(), name=DashboardReverseNames.changelog),
    path("notifications/", NotificationsView.as_view(), name=DashboardReverseNames.notifications),
    path("email-added/", EmailAdded.as_view(), name=DashboardReverseNames.email_added),
]

if smarter_settings.enable_dropzone_manifest_apply:
    logger.info(
        "%s manifest drop zone enabled. Set env ENABLE_DASHBOARD_APPLY=false to disable.",
        logging.formatted_text(__name__),
    )
else:
    logger.info(
        "%s manifest drop zone disabled. Set env ENABLE_DASHBOARD_APPLY=true to enable.",
        logging.formatted_text(__name__),
    )
