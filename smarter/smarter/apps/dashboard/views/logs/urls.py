"""
URL configuration for the dashboard logs views.

This module registers URL patterns for the server logs sub-application of the
dashboard. Registration is conditional on the
``SMARTER_ENABLE_DASHBOARD_SERVER_LOGS`` setting: when disabled, no routes are
registered and an informational log message is emitted.

Attributes:
    app_name (str): The Django application namespace, taken from
        :data:`.const.namespace`.
    urlpatterns (list): The list of URL patterns registered for this app.
        Empty when ``smarter_settings.enable_dashboard_server_logs`` is
        ``False``.

URL patterns (when enabled):

- ``""`` — :class:`.TerminalEmulatorLogView`
  (name: ``DashboardLogsReverseNames.terminal_emulator_view``)
- ``"api/"`` — included from :mod:`.api.urls`
  (namespace: ``api_urls.app_name``)

Example:
    Include these URLs from a parent URL configuration::

        from django.urls import include, path

        urlpatterns = [
            path("logs/", include("smarter.apps.dashboard.views.logs.urls")),
        ]
"""

from django.urls import include, path

from smarter.common.conf import smarter_settings
from smarter.common.mixins import SmarterReadyState
from smarter.lib import logging

from .api import urls as api_urls
from .const import namespace
from .names import DashboardLogsReverseNames
from .reactapp import TerminalEmulatorLogView

app_name = namespace
logger = logging.getLogger(__name__)


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
        "%s Server logs app url endpoint is %s. Set env `SMARTER_ENABLE_DASHBOARD_SERVER_LOGS=false` to disable.",
        logging.formatted_text(__name__),
        SmarterReadyState.READY,
    )
else:
    logger.info(
        "%s Server logs app is %s. Set env `SMARTER_ENABLE_DASHBOARD_SERVER_LOGS=true` to enable the server logs endpoint at /logs/.",
        logging.formatted_text(__name__),
        SmarterReadyState.NOT_READY,
    )
