# pylint: disable=W0613
"""
Backend for a terminal emulation window that looks like macOS Terminal.app.
It is used in the web console to provide direct support for Linux curl and
other command line tools.
"""

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from smarter.lib.django.views import (
    SmarterAuthenticatedNeverCachedWebView,
)


class TerminalEmulatorLogView(SmarterAuthenticatedNeverCachedWebView):
    """
    View for rendering the terminal emulation page, which is used in the web console
    """

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        View for rendering the Monaco terminal emulation page
        which only receives JSON dicts of LLM prompts.
        """

        context = {
            "terminal": {
                "root_id": "smarter-terminal-emulator-root",
                "csrf_cookie_name": settings.CSRF_COOKIE_NAME,  # this is the CSRF token cookie that should be included in the header of the POST request from the frontend.
                "django_session_cookie_name": settings.SESSION_COOKIE_NAME,  # this is the Django session.
                "cookie_domain": settings.SESSION_COOKIE_DOMAIN,
                "api_url": None,  # DELETE ME PLEASE
                "llm_provider_id": "1",
                "template_id": "1",
            }
        }
        self.template_path = "react/terminal-emulator.html"
        return render(request, self.template_path, context=context)

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        Receives a LLM prompt JSON dict from the frontend and sends this to
        the Provider passthrough service.
        """
        return HttpResponse(status=404)  # Not yet implemented.
