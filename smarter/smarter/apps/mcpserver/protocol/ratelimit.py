"""
The per-IP rate limit of the MCPServer's public endpoint.

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

from cache_results import lazy_cache
from django.http import HttpRequest

from smarter.common.conf import smarter_settings
from smarter.common.mixins import SmarterMiddlewareMixin

WINDOW_SECONDS = 60
"""The length of a rate limit window, in seconds."""

WINDOW_KEY_TIMEOUT = WINDOW_SECONDS * 2
"""How long a window's count is kept in the cache: two windows, so that it outlives its window."""

RATE_LIMITED = -32010
"""The JSON-RPC error code of a rate-limited request, in the implementation-defined range of MCP's error codes."""


class ClientAddress(SmarterMiddlewareMixin):
    """
    Finds a request's client address, as the platform's middleware does, outside of a middleware.

    :class:`~smarter.common.mixins.SmarterMiddlewareMixin` knows which headers carry the
    client's address behind the platform's proxies, in
    :meth:`~smarter.common.mixins.SmarterMiddlewareMixin.get_client_ip`. It is a middleware, so
    its constructor needs a ``get_response`` callable, which is never called here.
    """

    def __init__(self):
        """Create the helper, with a ``get_response`` that is never called."""
        super().__init__(get_response=lambda request: None)


_client_address: Optional[ClientAddress] = None
"""The one :class:`ClientAddress` of the process, created on the first call of :func:`client_ip`."""


def client_ip(request: HttpRequest) -> Optional[str]:
    """
    Return the public IP address of a request's client.

    The :class:`ClientAddress` helper is created on the first call, and reused.

    :param request: The request.
    :returns: The address, or None if it cannot be determined.
    """
    global _client_address  # pylint: disable=global-statement
    if _client_address is None:
        _client_address = ClientAddress()
    return _client_address.get_client_ip(request)


def current_window() -> int:
    """
    Return the number of the current rate limit window.

    The windows are numbered from the Unix epoch, so every pod agrees on the current one.

    :returns: The number of :data:`WINDOW_SECONDS`-long windows since the epoch.
    """
    now = time.time()
    return int(now // WINDOW_SECONDS)


def retry_after() -> int:
    """
    Return the seconds until the current rate limit window ends, for a ``Retry-After`` header.

    :returns: The seconds left in the window, at least 1.
    """
    now = time.time()
    seconds_into_window = int(now % WINDOW_SECONDS)
    seconds_left = WINDOW_SECONDS - seconds_into_window
    return max(1, seconds_left)


def rate_limit_key(ip: str, window: int) -> str:
    """
    Return the cache key of a client's request count in a window.

    :param ip: The client's IP address.
    :param window: The window's number, from :func:`current_window`.
    :returns: The key, e.g. ``smarter.apps.mcpserver.protocol.ratelimit.203.0.113.7.29374512``.
    """
    return f"smarter.apps.mcpserver.protocol.ratelimit.{ip}.{window}"


def is_rate_limited(ip: Optional[str]) -> bool:
    """
    Count a request of a client, and return whether the client is over the limit.

    The count is kept in the cache (Redis), so every pod of the platform shares it. The first
    request of a window creates its key with ``add()``, and each later one increments it with
    ``incr()``, which is atomic, so that concurrent requests are all counted.

    Side effects: one or two cache writes, unless the limit is off or the address is unknown.

    :param ip: The client's IP address, from :func:`client_ip`.
    :returns: True if the client has sent more than ``smarter_settings.mcpserver_rate_limit``
        requests in the current window. Always False if the limit is 0, or the address is unknown.
    """
    limit = smarter_settings.mcpserver_rate_limit
    if not limit or not ip:
        return False
    window = current_window()
    key = rate_limit_key(ip, window)
    is_first_request = lazy_cache.add(key, 1, timeout=WINDOW_KEY_TIMEOUT)
    if is_first_request:
        count = 1
    else:
        try:
            count = lazy_cache.incr(key)
        except ValueError:
            # the key expired between add() and incr().
            lazy_cache.set(key, 1, timeout=WINDOW_KEY_TIMEOUT)
            count = 1
    is_over_limit = count > limit
    return is_over_limit


__all__ = ["RATE_LIMITED", "client_ip", "is_rate_limited", "retry_after"]
