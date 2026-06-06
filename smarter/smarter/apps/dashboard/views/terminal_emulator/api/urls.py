"""
URLs for the logs views.
"""

from django.urls import path

from .const import namespace
from .names import DashboardLogsApiReverseNames
from .streams import stream_user_logs

app_name = namespace


urlpatterns = [
    path("stream/", stream_user_logs, name=DashboardLogsApiReverseNames.stream),
]
