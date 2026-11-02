"""
The page that the unsubscribe link of the welcome and Slack invitation emails opens.

The link carries a signed token of the recipient's email address (see
:func:`smarter.apps.account.models.unsubscribe_token`), so the page needs no sign-in, and nobody
can unsubscribe an address without its token.
"""

from typing import Optional

from django.core import signing
from django.http import HttpRequest, HttpResponse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.decorators.csrf import csrf_exempt

from smarter.apps.account.models import AccountContact, unsubscribe_email_address
from smarter.lib import logging
from smarter.lib.django.http.shortcuts import SmarterHttpResponseBadRequest
from smarter.lib.django.views import SmarterNeverCachedWebView
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.ACCOUNT_LOGGING])


# pylint: disable=W0613
@method_decorator(csrf_exempt, name="dispatch")
class AccountUnsubscribeView(SmarterNeverCachedWebView):
    """
    Unsubscribe an email address from the welcome and Slack invitation emails.

    A GET shows the address and an Unsubscribe button, and doesn't change anything, because mail
    scanners and link previews open the links of an email. A POST, from the button or from a mail
    client's own unsubscribe button (RFC 8058 one-click unsubscribe, which the emails'
    ``List-Unsubscribe-Post`` header announces), unsubscribes it with
    :meth:`AccountContact.unsubscribe() <smarter.apps.account.models.AccountContact.unsubscribe>`.

    The POST is exempt from CSRF protection, because a mail provider's one-click unsubscribe has
    no session and no CSRF token. The signed token in the url is what authorizes it.

    http://localhost:9357/account/unsubscribe/<token>/
    """

    template_path = "account/unsubscribe.html"

    @property
    def formatted_class_name(self) -> str:
        """Returns a formatted string of the class name for logging purposes."""
        return logging.SmarterFormattedText.text(f"{__name__}.{AccountUnsubscribeView.__name__}")

    def email_address(self, token: str) -> Optional[str]:
        """
        Return the email address of the url's token.

        :param token: The token of the url.
        :returns: The email address, or None if the token is not valid.
        """
        try:
            return unsubscribe_email_address(token)
        except signing.BadSignature:
            logger.warning("%s.email_address() received an invalid unsubscribe token.", self.formatted_class_name)
            return None

    def render(self, request: HttpRequest, email: str, unsubscribed: bool) -> HttpResponse:
        """
        Render the page for an email address.

        :param request: The request.
        :param email: The email address.
        :param unsubscribed: Whether the address is unsubscribed. An address that is no contact's,
            e.g. of a Slack invitation sent to someone who isn't a user, has nothing to record, so
            the page says it is unsubscribed once they confirm.
        :returns: The page, which asks to confirm, or says that the address is unsubscribed.
        """
        context = {"email": email, "unsubscribed": unsubscribed}
        return self.clean_http_response(request, template_path=self.template_path, context=context)

    def bad_link(self, request: HttpRequest) -> HttpResponse:
        """Return the page for a token that is not valid."""
        return SmarterHttpResponseBadRequest(
            request=request,
            error_message=_("This unsubscribe link is not valid. Copy the whole link from the email, and try again."),
        )

    def get(self, request, *args, **kwargs):
        email = self.email_address(kwargs.get("token", ""))
        if email is None:
            return self.bad_link(request)
        return self.render(request, email, unsubscribed=AccountContact.unsubscribed_at_of(email) is not None)

    def post(self, request, *args, **kwargs):
        email = self.email_address(kwargs.get("token", ""))
        if email is None:
            return self.bad_link(request)
        AccountContact.unsubscribe(email)
        return self.render(request, email, unsubscribed=True)
