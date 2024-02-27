# -*- coding: utf-8 -*-
# pylint: disable=W0613
"""Django signal receivers for plugin app."""

import json
import logging

from django.forms.models import model_to_dict

from .models import PluginSelectorHistory
from .plugin import Plugin
from .signals import (
    plugin_called,
    plugin_cloned,
    plugin_created,
    plugin_deleted,
    plugin_ready,
    plugin_selected,
    plugin_selected_called,
    plugin_selector_history_created,
    plugin_updated,
)


logger = logging.getLogger(__name__)


def formatted_json(json_obj: json) -> str:
    pretty_json = json.dumps(json_obj, indent=4)
    return f"\033[32m{pretty_json}\033[0m"


def formatted_text(text: str) -> str:
    # bold and dark red
    return f"\033[1;31m{text}\033[0m"


def handle_plugin_created(sender, **kwargs):
    """Handle plugin created signal."""

    plugin = kwargs.get("plugin")
    logger.info("%s signal received: %s", formatted_text("plugin_created"), plugin.name)


plugin_created.connect(handle_plugin_created, dispatch_uid="plugin_created")


def handle_plugin_cloned(sender, **kwargs):
    """Handle plugin cloned signal."""

    plugin_id = kwargs.get("plugin_id")
    plugin = Plugin(plugin_id=plugin_id)
    logger.info("%s signal received: %s", formatted_text("plugin_cloned"), plugin.name)


plugin_cloned.connect(handle_plugin_cloned, dispatch_uid="plugin_cloned")


def handle_plugin_updated(sender, **kwargs):
    """Handle plugin updated signal."""

    plugin = kwargs.get("plugin")
    logger.info("%s signal received: %s", formatted_text("plugin_updated"), plugin.name)


plugin_updated.connect(handle_plugin_updated, dispatch_uid="plugin_updated")


def handle_plugin_deleted(sender, **kwargs):
    """Handle plugin deleted signal."""

    plugin_id = kwargs.get("plugin_id")
    plugin_name = kwargs.get("plugin_name")
    info = f"{plugin_id} {plugin_name}"
    logger.info("%s signal received: %s", formatted_text("plugin_deleted"), info)


plugin_deleted.connect(handle_plugin_deleted, dispatch_uid="plugin_deleted")


def handle_plugin_called(sender, **kwargs):
    """Handle plugin called signal."""

    plugin = kwargs.get("plugin")
    user = kwargs.get("user")
    inquiry_type = kwargs.get("inquiry_type")
    inquiry_return = kwargs.get("inquiry_return")
    logger.info(
        "%s signal received: %s user: %s inquiry_type: %s inquiry_return: %s",
        formatted_text("plugin_called"),
        plugin.name,
        user.username,
        inquiry_type,
        inquiry_return,
    )


plugin_called.connect(handle_plugin_called, dispatch_uid="plugin_called")


def handle_plugin_ready(sender, **kwargs):
    """Handle plugin ready signal."""

    plugin = kwargs.get("plugin")
    logger.info("%s signal received: %s", formatted_text("plugin_ready"), plugin.name)


plugin_ready.connect(handle_plugin_ready, dispatch_uid="plugin_ready")


def handle_plugin_selected_called(sender, **kwargs):
    """Handle plugin selected called signal."""

    plugin = kwargs.get("plugin")
    messages = kwargs.get("messages")
    logger.info(
        "%s signal received: %s messages: %s",
        formatted_text("plugin_selected_called"),
        plugin.name,
        formatted_json(messages),
    )


plugin_selected_called.connect(handle_plugin_selected_called, dispatch_uid="plugin_selected_called")


def handle_plugin_selected(sender, **kwargs):
    """Handle plugin selected signal."""

    plugin = kwargs.get("plugin")
    plugin = Plugin(plugin_id=plugin.id)
    user = kwargs.get("user")
    messages = kwargs.get("messages")
    search_term = kwargs.get("search_term")
    logger.info(
        "%s signal received: %s search_term: %s \nmessages: %s",
        formatted_text("plugin_selected_called"),
        plugin.name,
        search_term,
        formatted_json(messages),
    )

    plugin_selector_history = PluginSelectorHistory(
        plugin_selector=plugin.plugin_selector,
        user=user,
        search_term=search_term,
        messages=messages,
    )
    plugin_selector_history.save()


plugin_selected.connect(handle_plugin_selected, dispatch_uid="plugin_selected")


def handle_plugin_selector_history_created(sender, **kwargs):
    """Handle plugin selector history created signal."""

    plugin_selector_history = kwargs.get("plugin_selector_history")
    logger.info(
        "%s signal received: %s",
        formatted_text("plugin_selector_history_created"),
        formatted_json(model_to_dict(plugin_selector_history)),
    )


plugin_selector_history_created.connect(
    handle_plugin_selector_history_created, dispatch_uid="plugin_selector_history_created"
)
