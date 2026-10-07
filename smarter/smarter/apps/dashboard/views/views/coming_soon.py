# pylint: disable=W0613
"""
Dashboard "Coming Soon" view and email capture endpoint.

This module provides a publicly accessible view that renders a pre-launch
"Coming Soon" page and handles email sign-up submissions. Submitted addresses
are stored in :class:`~smarter.apps.dashboard.models.EmailContactList` and
synced to Mailchimp via :class:`~smarter.common.helpers.mailchimp_helpers.MailchimpHelper`.

Classes:
    ComingSoon: Public view that renders the coming-soon page and processes
        email sign-up form submissions.

Example:
    Wire up the view in your URL configuration::

        from smarter.apps.dashboard.views.views.coming_soon import ComingSoon

        urlpatterns = [
            path("coming-soon/", ComingSoon.as_view(), name="coming_soon"),
        ]
"""

import html

from django import forms
from django.core.handlers.asgi import ASGIRequest
from django.http import JsonResponse

from smarter.apps.dashboard.models import EmailContactList
from smarter.common.helpers.mailchimp_helpers import MailchimpHelper
from smarter.lib import json
from smarter.lib.django.views import (
    SmarterWebHtmlView,
)


# ------------------------------------------------------------------------------
# Public Access Views
# ------------------------------------------------------------------------------
class ComingSoon(SmarterWebHtmlView):
    """
    Public view that renders the "Coming Soon" page and handles email sign-ups.

    Extends :class:`~smarter.lib.django.views.SmarterWebHtmlView` and requires
    no authentication.

    ``GET`` renders ``coming-soon.html`` with an empty
    :class:`ComingSoon.EmailForm`.

    ``POST`` validates the submitted email address, creates a new
    :class:`~smarter.apps.dashboard.models.EmailContactList` record if the
    address has not been seen before, adds the address to the Mailchimp list,
    and returns a JSON response directing the frontend to redirect to
    ``/email-added/``. If the email already exists, a different message is
    returned. Invalid form submissions return a JSON error payload.

    Attributes:
        template_path (str): ``"coming-soon.html"``
    """

    class EmailForm(forms.Form):
        """
        Simple form that validates a single email address field.

        Fields:
            email (EmailField): The subscriber's email address.
        """

        email = forms.EmailField()

    template_path = "coming-soon.html"

    def get(self, request, *args, **kwargs):
        """
        Handle GET requests to render the "Coming Soon" page with an empty email form.
        :param request: The incoming HTTP GET request from the client.
        :type request: django.core.handlers.wsgi.ASGIRequest
        :param args: Additional positional arguments forwarded by the URL dispatcher.
        :param kwargs: Additional keyword arguments forwarded by the URL dispatcher.
        :returns: An HTTP response with the rendered "Coming Soon" page.
        :rtype: django.http.HttpResponse
        """
        form = ComingSoon.EmailForm()
        context = {"form": form}
        return self.clean_http_response(request, template_path=self.template_path, context=context)

    def post(self, request: ASGIRequest):
        """
        Handle POST requests to process email sign-up submissions.
        On success, returns a JSON object with a redirect URL and a message
        indicating whether the email was newly added or already exists. On
        form validation failure, returns a JSON object containing the error
        messages.

        :param request: The incoming HTTP POST request containing the email sign-up data.
        :type request: django.core.handlers.wsgi.ASGIRequest
        :returns: A JSON response indicating success or failure of the email submission.
        :rtype: django.http.JsonResponse

        """
        form = ComingSoon.EmailForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            email_contact_list, created = EmailContactList.objects.get_or_create(email=email)
            if created:
                MailchimpHelper().add_list_member(email_contact_list.email)
                message = "We'll notify you when the launch date nears."
            else:
                message = f"{email_contact_list.email} is already in our contact list. We'll keep you updated."
            return JsonResponse(
                {
                    "redirect": "/email-added/",
                    "context": {
                        "email_added": {
                            "created": created,
                            "message": message,
                            "email": email_contact_list.email,
                        }
                    },
                }
            )
        html_error = html.escape(form.errors.as_text())
        return JsonResponse({"error": json.dumps(html_error)})
