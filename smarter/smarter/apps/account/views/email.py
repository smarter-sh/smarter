"""Dev views for working on the email templates of :class:`smarter.apps.account.models.ContactEmail`."""

# pylint: disable=W0613

from django.http import HttpResponseBadRequest
from django.utils import translation

from smarter.apps.account.models import (
    SLACK_INVITATION_EMAIL,
    WELCOME_EMAIL,
    ContactEmail,
    contact_email_context,
    welcome_email_languages,
)
from smarter.lib.django.views import SmarterNeverCachedWebView

PREVIEW_EMAIL_ADDRESS = "preview@example.com"
"""The recipient whose unsubscribe link a preview shows."""


class EmailPreviewView(SmarterNeverCachedWebView):
    """
    Dev view for working on a contact email's template.

    The email is rendered in the request's language, or in the language of the
    ``language`` query parameter, one of ``settings.LANGUAGES``. The urls are only
    added in the local environment.
    """

    contact_email: ContactEmail = WELCOME_EMAIL

    def get(self, request, *args, **kwargs):
        """
        Render the contact email's template, in the requested language.

        :param request: The request; its ``language`` query parameter defaults to the active language.
        :param kwargs: ``first_name``, for the greeting.
        :returns: The rendered email, or a 400 response for an unknown language.
        """
        first_name: str = kwargs.get("first_name", "big fella")
        language = request.GET.get("language") or translation.get_language()
        if language not in welcome_email_languages():
            return HttpResponseBadRequest(f"Unknown language. Choose one of {', '.join(welcome_email_languages())}.")
        with translation.override(language):
            context = contact_email_context(first_name=first_name, email=PREVIEW_EMAIL_ADDRESS)
            return self.clean_http_response(request, template_path=self.contact_email.template_name, context=context)


class EmailWelcomeView(EmailPreviewView):
    """
    Dev view for working on the welcome email template.

    http://localhost:9357/account/email/welcome/larry/
    http://localhost:9357/account/email/welcome/larry/?language=es
    """

    contact_email = WELCOME_EMAIL


class EmailSlackInvitationView(EmailPreviewView):
    """
    Dev view for working on the Slack invitation email template.

    http://localhost:9357/account/email/slack-invitation/larry/
    http://localhost:9357/account/email/slack-invitation/larry/?language=fr
    """

    contact_email = SLACK_INVITATION_EMAIL
