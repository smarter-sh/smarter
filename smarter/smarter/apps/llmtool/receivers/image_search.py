# pylint: disable=W0613
"""Django signal receivers of ImageSearchPlugin tool calls."""

from django.dispatch import receiver

from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

from ..plugin.static import PluginBase
from ..signals.image_search import (
    image_search_plugin_authenticated,
    image_search_plugin_authentication_failed,
    image_search_plugin_failed,
    image_search_plugin_request_completed,
    image_search_plugin_request_started,
    image_search_plugin_responded,
)
from .utils import response_characters

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.RECEIVER_LOGGING])

logger_prefix = formatted_text(__name__)


@receiver(image_search_plugin_request_started, dispatch_uid="image_search_plugin_request_started")
def handle_image_search_plugin_request_started(sender, plugin: PluginBase, function_args=None, **kwargs):
    """Handle ImageSearchPlugin request started signal."""
    logger.info(
        "%s.image_search_plugin_request_started() %s function_args: %s",
        logger_prefix,
        plugin.name,
        function_args,
    )


@receiver(image_search_plugin_authenticated, dispatch_uid="image_search_plugin_authenticated")
def handle_image_search_plugin_authenticated(sender, plugin: PluginBase, **kwargs):
    """Handle ImageSearchPlugin authenticated signal."""
    logger.info(
        "%s.image_search_plugin_authenticated() %s provider: %s",
        logger_prefix,
        plugin.name,
        kwargs.get("provider"),
    )


@receiver(image_search_plugin_authentication_failed, dispatch_uid="image_search_plugin_authentication_failed")
def handle_image_search_plugin_authentication_failed(sender, plugin: PluginBase, error: str, **kwargs):
    """Handle ImageSearchPlugin authentication failed signal."""
    logger.warning(
        "%s.image_search_plugin_authentication_failed() %s provider: %s error: %s",
        logger_prefix,
        plugin.name,
        kwargs.get("provider"),
        error,
    )


@receiver(image_search_plugin_responded, dispatch_uid="image_search_plugin_responded")
def handle_image_search_plugin_responded(sender, plugin: PluginBase, response=None, cached: bool = False, **kwargs):
    """Handle ImageSearchPlugin responded signal."""
    logger.info(
        "%s.image_search_plugin_responded() %s query: %s characters: %s cached: %s",
        logger_prefix,
        plugin.name,
        kwargs.get("query"),
        response_characters(response),
        cached,
    )


@receiver(image_search_plugin_failed, dispatch_uid="image_search_plugin_failed")
def handle_image_search_plugin_failed(sender, plugin: PluginBase, error: str, **kwargs):
    """Handle ImageSearchPlugin failed signal."""
    logger.warning("%s.image_search_plugin_failed() %s failed: %s", logger_prefix, plugin.name, error)


@receiver(image_search_plugin_request_completed, dispatch_uid="image_search_plugin_request_completed")
def handle_image_search_plugin_request_completed(sender, plugin: PluginBase, success: bool, duration: float, **kwargs):
    """Handle ImageSearchPlugin request completed signal."""
    logger.info(
        "%s.image_search_plugin_request_completed() %s success: %s duration: %.3fs",
        logger_prefix,
        plugin.name,
        success,
        duration,
    )
