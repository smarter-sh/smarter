"""
URL configuration for the web console's Terminal page.

The routes are always registered, and are a 404 while
``smarter_settings.app_dashboard_web_console_terminal_enable`` is off, and for every signed in user but a
superuser. See :func:`.enabled.require_terminal`. The terminal's ticket api is in the web
console's api, at ``/api/web/dashboard/terminal/ticket/``: see :mod:`.api.urls`. The terminal's
WebSocket is routed in :mod:`smarter.consumers`.

URL patterns:

- ``""`` — :class:`.reactapp.TerminalEmulatorView`
  (name: ``DashboardTerminalReverseNames.terminal_emulator_view``)
"""

from django.urls import path

from smarter.common.conf import smarter_settings
from smarter.common.mixins import SmarterReadyState
from smarter.lib import logging

from .const import terminal_namespace
from .enabled import require_terminal
from .names import DashboardTerminalReverseNames
from .reactapp import TerminalEmulatorView

app_name = terminal_namespace
logger = logging.getLogger(__name__)


urlpatterns = [
    path(
        "",
        require_terminal(TerminalEmulatorView.as_view()),
        name=DashboardTerminalReverseNames.terminal_emulator_view,
    ),
]

(logger.debug if smarter_settings.app_dashboard_web_console_terminal_enable else logger.info)(
    "Terminal app is %s. Set env `SMARTER_APP_DASHBOARD_WEB_CONSOLE_TERMINAL_ENABLE=%s` to %s it.",
    (
        SmarterReadyState.READY
        if smarter_settings.app_dashboard_web_console_terminal_enable
        else SmarterReadyState.NOT_READY
    ),
    "false" if smarter_settings.app_dashboard_web_console_terminal_enable else "true",
    "disable" if smarter_settings.app_dashboard_web_console_terminal_enable else "enable",
)
