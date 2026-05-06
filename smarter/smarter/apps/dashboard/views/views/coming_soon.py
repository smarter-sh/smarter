# pylint: disable=W0613
"""Django views"""

import html

from django import forms
from django.core.handlers.wsgi import WSGIRequest
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
    """Public Access Dashboard view"""

    class EmailForm(forms.Form):
        """Form for the sign-in page."""

        email = forms.EmailField()

    template_path = "coming-soon.html"

    def get(self, request, *args, **kwargs):
        form = ComingSoon.EmailForm()
        context = {"form": form}
        return self.clean_http_response(request, template_path=self.template_path, context=context)

    def post(self, request: WSGIRequest):
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
