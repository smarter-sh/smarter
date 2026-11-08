"""
Password reset links: making one, emailing it, and reading it back.

A link is ``/password-reset-link/<uidb64>/<token>/``, which expires: see :mod:`smarter.apps.account.email_links`.
The console serves the link's page, and its account api, :mod:`smarter.apps.account.api.web.views`, uses these
functions. Emails that were sent before the console served it keep working: the link's path is the same.
"""

from django.http import HttpRequest
from django.utils.translation import gettext as _

from smarter.apps.account.email_links import (
    email_link,
    render_email,
    user_from_email_link,
)
from smarter.apps.account.models import User
from smarter.apps.infrastructure.services import infrastructure
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.ACCOUNT_LOGGING])
logger_prefix = logging.SmarterFormattedText.text(__name__)

PASSWORD_RESET_LINK_NAME = "password_reset_link"
"""The url name of the link, which :mod:`smarter.urls.console` serves at ``/password-reset-link/<uidb64>/<token>/``."""

EMAIL_TEMPLATE_PATH = "account/authentication/email/password-reset.html"
"""The email's template."""


def password_reset_link(request: HttpRequest, user: User) -> str:
    """
    The absolute url of a new password reset link for the user.

    :param request: The request, for the link's host and protocol.
    :param user: The user.
    :returns: The link.
    :raises SmarterValueError: when ``user`` is not a User.
    """
    return email_link(request, user, PASSWORD_RESET_LINK_NAME)


def send_password_reset_email(request: HttpRequest, email: str) -> bool:
    """
    Email a password reset link to the user who has this address, if there is one.

    The caller answers the same either way, so that the response doesn't reveal which addresses have
    accounts.

    :param request: The request, for the link's host and the email's template context.
    :param email: The email address.
    :returns: True if an email was sent, False if no user has the address.
    :raises RuntimeError: when the email's template can't be rendered.
    """
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        logger.debug("%s.send_password_reset_email() no user has the address.", logger_prefix)
        return False
    context = {"password_reset": {"url": password_reset_link(request, user)}}
    body = render_email(request, EMAIL_TEMPLATE_PATH, context)
    # the reset link is a secret, so the admin gets no blind copy.
    infrastructure.email.send_email(subject=_("Reset your password"), body=body, to=email, html=True, bcc_admin=False)
    return True


def user_from_reset_link(uidb64: str, token: str) -> User:
    """
    The user of a password reset link, if the link is valid and hasn't expired.

    :param uidb64: The link's encoded user id.
    :param token: The link's token.
    :returns: The user.
    :raises EmailLinkError: when the link is unknown, malformed or expired.
    """
    return user_from_email_link(uidb64, token)
