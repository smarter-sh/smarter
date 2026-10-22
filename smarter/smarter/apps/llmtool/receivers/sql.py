# pylint: disable=W0613
"""Django signal receivers of SqlPlugin tool calls."""

from django.dispatch import receiver

from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

from ..plugin.static import PluginBase
from ..signals.sql import (
    sql_plugin_authenticated,
    sql_plugin_authentication_failed,
    sql_plugin_failed,
    sql_plugin_request_completed,
    sql_plugin_request_started,
    sql_plugin_responded,
)
from .utils import response_characters

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.RECEIVER_LOGGING])

logger_prefix = formatted_text(__name__)


@receiver(sql_plugin_request_started, dispatch_uid="sql_plugin_request_started")
def handle_sql_plugin_request_started(sender, plugin: PluginBase, function_args=None, **kwargs):
    """Handle SqlPlugin request started signal."""
    logger.info("%s.sql_plugin_request_started() %s function_args: %s", logger_prefix, plugin.name, function_args)


@receiver(sql_plugin_authenticated, dispatch_uid="sql_plugin_authenticated")
def handle_sql_plugin_authenticated(sender, plugin: PluginBase, **kwargs):
    """Handle SqlPlugin authenticated signal."""
    logger.info(
        "%s.sql_plugin_authenticated() %s connection: %s",
        logger_prefix,
        plugin.name,
        kwargs.get("connection"),
    )


@receiver(sql_plugin_authentication_failed, dispatch_uid="sql_plugin_authentication_failed")
def handle_sql_plugin_authentication_failed(sender, plugin: PluginBase, error: str, **kwargs):
    """Handle SqlPlugin authentication failed signal."""
    logger.warning(
        "%s.sql_plugin_authentication_failed() %s connection: %s error: %s",
        logger_prefix,
        plugin.name,
        kwargs.get("connection"),
        error,
    )


@receiver(sql_plugin_responded, dispatch_uid="sql_plugin_responded")
def handle_sql_plugin_responded(sender, plugin: PluginBase, response=None, cached: bool = False, **kwargs):
    """Handle SqlPlugin responded signal."""
    logger.info(
        "%s.sql_plugin_responded() %s sql: %s characters: %s cached: %s",
        logger_prefix,
        plugin.name,
        kwargs.get("sql"),
        response_characters(response),
        cached,
    )


@receiver(sql_plugin_failed, dispatch_uid="sql_plugin_failed")
def handle_sql_plugin_failed(sender, plugin: PluginBase, error: str, **kwargs):
    """Handle SqlPlugin failed signal."""
    logger.warning("%s.sql_plugin_failed() %s failed: %s", logger_prefix, plugin.name, error)


@receiver(sql_plugin_request_completed, dispatch_uid="sql_plugin_request_completed")
def handle_sql_plugin_request_completed(sender, plugin: PluginBase, success: bool, duration: float, **kwargs):
    """Handle SqlPlugin request completed signal."""
    logger.info(
        "%s.sql_plugin_request_completed() %s success: %s duration: %.3fs",
        logger_prefix,
        plugin.name,
        success,
        duration,
    )
