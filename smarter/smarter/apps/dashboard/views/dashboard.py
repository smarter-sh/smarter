"""Django views"""

import html
import json
import logging

from django import forms
from django.http import JsonResponse
from django.shortcuts import redirect

from smarter.common.helpers.mailchimp_helpers import MailchimpHelper
from smarter.lib.django.view_helpers import SmarterAuthenticatedWebView, SmarterWebView

from ..models import EmailContactList


logger = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
# Public Access Views
# ------------------------------------------------------------------------------
class ComingSoon(SmarterWebView):
    """Public Access Dashboard view"""

    class EmailForm(forms.Form):
        """Form for the sign-in page."""

        email = forms.EmailField()

    template_path = "coming-soon.html"

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            # TODO: redeploy the Bootstrap dashboard
            # -----------------------------------------------------------------
            # self.template_path = "dashboard/authenticated.html"
            # return super().get(request, *args, **kwargs)
            # -----------------------------------------------------------------
            return redirect("/admin/")
        form = ComingSoon.EmailForm()
        context = {"form": form}
        return self.clean_http_response(request, template_path=self.template_path, context=context)

    def post(self, request):
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
        html_error = html.escape(form.errors)
        return JsonResponse({"error": json.dumps(html_error)})


class EmailAdded(SmarterWebView):
    """Confirmation view for email added to contact list."""

    template_path = "dashboard/email-added.html"

    def post(self, request):
        context = json.loads(request.body.decode("utf-8"))
        return self.clean_http_response(request, template_path=self.template_path, context=context)


class DocumentationView(SmarterWebView):
    """Documentation view"""

    template_path = "dashboard/documentation.html"


class PlatformHelpView(SmarterWebView):
    """Platform help view"""

    template_path = "dashboard/help.html"


class ChangeLogView(SmarterWebView):
    """Notifications view"""

    template_path = "dashboard/changelog.html"


# ------------------------------------------------------------------------------
# Protected Views
# ------------------------------------------------------------------------------
class NotificationsView(SmarterAuthenticatedWebView):
    """Notifications view"""

    template_path = "dashboard/notifications.html"
