"""
Django Signal Receivers for mcpserver.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

# pylint: disable=W0613,C0115

from django.dispatch import receiver

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

module_prefix = __name__


@receiver(mcpserver_called, dispatch_uid="mcpserver_called")
def handle_mcpserver_called(sender, server: str, method: str, **kwargs):
    """Log a JSON-RPC request to the MCP server."""
    prefix = f"{logging.SmarterFormattedText.text(module_prefix)}.handle_mcpserver_called()"
    logger.debug("%s %s %s", prefix, server, method)


@receiver(mcpserver_tool_called, dispatch_uid="mcpserver_tool_called")
def handle_mcpserver_tool_called(
    sender, server: str, tool_name: str, arguments: dict, is_error: bool, characters: int, **kwargs
):
    """Log a tool call."""
    prefix = f"{logging.SmarterFormattedText.text(module_prefix)}.handle_mcpserver_tool_called()"
    logger.info(
        "%s %s %s(%s) returned %s characters%s",
        prefix,
        server,
        tool_name,
        logging.SmarterFormattedText.json(arguments),
        characters,
        ", an error" if is_error else "",
    )


@receiver(mcpserver_repository_indexed, dispatch_uid="mcpserver_repository_indexed")
def handle_mcpserver_repository_indexed(sender, index: RepositoryIndex, **kwargs):
    """Log a repository that was indexed."""
    prefix = f"{logging.SmarterFormattedText.text(module_prefix)}.handle_mcpserver_repository_indexed()"
    logger.info(
        "%s %s indexed at %s: %s files, %s bytes",
        prefix,
        index.repository,
        index.commit_sha,
        index.file_count,
        index.total_bytes,
    )


@receiver(mcpserver_repository_index_failed, dispatch_uid="mcpserver_repository_index_failed")
def handle_mcpserver_repository_index_failed(sender, repository: str, error: str, **kwargs):
    """Log a repository that could not be indexed."""
    prefix = f"{logging.SmarterFormattedText.text(module_prefix)}.handle_mcpserver_repository_index_failed()"
    logger.warning("%s %s could not be indexed: %s", prefix, repository, error)
