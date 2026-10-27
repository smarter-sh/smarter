"""
URL configuration for the dashboard's server logs.

The log stream, at ``api/stream/``, is read by the Prompt Passthrough's Server Logs tab.
Registration is conditional on the ``SMARTER_ENABLE_DASHBOARD_SERVER_LOGS`` setting: when
disabled, no routes are registered and an informational log message is emitted. While the
``ENABLE_WEB_CONSOLE_SERVER_LOGS`` waffle switch is off, the registered routes are a 404. See
:func:`.enabled.require_server_logs`.

Attributes:
    app_name (str): The Django application namespace, taken from
        :data:`.const.namespace`.
    urlpatterns (list): The list of URL patterns registered for this app.
        Empty when ``smarter_settings.enable_dashboard_server_logs`` is
        ``False``.

URL patterns (when enabled):

- ``"api/"`` — included from :mod:`.api.urls`
  (namespace: ``api_urls.app_name``)

Example:
    Include these URLs from a parent URL configuration::

        from django.urls import include, path

        urlpatterns = [
            path("logs/", include("smarter.apps.dashboard.views.terminal_emulator.urls")),
        ]
"""

from django.urls import include, path

from smarter.common.conf import smarter_settings
from smarter.common.mixins import SmarterReadyState
from smarter.lib import logging

from .api import urls as api_urls
from .const import namespace

app_name = namespace
logger = logging.getLogger(__name__)


urlpatterns = []

if smarter_settings.enable_dashboard_server_logs:
    urlpatterns.append(
        path("api/", include(api_urls, namespace=api_urls.app_name)),
    )

    logger.debug(
        "%s Server logs app url endpoint is %s. Set env `SMARTER_ENABLE_DASHBOARD_SERVER_LOGS=false` to disable.",
        logging.SmarterFormattedText.text(__name__),
        SmarterReadyState.READY,
    )
else:
    logger.info(
        "%s Server logs app is %s. Set env `SMARTER_ENABLE_DASHBOARD_SERVER_LOGS=true` to enable the server logs endpoint at /logs/.",
        logging.SmarterFormattedText.text(__name__),
        SmarterReadyState.NOT_READY,
    )
