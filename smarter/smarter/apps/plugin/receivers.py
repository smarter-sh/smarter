# pylint: disable=W0613
"""Django signal receivers for plugin app."""

import json
import logging

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.forms.models import model_to_dict

from smarter.common.const import SmarterWaffleSwitches
from smarter.common.helpers.console_helpers import formatted_json, formatted_text
from smarter.lib.django import waffle

from .models import (
    ApiConnection,
    PluginDataApi,
    PluginDataSql,
    PluginDataStatic,
    PluginMeta,
    PluginPrompt,
    PluginSelector,
    PluginSelectorHistory,
    SqlConnection,
)
from .plugin.static import StaticPlugin
from .signals import (
    plugin_called,
    plugin_cloned,
    plugin_created,
    plugin_deleted,
    plugin_ready,
    plugin_selected,
    plugin_sql_connection_attempted,
    plugin_sql_connection_failed,
    plugin_sql_connection_success,
    plugin_updated,
)
from .tasks import create_plugin_selector_history


logger = logging.getLogger(__name__)


@receiver(plugin_created, dispatch_uid="plugin_created")
def handle_plugin_created(sender, **kwargs):
    """Handle plugin created signal."""

    plugin: StaticPlugin = kwargs.get("plugin")
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
    plugin = StaticPlugin(plugin_id=plugin_id)
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

    if waffle.switch_is_active(SmarterWaffleSwitches.CHAT_LOGGING):
        logger.info(
            "%s - %s inquiry_type: %s inquiry_return: %s",
            formatted_text("plugin_called"),
            plugin.name,
            inquiry_type,
            formatted_json(inquiry_return) if inquiry_return else None,
        )
    else:
        logger.info(
            "%s - %s inquiry_type: %s",
            formatted_text("plugin_called"),
            plugin.name,
            inquiry_type,
        )


@receiver(plugin_ready, dispatch_uid="plugin_ready")
def handle_plugin_ready(sender, **kwargs):
    """Handle plugin ready signal."""

    plugin = kwargs.get("plugin")
    logger.info("%s - %s", formatted_text("plugin_ready"), plugin.name)


@receiver(plugin_selected, dispatch_uid="plugin_selected")
def handle_plugin_selected(sender, **kwargs):
    """Handle plugin selected signal."""

    user = kwargs.get("user")
    user_id: int = user.id if user else None
    plugin = kwargs.get("plugin")
    input_text: str = kwargs.get("input_text")
    messages: list[dict] = kwargs.get("messages")
    search_term: str = kwargs.get("search_term")
    session_key: str = kwargs.get("session_key")

    prompt = input_text if input_text else formatted_json(messages)
    logger.info(
        "signal received for %s - %s search_term: %s prompt(s): %s",
        formatted_text("plugin_selected"),
        plugin.name,
        search_term,
        prompt,
    )

    create_plugin_selector_history.delay(
        plugin_id=plugin.id,
        user_id=user_id,
        input_text=input_text,
        messages=messages,
        search_term=search_term,
        session_key=session_key,
    )


# ------------------------------------------------------------------------------
# Django model receivers.
# ------------------------------------------------------------------------------


@receiver(post_save, sender=PluginMeta)
def handle_plugin_meta_created(sender, instance, created, **kwargs):

    if created:
        logger.info("%s %s", formatted_text("PluginMeta() record created:"), instance.name)


@receiver(post_save, sender=PluginSelector)
def handle_plugin_selector_created(sender, instance, created, **kwargs):
    """Handle plugin selector created signal."""

    if created:
        logger.info("%s", formatted_text("PluginSelector() record created."))


@receiver(post_save, sender=PluginPrompt)
def handle_plugin_prompt_created(sender, instance, created, **kwargs):
    """Handle plugin prompt created signal."""

    if created:
        logger.info("%s", formatted_text("PluginPrompt() record created."))


@receiver(post_save, sender=PluginDataStatic)
def handle_plugin_data_created(sender, instance, created, **kwargs):
    """Handle plugin data created signal."""

    if created:
        logger.info("%s", formatted_text("PluginDataStatic() record created."))


@receiver(post_save, sender=PluginSelectorHistory)
def handle_plugin_selector_history_created(sender, instance, created, **kwargs):
    """Handle plugin selector history created signal."""

    if created:
        logger.info(
            "%s - %s",
            formatted_text("PluginSelectorHistory() created"),
            formatted_json(model_to_dict(instance)),
        )


@receiver(post_save, sender=ApiConnection)
def handle_api_connection_created(sender, instance, created, **kwargs):
    """Handle API connection created signal."""

    if created:
        logger.info(
            "%s - %s",
            formatted_text("ApiConnection() created"),
            formatted_json(model_to_dict(instance)),
        )
    else:
        logger.info(
            "%s - %s",
            formatted_text("ApiConnection() updated"),
            formatted_json(model_to_dict(instance)),
        )


@receiver(post_save, sender=SqlConnection)
def handle_sql_connection_created(sender, instance, created, **kwargs):
    """Handle SQL connection created signal."""

    if created:
        logger.info(
            "%s - %s",
            formatted_text("SqlConnection() created"),
            formatted_json(model_to_dict(instance)),
        )
    else:
        logger.info(
            "%s - %s",
            formatted_text("SqlConnection() updated"),
            formatted_json(model_to_dict(instance)),
        )


@receiver(post_save, sender=PluginDataApi)
def handle_plugin_data_api_created(sender, instance, created, **kwargs):
    """Handle plugin data API created signal."""

    if created:
        logger.info(
            "%s - %s",
            formatted_text("PluginDataApi() created"),
            formatted_json(model_to_dict(instance)),
        )
    else:
        logger.info(
            "%s - %s",
            formatted_text("PluginDataApi() updated"),
            formatted_json(model_to_dict(instance)),
        )


@receiver(post_save, sender=PluginDataSql)
def handle_plugin_data_sql_created(sender, instance, created, **kwargs):
    """Handle plugin data SQL created signal."""

    if created:
        logger.info(
            "%s - %s",
            formatted_text("PluginDataSql() created"),
            formatted_json(model_to_dict(instance)),
        )
    else:
        logger.info(
            "%s - %s",
            formatted_text("PluginDataSql() updated"),
            formatted_json(model_to_dict(instance)),
        )


# ------------------------------------------------------------------------------
# plugin sql connection signals.
# ------------------------------------------------------------------------------
def masked_dict(dic: dict) -> dict:
    """Mask sensitive data in a dictionary."""
    masked = dic.copy()
    if "PASSWORD" in masked:
        masked["PASSWORD"] = "********"
    return masked


@receiver(plugin_sql_connection_attempted, dispatch_uid="plugin_sql_connection_attempted")
def handle_plugin_sql_connection_attempted(sender, connection: SqlConnection, **kwargs):
    """Handle plugin SQL connection attempted signal."""

    logger.info(
        "%s - %s",
        formatted_text("plugin_sql_connection_attempted"),
        formatted_json(masked_dict(connection.django_db_connection)),
    )


@receiver(plugin_sql_connection_success, dispatch_uid="plugin_sql_connection_success")
def handle_plugin_sql_connection_success(sender, connection: SqlConnection, **kwargs):
    """Handle plugin SQL connection success signal."""

    logger.info(
        "%s - %s",
        formatted_text("plugin_sql_connection_success"),
        formatted_json(masked_dict(connection.django_db_connection)),
    )


@receiver(plugin_sql_connection_failed, dispatch_uid="plugin_sql_connection_failed")
def handle_plugin_sql_connection_failed(sender, connection: SqlConnection, **kwargs):
    """Handle plugin SQL connection failed signal."""

    logger.info(
        "%s - %s",
        formatted_text("plugin_sql_connection_failed"),
        formatted_json(masked_dict(connection.django_db_connection)),
    )
