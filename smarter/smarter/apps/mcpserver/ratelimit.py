"""
The per-IP rate limit of the Smarter Project MCP server.

The MCP server requires no authentication, so each client IP address may send at most
``smarter_settings.mcpserver_rate_limit`` requests a minute, 1200 by default. The requests
are counted in fixed one-minute windows, in Redis, so that every pod of the platform shares
the count. A request beyond the limit is answered ``429 Too Many Requests``, with a
``Retry-After`` header, until the window ends.

The client's address is found as :class:`~smarter.common.mixins.SmarterMiddlewareMixin`
finds it, from ``X-Forwarded-For``, ``X-Real-IP``, ``CF-Connecting-IP`` or the connection
itself, ignoring private addresses, which are the platform's own proxies. A request whose
public address cannot be determined, e.g. in local development, is not limited.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

import time
from typing import Optional

from django.http import HttpRequest

from smarter.common.conf import smarter_settings
from smarter.common.mixins import SmarterMiddlewareMixin
from smarter.lib.cache import lazy_cache

WINDOW_SECONDS = 60
"""The length of a rate limit window."""
RATE_LIMITED = -32010
"""The JSON-RPC error code of a rate-limited request, in the implementation-defined range of MCP's error codes."""


class ClientAddress(SmarterMiddlewareMixin):
    """:meth:`SmarterMiddlewareMixin.get_client_ip`, outside of a middleware."""

    def __init__(self):
        super().__init__(get_response=lambda request: None)


_client_address: Optional[ClientAddress] = None


def client_ip(request: HttpRequest) -> Optional[str]:
    """
    Return the public IP address of a request's client.

    :param request: The request.
    :returns: The address, or None if it cannot be determined.
    """
    global _client_address  # pylint: disable=global-statement
    if _client_address is None:
        _client_address = ClientAddress()
    return _client_address.get_client_ip(request)


def current_window() -> int:
    """Return the number of the current rate limit window."""
    return int(time.time() // WINDOW_SECONDS)


def retry_after() -> int:
    """Return the seconds until the current rate limit window ends."""
    return max(1, WINDOW_SECONDS - int(time.time() % WINDOW_SECONDS))


def rate_limit_key(ip: str, window: int) -> str:
    """Return the cache key of a client's request count in a window."""
    return f"smarter.apps.mcpserver.ratelimit.{ip}.{window}"


def is_rate_limited(ip: Optional[str]) -> bool:
    """
    Count a request of a client, and return whether the client is over the limit.

    :param ip: The client's IP address, from :func:`client_ip`.
    :returns: True if the client has sent more than ``smarter_settings.mcpserver_rate_limit``
        requests in the current window. Always False if the limit is 0, or the address is unknown.
    """
    limit = smarter_settings.mcpserver_rate_limit
    if not limit or not ip:
        return False
    key = rate_limit_key(ip, current_window())
    if lazy_cache.add(key, 1, timeout=WINDOW_SECONDS * 2):
        return 1 > limit
    try:
        count = lazy_cache.incr(key)
    except ValueError:
        # the key expired between add() and incr().
        lazy_cache.set(key, 1, timeout=WINDOW_SECONDS * 2)
        count = 1
    return count > limit


__all__ = ["RATE_LIMITED", "client_ip", "is_rate_limited", "retry_after"]
