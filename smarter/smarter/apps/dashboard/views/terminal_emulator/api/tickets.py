# pylint: disable=W0613
"""
Single use tickets for the web console terminal's WebSocket.

A browser opens a WebSocket with its session cookie, which the browser also sends when another
site's page opens the same WebSocket. Channels' origin check refuses such a connection, and a
ticket refuses it as well: the terminal's page POSTs, with its CSRF token, to
:class:`TerminalTicketApiView`, which only a superuser can call, and opens the WebSocket with the
ticket that it returns. :class:`.consumers.TerminalConsumer` accepts the connection only if the
ticket was issued to the same user, within :data:`.const.TERMINAL_TICKET_TIMEOUT` seconds, and has
not been redeemed before.
"""

import secrets

from cache_results import lazy_cache
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, JsonResponse
from django.utils.decorators import method_decorator

from smarter.lib import logging
from smarter.lib.django.views import SmarterAuthenticatedNeverCachedWebView

from .const import TERMINAL_TICKET_TIMEOUT, TERMINAL_WEBSOCKET_PATH
from .messages import TerminalTicket

logger = logging.getLogger(__name__)
logger_prefix = logging.SmarterFormattedText.text(__name__)

TICKET_CACHE_PREFIX = "smarter.apps.dashboard.terminal.ticket."
"""The cache key prefix of a ticket, whose value is the id of the user that it was issued to."""

MAX_TICKET_LENGTH = 128
"""Longer tickets are refused without a cache lookup."""


def issue_ticket(user_id: int) -> str:
    """
    Issue a ticket to a user, valid for :data:`.const.TERMINAL_TICKET_TIMEOUT` seconds.

    :param user_id: The user's id.
    :returns: The ticket.
    """
    ticket = secrets.token_urlsafe(32)
    lazy_cache.set(TICKET_CACHE_PREFIX + ticket, user_id, timeout=TERMINAL_TICKET_TIMEOUT)
    return ticket


def redeem_ticket(ticket: str, user_id: int) -> bool:
    """
    Redeem a ticket: whether it was issued to the user, and is still valid.

    A ticket can be
    redeemed once, by whoever presents it first, even by another user, who is refused.

    :param ticket: The ticket.
    :param user_id: The id of the user that presents it.
    :returns: True if the ticket was issued to the user, and has not expired or been redeemed.
    """
    if not ticket or len(ticket) > MAX_TICKET_LENGTH:
        return False
    key = TICKET_CACHE_PREFIX + ticket
    owner = lazy_cache.get(key)
    # delete() is True only for the caller that deleted it, so a ticket is redeemed once.
    if owner is None or not lazy_cache.delete(key):
        return False
    return owner == user_id


@method_decorator(login_required, name="dispatch")
class TerminalTicketApiView(SmarterAuthenticatedNeverCachedWebView):
    """
    Issue a terminal ticket to the signed in superuser.

    Wrapped in :func:`..enabled.require_terminal` in the url patterns, so that it is a 404 while
    the terminal is disabled, and for every other user.

    Response shape (:class:`.messages.TerminalTicket`):

    .. code-block:: json

        {"ticket": "Vb3...", "url": "/ws/terminal/"}
    """

    @property
    def formatted_class_name(self) -> str:
        """Returns a formatted string of the class name for logging purposes."""
        class_name = f"{__name__}.{TerminalTicketApiView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Issue a ticket.

        :param request: The POST request, with the CSRF token.
        :param args: Additional positional arguments forwarded by the URL dispatcher.
        :param kwargs: Additional keyword arguments forwarded by the URL dispatcher.
        :returns: The ticket, and the WebSocket's path.
        :rtype: django.http.JsonResponse
        """
        ticket = TerminalTicket(ticket=issue_ticket(request.user.pk), url=f"/{TERMINAL_WEBSOCKET_PATH}")
        logger.info("%s.post() issued a terminal ticket to %s.", self.formatted_class_name, request.user)
        return JsonResponse(ticket.model_dump(mode="json"))
