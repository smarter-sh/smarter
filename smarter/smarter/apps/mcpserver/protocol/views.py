# pylint: disable=W0613
"""
The Django views of the MCP servers.

:class:`SmarterProjectMCPServerView` is the MCP Streamable HTTP endpoint of
:class:`~smarter.apps.mcpserver.protocol.server.SmarterProjectMCPServer`. It is mounted at:

- ``/api/v1/mcp/smarter-project/``: every repository of The Smarter Project.
- ``/api/v1/mcp/smarter-project/<repository>/``: one repository, e.g. ``smarter-cli``.

:class:`SmarterOperationsMCPServerView` is the endpoint of
:class:`~smarter.apps.mcpserver.protocol.operations_server.SmarterOperationsMCPServer`, at
``/api/v1/mcp/smarter-operations/``. It serves only a request whose ``Authorization: Token``
header carries the api key (a ``SmarterAuthToken``) of an active staff user: without one it
answers ``401 Unauthorized``, and for a user who is not staff ``403 Forbidden``, before it reads
the request's JSON-RPC.

Only POST is served. A POST whose messages are all notifications is answered ``202
Accepted``, with no body, and every other POST with ``application/json``. The server
issues no session, and offers no GET stream, so GET and DELETE are answered ``405 Method
Not Allowed``, which MCP clients expect of a stateless server.

The endpoint requires no authentication: its read-only tools serve the public
repositories of The Smarter Project. A client may send the user's GitHub classic personal
access token in an ``Authorization: Bearer`` header, and is then also served the tools
that write as that user: ``create_issue``, ``comment_on_issue``, ``close_issue`` and
``create_pull_request``. The token is passed to the tool as a
``SecretStr``, and is never logged. Each client IP address may send at most
``smarter_settings.mcpserver_rate_limit`` requests a minute: see
:mod:`smarter.apps.mcpserver.ratelimit`.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from http import HTTPStatus
from typing import Optional

import mcp_types
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from pydantic import SecretStr
from rest_framework.exceptions import AuthenticationFailed

from smarter.apps.account.models import User
from smarter.apps.mcpserver.protocol.base import MCPServerBase
from smarter.apps.mcpserver.protocol.operations_server import (
    SmarterOperationsMCPServer,
)
from smarter.apps.mcpserver.ratelimit import (
    RATE_LIMITED,
    client_ip,
    is_rate_limited,
    retry_after,
)
from smarter.apps.mcpserver.repositories import get_repository, repository_names
from smarter.lib import json, logging
from smarter.lib.django.views import SmarterView
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.drf.token_authentication import SmarterTokenAuthentication

from .server import SmarterProjectMCPServer

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.MCPSERVER_LOGGING])

BEARER_SCHEME = "bearer"
TOKEN_SCHEME = "token"
"""The scheme of a Smarter api key in an ``Authorization`` header: ``Token <key>``."""

UNAUTHORIZED = -32001
"""The JSON-RPC error code of a request without a valid staff api key."""


def bearer_token(request: HttpRequest) -> Optional[SecretStr]:
    """
    Return the token of a request's ``Authorization: Bearer`` header.

    :param request: The request.
    :returns: The token, or None if the request has no bearer token.
    """
    scheme, _, token = request.headers.get("Authorization", "").strip().partition(" ")
    token = token.strip()
    if scheme.lower() != BEARER_SCHEME or not token:
        return None
    return SecretStr(token)


def api_key(request: HttpRequest) -> Optional[str]:
    """
    Return the api key of a request's ``Authorization: Token`` header.

    :param request: The request.
    :returns: The key, or None if the request has none.
    """
    scheme, _, key = request.headers.get("Authorization", "").strip().partition(" ")
    key = key.strip()
    if scheme.lower() != TOKEN_SCHEME or not key:
        return None
    return key


def staff_user(request: HttpRequest) -> tuple[Optional[User], HTTPStatus]:
    """
    Return the active staff user whose api key a request carries.

    :param request: The request.
    :returns: The user and ``200 OK``, or None and ``401 Unauthorized`` if the request has no valid,
        active api key, or None and ``403 Forbidden`` if its user is not an active staff user.
    """
    key = api_key(request)
    if key is None:
        return None, HTTPStatus.UNAUTHORIZED
    try:
        user, _ = SmarterTokenAuthentication().authenticate_credentials(key.encode("utf-8"))
    except AuthenticationFailed:
        return None, HTTPStatus.UNAUTHORIZED
    if not (user.is_active and user.is_staff):
        return None, HTTPStatus.FORBIDDEN
    return user, HTTPStatus.OK


def rate_limited(view: SmarterView, request: HttpRequest) -> Optional[JsonResponse]:
    """
    Return a ``429 Too Many Requests`` response if the request's IP address is over the rate limit.

    :param view: The view, for logging.
    :param request: The request.
    :returns: The response, or None if the request may go on.
    """
    ip = client_ip(request)
    if not is_rate_limited(ip):
        return None
    logger.warning("%s rate limited %s", view.formatted_class_name, ip)
    error = MCPServerBase.error(
        None, RATE_LIMITED, "rate limit exceeded: too many requests from your IP address. Try again later."
    )
    limited = JsonResponse(MCPServerBase.dump(error), status=HTTPStatus.TOO_MANY_REQUESTS)
    limited["Retry-After"] = str(retry_after())
    return limited


def answer(request: HttpRequest, server: MCPServerBase) -> HttpResponse:
    """
    Answer the JSON-RPC message, or batch of messages, of a request's body with a server.

    :param request: The request.
    :param server: The MCP server.
    :returns: The JSON-RPC response, ``202 Accepted`` if no message needs one, or ``400 Bad Request``
        if the body is not JSON.
    """
    try:
        payload = json.loads(request.body or b"")
    except ValueError:
        error = MCPServerBase.error(None, mcp_types.PARSE_ERROR, "the request body is not JSON.")
        return JsonResponse(MCPServerBase.dump(error), status=HTTPStatus.BAD_REQUEST)
    response = server.handle(payload)
    if response is None:
        return HttpResponse(status=HTTPStatus.ACCEPTED)
    return JsonResponse(response, safe=False)


@method_decorator(csrf_exempt, name="dispatch")
@method_decorator(never_cache, name="dispatch")
class SmarterProjectMCPServerView(SmarterView):
    """
    The MCP Streamable HTTP endpoint of the Smarter Project MCP server.

    :param repository: From the url: the repository's name, or None for every repository.
    """

    http_method_names = ["post", "options"]

    @property
    def formatted_class_name(self) -> str:
        """The class name, for logging."""
        return f"{logging.SmarterFormattedText.text(__name__)}.{self.__class__.__name__}"

    def post(self, request: HttpRequest, repository: Optional[str] = None) -> HttpResponse:
        """
        Answer the JSON-RPC message, or batch of messages, in the request body.

        :param request: The request.
        :param repository: The repository's name, or None for every repository.
        :returns: The JSON-RPC response, or ``202 Accepted`` if no message needs one. An
            unknown repository is ``404 Not Found``, a body that is not JSON is ``400 Bad Request``,
            and a client over the rate limit is ``429 Too Many Requests``.
        """
        limited = rate_limited(self, request)
        if limited is not None:
            return limited
        project_repository = None
        if repository is not None:
            project_repository = get_repository(repository)
            if project_repository is None:
                return JsonResponse(
                    {
                        "detail": f"{repository} is not a repository of The Smarter Project: {', '.join(repository_names())}."
                    },
                    status=HTTPStatus.NOT_FOUND,
                )
        return answer(request, SmarterProjectMCPServer(project_repository, github_token=bearer_token(request)))


@method_decorator(csrf_exempt, name="dispatch")
@method_decorator(never_cache, name="dispatch")
class SmarterOperationsMCPServerView(SmarterView):
    """The MCP Streamable HTTP endpoint of the Smarter Operations MCP server, for staff only."""

    http_method_names = ["post", "options"]

    @property
    def formatted_class_name(self) -> str:
        """The class name, for logging."""
        return f"{logging.SmarterFormattedText.text(__name__)}.{self.__class__.__name__}"

    def post(self, request: HttpRequest) -> HttpResponse:
        """
        Answer the JSON-RPC message, or batch of messages, in the request body, for a staff user.

        :param request: The request.
        :returns: The JSON-RPC response, or ``202 Accepted`` if no message needs one. A request
            without a valid api key is ``401 Unauthorized``, one whose user is not an active staff
            user is ``403 Forbidden``, a client over the rate limit is ``429 Too Many Requests``, and
            a body that is not JSON is ``400 Bad Request``.
        """
        limited = rate_limited(self, request)
        if limited is not None:
            return limited
        user, status = staff_user(request)
        if user is None:
            logger.warning("%s refused a request from %s: %s", self.formatted_class_name, client_ip(request), status)
            message = (
                "this server requires the api key of a staff user, in an Authorization: Token <key> header."
                if status == HTTPStatus.UNAUTHORIZED
                else "this server is for the platform's staff only."
            )
            refused = JsonResponse(MCPServerBase.dump(MCPServerBase.error(None, UNAUTHORIZED, message)), status=status)
            if status == HTTPStatus.UNAUTHORIZED:
                refused["WWW-Authenticate"] = "Token"
            return refused
        return answer(request, SmarterOperationsMCPServer(user))


__all__ = [
    "SmarterOperationsMCPServerView",
    "SmarterProjectMCPServerView",
    "api_key",
    "bearer_token",
    "staff_user",
]
