# pylint: disable=W0613
"""Django signal receivers for plugin app."""

import json
import logging

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.forms.models import model_to_dict

from smarter.common.helpers.console_helpers import formatted_json, formatted_text

from .models import (
    PluginDataStatic,
    PluginMeta,
    PluginPrompt,
    PluginSelector,
    PluginSelectorHistory,
)
from .plugin.static import PluginStatic
from .signals import (
    plugin_called,
    plugin_cloned,
    plugin_created,
    plugin_deleted,
    plugin_ready,
    plugin_selected,
    plugin_updated,
)


logger = logging.getLogger(__name__)


@receiver(plugin_created, dispatch_uid="plugin_created")
def handle_plugin_created(sender, **kwargs):
    """Handle plugin created signal."""

    plugin: PluginStatic = kwargs.get("plugin")
    logger.info(
        "%s - account: %s - user: %s - name: %s",
        formatted_text("plugin_created"),
        plugin.user_profile.account,
        plugin.user_profile.user,
        plugin.name,
    )


@receiver(plugin_cloned, dispatch_uid="plugin_cloned")
def handle_plugin_cloned(sender, **kwargs):
    """Handle plugin cloned signal."""

    plugin_id = kwargs.get("plugin_id")
    plugin = PluginStatic(plugin_id=plugin_id)
    logger.info("%s - %s", formatted_text("plugin_cloned"), plugin.name)


@receiver(plugin_updated, dispatch_uid="plugin_updated")
def handle_plugin_updated(sender, **kwargs):
    """Handle plugin updated signal."""

    plugin = kwargs.get("plugin")
    logger.info("%s - %s", formatted_text("plugin_updated"), plugin.name)


@receiver(plugin_deleted, dispatch_uid="plugin_deleted")
def handle_plugin_deleted(sender, **kwargs):
    """Handle plugin deleted signal."""

    plugin_id = kwargs.get("plugin_id")
    plugin_name = kwargs.get("plugin_name")
    info = f"{plugin_id} {plugin_name}"
    logger.info("%s - %s", formatted_text("plugin_deleted"), info)


@receiver(plugin_called, dispatch_uid="plugin_called")
def handle_plugin_called(sender, **kwargs):
    """Handle plugin called signal."""

    plugin = kwargs.get("plugin")
    inquiry_type = kwargs.get("inquiry_type")
    inquiry_return = kwargs.get("inquiry_return")

    try:
        inquiry_return = json.loads(inquiry_return)
    except (TypeError, json.JSONDecodeError):
        pass

    logger.info(
        "%s - %s inquiry_type: %s inquiry_return: %s",
        formatted_text("plugin_called"),
        plugin.name,
        inquiry_type,
        formatted_json(inquiry_return) if inquiry_return else None,
    )


@receiver(plugin_ready, dispatch_uid="plugin_ready")
def handle_plugin_ready(sender, **kwargs):
    """Handle plugin ready signal."""

    plugin = kwargs.get("plugin")
    logger.info("%s - %s", formatted_text("plugin_ready"), plugin.name)


@receiver(plugin_selected, dispatch_uid="plugin_selected")
def handle_plugin_selected(sender, **kwargs):
    """Handle plugin selected signal."""

    plugin = kwargs.get("plugin")
    plugin = PluginStatic(plugin_id=plugin.id)
    input_text: str = kwargs.get("input_text")
    messages: list[dict] = kwargs.get("messages")
    search_term: str = kwargs.get("search_term")
    session_key: str = kwargs.get("session_key")

    prompt = input_text if input_text else formatted_json(messages)
    logger.info(
        "%s - %s search_term: %s \nprompt(s): %s",
        formatted_text("plugin_selected"),
        plugin.name,
        search_term,
        prompt,
    )

    PluginSelectorHistory.objects.create(
        plugin_selector=plugin.plugin_selector,
        search_term=search_term,
        messages={"input_text": input_text} if input_text else messages,
        session_key=session_key,
    )


# ------------------------------------------------------------------------------
# Django model receivers.
# ------------------------------------------------------------------------------


@receiver(post_save, sender=PluginMeta)
def handle_plugin_meta_created(sender, instance, **kwargs):

    logger.info("%s %s", formatted_text("PluginMeta() record created:"), instance.name)


@receiver(post_save, sender=PluginSelector)
def handle_plugin_selector_created(sender, **kwargs):
    """Handle plugin selector created signal."""

    logger.info("%s", formatted_text("PluginSelector() record created."))


@receiver(post_save, sender=PluginPrompt)
def handle_plugin_prompt_created(sender, **kwargs):
    """Handle plugin prompt created signal."""

    logger.info("%s", formatted_text("PluginPrompt() record created."))


@receiver(post_save, sender=PluginDataStatic)
def handle_plugin_data_created(sender, **kwargs):
    """Handle plugin data created signal."""

    logger.info("%s", formatted_text("PluginDataStatic() record created."))


@receiver(post_save, sender=PluginSelectorHistory)
def handle_plugin_selector_history_created(sender, **kwargs):
    """Handle plugin selector history created signal."""

    plugin_selector_history = kwargs.get("instance")
    logger.info(
        "%s - %s",
        formatted_text("PluginSelectorHistory() created"),
        formatted_json(model_to_dict(plugin_selector_history)),
    )
