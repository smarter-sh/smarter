"""Email template views."""

# pylint: disable=W0613

from django.http import HttpResponseBadRequest
from django.utils import translation

from smarter.apps.account.models import welcome_email_context, welcome_email_languages
from smarter.lib.django.views import SmarterNeverCachedWebView


class EmailWelcomeView(SmarterNeverCachedWebView):
    """
    Dev view for working on the welcome email template.

    The email is rendered in the request's language, or in the language of the
    ``language`` query parameter, one of ``settings.LANGUAGES``.

    http://localhost:9357/dashboard/account/email/welcome/larry/
    http://localhost:9357/dashboard/account/email/welcome/larry/?language=es
    """

    template_path = "account/email/welcome.html"

    def get(self, request, *args, **kwargs):
        first_name: str = kwargs.get("first_name", "big fella")
        first_name = first_name.capitalize()
        language = request.GET.get("language") or translation.get_language()
        if language not in welcome_email_languages():
            return HttpResponseBadRequest(f"Unknown language. Choose one of {', '.join(welcome_email_languages())}.")
        with translation.override(language):
            context = welcome_email_context(first_name)
            return self.clean_http_response(request, template_path=self.template_path, context=context)
