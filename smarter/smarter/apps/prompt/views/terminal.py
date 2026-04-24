# pylint: disable=W0613
"""
Backend for a terminal emulation window that looks like macOS Terminal.app.
It is used in the web console to provide direct support for Linux curl and
other command line tools.
"""

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from smarter.lib.django.views import (
    SmarterAuthenticatedNeverCachedWebView,
)


class TerminalEmulatorView(SmarterAuthenticatedNeverCachedWebView):
    """
    View for rendering the terminal emulation page, which is used in the web console
    """

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        View for rendering the Monaco terminal emulation page
        which only receives JSON dicts of LLM prompts.
        """

        context = {"page_title": "Terminal"}
        self.template_path = "prompt/terminal.html"
        return render(request, self.template_path, context=context)

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        Receives a LLM prompt JSON dict from the frontend and sends this to
        the Provider passthrough service.
        """
        return HttpResponse(status=404)  # Not yet implemented.

    def patch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        This endpoint is not used for the terminal view, as all communication
        is done via WebSockets. However, we define it to satisfy the requirements
        of the SmarterAuthenticatedNeverCachedWebView base class.
        """
        return HttpResponse(status=405)  # Method Not Allowed

    def delete(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        This endpoint is not used for the terminal view, as all communication
        is done via WebSockets. However, we define it to satisfy the requirements
        of the SmarterAuthenticatedNeverCachedWebView base class.
        """
        return HttpResponse(status=405)  # Method Not Allowed

    def put(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        This endpoint is not used for the terminal view, as all communication
        is done via WebSockets. However, we define it to satisfy the requirements
        of the SmarterAuthenticatedNeverCachedWebView base class.
        """
        return HttpResponse(status=405)  # Method Not Allowed
