# pylint: disable=W0613
"""Django signal receivers of WebsearchPlugin searches and page reads."""

from django.dispatch import receiver

from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

from ..plugin.static import PluginBase
from ..signals.websearch import (
    websearch_failed,
    websearch_fetched,
    websearch_searched,
)

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.RECEIVER_LOGGING])

logger_prefix = formatted_text(__name__)


@receiver(websearch_searched, dispatch_uid="websearch_searched")
def handle_websearch_searched(sender, plugin: PluginBase, query: str, provider: str, result_count: int, **kwargs):
    """Handle websearch searched signal."""
    logger.info(
        "%s.websearch_searched() %s query: %s provider: %s results: %s cached: %s",
        logger_prefix,
        plugin.name,
        query,
        provider,
        result_count,
        kwargs.get("cached"),
    )


@receiver(websearch_fetched, dispatch_uid="websearch_fetched")
def handle_websearch_fetched(sender, plugin: PluginBase, url: str, **kwargs):
    """Handle websearch fetched signal."""
    logger.info(
        "%s.websearch_fetched() %s url: %s final_url: %s characters: %s truncated: %s cached: %s",
        logger_prefix,
        plugin.name,
        url,
        kwargs.get("final_url"),
        kwargs.get("characters"),
        kwargs.get("truncated"),
        kwargs.get("cached"),
    )


@receiver(websearch_failed, dispatch_uid="websearch_failed")
def handle_websearch_failed(sender, plugin: PluginBase, operation: str, target: str, error: str, **kwargs):
    """Handle websearch failed signal."""
    logger.warning(
        "%s.websearch_failed() %s %s %s failed: %s",
        logger_prefix,
        plugin.name,
        operation,
        target,
        error,
    )
