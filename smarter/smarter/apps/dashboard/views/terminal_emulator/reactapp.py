# pylint: disable=W0613
"""
The web console's Terminal page: a bash shell inside the server's container, for superusers.

This module provides the Django view that renders a browser-based terminal window styled after
macOS Terminal.app. The terminal is the ``@smarter/terminal-emulator`` React app, which draws
with xterm.js. It POSTs to the ticket api for a single use ticket, then opens the terminal's
WebSocket with it, which runs a bash shell in the server process that accepts it. See
:mod:`.api.tickets` and :mod:`.api.consumers`.

Classes:
    TerminalEmulatorView: Renders the React-based terminal page.

Example:
    Wire up the view in your URL configuration::

        from smarter.apps.dashboard.views.terminal_emulator.enabled import require_terminal
        from smarter.apps.dashboard.views.terminal_emulator.reactapp import TerminalEmulatorView

        urlpatterns = [
            path("terminal/", require_terminal(TerminalEmulatorView.as_view()), name="terminal_emulator_view"),
        ]
"""

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from smarter.lib import logging
from smarter.lib.django.shortcuts import reverse
from smarter.lib.django.views import (
    SmarterAuthenticatedNeverCachedWebView,
)
from smarter.lib.django.waffle import SmarterWaffleSwitches, switch_is_active

logger = logging.getLogger(__name__)


# pylint: disable=C0415
class TerminalEmulatorView(SmarterAuthenticatedNeverCachedWebView):
    """
    Renders the React-based Terminal page.

    Extends :class:`~smarter.lib.django.views.SmarterAuthenticatedNeverCachedWebView`
    to ensure that only authenticated users can access the terminal and that
    responses are never served from cache. The url patterns wrap it in
    :func:`.enabled.require_terminal`, so that only a superuser can, and only while the terminal
    is enabled.

    On a ``GET`` request the view builds a context dictionary containing the ticket api's URL and
    the cookie names required by the React frontend, then renders ``react/terminal-emulator.html``.

    Context keys passed to the template:

    .. code-block:: python

        {
            "terminal": {
                "root_id": str,                   # DOM element id for the React root
                "csrf_cookie_name": str,          # Django CSRF cookie name
                "django_session_cookie_name": str,# Django session cookie name
                "cookie_domain": str,             # Session cookie domain
                "api_url": str,                   # The ticket api's URL
                "react_debug_mode": bool,
                "smarter_request_id": str,
            }
        }
    """

    @property
    def formatted_class_name(self) -> str:
        """Returns a formatted string of the class name for logging purposes."""
        class_name = f"{__name__}.{TerminalEmulatorView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        Render the Terminal page.

        :param request: The incoming HTTP GET request from the client.
        :type request: django.http.HttpRequest
        :param args: Additional positional arguments forwarded by the URL dispatcher.
        :param kwargs: Additional keyword arguments forwarded by the URL dispatcher.
        :returns: An HTTP 200 response rendering ``react/terminal-emulator.html``
            with the terminal context dictionary.
        :rtype: django.http.HttpResponse
        """
        from smarter.apps.dashboard.views.views.urls import DashboardReverseNames

        from .names import DashboardTerminalReverseNames

        context = {
            "terminal": {
                "root_id": "smarter-terminal-emulator-root",
                "csrf_cookie_name": settings.CSRF_COOKIE_NAME,  # this is the CSRF token cookie that should be included in the
                # header of the POST request from the frontend.
                "django_session_cookie_name": settings.SESSION_COOKIE_NAME,  # this is the Django session.
                "cookie_domain": settings.SESSION_COOKIE_DOMAIN,
                "api_url": reverse(
                    DashboardReverseNames.namespace,
                    DashboardTerminalReverseNames.namespace,
                    DashboardTerminalReverseNames.ticket,
                ),  # the ticket api, whose ticket opens the terminal's WebSocket.
                "react_debug_mode": switch_is_active(SmarterWaffleSwitches.ENABLE_REACTAPP_DEBUG_MODE),
                "smarter_request_id": self.generate_smarter_request_id(),
            }
        }
        self.template_path = "react/terminal-emulator.html"

        logger.debug(
            "%s.get() rendering terminal emulator with context: %s",
            self.formatted_class_name,
            logging.SmarterFormattedText.json(context),
        )
        return render(request, self.template_path, context=context)
