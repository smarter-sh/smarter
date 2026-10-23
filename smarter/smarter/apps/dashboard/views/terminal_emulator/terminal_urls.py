"""
URL configuration for the web console's Terminal page and its ticket api.

The routes are always registered, and are a 404 while
``smarter_settings.enable_web_console_terminal`` is off, and for every signed in user but a
superuser. See :func:`.enabled.require_terminal`. The terminal's WebSocket is routed in
:mod:`smarter.consumers`.

URL patterns:

- ``""`` — :class:`.reactapp.TerminalEmulatorView`
  (name: ``DashboardTerminalReverseNames.terminal_emulator_view``)
- ``"api/ticket/"`` — :class:`.api.tickets.TerminalTicketApiView`
  (name: ``DashboardTerminalReverseNames.ticket``)
"""

from django.urls import path

from smarter.common.conf import smarter_settings
from smarter.common.mixins import SmarterReadyState
from smarter.lib import logging

from .api.tickets import TerminalTicketApiView
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
    path(
        "api/ticket/",
        require_terminal(TerminalTicketApiView.as_view()),
        name=DashboardTerminalReverseNames.ticket,
    ),
]

(logger.debug if smarter_settings.enable_web_console_terminal else logger.info)(
    "%s Terminal app is %s. Set env `SMARTER_ENABLE_WEB_CONSOLE_TERMINAL=%s` to %s it.",
    logging.formatted_text(__name__),
    SmarterReadyState.READY if smarter_settings.enable_web_console_terminal else SmarterReadyState.NOT_READY,
    "false" if smarter_settings.enable_web_console_terminal else "true",
    "disable" if smarter_settings.enable_web_console_terminal else "enable",
)
