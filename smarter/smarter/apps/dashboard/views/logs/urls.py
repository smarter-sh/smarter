"""
URLs for the logs views.
"""

from django.urls import include, path

from smarter.common.conf import smarter_settings
from smarter.lib import logging

from .api import urls as api_urls
from .const import namespace
from .names import DashboardLogsReverseNames
from .reactapp import TerminalEmulatorLogView

app_name = namespace
logger = logging.getLogger(__name__)
logger_prefix = logging.formatted_text(__name__)


urlpatterns = []

if smarter_settings.enable_dashboard_server_logs:
    urlpatterns.append(
        path("", TerminalEmulatorLogView.as_view(), name=DashboardLogsReverseNames.terminal_emulator_view),
    )
    urlpatterns.append(
        path("api/", include(api_urls, namespace=api_urls.app_name)),
    )

    # Note: future use of WebSockets for real-time log streaming.
    # urlpatterns.append(
    #     path("api/consumer/", RedisLogConsumer.as_asgi(), name=DashboardLogsReverseNames.consumer),  # type: ignore
    # )

    logger.info(
        "%s Server logs app url endpoint enabled. Set env `SMARTER_ENABLE_DASHBOARD_SERVER_LOGS=false` to disable.",
        logging.formatted_text(__name__),
    )
else:
    logger.info(
        "%s Server logs app is disabled. Set env `SMARTER_ENABLE_DASHBOARD_SERVER_LOGS=true` to enable the server logs endpoint at /logs/.",
        logging.formatted_text(__name__),
    )
