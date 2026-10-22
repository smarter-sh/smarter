"""Utility functions for the LLMClient app, including caching and validation helpers."""

from typing import Callable, NamedTuple, Optional

from django.http import HttpRequest

from smarter.common.conf import smarter_settings
from smarter.common.helpers.console_helpers import (
    formatted_text,
)
from smarter.lib import logging
from smarter.lib.cache import cache_results
from smarter.lib.django.waffle.switches import SmarterWaffleSwitches

from .llmclient import LLMClient
from .llmclient_extension import LLMClientExtensions
from .llmclient_helper import LLMClientHelper
from .llmclient_mcpclient import LLMClientMCPClients
from .llmclient_plugin import LLMClientPlugin

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
        # its owner's profile, account and user too, which the chat session reads.
        llmclient = (
            LLMClient.objects.filter(pk=llmclient_id)
            .select_related("user_profile__account", "user_profile__user")
            .first()
        )
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


class LLMClientToolCounts(NamedTuple):
    """The number of each kind of tool that an LLMClient offers the LLM."""

    extensions: int
    plugins: int
    mcpclients: int

    @property
    def total(self) -> int:
        """All of the LLMClient's tools."""
        return self.extensions + self.plugins + self.mcpclients


@cache_results(timeout=smarter_settings.llmclient_cache_expiration)
def get_cached_llmclient_tool_counts(llmclient_id: int) -> LLMClientToolCounts:
    """
    Count an LLMClient's extensions, plugins and MCPClients, the tools that it offers the LLM.

    Smarter Chat's configuration api reads these counts on every page load, for ``total_tools``,
    ``plugins.meta_data.total_plugins`` and ``extensions.meta_data.total_extensions``. They are
    counted, rather than loaded and serialized, and cached until a tool is added to or removed from
    the LLMClient (see :func:`invalidate_cached_llmclient_tool_counts`). A tool with an empty name is
    left out, as :meth:`smarter.apps.llmclient.serializers.LLMClientSerializer.get_tools` does.

    .. code-block:: python

        counts = get_cached_llmclient_tool_counts(llmclient.id)
        print(counts.total)

    :param llmclient_id: The LLMClient's id.
    :type llmclient_id: int
    :returns: The counts.
    :rtype: LLMClientToolCounts
    """
    return LLMClientToolCounts(
        extensions=LLMClientExtensions.objects.filter(llmclient_id=llmclient_id).exclude(extension__slug="").count(),
        plugins=LLMClientPlugin.objects.filter(llmclient_id=llmclient_id).exclude(plugin_meta__name="").count(),
        mcpclients=LLMClientMCPClients.objects.filter(llmclient_id=llmclient_id).exclude(mcpclient__name="").count(),
    )


def invalidate_cached_llmclient_tool_counts(llmclient_id: Optional[int]) -> None:
    """
    Invalidate an LLMClient's cached tool counts, after one of its tools was added or removed.

    :param llmclient_id: The LLMClient's id, or None for a link row without one.
    :type llmclient_id: Optional[int]
    """
    if llmclient_id is not None:
        get_cached_llmclient_tool_counts.invalidate(llmclient_id)  # type: ignore[attr-defined]


__all__ = [
    "LLMCLIENT_HOST_PATHS",
    "LLMClientNotResolvedError",
    "LLMClientToolCounts",
    "get_cached_llmclient_by_request",
    "get_cached_llmclient_tool_counts",
    "invalidate_cached_llmclient_by_hosts",
    "invalidate_cached_llmclient_tool_counts",
]
