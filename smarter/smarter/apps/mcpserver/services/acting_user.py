"""
The acting user of a request from this platform to its own staff-only endpoint.

An LLMClient that has an MCPClient of the MCPServer's staff-only endpoint, e.g. the built-in
``smarter_sysadmin``, calls that server for the person who is chatting with it. The server must
know who that is: its tools read the platform's logs and its users' accounts, so it serves only
the platform's staff, and records each call under the person who made it.

An MCPClient can only send a credential from a Secret, the same for everyone who chats, and a
prompt runs as its LLMClient's owner. So the platform says who is chatting itself, with a
signed header, :data:`ACTING_USER_HEADER`:

1. The prompt api sets the acting user, the user who sent the prompt, with :func:`acting_user`,
   for the length of the prompt. The MCPClient api's tool call does the same.
2. :class:`~smarter.apps.mcpclient.connection.MCPServerConnection` keeps the acting user when it
   is created, in the prompt's own thread, and adds :func:`acting_user_headers` to every
   request, which is the header only for a request to this
   platform's own staff-only endpoint (:func:`is_staff_endpoint_url`), and nothing
   for any other server, so that no other server learns who is chatting.
3. :class:`~smarter.apps.mcpserver.protocol.views.StaffEndpointView` verifies the
   header with :func:`verify_acting_user`. A request without an acting user, e.g. the catalog
   refresh that runs in the background, may list the tools, but not call one. A tool call
   requires an acting user who is one of the platform's staff,
   :func:`~smarter.apps.account.utils.is_platform_staff`.

The header is signed with the platform's ``SECRET_KEY``, by :class:`django.core.signing.TimestampSigner`
with its own salt, and expires after :data:`MAX_AGE_SECONDS`, so only this platform can make one,
and one that is copied from a log is soon useless. It carries the user's id, not their name or
email address.
"""

import contextlib
from contextvars import ContextVar
from typing import Iterator, Optional
from urllib.parse import urljoin, urlparse

from django.conf import settings
from django.core import signing
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from smarter.apps.account.models import User
from smarter.common.conf import smarter_settings
from smarter.lib import logging
from smarter.lib.django.shortcuts import reverse
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.MCPSERVER_LOGGING])
logger_prefix = logging.SmarterFormattedText.text(__name__)

ACTING_USER_HEADER = "X-Smarter-Acting-User"
"""The http header that carries the signed acting user.

An MCPClient's manifest may not set it.
"""

SALT = "smarter.apps.mcpserver.acting_user"
"""
The signer's salt, so that no other value that the platform signs is accepted as an acting user.

It is the module's original dotted path, from before it moved into ``services``. Changing it would
make the pods of a rolling deploy refuse each other's signatures, so it stays as it is.
"""

MAX_AGE_SECONDS = 300
"""How long a signed acting user is valid: long enough for a slow tool call, short enough to be useless when copied."""

_acting_user: ContextVar[Optional[User]] = ContextVar("smarter_mcpserver_acting_user", default=None)
"""The user for whom this thread, or task, is calling MCP servers, set by :func:`acting_user`."""


class ActingUser(BaseModel):
    """
    The signed content of :data:`ACTING_USER_HEADER`.

    :param user_id: The id of the user who is chatting, or None for a request that the platform
        makes for nobody in particular, e.g. the background refresh of an MCPClient's catalog.
    """

    model_config = ConfigDict(extra="forbid")

    user_id: Optional[int] = Field(
        None,
        description="The id of the user for whom the platform calls the server, or None for nobody in particular.",
    )


@contextlib.contextmanager
def acting_user(user: Optional[object]) -> Iterator[None]:
    """
    Make a user the acting user of the MCP server requests that the block makes.

    The value is a context variable, so it follows the code into
    :func:`asgiref.sync.async_to_sync` and :func:`asgiref.sync.sync_to_async`, and is restored when
    the block ends.

    **Example usage**::

        with acting_user(request.user):
            response = handler(user_profile, prompt, data)

    :param user: The user. Anything that is not a :class:`~django.contrib.auth.models.User`, e.g.
        ``AnonymousUser`` or None, means nobody in particular.
    :yields: Nothing.
    """
    if isinstance(user, User):
        value = user
    else:
        value = None
    token = _acting_user.set(value)
    try:
        yield
    finally:
        _acting_user.reset(token)


def current_acting_user() -> Optional[User]:
    """
    Return the acting user that :func:`acting_user` set, if any.

    :returns: The user, or None outside an :func:`acting_user` block, or for an anonymous user.
    """
    user = _acting_user.get()
    return user


def staff_endpoint_url() -> str:
    """
    Return the url of this platform's staff-only endpoint.

    It is reversed against the platform's urlconf, because a prompt may run on a deployed
    LLMClient's host, whose urlconf has no MCPServer endpoints.

    :returns: The url, e.g. ``https://alpha.platform.example.com/api/v1/mcp/smarter-operations/``.
    """
    # pylint: disable=C0415
    from smarter.apps.mcpserver.urls import MCPServerReverseNames

    path = reverse(
        f"{MCPServerReverseNames.namespace}:{MCPServerReverseNames.staff}",
        urlconf=settings.ROOT_URLCONF,
    )
    url = urljoin(smarter_settings.environment_url, path)
    return url


def is_staff_endpoint_url(url: Optional[str]) -> bool:
    """
    Return whether a url is that of this platform's own staff-only endpoint.

    The scheme, host, port and path must all match :func:`staff_endpoint_url`, with or without
    a trailing slash, so that a server elsewhere whose path looks the same never gets the header.

    :param url: An MCPClient's endpoint url.
    :returns: True if the url is this platform's staff-only endpoint.
    """
    if not url:
        return False
    candidate = urlparse(url)
    expected = urlparse(staff_endpoint_url())
    if candidate.scheme.lower() != expected.scheme.lower():
        return False
    if candidate.netloc.lower() != expected.netloc.lower():
        return False
    candidate_path = candidate.path.rstrip("/")
    expected_path = expected.path.rstrip("/")
    return candidate_path == expected_path


def sign_acting_user(user: Optional[User]) -> str:
    """
    Return the signed value of :data:`ACTING_USER_HEADER` for a user.

    :param user: The user, or None for nobody in particular.
    :returns: The signed, timestamped value.
    """
    if user is None:
        user_id = None
    else:
        user_id = user.pk
    payload = ActingUser(user_id=user_id)
    signer = signing.TimestampSigner(salt=SALT)
    value = signer.sign_object(payload.model_dump(mode="json"))
    return value


def verify_acting_user(value: str) -> Optional[ActingUser]:
    """
    Verify a signed value of :data:`ACTING_USER_HEADER`.

    :param value: The header's value.
    :returns: The acting user, or None if the value was not signed by this platform with
        :data:`SALT`, has expired, or is not an :class:`ActingUser`.
    """
    signer = signing.TimestampSigner(salt=SALT)
    try:
        payload = signer.unsign_object(value, max_age=MAX_AGE_SECONDS)
    except signing.BadSignature as e:
        # SignatureExpired is a BadSignature.
        logger.warning("%s.verify_acting_user() refused a signed acting user: %s", logger_prefix, type(e).__name__)
        return None
    try:
        verified = ActingUser.model_validate(payload)
    except ValidationError:
        logger.warning("%s.verify_acting_user() refused a signed acting user that is not one.", logger_prefix)
        return None
    return verified


def acting_user_headers(url: Optional[str], user: Optional[User]) -> dict[str, str]:
    """
    Return the acting user header to send to an MCP server, if it is this platform's staff-only endpoint.

    :param url: The MCP server's url.
    :param user: The acting user, usually the :func:`current_acting_user` when the connection was
        created, or None for nobody in particular.
    :returns: ``{ACTING_USER_HEADER: <signed value>}`` for this platform's own staff-only endpoint,
        or an empty dict for any other MCP server, which never learns who is chatting.
    """
    if not is_staff_endpoint_url(url):
        return {}
    value = sign_acting_user(user)
    headers = {ACTING_USER_HEADER: value}
    return headers


__all__ = [
    "ACTING_USER_HEADER",
    "ActingUser",
    "acting_user",
    "acting_user_headers",
    "current_acting_user",
    "is_staff_endpoint_url",
    "staff_endpoint_url",
    "sign_acting_user",
    "verify_acting_user",
]
