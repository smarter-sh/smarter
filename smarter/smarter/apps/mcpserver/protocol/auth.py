"""
Who is calling the MCPServer's endpoints: the credentials of a request, and the platform's staff.

The public endpoint (``/api/v1/mcp/smarter-project/``) needs no credential, but serves its tools
that write to GitHub only to a request that carries the caller's GitHub token, from
:func:`bearer_token`. The staff-only endpoint (``/api/v1/mcp/smarter-operations/``) serves only the
platform's staff (:func:`~smarter.apps.account.utils.is_platform_staff`), whom it finds with
:func:`acting_staff_user`, for a request that this platform signed for the person who is chatting
with an LLMClient, or else with :func:`staff_user`, for a request whose api key is a staff user's.
:mod:`~smarter.apps.mcpserver.protocol.views` calls them before it reads a request's JSON-RPC.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from http import HTTPStatus
from typing import Optional

from django.http import HttpRequest
from pydantic import SecretStr
from rest_framework.exceptions import AuthenticationFailed

from smarter.apps.account.models import User
from smarter.apps.account.utils import is_platform_staff
from smarter.apps.mcpserver.services.acting_user import verify_acting_user
from smarter.lib.drf.token_authentication import SmarterTokenAuthentication

BEARER_SCHEME = "bearer"
"""The scheme of a GitHub token in an ``Authorization`` header: ``Bearer <token>``, compared case insensitively."""

TOKEN_SCHEME = "token"
"""The scheme of a Smarter api key in an ``Authorization`` header: ``Token <key>``, compared case insensitively."""


def _authorization_credentials(request: HttpRequest, scheme: str) -> Optional[str]:
    """
    Return the credentials of a request's ``Authorization`` header, if it uses a scheme.

    The header is ``<scheme> <credentials>``, e.g. ``Token 1a2b...``. The scheme is compared case
    insensitively, and the credentials are stripped of whitespace.

    :param request: The request.
    :param scheme: The expected scheme, in lower case: :data:`BEARER_SCHEME` or :data:`TOKEN_SCHEME`.
    :returns: The credentials, or None if the request has no ``Authorization`` header, its scheme is
        another one, or its credentials are empty.
    """
    header = request.headers.get("Authorization", "")
    header = header.strip()
    header_scheme, _, credentials = header.partition(" ")
    credentials = credentials.strip()
    if header_scheme.lower() != scheme:
        return None
    if not credentials:
        return None
    return credentials


def bearer_token(request: HttpRequest) -> Optional[SecretStr]:
    """
    Return the token of a request's ``Authorization: Bearer`` header.

    The MCPServer's public endpoint serves its tools that write to GitHub, e.g. ``create_issue``, to
    a request that carries the user's GitHub token in this header. The token is wrapped in a
    :class:`~pydantic.SecretStr`, so that it is never logged or shown by accident.

    :param request: The request.
    :returns: The token, or None if the request has no bearer token.
    """
    token = _authorization_credentials(request, BEARER_SCHEME)
    if token is None:
        return None
    return SecretStr(token)


def api_key(request: HttpRequest) -> Optional[str]:
    """
    Return the api key of a request's ``Authorization: Token`` header.

    This is the header that the Smarter api, and the ``smarter`` CLI, use for a
    ``SmarterAuthToken``. The key is not checked here: see :func:`staff_user`.

    :param request: The request.
    :returns: The key, or None if the request has none.
    """
    key = _authorization_credentials(request, TOKEN_SCHEME)
    return key


def staff_user(request: HttpRequest) -> tuple[Optional[User], HTTPStatus]:
    """
    Return the platform staff user whose api key a request carries.

    The key is checked with :class:`~smarter.lib.drf.token_authentication.SmarterTokenAuthentication`,
    the same check as the rest of the Smarter api, which reads the ``SmarterAuthToken`` from the
    database, refuses a key that is unknown or not active, and sends its authentication signals.
    Its user must be one of the platform's staff,
    :func:`~smarter.apps.account.utils.is_platform_staff`: the admin of another account is staff
    of that account only.

    :param request: The request.
    :returns: The user and ``200 OK``, or None and ``401 Unauthorized`` if the request has no valid,
        active api key, or None and ``403 Forbidden`` if its user is not one of the platform's staff.
    """
    key = api_key(request)
    if key is None:
        return None, HTTPStatus.UNAUTHORIZED
    try:
        user, _ = SmarterTokenAuthentication().authenticate_credentials(key.encode("utf-8"))
    except AuthenticationFailed:
        return None, HTTPStatus.UNAUTHORIZED
    if not is_platform_staff(user):
        return None, HTTPStatus.FORBIDDEN
    return user, HTTPStatus.OK


def acting_staff_user(value: str) -> tuple[Optional[User], HTTPStatus]:
    """
    Return the platform staff user of a signed ``X-Smarter-Acting-User`` header.

    The platform sends this header to its own staff-only endpoint, for the user who is
    chatting with an LLMClient that has an MCPClient of it: see
    :mod:`~smarter.apps.mcpserver.services.acting_user`.

    **Side effects:** one database query for the user, and one for their profile in the Smarter
    account.

    :param value: The header's value.
    :returns: The user and ``200 OK``; None and ``200 OK`` for a request that the platform signed for
        nobody in particular, which may list the tools but not call them; None and
        ``401 Unauthorized`` if this platform did not sign the value, or it has expired; or None and
        ``403 Forbidden`` if its user is not one of the platform's staff, or no longer exists.
    """
    verified = verify_acting_user(value)
    if verified is None:
        return None, HTTPStatus.UNAUTHORIZED
    if verified.user_id is None:
        return None, HTTPStatus.OK
    user = User.objects.filter(pk=verified.user_id).first()
    if not is_platform_staff(user):
        return None, HTTPStatus.FORBIDDEN
    return user, HTTPStatus.OK


__all__ = [
    "BEARER_SCHEME",
    "TOKEN_SCHEME",
    "acting_staff_user",
    "api_key",
    "bearer_token",
    "staff_user",
]
