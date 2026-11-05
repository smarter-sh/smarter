"""
URL configuration for the terminal's ticket api, in the web console's api.

It is mounted at ``/api/web/dashboard/terminal/``, from :mod:`smarter.apps.dashboard.api.web.urls`.
The route is always registered, and is a 404 while ``smarter_settings.enable_web_console_terminal``
is off, and for every signed in user but a superuser. See :func:`..enabled.require_terminal`.

URL patterns:

- ``"ticket/"`` — :class:`.tickets.TerminalTicketApiView`
  (name: ``DashboardTerminalApiReverseNames.ticket``)

These endpoints are part of Smarter's Django-React integration. The Django view that renders a
console page reverses their urls and passes them to the page's React app, in the attributes of
its root element, and the app calls them with the browser's Django session and CSRF token. See
:doc:`/smarter-framework/developer-reference/react-integration`.
"""

from django.urls import path

from smarter.apps.dashboard.views.terminal_emulator.api.names import (
    DashboardTerminalApiReverseNames,
)
from smarter.apps.dashboard.views.terminal_emulator.api.tickets import (
    TerminalTicketApiView,
)
from smarter.apps.dashboard.views.terminal_emulator.const import terminal_namespace
from smarter.apps.dashboard.views.terminal_emulator.enabled import require_terminal

app_name = terminal_namespace


urlpatterns = [
    path(
        "ticket/",
        require_terminal(TerminalTicketApiView.as_view()),
        name=DashboardTerminalApiReverseNames.ticket,
    ),
]
