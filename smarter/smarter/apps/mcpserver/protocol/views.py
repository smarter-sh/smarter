# pylint: disable=W0613
"""
The Django views of the MCPServer's two endpoints, over MCP's Streamable HTTP transport.

:class:`PublicEndpointView` is the endpoint of the public tools,
:class:`~smarter.apps.mcpserver.protocol.public.PublicEndpoint`. It is mounted at:

- ``/api/v1/mcp/smarter-project/``: every repository of The Smarter Project.
- ``/api/v1/mcp/smarter-project/<repository>/``: one repository, e.g. ``smarter-cli``.

:class:`StaffEndpointView` is the endpoint of the staff-only tools,
:class:`~smarter.apps.mcpserver.protocol.staff.StaffEndpoint`, at
``/api/v1/mcp/smarter-operations/``. It serves only the platform's staff
(:func:`~smarter.apps.account.utils.is_platform_staff`: the active staff users of the Smarter
account, not the admins of other accounts), in one of two ways:

- a request whose ``Authorization: Token`` header carries a staff user's api key (a
  ``SmarterAuthToken``), e.g. from Claude Code, or
- a request that this platform signed, whose ``X-Smarter-Acting-User`` header names the staff user
  who is chatting with an LLMClient, e.g. ``smarter_sysadmin``: see
  :mod:`~smarter.apps.mcpserver.services.acting_user`. One that the platform signed for nobody in
  particular, e.g. the background refresh of an MCPClient's catalog, may list the tools, but every
  tool refuses to run.

Without a valid credential it answers ``401 Unauthorized``, and for a user who is not one of the
platform's staff ``403 Forbidden``, before it reads the request's JSON-RPC. The checks are in
:mod:`smarter.apps.mcpserver.protocol.auth`.

Only POST is served. A POST whose messages are all notifications is answered ``202
Accepted``, with no body, and every other POST with ``application/json``. The server
issues no session, and offers no GET stream, so GET and DELETE are answered ``405 Method
Not Allowed``, which MCP clients expect of a stateless server.

The public endpoint requires no authentication: its read-only tools serve the public
repositories of The Smarter Project. A client may send the user's GitHub classic personal
access token in an ``Authorization: Bearer`` header, and is then also served the tools
that write as that user: ``create_issue``, ``comment_on_issue``, ``close_issue`` and
``create_pull_request``. The token is passed to the tool as a
``SecretStr``, and is never logged. Each client IP address may send at most
``smarter_settings.mcpserver_rate_limit`` requests a minute: see
:mod:`smarter.apps.mcpserver.protocol.ratelimit`.

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

from smarter.apps.mcpserver.protocol.auth import (
    acting_staff_user,
    bearer_token,
    staff_user,
)
from smarter.apps.mcpserver.protocol.base import MCPEndpointBase
from smarter.apps.mcpserver.protocol.public import PublicEndpoint
from smarter.apps.mcpserver.protocol.ratelimit import (
    RATE_LIMITED,
    client_ip,
    is_rate_limited,
    retry_after,
)
from smarter.apps.mcpserver.protocol.staff import StaffEndpoint
from smarter.apps.mcpserver.services.acting_user import ACTING_USER_HEADER
from smarter.apps.mcpserver.services.repositories import (
    get_repository,
    repository_names,
)
from smarter.lib import json, logging
from smarter.lib.django.views import SmarterView
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.MCPSERVER_LOGGING])

UNAUTHORIZED = -32001
"""The JSON-RPC error code of a request without a valid staff api key."""


def rate_limited(view: SmarterView, request: HttpRequest) -> Optional[JsonResponse]:
    """
    Return a ``429 Too Many Requests`` response if the request's IP address is over the rate limit.

    Each call counts the request against its IP address's limit, in the cache (Redis), which every
    pod shares: see
    :func:`~smarter.apps.mcpserver.protocol.ratelimit.is_rate_limited`. A refused request is logged as a
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
    error = MCPEndpointBase.error(None, RATE_LIMITED, message)
    body = MCPEndpointBase.dump(error)
    limited = JsonResponse(body, status=HTTPStatus.TOO_MANY_REQUESTS)
    limited["Retry-After"] = str(retry_after())
    return limited


def answer(request: HttpRequest, server: MCPEndpointBase) -> HttpResponse:
    """
    Answer the JSON-RPC message, or batch of messages, of a request's body with a server.

    Both views end with this, once they have checked the rate limit and, for the staff-only
    endpoint, the caller.

    :param request: The request.
    :param server: The MCP server.
    :returns: The JSON-RPC response, ``202 Accepted`` if no message needs one, or ``400 Bad Request``
        if the body is not JSON.
    """
    try:
        payload = json.loads(request.body or b"")
    except ValueError:
        error = MCPEndpointBase.error(None, mcp_types.PARSE_ERROR, "the request body is not JSON.")
        body = MCPEndpointBase.dump(error)
        return JsonResponse(body, status=HTTPStatus.BAD_REQUEST)
    response = server.handle(payload)
    if response is None:
        return HttpResponse(status=HTTPStatus.ACCEPTED)
    return JsonResponse(response, safe=False)


@method_decorator(csrf_exempt, name="dispatch")
@method_decorator(never_cache, name="dispatch")
class PublicEndpointView(SmarterView):
    """
    The view of the MCPServer's public endpoint, over MCP's Streamable HTTP transport.

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
        server = PublicEndpoint(project_repository, github_token=github_token)
        return answer(request, server)


@method_decorator(csrf_exempt, name="dispatch")
@method_decorator(never_cache, name="dispatch")
class StaffEndpointView(SmarterView):
    """
    The view of the MCPServer's staff-only endpoint, over MCP's Streamable HTTP transport, for staff only.

    It checks the rate limit first, then the caller: the signed ``X-Smarter-Acting-User`` header
    that the platform sends for the user who is chatting with an LLMClient, with
    :func:`acting_staff_user`, or else the api key of the ``Authorization: Token`` header, with
    :func:`staff_user`. It reads the JSON-RPC only for one of the platform's staff, or for a request
    that the platform signed itself, so that nobody else learns even which tools the server has.
    The server's tools record each call in the audit trail,
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
            without a valid api key or signed acting user is ``401 Unauthorized``, one whose user is
            not one of the platform's staff is ``403 Forbidden``, a client over the rate limit is
            ``429 Too Many Requests``, and a body that is not JSON is ``400 Bad Request``.
        """
        limited = rate_limited(self, request)
        if limited is not None:
            return limited
        signed_acting_user = request.headers.get(ACTING_USER_HEADER)
        if signed_acting_user is not None:
            user, status = acting_staff_user(signed_acting_user)
        else:
            user, status = staff_user(request)
        if status != HTTPStatus.OK:
            # the status, not the client's IP address, which is personal data.
            logger.warning("%s refused a request: %s", self.formatted_class_name, status)
            if status == HTTPStatus.UNAUTHORIZED:
                message = "this server requires the api key of a staff user, in an Authorization: Token <key> header."
            else:
                message = "this server is for the platform's staff only."
            error = MCPEndpointBase.error(None, UNAUTHORIZED, message)
            body = MCPEndpointBase.dump(error)
            refused = JsonResponse(body, status=status)
            if status == HTTPStatus.UNAUTHORIZED:
                refused["WWW-Authenticate"] = "Token"
            return refused
        server = StaffEndpoint(user)
        return answer(request, server)


__all__ = ["PublicEndpointView", "StaffEndpointView", "answer", "rate_limited"]
