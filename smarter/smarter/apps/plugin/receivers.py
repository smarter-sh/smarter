# pylint: disable=W0613
"""Django signal receivers for plugin app."""

import logging
from typing import Optional, Union

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.forms.models import model_to_dict

from smarter.common.helpers.console_helpers import formatted_json, formatted_text
from smarter.lib import json
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper
from smarter.lib.manifest.broker import AbstractBroker

from .models import (
    PluginDataApi,
    PluginDataSql,
    PluginDataStatic,
    PluginMeta,
    PluginPrompt,
    PluginSelector,
    PluginSelectorHistory,
)
from .plugin.static import PluginBase
from .signals import (
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
)
from .tasks import create_plugin_selector_history


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.RECEIVER_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)

prefix = "smarter.apps.plugin.receivers."


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


@receiver(plugin_deleting, dispatch_uid=prefix + ".plugin_deleting")
def handle_plugin_deleting(sender, plugin, plugin_meta: PluginMeta, **kwargs):
    """Handle plugin deleting signal."""
    logger.info(
        "%s %s is being deleted.",
        formatted_text("smarter.apps.plugin.receivers.plugin_deleting"),
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
    inquiry_return: Optional[Union[dict, list, str]] = kwargs.get("inquiry_return")

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
    messages: list[dict] = kwargs.get("messages", [])
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

    create_plugin_selector_history.delay(
        plugin_id=plugin.id,  # type: ignore
        user_id=user_id,
        input_text=input_text,
        messages=messages,
        search_term=search_term,
    )


# ------------------------------------------------------------------------------
# Django model receivers.
# ------------------------------------------------------------------------------


@receiver(post_save, sender=PluginMeta)
def handle_plugin_meta_saved(sender, instance, created, **kwargs):
    """Handle plugin meta saved signal."""

    if created:
        logger.info("%s %s", formatted_text(prefix + "post_save() PluginMeta() record created:"), instance.name)
    else:
        logger.info(
            "%s %s",
            formatted_text(prefix + "post_save() PluginMeta() record updated:"),
            instance.name,
        )


@receiver(post_save, sender=PluginSelector)
def handle_plugin_selector_saved(sender, instance, created, **kwargs):
    """Handle plugin selector saved signal."""

    if created:
        logger.info("%s", formatted_text(prefix + "post_save() PluginSelector() record created."))
    else:
        logger.info(
            "%s - %s",
            formatted_text(prefix + "post_save() PluginSelector() record updated:"),
            formatted_json(model_to_dict(instance)),
        )


@receiver(post_save, sender=PluginPrompt)
def handle_plugin_prompt_saved(sender, instance, created, **kwargs):
    """Handle plugin prompt saved signal."""

    if created:
        logger.info("%s", formatted_text(prefix + "post_save() PluginPrompt() record created."))
    else:
        logger.info(
            "%s - %s",
            formatted_text(prefix + "post_save() PluginPrompt() record updated:"),
            formatted_json(model_to_dict(instance)),
        )


@receiver(post_save, sender=PluginDataStatic)
def handle_plugin_data_saved(sender, instance, created, **kwargs):
    """Handle plugin data saved signal."""

    if created:
        logger.info("%s", formatted_text(prefix + "post_save() PluginDataStatic() record created."))
    else:
        logger.info(
            "%s - %s",
            formatted_text(prefix + "post_save() PluginDataStatic() record updated:"),
            formatted_json(model_to_dict(instance)),
        )


@receiver(post_save, sender=PluginSelectorHistory)
def handle_plugin_selector_history_saved(sender, instance, created, **kwargs):
    """Handle plugin selector history saved signal."""

    if created:
        logger.info(
            "%s - %s",
            formatted_text(prefix + "post_save() PluginSelectorHistory() created"),
            formatted_json(model_to_dict(instance)),
        )
    else:
        logger.info(
            "%s - %s",
            formatted_text(prefix + "post_save() PluginSelectorHistory() updated"),
            formatted_json(model_to_dict(instance)),
        )


@receiver(post_save, sender=PluginDataApi)
def handle_plugin_data_api_saved(sender, instance, created, **kwargs):
    """Handle plugin data API saved signal."""

    if created:
        logger.info(
            "%s - %s",
            formatted_text(prefix + "post_save() PluginDataApi() created"),
            formatted_json(model_to_dict(instance)),
        )
    else:
        logger.info(
            "%s - %s",
            formatted_text(prefix + "post_save() PluginDataApi() updated"),
            formatted_json(model_to_dict(instance)),
        )


@receiver(post_save, sender=PluginDataSql)
def handle_plugin_data_sql_saved(sender, instance, created, **kwargs):
    """Handle plugin data SQL saved signal."""

    if created:
        logger.info(
            "%s - %s",
            formatted_text(prefix + "post_save() PluginDataSql() created"),
            formatted_json(model_to_dict(instance)),
        )
    else:
        logger.info(
            "%s - %s",
            formatted_text(prefix + "post_save() PluginDataSql() updated"),
            formatted_json(model_to_dict(instance)),
        )


# ------------------------------------------------------------------------------
# pre_delete signals for
#    PluginDataApi,
#    PluginDataSql,
#    PluginDataStatic,
#    PluginMeta,
#    PluginPrompt,
#    PluginSelector,
#    PluginSelectorHistory,
# ------------------------------------------------------------------------------
@receiver(pre_delete, sender=PluginDataApi)
def handle_plugin_data_api_pre_delete(sender, instance, **kwargs):
    """Handle pre-delete signal for PluginDataApi."""
    logger.info(
        "%s - %s deleting.",
        formatted_text(prefix + "PluginDataApi().pre_delete()"),
        instance,
    )


@receiver(pre_delete, sender=PluginDataSql)
def handle_plugin_data_sql_pre_delete(sender, instance, **kwargs):
    """Handle pre-delete signal for PluginDataSql."""
    logger.info(
        "%s - %s deleting.",
        formatted_text(prefix + "PluginDataSql().pre_delete()"),
        instance,
    )


@receiver(pre_delete, sender=PluginDataStatic)
def handle_plugin_data_static_pre_delete(sender, instance, **kwargs):
    """Handle pre-delete signal for PluginDataStatic."""
    logger.info(
        "%s - %s deleting.",
        formatted_text(prefix + "PluginDataStatic().pre_delete()"),
        instance,
    )


@receiver(pre_delete, sender=PluginMeta)
def handle_plugin_meta_pre_delete(sender, instance, **kwargs):
    """Handle pre-delete signal for PluginMeta."""
    logger.info(
        "%s - %s deleting.",
        formatted_text(prefix + "PluginMeta().pre_delete()"),
        instance,
    )


@receiver(pre_delete, sender=PluginPrompt)
def handle_plugin_prompt_pre_delete(sender, instance, **kwargs):
    """Handle pre-delete signal for PluginPrompt."""
    logger.info(
        "%s - %s deleting.",
        formatted_text(prefix + "PluginPrompt().pre_delete()"),
        instance,
    )


@receiver(pre_delete, sender=PluginSelector)
def handle_plugin_selector_pre_delete(sender, instance, **kwargs):
    """Handle pre-delete signal for PluginSelector."""
    logger.info(
        "%s - %s deleting.",
        formatted_text(prefix + "PluginSelector().pre_delete()"),
        instance,
    )


@receiver(pre_delete, sender=PluginSelectorHistory)
def handle_plugin_selector_history_pre_delete(sender, instance, **kwargs):
    """Handle pre-delete signal for PluginSelectorHistory."""
    logger.info(
        "%s - %s deleting.",
        formatted_text(prefix + "PluginSelectorHistory().pre_delete()"),
        instance,
    )


@receiver(broker_ready, dispatch_uid="broker_ready")
def handle_broker_ready(sender, broker: AbstractBroker, **kwargs):
    """Handle broker ready signal."""

    logger.info(
        "%s %s %s for %s is ready.",
        formatted_text(f"{prefix}broker_ready()"),
        broker.kind,
        str(broker),
        broker.name,
    )
