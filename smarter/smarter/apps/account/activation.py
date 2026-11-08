"""
Account activation: a user who signs up with an email address and a password is inactive until they follow the.

link that the platform emails them, which proves that the address is theirs.

The link is ``/account/activate/<uidb64>/<token>/``: see :mod:`smarter.apps.account.email_links`. The console
serves its page, which activates the user and signs them in through the account api,
:mod:`smarter.apps.account.api.web.views`. Signing in uses the link, so it can't be used twice.

Users that social sign-in creates are inactive too, but are activated by an administrator, never by email:
self-service activation is only for those who signed up with a password, while the
``ENABLE_ACCOUNT_REGISTRATION`` switch allowed it. See ``SOCIAL_AUTH_CREATE_USERS`` in ``settings/base.py``.
"""

from django.contrib.auth import login
from django.http import HttpRequest
from django.utils.translation import gettext as _

from smarter.apps.account.email_links import (
    email_link,
    render_email,
    user_from_email_link,
)
from smarter.apps.account.login_audit import login_identity
from smarter.apps.account.models import User
from smarter.apps.infrastructure.services import infrastructure
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.ACCOUNT_LOGGING])
logger_prefix = logging.SmarterFormattedText.text(__name__)

ACCOUNT_ACTIVATE_LINK_NAME = "account:account_activate"
"""The url name of the link, which :mod:`smarter.apps.account.urls` serves at ``/account/activate/<uidb64>/<token>/``."""

EMAIL_TEMPLATE_PATH = "account/authentication/email/account-activation.html"
"""The email's template."""

PASSWORD_BACKEND = "django.contrib.auth.backends.ModelBackend"
"""The authentication backend of a user who signed up with a password, which the activation signs them in with."""


def can_activate_by_email(user: User) -> bool:
    """
    Whether a user may activate their own account with an emailed link.

    :param user: The user.
    :returns: True for an inactive user who signed up with a password. A user that social sign-in created has
        no usable password, and waits for an administrator.
    """
    if user.is_active:
        return False
    return user.has_usable_password()


def activation_link(request: HttpRequest, user: User) -> str:
    """
    The absolute url of a new activation link for the user.

    :param request: The request, for the link's host and protocol.
    :param user: The user.
    :returns: The link.
    """
    return email_link(request, user, ACCOUNT_ACTIVATE_LINK_NAME)


def send_activation_email(request: HttpRequest, user: User) -> None:
    """
    Email the user a link to activate their account.

    :param request: The request, for the link's host and the email's template context.
    :param user: The inactive user.
    :raises RuntimeError: when the email's template can't be rendered.
    """
    context = {"account_activation": {"url": activation_link(request, user)}}
    body = render_email(request, EMAIL_TEMPLATE_PATH, context)
    # the activation link is a secret, so the admin gets no blind copy.
    infrastructure.email.send_email(
        subject=_("Activate your account."), body=body, to=user.email, html=True, bcc_admin=False
    )
    logger.info("%s.send_activation_email() sent to identity %s", logger_prefix, login_identity(user.email))


def resend_activation_email(request: HttpRequest, email: str) -> bool:
    """
    Email a new activation link to the user who has this address, if they may activate by email.

    The caller answers the same either way, so that the response doesn't reveal which addresses have accounts.

    :param request: The request.
    :param email: The email address.
    :returns: True if an email was sent.
    :raises RuntimeError: when the email's template can't be rendered.
    """
    user = User.objects.filter(email__iexact=email).first()
    if user is None:
        return False
    if not can_activate_by_email(user):
        return False
    send_activation_email(request, user)
    return True


def activate(request: HttpRequest, uidb64: str, token: str) -> User:
    """
    Activate the user of an emailed link, and sign them in.

    Signing in changes the user's last sign-in, which the link's token hashes, so the link can't be used again.

    :param request: The request, whose session the user is signed in to.
    :param uidb64: The link's encoded user id.
    :param token: The link's token.
    :returns: The active, signed-in user.
    :raises EmailLinkError: when the link is unknown, malformed, used or expired.
    """
    user = user_from_email_link(uidb64, token)
    if not user.is_active:
        user.is_active = True
        user.save(update_fields=["is_active"])
        logger.info("%s.activate() activated identity %s", logger_prefix, login_identity(user.email))
    login(request, user, backend=PASSWORD_BACKEND)
    return user
