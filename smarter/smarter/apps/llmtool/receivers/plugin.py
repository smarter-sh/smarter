# pylint: disable=W0613
"""Django signal receivers of the lifecycle of every plugin: create, clone, update, delete, select and call."""

from typing import Optional, Union

from django.dispatch import receiver

from smarter.common.helpers.console_helpers import formatted_json, formatted_text
from smarter.lib import json, logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.manifest.broker import AbstractBroker
from smarter.lib.typing import SmarterDictType

from ..models import (
    PluginMeta,
)
from ..plugin.static import PluginBase
from ..signals.plugin import (
    broker_ready,
    plugin_called,
    plugin_cloned,
    plugin_created,
    plugin_deleted,
    plugin_deleting,
    plugin_ready,
    plugin_responded,
    plugin_selected,
    plugin_updated,
    search_term_matched,
)
from ..tasks import create_plugin_selector_history

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.RECEIVER_LOGGING])

prefix = f"{__name__}."


@receiver(plugin_created, dispatch_uid="plugin_created")
def handle_plugin_created(sender, plugin: PluginBase, **kwargs):
    """Handle plugin created signal."""

    logger.info(
        "%s - %s - name: %s data: %s",
        formatted_text(prefix + "plugin_created"),
        plugin.user_profile,
        plugin.name,
        formatted_json(plugin.data) if plugin.data else None,
    )


@receiver(plugin_cloned, dispatch_uid="plugin_cloned")
def handle_plugin_cloned(sender, plugin: PluginBase, **kwargs):
    """Handle plugin cloned signal."""

    logger.info("%s - %s data: %s", formatted_text(prefix + "plugin_cloned"), plugin.name, plugin.data)


@receiver(plugin_updated, dispatch_uid="plugin_updated")
def handle_plugin_updated(sender, plugin: PluginBase, **kwargs):
    """Handle plugin updated signal."""

    logger.info(
        "%s - %s - name: %s data: %s",
        formatted_text(prefix + "plugin_updated"),
        plugin.user_profile,
        plugin.name,
        formatted_json(plugin.data) if plugin.data else None,
    )


@receiver(plugin_deleting, dispatch_uid="plugin_deleting")
def handle_plugin_deleting(sender, plugin, plugin_meta: PluginMeta, **kwargs):
    """Handle plugin deleting signal."""
    logger.info(
        "%s %s is being deleted.",
        formatted_text(prefix + "plugin_deleting"),
        plugin_meta.name,
    )


@receiver(plugin_deleted, dispatch_uid="plugin_deleted")
def handle_plugin_deleted(sender, plugin: PluginBase, plugin_name: str, **kwargs):
    """Handle plugin deleted signal."""

    logger.info("%s - %s", formatted_text(prefix + "plugin_deleted"), plugin_name)


@receiver(plugin_called, dispatch_uid="plugin_called")
def handle_plugin_called(sender, plugin: PluginBase, **kwargs):
    """Handle plugin called signal."""

    inquiry_type: Optional[str] = kwargs.get("inquiry_type")

    logger.info("%s - %s inquiry_type: %s", formatted_text(prefix + "plugin_called"), plugin.name, inquiry_type)


@receiver(plugin_responded, dispatch_uid="plugin_responded")
def handle_plugin_responded(sender, plugin: PluginBase, **kwargs):
    """Handle plugin responded signal."""

    inquiry_type: Optional[str] = kwargs.get("inquiry_type")
    # plugins send their response as ``response``.
    inquiry_return: Optional[Union[SmarterDictType, list, str]] = kwargs.get("response", kwargs.get("inquiry_return"))

    try:
        inquiry_return = json.loads(inquiry_return) if isinstance(inquiry_return, str) else inquiry_return
    except (TypeError, json.JSONDecodeError):
        pass

    logger.info(
        "%s - %s inquiry_type: %s inquiry_return: %s",
        formatted_text(prefix + "plugin_responded"),
        plugin.name,
        inquiry_type,
        formatted_json(inquiry_return) if isinstance(inquiry_return, (dict, list)) else inquiry_return,
    )


@receiver(plugin_ready, dispatch_uid="plugin_ready")
def handle_plugin_ready(sender, plugin: PluginBase, **kwargs):
    """Handle plugin ready signal."""

    logger.info("%s - %s", formatted_text(prefix + "plugin_ready"), plugin.name)


@receiver(plugin_selected, dispatch_uid="plugin_selected")
def handle_plugin_selected(sender, *args, **kwargs):
    """Handle plugin selected signal."""
    # plugin: PluginBase, user, messages: list[dict], search_term: str, messages: list[dict] = None
    input_text: Optional[str] = kwargs.get("input_text")
    plugin: Optional[PluginBase] = kwargs.get("plugin")
    user = kwargs.get("user")
    messages: list[SmarterDictType] = kwargs.get("messages", [])
    search_term: str = kwargs.get("search_term", "")
    user_id: int = user.id if user else None  # type: ignore

    prompt = input_text if input_text else formatted_json(messages)
    logger.info(
        "signal received for %s - %s search_term: %s prompt(s): %s",
        formatted_text(prefix + "plugin_selected"),
        plugin.name if plugin else "Unknown Plugin",
        search_term,
        prompt,
    )
    if plugin is None or plugin.id is None:
        logger.warning(
            "%s received without a plugin id. Plugin selector history is not recorded.",
            formatted_text(prefix + "plugin_selected"),
        )
        return

    create_plugin_selector_history.delay(
        plugin_id=plugin.id,
        user_id=user_id,
        input_text=input_text,
        messages=messages,
        search_term=search_term,
    )


@receiver(search_term_matched, dispatch_uid="search_term_matched")
def handle_search_term_matched(sender, prompt: str, search_term: str, method: str, matched_text=None, **kwargs):
    """Handle search term matched signal."""
    logger.info(
        "signal received for %s - search_term: %s method: %s matched_text: %s prompt: %s",
        formatted_text(prefix + "search_term_matched"),
        search_term,
        method,
        matched_text,
        prompt,
    )


@receiver(broker_ready, dispatch_uid="broker_ready")
def handle_broker_ready(sender, broker: AbstractBroker, **kwargs):
    """
    Log that a broker is ready.

    Brokers of every kind send this signal, so the message names the broker's own class, e.g.
    ``smarter.apps.guardrail.manifest.brokers.guardrail.SAMGuardrailBroker.broker_ready()``,
    rather than this module.
    """
    logger.info(
        "%s %s %s for %s is ready.",
        formatted_text(f"{sender.__module__}.{sender.__name__}.broker_ready()"),
        broker.kind,
        str(broker),
        broker.name,
    )
