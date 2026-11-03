"""
The cache of the MCPServer's public tool results.

Every tool of the MCP server is read-only, and its data changes only when a repository, or
the blog, is indexed again. So each tool call's result is cached for
:data:`TOOL_RESULT_CACHE_TTL` seconds, by the server's scope, the tool's name and its
validated arguments, plus an index generation that changes whenever an index changes. A
newly indexed repository or post is therefore found at once, and not an hour later.

- :meth:`~smarter.apps.mcpserver.protocol.tools.public.PublicTool.call` caches each result with
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
"""Seconds to cache a tool call's result: one hour.

A new index generation makes a result stale sooner, so the TTL only bounds how long a stale
entry stays in Redis.
"""

TOOL_CACHE_NAMESPACE = "mcpserver"
"""The namespace of the server's tool results in :func:`~smarter.lib.cache.tool_results.cached_tool_call`."""

INDEX_GENERATION_KEY = "smarter.apps.mcpserver.protocol.caching.index_generation"
"""The cache key of the current index generation, which is part of every cached result's key."""


def index_generation() -> int:
    """
    Return the current index generation, which is part of the key of every cached tool result.

    The generation is stored in the cache, without a timeout, by
    :func:`invalidate_cached_tool_results`. Side effect: one cache read.

    :returns: The time, in nanoseconds, when an index last changed, or 0 if none has since the cache was cleared.
    """
    generation = lazy_cache.get(INDEX_GENERATION_KEY)
    if generation is None:
        return 0
    return int(generation)


def invalidate_cached_tool_results() -> None:
    """
    Start a new index generation, so that every cached tool result is stale and expires with its TTL.

    Nothing is deleted: the old results are simply never looked up again, because every new
    key holds the new generation. That is cheaper, and safer, than finding and deleting every
    key of the namespace.

    Side effects: one cache write, of :data:`INDEX_GENERATION_KEY`, without a timeout, and an
    info log message.
    """
    generation = time.time_ns()
    lazy_cache.set(INDEX_GENERATION_KEY, generation, timeout=None)
    logger.info("%s.invalidate_cached_tool_results() started a new index generation.", logger_prefix)


__all__ = ["TOOL_CACHE_NAMESPACE", "TOOL_RESULT_CACHE_TTL", "index_generation", "invalidate_cached_tool_results"]
