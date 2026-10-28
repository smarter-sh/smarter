"""
The cache of the Smarter Project MCP server's tool results.

Every tool of the MCP server is read-only, and its data changes only when a repository, or
the blog, is indexed again. So each tool call's result is cached for
:data:`TOOL_RESULT_CACHE_TTL` seconds, by the server's scope, the tool's name and its
validated arguments, plus an index generation that changes whenever an index changes. A
newly indexed repository or post is therefore found at once, and not an hour later.

- :meth:`~smarter.apps.mcpserver.tools.SmarterProjectTool.call` caches each result with
  :func:`smarter.lib.cache.tool_results.cached_tool_call`, keyed by :func:`index_generation`.
- :func:`invalidate_cached_tool_results` starts a new index generation, which makes every
  cached result stale. :mod:`~smarter.apps.mcpserver.receivers` calls it when an index changes.

A tool raises :class:`~smarter.apps.mcpserver.exceptions.SmarterMCPServerToolError` on an
error, so errors are never cached.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

import time

from cache_results import lazy_cache

from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.MCPSERVER_LOGGING, SmarterWaffleSwitches.CACHE_LOGGING]
)
logger_prefix = logging.SmarterFormattedText.text(__name__)

TOOL_RESULT_CACHE_TTL = 60 * 60
"""Seconds to cache a tool call's result."""

TOOL_CACHE_NAMESPACE = "mcpserver"
"""The namespace of the server's tool results in :func:`~smarter.lib.cache.tool_results.cached_tool_call`."""

INDEX_GENERATION_KEY = "smarter.apps.mcpserver.caching.index_generation"
"""The cache key of the current index generation, which is part of every cached result's key."""


def index_generation() -> int:
    """
    Return the current index generation.

    :returns: The time, in nanoseconds, when an index last changed, or 0 if none has since the cache was cleared.
    """
    return int(lazy_cache.get(INDEX_GENERATION_KEY) or 0)


def invalidate_cached_tool_results() -> None:
    """Start a new index generation, so that every cached tool result is stale and expires with its TTL."""
    lazy_cache.set(INDEX_GENERATION_KEY, time.time_ns(), timeout=None)
    logger.info("%s.invalidate_cached_tool_results() started a new index generation.", logger_prefix)


__all__ = ["TOOL_CACHE_NAMESPACE", "TOOL_RESULT_CACHE_TTL", "index_generation", "invalidate_cached_tool_results"]
