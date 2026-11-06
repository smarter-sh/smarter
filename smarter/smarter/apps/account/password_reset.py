"""
Password reset links: making one, emailing it, and reading it back.

A link is ``/password-reset-link/<uidb64>/<token>/``, which expires. The server-rendered password pages,
:mod:`smarter.apps.account.views.password_management`, and the console's account api,
:mod:`smarter.apps.account.api.web.views`, both use these functions. Emails already sent keep working:
the link's path doesn't change when the console serves it.
"""

from http import HTTPStatus

from django.http import HttpRequest, HttpResponse
from django.utils.translation import gettext as _

from smarter.apps.account.models import User
from smarter.apps.infrastructure.services import infrastructure
from smarter.common.exceptions import SmarterValueError
from smarter.lib import logging
from smarter.lib.django.token_generators import (
    ExpiringTokenGenerator,
    SmarterTokenConversionError,
    SmarterTokenExpiredError,
    SmarterTokenIntegrityError,
    SmarterTokenParseError,
)
from smarter.lib.django.views import SmarterView
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.ACCOUNT_LOGGING])
logger_prefix = logging.SmarterFormattedText.text(__name__)

PASSWORD_RESET_LINK_NAME = "password_reset_link"
"""The url name of the link, which :mod:`smarter.urls.console` serves at ``/password-reset-link/<uidb64>/<token>/``."""

EMAIL_TEMPLATE_PATH = "account/authentication/email/password-reset.html"
"""The email's template."""

expiring_token = ExpiringTokenGenerator()


class PasswordResetLinkError(Exception):
    """
    A password reset link that can't be used.

    :param message: Why, for the user.
    :param status: The http status that answers it: 404 for an unknown user, 403 for an expired link,
        400 for a malformed one.
    """

    def __init__(self, message: str, status: HTTPStatus):
        super().__init__(message)
        self.status = status


def password_reset_link(request: HttpRequest, user: User) -> str:
    """
    The absolute url of a new password reset link for the user.

    :param request: The request, for the link's host and protocol.
    :param user: The user.
    :returns: The link.
    :raises SmarterValueError: when ``user`` is not a User.
    """
    if not isinstance(user, User):
        raise SmarterValueError("Invalid user object.")
    return expiring_token.encode_link(request=request, user=user, reverse_link=PASSWORD_RESET_LINK_NAME)  # type: ignore[arg-type]


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
    link = password_reset_link(request, user)
    context = {"password_reset": {"url": link}}
    body = SmarterView().render_clean_html(request, template_path=EMAIL_TEMPLATE_PATH, context=context)
    if isinstance(body, HttpResponse):
        # render_clean_html() logged why the template failed.
        raise RuntimeError(f"{logger_prefix}.send_password_reset_email() could not render {EMAIL_TEMPLATE_PATH}.")
    # the reset link is a secret, so the admin gets no blind copy.
    infrastructure.email.send_email(subject=_("Reset your password"), body=body, to=email, html=True, bcc_admin=False)
    return True


def user_from_reset_link(uidb64: str, token: str) -> User:
    """
    The user of a password reset link, if the link is valid and hasn't expired.

    :param uidb64: The link's encoded user id.
    :param token: The link's token.
    :returns: The user.
    :raises PasswordResetLinkError: when the link is unknown, malformed or expired.
    """
    try:
        return expiring_token.decode_link(uidb64=uidb64, token=token)
    except User.DoesNotExist as e:
        raise PasswordResetLinkError(
            _("Invalid password reset link. User does not exist."), HTTPStatus.NOT_FOUND
        ) from e
    except SmarterTokenExpiredError as e:
        raise PasswordResetLinkError(str(e), HTTPStatus.FORBIDDEN) from e
    except (
        TypeError,
        ValueError,
        OverflowError,
        SmarterTokenParseError,
        SmarterTokenConversionError,
        SmarterTokenIntegrityError,
    ) as e:
        raise PasswordResetLinkError(str(e), HTTPStatus.BAD_REQUEST) from e
