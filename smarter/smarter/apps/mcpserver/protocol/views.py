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

The Smarter Project endpoint requires no authentication: its read-only tools serve the public
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
"""The scheme of a GitHub token in an ``Authorization`` header: ``Bearer <token>``, compared case insensitively."""

TOKEN_SCHEME = "token"
"""The scheme of a Smarter api key in an ``Authorization`` header: ``Token <key>``, compared case insensitively."""

UNAUTHORIZED = -32001
"""The JSON-RPC error code of a request without a valid staff api key."""


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

    The Smarter Project MCP server serves its tools that write to GitHub, e.g. ``create_issue``, to
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
    Return the active staff user whose api key a request carries.

    The key is checked with :class:`~smarter.lib.drf.token_authentication.SmarterTokenAuthentication`,
    the same check as the rest of the Smarter api, which reads the ``SmarterAuthToken`` from the
    database, refuses a key that is unknown or not active, and sends its authentication signals.

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
    if not user.is_active:
        return None, HTTPStatus.FORBIDDEN
    if not user.is_staff:
        return None, HTTPStatus.FORBIDDEN
    return user, HTTPStatus.OK


def rate_limited(view: SmarterView, request: HttpRequest) -> Optional[JsonResponse]:
    """
    Return a ``429 Too Many Requests`` response if the request's IP address is over the rate limit.

    Each call counts the request against its IP address's limit, in the cache (Redis), which every
    pod shares: see
    :func:`~smarter.apps.mcpserver.ratelimit.is_rate_limited`. A refused request is logged as a
    warning, and its response carries a JSON-RPC error and a ``Retry-After`` header, in seconds.

    :param view: The view, for logging.
    :param request: The request.
    :returns: The response, or None if the request may go on.
    """
    ip = client_ip(request)
    if not is_rate_limited(ip):
        return None
    logger.warning("%s rate limited %s", view.formatted_class_name, ip)
    message = "rate limit exceeded: too many requests from your IP address. Try again later."
    error = MCPServerBase.error(None, RATE_LIMITED, message)
    body = MCPServerBase.dump(error)
    limited = JsonResponse(body, status=HTTPStatus.TOO_MANY_REQUESTS)
    limited["Retry-After"] = str(retry_after())
    return limited


def answer(request: HttpRequest, server: MCPServerBase) -> HttpResponse:
    """
    Answer the JSON-RPC message, or batch of messages, of a request's body with a server.

    Both views end with this, once they have checked the rate limit and, for the operations
    server, the api key.

    :param request: The request.
    :param server: The MCP server.
    :returns: The JSON-RPC response, ``202 Accepted`` if no message needs one, or ``400 Bad Request``
        if the body is not JSON.
    """
    try:
        payload = json.loads(request.body or b"")
    except ValueError:
        error = MCPServerBase.error(None, mcp_types.PARSE_ERROR, "the request body is not JSON.")
        body = MCPServerBase.dump(error)
        return JsonResponse(body, status=HTTPStatus.BAD_REQUEST)
    response = server.handle(payload)
    if response is None:
        return HttpResponse(status=HTTPStatus.ACCEPTED)
    return JsonResponse(response, safe=False)


@method_decorator(csrf_exempt, name="dispatch")
@method_decorator(never_cache, name="dispatch")
class SmarterProjectMCPServerView(SmarterView):
    """
    The MCP Streamable HTTP endpoint of the Smarter Project MCP server.

    It is public: no authentication, but a rate limit for each IP address. CSRF does not apply,
    because MCP clients are not browsers with a session, and responses are never cached, because
    each one answers a different JSON-RPC message.

    :param repository: From the url: the repository's name, or None for every repository.
    """

    http_method_names = ["post", "options"]
    """Only POST and OPTIONS: GET and DELETE are ``405 Method Not Allowed``, as MCP clients expect of a stateless server."""

    @property
    def formatted_class_name(self) -> str:
        """The module and class name, formatted for the start of a log message."""
        module_name = logging.SmarterFormattedText.text(__name__)
        return f"{module_name}.{self.__class__.__name__}"

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
                choices = ", ".join(repository_names())
                detail = f"{repository} is not a repository of The Smarter Project: {choices}."
                return JsonResponse({"detail": detail}, status=HTTPStatus.NOT_FOUND)
        github_token = bearer_token(request)
        server = SmarterProjectMCPServer(project_repository, github_token=github_token)
        return answer(request, server)


@method_decorator(csrf_exempt, name="dispatch")
@method_decorator(never_cache, name="dispatch")
class SmarterOperationsMCPServerView(SmarterView):
    """
    The MCP Streamable HTTP endpoint of the Smarter Operations MCP server, for staff only.

    It checks the rate limit first, then the api key of the ``Authorization: Token`` header, with
    :func:`staff_user`, and reads the JSON-RPC only for an active staff user, so that nobody else
    learns even which tools the server has. The server's tools record each call in the audit trail,
    :class:`~smarter.apps.mcpserver.models.OperationsToolCall`, under that user.
    """

    http_method_names = ["post", "options"]
    """Only POST and OPTIONS: GET and DELETE are ``405 Method Not Allowed``, as MCP clients expect of a stateless server."""

    @property
    def formatted_class_name(self) -> str:
        """The module and class name, formatted for the start of a log message."""
        module_name = logging.SmarterFormattedText.text(__name__)
        return f"{module_name}.{self.__class__.__name__}"

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
            ip = client_ip(request)
            logger.warning("%s refused a request from %s: %s", self.formatted_class_name, ip, status)
            if status == HTTPStatus.UNAUTHORIZED:
                message = "this server requires the api key of a staff user, in an Authorization: Token <key> header."
            else:
                message = "this server is for the platform's staff only."
            error = MCPServerBase.error(None, UNAUTHORIZED, message)
            body = MCPServerBase.dump(error)
            refused = JsonResponse(body, status=status)
            if status == HTTPStatus.UNAUTHORIZED:
                refused["WWW-Authenticate"] = "Token"
            return refused
        server = SmarterOperationsMCPServer(user)
        return answer(request, server)


__all__ = [
    "SmarterOperationsMCPServerView",
    "SmarterProjectMCPServerView",
    "api_key",
    "bearer_token",
    "staff_user",
]
