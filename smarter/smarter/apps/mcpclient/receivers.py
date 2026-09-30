"""
Django Signal Receivers for mcpclient.

.. note::

    **Experimental.** The MCPClient was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

# pylint: disable=W0613,C0115

from django.db import transaction
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .caching import invalidate_cached_catalog
from .models import MCPClient
from .serializers import MCPClientSerializer
from .signals import (
    mcpclient_connected,
    mcpclient_connection_failed,
    mcpclient_resource_read,
    mcpclient_tool_called,
    mcpclient_tool_failed,
    mcpclient_tool_responded,
)
from .tasks import refresh_mcpclient

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.MCPCLIENT_LOGGING])

module_prefix = __name__


@receiver(post_save, sender=MCPClient)
def mcpclient_saved(sender, instance: MCPClient, created: bool, **kwargs):
    """
    Log the MCPClient, and refresh its catalog once the transaction commits.

    Status updates are made with queryset updates, which do not send ``post_save``, so
    this runs only when the MCPClient's configuration is saved.
    """
    prefix = logging.formatted_text(f"{module_prefix}.mcpclient_saved()")
    data = logging.formatted_json(MCPClientSerializer(instance).data)
    logger.info("%s - %s %s, %s", prefix, "created" if created else "updated", instance, data)
    if instance.is_active and instance.endpoint_url:
        mcpclient_id = instance.pk
        transaction.on_commit(lambda: refresh_mcpclient.delay(mcpclient_id))


@receiver(pre_delete, sender=MCPClient)
def mcpclient_deleted(sender, instance: MCPClient, **kwargs):
    """Log the MCPClient, and invalidate its cached catalog."""
    prefix = logging.formatted_text(f"{module_prefix}.mcpclient_deleted()")
    logger.info("%s - %s", prefix, instance)
    invalidate_cached_catalog(instance)


@receiver(mcpclient_connected, dispatch_uid="mcpclient_connected")
def handle_mcpclient_connected(sender, mcpclient: MCPClient, catalog, **kwargs):
    """Log a successful connection to an MCP server."""
    logger.info(
        "%s - %s connected to %s %s, protocol %s, %s tools",
        logging.formatted_text(f"{module_prefix}.mcpclient_connected"),
        mcpclient.name,
        catalog.server_name,
        catalog.server_version,
        catalog.protocol_version,
        len(catalog.tools),
    )


@receiver(mcpclient_connection_failed, dispatch_uid="mcpclient_connection_failed")
def handle_mcpclient_connection_failed(sender, mcpclient: MCPClient, error: str, **kwargs):
    """Log a failed connection to an MCP server."""
    logger.warning(
        "%s - %s: %s",
        logging.formatted_text(f"{module_prefix}.mcpclient_connection_failed"),
        mcpclient.name,
        error,
    )


@receiver(mcpclient_tool_called, dispatch_uid="mcpclient_tool_called")
def handle_mcpclient_tool_called(sender, mcpclient: MCPClient, tool_name: str, arguments: dict, **kwargs):
    """Log a tool call.

    The arguments are not logged, because they may contain user data.
    """
    logger.info(
        "%s - %s %s",
        logging.formatted_text(f"{module_prefix}.mcpclient_tool_called"),
        mcpclient.name,
        tool_name,
    )


@receiver(mcpclient_tool_responded, dispatch_uid="mcpclient_tool_responded")
def handle_mcpclient_tool_responded(
    sender, mcpclient: MCPClient, tool_name: str, is_error: bool, characters: int, **kwargs
):
    """Log a tool's result."""
    logger.info(
        "%s - %s %s is_error: %s characters: %s",
        logging.formatted_text(f"{module_prefix}.mcpclient_tool_responded"),
        mcpclient.name,
        tool_name,
        is_error,
        characters,
    )


@receiver(mcpclient_tool_failed, dispatch_uid="mcpclient_tool_failed")
def handle_mcpclient_tool_failed(sender, mcpclient: MCPClient, tool_name: str, error: str, **kwargs):
    """Log a failed tool call."""
    logger.warning(
        "%s - %s %s failed: %s",
        logging.formatted_text(f"{module_prefix}.mcpclient_tool_failed"),
        mcpclient.name,
        tool_name,
        error,
    )


@receiver(mcpclient_resource_read, dispatch_uid="mcpclient_resource_read")
def handle_mcpclient_resource_read(sender, mcpclient: MCPClient, uri: str, characters: int, **kwargs):
    """Log a resource read."""
    logger.info(
        "%s - %s %s characters: %s",
        logging.formatted_text(f"{module_prefix}.mcpclient_resource_read"),
        mcpclient.name,
        uri,
        characters,
    )
