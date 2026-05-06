"""
URLs for the logs views.
"""

from django.urls import path

from smarter.lib import logging

from .const import namespace
from .names import DashboardLogsApiReverseNames
from .streams import stream_user_logs

app_name = namespace
logger = logging.getLogger(__name__)
logger_prefix = logging.formatted_text(__name__)


urlpatterns = [
    path("stream/", stream_user_logs, name=DashboardLogsApiReverseNames.stream),
]

# Note: future use of WebSockets for real-time log streaming.
# urlpatterns.append(
#     path("api/consumer/", RedisLogConsumer.as_asgi(), name=DashboardLogsReverseNames.consumer),  # type: ignore
# )
