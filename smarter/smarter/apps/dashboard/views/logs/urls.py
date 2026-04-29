"""
URLs for the logs views.
"""

from django.urls import path

from smarter.common.conf import smarter_settings
from smarter.lib import logging

from .const import namespace
from .names import LogsNames

# from .consumers import RedisLogConsumer
from .reactapp import TerminalEmulatorLogView
from .streams import stream_global_logs

app_name = namespace
logger = logging.getLogger(__name__)
logger_prefix = logging.formatted_text(__name__)


urlpatterns = []

if smarter_settings.enable_dashboard_server_logs:
    urlpatterns.append(
        path("", TerminalEmulatorLogView.as_view(), name=LogsNames.logs),
    )
    urlpatterns.append(
        path("api/stream/", stream_global_logs, name=LogsNames.stream),
    )
    # urlpatterns.append(
    #     path("api/consumer/", RedisLogConsumer.as_asgi(), name=LogsNames.consumer),  # type: ignore
    # )

    logger.info("%s Server logs app url endpoint enabled.", logger_prefix)
else:
    logger.info(
        "%s Server logs app is disabled. Set env `SMARTER_ENABLE_DASHBOARD_SERVER_LOGS=true` to enable the server logs endpoint at /logs/.",
        logger_prefix,
    )
