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
from .views import (
    ChangeLogView,
    DashboardView,
    EmailAdded,
    ManifestDropZoneView,
    NotificationsView,
    PromptPassthroughView,
    TerminalEmulatorLogView,
)

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
    prompt_passthrough = camel_case_object_name(PromptPassthroughView)


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
]

if smarter_settings.enable_dashboard_server_logs:
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
        "%s Server logs app is disabled. Set env `SMARTER_ENABLE_DASHBOARD_SERVER_LOGS=true` to enable the server logs endpoint at /logs/.",
        formatted_text(__name__),
    )

if smarter_settings.enable_dashboard_passthrough_prompt:
    urlpatterns.append(
        path("prompt/", PromptPassthroughView.as_view(), name=DashboardNames.prompt_passthrough),
    )
    logger.info(
        "%s Dashboard prompt passthrough endpoint enabled.",
        formatted_text(__name__),
    )
else:
    logger.info(
        "%s Dashboard prompt passthrough endpoint is disabled. Set env `SMARTER_ENABLE_DASHBOARD_PASSTHROUGH_PROMPT=true` to enable the LLM prompt API passthrough request/response endpoint at /prompt/.",
        formatted_text(__name__),
    )

if smarter_settings.enable_dashboard_apply:
    urlpatterns.append(
        path("apply/", ManifestDropZoneView.as_view(), name=DashboardNames.manifest_drop_zone),
    )
    logger.info(
        "%s Dashboard apply drop zone endpoint enabled. This allows users to apply manifests by dragging and dropping files onto the dashboard. Set env `SMARTER_ENABLE_DASHBOARD_APPLY=false` to disable.",
        formatted_text(__name__),
    )
else:
    logger.info(
        "%s Dashboard apply drop zone endpoint is disabled. Set env `SMARTER_ENABLE_DASHBOARD_APPLY=true` to enable the manifest drop zone at /apply/.",
        formatted_text(__name__),
    )
