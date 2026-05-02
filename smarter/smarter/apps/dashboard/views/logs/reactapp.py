# pylint: disable=W0613
"""
Backend for a terminal emulation window that looks like macOS Terminal.app.
It is used in the web console to provide direct support for Linux curl and
other command line tools.
"""

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.urls import reverse

from smarter.lib import logging
from smarter.lib.django.views import (
    SmarterAuthenticatedNeverCachedWebView,
)

logger = logging.getLogger(__name__)


# pylint: disable=C0415
class TerminalEmulatorLogView(SmarterAuthenticatedNeverCachedWebView):
    """
    View for rendering the React component terminal emulator.
    """

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        View for rendering the Monaco terminal emulation page
        which only receives JSON dicts of LLM prompts.

        :param request: The HTTP request object from the client.
        :return: An HttpResponse rendering the terminal emulator page with the appropriate context.
        :rtype: HttpResponse
        """
        from .names import LogsNames

        reverse_name = ":".join([LogsNames.namespace, LogsNames.stream])

        context = {
            "terminal": {
                "root_id": "smarter-terminal-emulator-root",
                "csrf_cookie_name": settings.CSRF_COOKIE_NAME,  # this is the CSRF token cookie that should be included in the header of the POST request from the frontend.
                "django_session_cookie_name": settings.SESSION_COOKIE_NAME,  # this is the Django session.
                "cookie_domain": settings.SESSION_COOKIE_DOMAIN,
                "api_url": reverse(reverse_name),  # the WebSocket endpoint with the log data stream.
            }
        }
        self.template_path = "react/terminal-emulator.html"

        logger.debug("%s.get() Rendering terminal emulator with context: %s", self.formatted_class_name, context)
        return render(request, self.template_path, context=context)
