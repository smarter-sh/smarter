"""
Email template views.
"""

# pylint: disable=W0613

from smarter.apps.account.models import welcome_email_context
from smarter.lib.django.view_helpers import SmarterNeverCachedWebView


class EmailWelcomeView(SmarterNeverCachedWebView):
    """
    Dev view for working on the welcome email template.
    http://localhost:8000/dashboard/account/email/welcome/larry/
    """

    template_path = "account/email/welcome.html"

    def get(self, request, *args, **kwargs):
        first_name: str = kwargs.get("first_name", "big fella")
        first_name = first_name.capitalize()
        context = welcome_email_context(first_name)
        return self.clean_http_response(request, template_path=self.template_path, context=context)
