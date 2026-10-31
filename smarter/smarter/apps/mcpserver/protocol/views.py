# pylint: disable=W0613
"""
The Django view of the Smarter Project MCP server.

:class:`SmarterProjectMCPServerView` is the MCP Streamable HTTP endpoint of
:class:`~smarter.apps.mcpserver.protocol.server.SmarterProjectMCPServer`. It is mounted at:

- ``/api/v1/mcp/smarter-project/``: every repository of The Smarter Project.
- ``/api/v1/mcp/smarter-project/<repository>/``: one repository, e.g. ``smarter-cli``.

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

from .server import SmarterProjectMCPServer

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.MCPSERVER_LOGGING])

BEARER_SCHEME = "bearer"


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
        ip = client_ip(request)
        if is_rate_limited(ip):
            logger.warning("%s rate limited %s", self.formatted_class_name, ip)
            error = SmarterProjectMCPServer.error(
                None, RATE_LIMITED, "rate limit exceeded: too many requests from your IP address. Try again later."
            )
            limited = JsonResponse(SmarterProjectMCPServer.dump(error), status=HTTPStatus.TOO_MANY_REQUESTS)
            limited["Retry-After"] = str(retry_after())
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
        try:
            payload = json.loads(request.body or b"")
        except ValueError:
            error = SmarterProjectMCPServer.error(None, mcp_types.PARSE_ERROR, "the request body is not JSON.")
            return JsonResponse(SmarterProjectMCPServer.dump(error), status=HTTPStatus.BAD_REQUEST)
        response = SmarterProjectMCPServer(project_repository, github_token=bearer_token(request)).handle(payload)
        if response is None:
            return HttpResponse(status=HTTPStatus.ACCEPTED)
        return JsonResponse(response, safe=False)


__all__ = ["SmarterProjectMCPServerView", "bearer_token"]
