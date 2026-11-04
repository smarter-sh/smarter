"""
Django signal receivers of the MCPServer app.

They log the MCPServer's requests and tool calls, and the outcome of each attempt to index a
repository or the blog. One of them also keeps the tool result cache correct: when a repository
is indexed at a new commit, :func:`handle_mcpserver_repository_indexed` starts a new index
generation, so that no tool answers from the old files (see
:mod:`smarter.apps.mcpserver.protocol.caching`).

The signals are defined in :mod:`smarter.apps.mcpserver.signals`. The receivers are connected
when :meth:`smarter.apps.mcpserver.apps.MCPServerConfig.ready` imports this module.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

# pylint: disable=W0613,C0115

from django.dispatch import receiver

from smarter.apps.mcpserver.protocol.caching import invalidate_cached_tool_results
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .models import RepositoryIndex
from .signals import (
    mcpserver_called,
    mcpserver_repository_index_failed,
    mcpserver_repository_indexed,
    mcpserver_tool_called,
)

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.MCPSERVER_LOGGING])
logger_prefix = logging.SmarterFormattedText.text(__name__)


@receiver(mcpserver_called, dispatch_uid="mcpserver_called")
def handle_mcpserver_called(sender, server: str, method: str, **kwargs):
    """
    Log a JSON-RPC request to the MCPServer, at DEBUG.

    :param sender: The class that sent the signal.
    :param server: The server's name, e.g. ``smarter-project-smarter-cli``.
    :param method: The JSON-RPC method, e.g. ``tools/call``.
    :param kwargs: The signal's other arguments, which are ignored.
    """
    logger.debug("%s.handle_mcpserver_called() %s %s", logger_prefix, server, method)


@receiver(mcpserver_tool_called, dispatch_uid="mcpserver_tool_called")
def handle_mcpserver_tool_called(
    sender, server: str, tool_name: str, arguments: dict, is_error: bool, characters: int, **kwargs
):
    """
    Log a call to one of the MCPServer's tools, with its argument names and the length of its result.

    The argument values are logged at DEBUG only. They are whatever the caller sent, and the public
    endpoint is open to anyone: a search query, an issue's body, or a pull request's author and
    files may hold personal data or a credential, which must not reach the INFO log.

    :param sender: The class that sent the signal.
    :param server: The server's name.
    :param tool_name: The tool's name, e.g. ``read_file``.
    :param arguments: The tool's arguments.
    :param is_error: Whether the tool returned an error.
    :param characters: The length of the tool's result.
    :param kwargs: The signal's other arguments, which are ignored.
    """
    argument_names = ", ".join(arguments.keys())
    if is_error:
        outcome = ", an error"
    else:
        outcome = ""
    logger.info(
        "%s.handle_mcpserver_tool_called() %s %s(%s) returned %s characters%s",
        logger_prefix,
        server,
        tool_name,
        argument_names,
        characters,
        outcome,
    )
    formatted_arguments = logging.SmarterFormattedText.json(arguments)
    logger.debug(
        "%s.handle_mcpserver_tool_called() %s %s arguments: %s",
        logger_prefix,
        server,
        tool_name,
        formatted_arguments,
    )


@receiver(mcpserver_repository_indexed, dispatch_uid="mcpserver_repository_indexed")
def handle_mcpserver_repository_indexed(sender, index: RepositoryIndex, **kwargs):
    """
    Make the cached tool results stale, since a repository's files changed, and log it.

    Side effect: a cache write, through
    :func:`~smarter.apps.mcpserver.protocol.caching.invalidate_cached_tool_results`, which starts a new
    index generation.

    :param sender: The function that indexed the repository.
    :param index: The repository's index, at its new commit.
    :param kwargs: The signal's other arguments, which are ignored.
    """
    invalidate_cached_tool_results()
    logger.info(
        "%s.handle_mcpserver_repository_indexed() %s indexed at %s: %s files, %s bytes",
        logger_prefix,
        index.repository,
        index.commit_sha,
        index.file_count,
        index.total_bytes,
    )


@receiver(mcpserver_repository_index_failed, dispatch_uid="mcpserver_repository_index_failed")
def handle_mcpserver_repository_index_failed(sender, repository: str, error: str, **kwargs):
    """
    Log a repository, or the blog, that could not be indexed, at WARNING.

    The cached tool results are left alone, because the index did not change.

    :param sender: The function that tried to index the repository.
    :param repository: The repository's name, or the blog's.
    :param error: Why it could not be indexed.
    :param kwargs: The signal's other arguments, which are ignored.
    """
    logger.warning(
        "%s.handle_mcpserver_repository_index_failed() %s could not be indexed: %s",
        logger_prefix,
        repository,
        error,
    )
