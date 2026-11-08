"""
The links that the platform emails to a user: making one, and reading one back.

A link is ``/<path>/<uidb64>/<token>/``: the user's encoded id and a token that expires, made by
:class:`~smarter.lib.django.token_generators.ExpiringTokenGenerator`. The token hashes the user's password
and last sign-in, so a link stops working once its user changes their password or signs in. Password
reset links (:mod:`smarter.apps.account.password_reset`) and account activation links
(:mod:`smarter.apps.account.activation`) are both made and read here.
"""

from http import HTTPStatus

from django.http import HttpRequest, HttpResponse
from django.utils.translation import gettext as _

from smarter.apps.account.models import User
from smarter.common.exceptions import SmarterValueError
from smarter.lib.django.token_generators import (
    ExpiringTokenGenerator,
    SmarterTokenConversionError,
    SmarterTokenExpiredError,
    SmarterTokenIntegrityError,
    SmarterTokenParseError,
)
from smarter.lib.django.views import SmarterView

expiring_token = ExpiringTokenGenerator()


class EmailLinkError(Exception):
    """
    An emailed link that can't be used.

    :param message: Why, for the user.
    :param status: The http status that answers it: 404 for an unknown user, 403 for an expired link,
        400 for a malformed or used one.
    """

    def __init__(self, message: str, status: HTTPStatus):
        super().__init__(message)
        self.status = status


def email_link(request: HttpRequest, user: User, url_name: str) -> str:
    """
    The absolute url of a new link for the user.

    :param request: The request, for the link's host and protocol.
    :param user: The user.
    :param url_name: The name of the link's url, whose kwargs are ``uidb64`` and ``token``.
    :returns: The link.
    :raises SmarterValueError: when ``user`` is not a User.
    """
    if not isinstance(user, User):
        raise SmarterValueError("Invalid user object.")
    return expiring_token.encode_link(request=request, user=user, reverse_link=url_name)  # type: ignore[arg-type]


def user_from_email_link(uidb64: str, token: str) -> User:
    """
    The user of an emailed link, if the link is valid and hasn't expired.

    :param uidb64: The link's encoded user id.
    :param token: The link's token.
    :returns: The user.
    :raises EmailLinkError: when the link is unknown, malformed, used or expired.
    """
    try:
        return expiring_token.decode_link(uidb64=uidb64, token=token)
    except User.DoesNotExist as e:
        raise EmailLinkError(_("Invalid link. The user does not exist."), HTTPStatus.NOT_FOUND) from e
    except SmarterTokenExpiredError as e:
        raise EmailLinkError(str(e), HTTPStatus.FORBIDDEN) from e
    except (
        TypeError,
        ValueError,
        OverflowError,
        SmarterTokenParseError,
        SmarterTokenConversionError,
        SmarterTokenIntegrityError,
    ) as e:
        raise EmailLinkError(str(e), HTTPStatus.BAD_REQUEST) from e


def render_email(request: HttpRequest, template_path: str, context: dict[str, dict[str, str]]) -> str:
    """
    An email's html, rendered from its template, without comments and minified.

    :param request: The request, for the template's context processors, e.g. the branding.
    :param template_path: The email's template.
    :param context: The template's context, e.g. the link.
    :returns: The html.
    :raises RuntimeError: when the template can't be rendered.
    """
    body = SmarterView().render_clean_html(request, template_path=template_path, context=context)
    if isinstance(body, HttpResponse):
        # render_clean_html() logged why the template failed.
        raise RuntimeError(f"could not render {template_path}.")
    return body
