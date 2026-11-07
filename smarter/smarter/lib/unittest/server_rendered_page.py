"""
A page in Django's console frame, for tests of the frame.

The frame is ``templates/dashboard/base.html``'s: the sidebar, the user menu, the welcome dialog, the onboarding
hints and the tips. The console's pages moved into the single-page console (ADR-035), which serves their paths with
its ``index.html``, and the pages that Django still renders in the frame, the workbench's, each need an LLMClient. So
the tests of the frame get it from :func:`get_server_rendered_page`, which renders the frame alone at a path of
:data:`urlpatterns`, a urlconf that tests use in place of the console's, to which it adds that one path.

django-hosts chooses each request's urlconf by its host (``smarter.hosts``), not by ``ROOT_URLCONF``, so the helper
gives the console's host patterns this urlconf while it makes its request.
"""

from contextlib import ExitStack
from unittest.mock import patch

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.test import Client
from django.urls import path
from django_hosts.resolvers import get_host_patterns

from smarter.lib.django.views import SmarterAuthenticatedNeverCachedWebView
from smarter.urls import console as console_urls

SERVER_RENDERED_PAGE = "/test/server-rendered-page/"
"""The path of the frame's page, in this module's urlconf."""


class ServerRenderedPageView(SmarterAuthenticatedNeverCachedWebView):
    """Django's console frame, with no page inside it, for a signed-in user."""

    template_path = "dashboard/base.html"

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        Render the frame.

        :param request: The request.
        :returns: The frame's page.
        """
        return render(request, self.template_path)


urlpatterns = [path(SERVER_RENDERED_PAGE.strip("/") + "/", ServerRenderedPageView.as_view())] + console_urls.urlpatterns


def get_server_rendered_page(client: Client, **kwargs) -> HttpResponse:
    """
    Get the frame's page, with the test client's user and session, through every middleware.

    :param client: The test client, signed in or not.
    :param kwargs: Passed to ``client.get()``, e.g. ``follow=True``.
    :returns: The response: the frame, or the redirect to the sign-in page of an anonymous user.
    """
    with ExitStack() as stack:
        for host in get_host_patterns():
            if host.urlconf in (console_urls, console_urls.__name__):
                stack.enter_context(patch.object(host, "urlconf", __name__))
        response = client.get(SERVER_RENDERED_PAGE, **kwargs)
    return response
