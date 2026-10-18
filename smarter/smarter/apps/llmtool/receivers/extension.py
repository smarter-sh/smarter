# pylint: disable=W0613
"""Django signal receivers of Smarter Extensions: installation, and calls to their tools."""

from django.dispatch import receiver

from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

from ..signals.extension import (
    extension_disabled,
    extension_enabled,
    extension_installed,
    extension_tool_called,
    extension_tool_completed,
    extension_tool_failed,
    extension_tool_responded,
    extension_uninstalled,
    extension_upgraded,
)

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.RECEIVER_LOGGING])

prefix = f"{__name__}."


@receiver(extension_installed, dispatch_uid="extension_installed")
def handle_extension_installed(sender, extension, version, **kwargs):
    """Handle extension installed signal."""
    logger.info("%s - %s version: %s", formatted_text(prefix + "extension_installed"), extension.slug, version.version)


@receiver(extension_upgraded, dispatch_uid="extension_upgraded")
def handle_extension_upgraded(sender, extension, version, previous_version: str, **kwargs):
    """Handle extension upgraded signal."""
    logger.info(
        "%s - %s version: %s previous_version: %s",
        formatted_text(prefix + "extension_upgraded"),
        extension.slug,
        version.version,
        previous_version,
    )


@receiver(extension_uninstalled, dispatch_uid="extension_uninstalled")
def handle_extension_uninstalled(sender, slug: str, **kwargs):
    """Handle extension uninstalled signal."""
    logger.info("%s - %s", formatted_text(prefix + "extension_uninstalled"), slug)


@receiver(extension_enabled, dispatch_uid="extension_enabled")
def handle_extension_enabled(sender, extension, **kwargs):
    """Handle extension enabled signal."""
    logger.info("%s - %s", formatted_text(prefix + "extension_enabled"), extension.slug)


@receiver(extension_disabled, dispatch_uid="extension_disabled")
def handle_extension_disabled(sender, extension, reason: str = "", **kwargs):
    """Handle extension disabled signal."""
    logger.warning("%s - %s reason: %s", formatted_text(prefix + "extension_disabled"), extension.slug, reason)


@receiver(extension_tool_called, dispatch_uid="extension_tool_called")
def handle_extension_tool_called(sender, slug: str, version: str, tool_name: str, arguments=None, **kwargs):
    """Handle extension tool called signal."""
    logger.info(
        "%s - %s %s %s arguments: %s",
        formatted_text(prefix + "extension_tool_called"),
        slug,
        version,
        tool_name,
        arguments,
    )


@receiver(extension_tool_responded, dispatch_uid="extension_tool_responded")
def handle_extension_tool_responded(sender, slug: str, version: str, tool_name: str, characters: int = 0, **kwargs):
    """Handle extension tool responded signal."""
    logger.info(
        "%s - %s %s %s characters: %s",
        formatted_text(prefix + "extension_tool_responded"),
        slug,
        version,
        tool_name,
        characters,
    )


@receiver(extension_tool_failed, dispatch_uid="extension_tool_failed")
def handle_extension_tool_failed(sender, slug: str, version: str, tool_name: str, error: str, **kwargs):
    """Handle extension tool failed signal."""
    logger.warning(
        "%s - %s %s %s failed: %s",
        formatted_text(prefix + "extension_tool_failed"),
        slug,
        version,
        tool_name,
        error,
    )


@receiver(extension_tool_completed, dispatch_uid="extension_tool_completed")
def handle_extension_tool_completed(
    sender, slug: str, version: str, tool_name: str, success: bool, duration: float, **kwargs
):
    """Handle extension tool completed signal."""
    logger.info(
        "%s - %s %s %s success: %s duration: %.3fs",
        formatted_text(prefix + "extension_tool_completed"),
        slug,
        version,
        tool_name,
        success,
        duration,
    )
