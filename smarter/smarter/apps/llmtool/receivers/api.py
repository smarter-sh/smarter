# pylint: disable=W0613
"""Django signal receivers of ApiPlugin tool calls."""

from django.dispatch import receiver

from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

from ..plugin.static import PluginBase
from ..signals.api import (
    api_plugin_authenticated,
    api_plugin_authentication_failed,
    api_plugin_failed,
    api_plugin_request_completed,
    api_plugin_request_started,
    api_plugin_responded,
)
from .utils import response_characters

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.RECEIVER_LOGGING])

prefix = f"{__name__}."


@receiver(api_plugin_request_started, dispatch_uid="api_plugin_request_started")
def handle_api_plugin_request_started(sender, plugin: PluginBase, function_args=None, **kwargs):
    """Handle ApiPlugin request started signal."""
    logger.info(
        "%s - %s function_args: %s", formatted_text(prefix + "api_plugin_request_started"), plugin.name, function_args
    )


@receiver(api_plugin_authenticated, dispatch_uid="api_plugin_authenticated")
def handle_api_plugin_authenticated(sender, plugin: PluginBase, **kwargs):
    """Handle ApiPlugin authenticated signal."""
    logger.info(
        "%s - %s connection: %s auth_method: %s status_code: %s",
        formatted_text(prefix + "api_plugin_authenticated"),
        plugin.name,
        kwargs.get("connection"),
        kwargs.get("auth_method"),
        kwargs.get("status_code"),
    )


@receiver(api_plugin_authentication_failed, dispatch_uid="api_plugin_authentication_failed")
def handle_api_plugin_authentication_failed(sender, plugin: PluginBase, error: str, **kwargs):
    """Handle ApiPlugin authentication failed signal."""
    logger.warning(
        "%s - %s connection: %s auth_method: %s status_code: %s error: %s",
        formatted_text(prefix + "api_plugin_authentication_failed"),
        plugin.name,
        kwargs.get("connection"),
        kwargs.get("auth_method"),
        kwargs.get("status_code"),
        error,
    )


@receiver(api_plugin_responded, dispatch_uid="api_plugin_responded")
def handle_api_plugin_responded(sender, plugin: PluginBase, response=None, cached: bool = False, **kwargs):
    """Handle ApiPlugin responded signal."""
    logger.info(
        "%s - %s %s %s characters: %s cached: %s",
        formatted_text(prefix + "api_plugin_responded"),
        plugin.name,
        kwargs.get("method"),
        kwargs.get("endpoint"),
        response_characters(response),
        cached,
    )


@receiver(api_plugin_failed, dispatch_uid="api_plugin_failed")
def handle_api_plugin_failed(sender, plugin: PluginBase, error: str, **kwargs):
    """Handle ApiPlugin failed signal."""
    logger.warning("%s - %s failed: %s", formatted_text(prefix + "api_plugin_failed"), plugin.name, error)


@receiver(api_plugin_request_completed, dispatch_uid="api_plugin_request_completed")
def handle_api_plugin_request_completed(sender, plugin: PluginBase, success: bool, duration: float, **kwargs):
    """Handle ApiPlugin request completed signal."""
    logger.info(
        "%s - %s success: %s duration: %.3fs",
        formatted_text(prefix + "api_plugin_request_completed"),
        plugin.name,
        success,
        duration,
    )
