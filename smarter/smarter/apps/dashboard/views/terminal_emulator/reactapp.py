# pylint: disable=W0613
"""
Backend for the terminal emulator view in the dashboard logs app.

This module provides the Django view that renders a browser-based terminal
emulation window styled after macOS Terminal.app. The terminal is backed by a
React component and is used in the web console to give users direct access to
Linux command-line tools such as ``curl`` without leaving the browser.

The rendered page connects to a WebSocket endpoint that streams log data and
accepts command input, with authentication enforced via Django's session and
CSRF mechanisms.

Classes:
    TerminalEmulatorLogView: Authenticated view that renders the React-based
        terminal emulator page.

Example:
    Wire up the view in your URL configuration::

        from smarter.apps.dashboard.views.terminal_emulator.reactapp import TerminalEmulatorLogView

        urlpatterns = [
            path("terminal/", TerminalEmulatorLogView.as_view(), name="smarter-terminal-emulator"),
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

logger = logging.getLogger(__name__)


# pylint: disable=C0415
class TerminalEmulatorLogView(SmarterAuthenticatedNeverCachedWebView):
    """
    Authenticated view that renders the React-based terminal emulator page.

    Extends :class:`~smarter.lib.django.views.SmarterAuthenticatedNeverCachedWebView`
    to ensure that only authenticated users can access the terminal and that
    responses are never served from cache.

    On a ``GET`` request the view builds a context dictionary containing the
    WebSocket API URL and the relevant cookie/session names required by the
    React frontend, then renders ``react/terminal-emulator.html``.

    Attributes:
        template_path (str): Set at request time to
            ``"react/terminal-emulator.html"``.

    Context keys passed to the template:

    .. code-block:: python

        {
            "terminal": {
                "root_id": str,                  # DOM element id for the React root
                "csrf_cookie_name": str,          # Django CSRF cookie name
                "django_session_cookie_name": str,# Django session cookie name
                "cookie_domain": str,             # Session cookie domain
                "api_url": str,                   # WebSocket endpoint URL
            }
        }
    """

    @property
    def formatted_class_name(self) -> str:
        """Returns a formatted string of the class name for logging purposes."""
        class_name = f"{__name__}.{TerminalEmulatorLogView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        Render the terminal emulator page for the authenticated user.

        Builds a context dictionary that wires the React frontend to the
        correct WebSocket API endpoint and supplies the cookie/session names
        needed for CSRF and session authentication. The context is then passed
        to ``react/terminal-emulator.html``.

        :param request: The incoming HTTP GET request from the client.
        :type request: django.http.HttpRequest
        :param args: Additional positional arguments forwarded by the URL dispatcher.
        :param kwargs: Additional keyword arguments forwarded by the URL dispatcher.
        :returns: An HTTP 200 response rendering ``react/terminal-emulator.html``
            with the terminal context dictionary.
        :rtype: django.http.HttpResponse
        """
        from smarter.apps.dashboard.views.terminal_emulator.api.urls import (
            DashboardLogsApiReverseNames,
        )
        from smarter.apps.dashboard.views.views.urls import DashboardReverseNames

        from .names import DashboardLogsReverseNames

        context = {
            "terminal": {
                "root_id": "smarter-terminal-emulator-root",
                "csrf_cookie_name": settings.CSRF_COOKIE_NAME,  # this is the CSRF token cookie that should be included in the
                # header of the POST request from the frontend.
                "django_session_cookie_name": settings.SESSION_COOKIE_NAME,  # this is the Django session.
                "cookie_domain": settings.SESSION_COOKIE_DOMAIN,
                "api_url": reverse(
                    DashboardReverseNames.namespace,
                    DashboardLogsReverseNames.namespace,
                    DashboardLogsApiReverseNames.namespace,
                    DashboardLogsApiReverseNames.stream,
                ),  # the WebSocket endpoint with the log data stream.
            }
        }
        self.template_path = "react/terminal-emulator.html"

        logger.debug(
            "%s.get() rendering terminal emulator with context: %s",
            self.formatted_class_name,
            logging.formatted_json(context),
        )
        return render(request, self.template_path, context=context)
