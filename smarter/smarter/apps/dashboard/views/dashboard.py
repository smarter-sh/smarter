# -*- coding: utf-8 -*-
"""Django views"""
import logging

from django import forms
from django.http import JsonResponse

from smarter.apps.dashboard.models import EmailContactList
from smarter.view_helpers import SmarterAuthenticatedWebView, SmarterWebView


logger = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
# Public Access Views
# ------------------------------------------------------------------------------
class LandingPage(SmarterWebView):
    """Public Access Dashboard view"""

    class EmailForm(forms.Form):
        """Form for the sign-in page."""

        email = forms.EmailField()

    template_path = "landing-page.html"

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            self.template_path = "dashboard/authenticated.html"
            return super().get(request, *args, **kwargs)
        form = LandingPage.EmailForm()
        context = {"form": form}
        return self.clean_http_response(request, template_path=self.template_path, context=context)

    def post(self, request):
        form = LandingPage.EmailForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            EmailContactList.objects.get_or_create(email=email)
            return JsonResponse({"redirect": "/email-added/"})
        return JsonResponse({"error": "Invalid form"})


class EmailAdded(SmarterWebView):
    """Confirmation view for email added to contact list."""

    template_path = "dashboard/email-added.html"


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
