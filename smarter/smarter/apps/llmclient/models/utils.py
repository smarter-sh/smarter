"""Utility functions for the LLMClient app, including caching and validation helpers."""

from typing import Callable, Optional

from django.http import HttpRequest

from smarter.common.helpers.console_helpers import (
    formatted_text,
)
from smarter.lib import logging
from smarter.lib.cache import cache_results
from smarter.lib.django.waffle.switches import SmarterWaffleSwitches

from .llmclient import LLMClient
from .llmclient_helper import LLMClientHelper

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.LLM_CLIENT_LOGGING])

LLMCLIENT_HOST_PATHS = ("/", "/config/", "/prompt/")
"""The paths that a deployed LLMClient's own host serves.

See ``smarter.urls.llmclients``.
"""


class LLMClientNotResolvedError(Exception):
    """No LLMClient serves the request's host and path.

    Raised inside the cache, so that a miss is never cached.
    """


def _llmclient_id_resolver(request: Optional[HttpRequest] = None) -> Callable[[str, str, str], int]:
    """
    The cached resolution of a host and path to the id of the LLMClient that serves them.

    The function is rebuilt for each request, because it resolves with the request, but its cache key
    depends only on its module, name and arguments, so every instance shares the same cache, and
    :func:`invalidate_cached_llmclient_by_hosts` can invalidate it.

    :param request: The request, which LLMClientHelper resolves. None for invalidation only.
    :type request: Optional[django.http.HttpRequest]
    :returns: The cached function, ``(host, path, username) -> LLMClient id``.
    """

    # pylint: disable=W0613
    @cache_results()
    def resolve_llmclient_id(host: str, path: str, username: str) -> int:
        """
        The id of the LLMClient that serves the host and path, for the user.

        ``username`` is part of the key because LLMClientHelper resolves some urls, e.g. the cli's
        ``/api/v1/cli/prompt/<name>/``, by the user's LLMClients. It is empty for a deployed LLMClient's
        own host, whose resolution doesn't depend on the user.

        The id, not the LLMClient, is cached, so that its fields, e.g. ``deployed``, are always read fresh.
        A miss raises, so that it is never cached: a host that is not yet deployed resolves as soon as
        it is.

        :raises LLMClientNotResolvedError: If no LLMClient serves them.
        """
        llmclient = LLMClientHelper(request).llmclient if request is not None else None
        if llmclient is None:
            raise LLMClientNotResolvedError(f"No LLMClient serves {host}{path}")
        logger.debug(
            "%s.resolve_llmclient_id() resolved and cached llmclient '%s' for %s%s",
            formatted_text(__name__),
            llmclient,
            host,
            path,
        )
        return llmclient.pk

    return resolve_llmclient_id


def _request_host(request: HttpRequest) -> str:
    """The request's host, as the client sent it, lowercased.

    ``get_host()`` would raise for a disallowed host.
    """
    return str(request.META.get("HTTP_HOST") or request.META.get("SERVER_NAME") or "").strip().lower()


def _cache_args(request: HttpRequest) -> tuple[str, str, str]:
    """The resolution's cache key: the host and path, and the user unless the path is a deployed LLMClient's."""
    host = _request_host(request)
    path = request.path
    if path in LLMCLIENT_HOST_PATHS:
        return host, path, ""
    user = getattr(request, "user", None)
    username = str(getattr(user, "username", "") or "") if getattr(user, "is_authenticated", False) else ""
    return host, path, username


def get_cached_llmclient_by_request(request: HttpRequest) -> Optional[LLMClient]:
    """
    Returns the LLMClient that serves the request's host and path, or None.

    The resolution, by LLMClientHelper, is cached by host and path, without the scheme or the query
    string, and by user, except on a deployed LLMClient's own paths, so that its cache keys are bounded
    and can be invalidated (:func:`invalidate_cached_llmclient_by_hosts`). Only the LLMClient's id is
    cached, and the LLMClient is read fresh, by its primary key, on each call; if it was deleted, the
    request is resolved again. A host that resolves to no LLMClient is never cached, so it resolves as
    soon as an LLMClient serves it.

    .. code-block:: python

        llmclient = get_cached_llmclient_by_request(request)
        print(llmclient.url)

    :param request: The Django HttpRequest object containing the URL and user context.
    :type request: django.http.HttpRequest
    :returns: The LLMClient instance associated with the request's host and path, or None if not found.
    :rtype: Optional[LLMClient]
    """
    if not request:
        return None
    resolver = _llmclient_id_resolver(request)
    args = _cache_args(request)
    for attempt in range(2):
        try:
            llmclient_id = resolver(*args)
        except LLMClientNotResolvedError:
            return None
        llmclient = LLMClient.objects.filter(pk=llmclient_id).first()
        if llmclient is not None or attempt:
            return llmclient
        # the cached LLMClient was deleted: resolve again.
        resolver.invalidate(*args)  # type: ignore[attr-defined]
    return None


def invalidate_cached_llmclient_by_hosts(llmclient: LLMClient) -> None:
    """
    Invalidate the cached resolution of an LLMClient's own hosts, its default host and its custom.

    domain, e.g. after it is renamed or deleted.

    :param llmclient: The LLMClient.
    :type llmclient: LLMClient
    """
    resolver = _llmclient_id_resolver()
    hosts = set()
    for attribute in ("default_host", "custom_host"):
        try:
            host = getattr(llmclient, attribute)
        # pylint: disable=broad-exception-caught
        except Exception:
            host = None
        if host:
            hosts.add(str(host).lower())
    for host in hosts:
        for path in LLMCLIENT_HOST_PATHS:
            resolver.invalidate(host, path, "")  # type: ignore[attr-defined]


__all__ = [
    "LLMCLIENT_HOST_PATHS",
    "LLMClientNotResolvedError",
    "get_cached_llmclient_by_request",
    "invalidate_cached_llmclient_by_hosts",
]
