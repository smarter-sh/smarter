"""URLs for the logs views."""

from django.urls import path

from ..enabled import require_server_logs
from .const import namespace
from .names import DashboardLogsApiReverseNames
from .streams import stream_user_logs

app_name = namespace


urlpatterns = [
    path("stream/", require_server_logs(stream_user_logs), name=DashboardLogsApiReverseNames.stream),
]
