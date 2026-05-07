# pylint: disable=W0613
"""
Confirmation view for the email sign-up flow.

This module provides a publicly accessible view that renders the
"email added" confirmation page after a user successfully submits their
email address on the "Coming Soon" page. The context data is passed in the
request body as a JSON payload and forwarded directly to the template.

Classes:
    EmailAdded: Public POST view that renders the email-added confirmation page.

Example:
    Wire up the view in your URL configuration::

        from smarter.apps.dashboard.views.views.email_added import EmailAdded

        urlpatterns = [
            path("email-added/", EmailAdded.as_view(), name="email_added"),
        ]
"""

from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponse

from smarter.lib import json
from smarter.lib.django.views import (
    SmarterWebHtmlView,
)


# ------------------------------------------------------------------------------
# Public Access Views
# ------------------------------------------------------------------------------
class EmailAdded(SmarterWebHtmlView):
    """
    Public view that renders the email sign-up confirmation page.

    Extends :class:`~smarter.lib.django.views.SmarterWebHtmlView` and requires
    no authentication.

    On a ``POST`` request the view decodes the JSON body sent by the
    :class:`~smarter.apps.dashboard.views.views.coming_soon.ComingSoon` view,
    uses the decoded data as the template context, and renders
    ``dashboard/email-added.html``.

    Attributes:
        template_path (str): ``"dashboard/email-added.html"``
    """

    template_path = "dashboard/email-added.html"

    def post(self, request: WSGIRequest) -> HttpResponse:
        """
        Handle POST requests to render the email-added confirmation page with
        context from the request body.

        :param request: The incoming HTTP POST request from the client, expected to contain a JSON body with context data for the template.
        :type request: django.core.handlers.wsgi.WSGIRequest
        :returns: An HTTP response with the rendered email-added confirmation page.
        :rtype: django.http.HttpResponse
        """
        context = json.loads(request.body.decode("utf-8"))
        return self.clean_http_response(request, template_path=self.template_path, context=context)
