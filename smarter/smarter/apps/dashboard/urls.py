"""URL configuration for the web platform."""

import logging

from django.urls import include, path
from django.views.generic.base import RedirectView

from smarter.apps.account import urls as account_urls
from smarter.apps.dashboard import urls_profile
from smarter.apps.plugin import urls as plugin_urls
from smarter.common.conf import smarter_settings
from smarter.common.helpers.console_helpers import formatted_text
from smarter.common.utils import camel_case_object_name

from .const import namespace
from .streams import stream_global_logs
from .views.dashboard import ChangeLogView, DashboardView, EmailAdded, NotificationsView
from .views.logs import TerminalEmulatorLogView
from .views.manifest_drop_zone import ManifestDropZoneView

logger = logging.getLogger(__name__)

app_name = namespace


class DashboardNames:
    """
    A class to hold the names of the dashboard views for easy reference throughout the codebase.
    """

    namespace = namespace

    logs = camel_case_object_name(TerminalEmulatorLogView)
    logs_stream = camel_case_object_name(stream_global_logs)
    notifications = camel_case_object_name(NotificationsView)
    changelog = camel_case_object_name(ChangeLogView)
    email_added = camel_case_object_name(EmailAdded)
    manifest_drop_zone = camel_case_object_name(ManifestDropZoneView)


urlpatterns = [
    path("", DashboardView.as_view(), name="dashboard"),
    path("account/", include(account_urls)),
    path("plugins/", include(plugin_urls)),
    path("profile/", include(urls_profile)),
    path("help/", RedirectView.as_view(url="/docs/"), name="help"),
    path("support/", RedirectView.as_view(url="/docs/"), name="support"),
    path("changelog/", ChangeLogView.as_view(), name=DashboardNames.changelog),
    path("notifications/", NotificationsView.as_view(), name=DashboardNames.notifications),
    path("email-added/", EmailAdded.as_view(), name=DashboardNames.email_added),
    path("apply/", ManifestDropZoneView.as_view(), name=DashboardNames.manifest_drop_zone),
]

if smarter_settings.enable_server_logs:
    # enable end points for the React terminal emulator logs view and its associated log stream
    urlpatterns.append(
        path("logs/", TerminalEmulatorLogView.as_view(), name=DashboardNames.logs),
    )
    urlpatterns.append(
        path("logs/stream/", stream_global_logs, name=DashboardNames.logs_stream),
    )
    logger_prefix = formatted_text(__name__)
    logger.info("%s Server logs app url endpoint enabled.", logger_prefix)
else:
    logger.info(
        "%s Server logs app is disabled. Set env `SMARTER_ENABLE_SERVER_LOGS=true` to enable the server logs endpoint at /logs/.",
        formatted_text(__name__),
    )
