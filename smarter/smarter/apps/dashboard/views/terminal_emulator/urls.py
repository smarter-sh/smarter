"""
URL configuration for the dashboard's server logs, in the web console's api.

It is mounted at ``/api/web/dashboard/logs/``, from :mod:`smarter.apps.dashboard.api.web.urls`.
The log stream, at ``stream/``, is read by the Prompt Passthrough's Server Logs tab and by Smarter
Chat's Console in the workbench. Registration is conditional on the
``SMARTER_ENABLE_DASHBOARD_SERVER_LOGS`` setting: when disabled, no routes are registered and an
informational log message is emitted. While the ``ENABLE_WEB_CONSOLE_SERVER_LOGS`` waffle switch is
off, the registered routes are a 404. See :func:`.enabled.require_server_logs`.

Attributes:
    app_name (str): The Django application namespace, taken from
        :data:`~smarter.apps.dashboard.views.terminal_emulator.const.namespace`.
    urlpatterns (list): The list of URL patterns registered for this app.
        Empty when ``smarter_settings.enable_dashboard_server_logs`` is
        ``False``.

URL patterns (when enabled):

- ``"stream/"`` — :func:`.api.streams.stream_user_logs`
  (name: ``DashboardLogsApiReverseNames.stream``)

These endpoints are part of Smarter's Django-React integration. The Django view that renders a
console page reverses their urls and passes them to the page's React app, in the attributes of
its root element, and the app calls them with the browser's Django session and CSRF token. See
:doc:`/smarter-framework/developer-reference/react-integration`.
"""

from django.urls import path

from smarter.apps.dashboard.views.terminal_emulator.api.names import (
    DashboardLogsApiReverseNames,
)
from smarter.apps.dashboard.views.terminal_emulator.api.streams import stream_user_logs
from smarter.apps.dashboard.views.terminal_emulator.const import namespace
from smarter.apps.dashboard.views.terminal_emulator.enabled import require_server_logs
from smarter.common.conf import smarter_settings
from smarter.common.mixins import SmarterReadyState
from smarter.lib import logging

app_name = namespace
logger = logging.getLogger(__name__)


urlpatterns = []

if smarter_settings.enable_dashboard_server_logs:
    urlpatterns.append(
        path("stream/", require_server_logs(stream_user_logs), name=DashboardLogsApiReverseNames.stream),
    )

    logger.debug(
        "%s Server logs app url endpoint is %s. Set env `SMARTER_ENABLE_DASHBOARD_SERVER_LOGS=false` to disable.",
        logging.SmarterFormattedText.text(__name__),
        SmarterReadyState.READY,
    )
else:
    logger.info(
        "%s Server logs app is %s. Set env `SMARTER_ENABLE_DASHBOARD_SERVER_LOGS=true` to enable the server logs endpoint at /api/web/dashboard/logs/.",
        logging.SmarterFormattedText.text(__name__),
        SmarterReadyState.NOT_READY,
    )
