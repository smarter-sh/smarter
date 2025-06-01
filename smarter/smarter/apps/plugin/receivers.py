# pylint: disable=W0613
"""Django signal receivers for plugin app."""

import json
import logging

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.forms.models import model_to_dict
from requests import Response

from smarter.common.helpers.console_helpers import formatted_json, formatted_text
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches

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
from .plugin.static import PluginBase
from .signals import (  # plugin signals; sql_connection signals; api_connection signals
    plugin_api_connection_attempted,
    plugin_api_connection_failed,
    plugin_api_connection_query_attempted,
    plugin_api_connection_query_failed,
    plugin_api_connection_query_success,
    plugin_api_connection_success,
    plugin_called,
    plugin_cloned,
    plugin_created,
    plugin_deleted,
    plugin_deleting,
    plugin_ready,
    plugin_selected,
    plugin_sql_connection_attempted,
    plugin_sql_connection_failed,
    plugin_sql_connection_query_attempted,
    plugin_sql_connection_query_failed,
    plugin_sql_connection_query_success,
    plugin_sql_connection_success,
    plugin_updated,
)
from .tasks import create_plugin_selector_history


logger = logging.getLogger(__name__)
prefix = "smarter.apps.plugin.receivers."


@receiver(plugin_created, dispatch_uid="plugin_created")
def handle_plugin_created(sender, plugin: PluginBase, **kwargs):
    """Handle plugin created signal."""

    logger.info(
        "%s - account: %s - user: %s - name: %s data: %s",
        formatted_text(prefix + "plugin_created"),
        plugin.user_profile.account,
        plugin.user_profile.user,
        plugin.name,
        formatted_json(plugin.data),
    )


@receiver(plugin_cloned, dispatch_uid="plugin_cloned")
def handle_plugin_cloned(sender, plugin: PluginBase, **kwargs):
    """Handle plugin cloned signal."""

    logger.info("%s - %s data: %s", formatted_text(prefix + "plugin_cloned"), plugin.name, plugin.data)


@receiver(plugin_updated, dispatch_uid="plugin_updated")
def handle_plugin_updated(sender, plugin: PluginBase, **kwargs):
    """Handle plugin updated signal."""

    logger.info(
        "%s - account: %s - user: %s - name: %s data: %s",
        formatted_text(prefix + "plugin_updated"),
        plugin.user_profile.account,
        plugin.user_profile.user,
        plugin.name,
        formatted_json(plugin.data),
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

    inquiry_type = kwargs.get("inquiry_type")
    inquiry_return = kwargs.get("inquiry_return")

    try:
        inquiry_return = json.loads(inquiry_return)
    except (TypeError, json.JSONDecodeError):
        pass

    if waffle.switch_is_active(SmarterWaffleSwitches.CHAT_LOGGING):
        logger.info(
            "%s - %s inquiry_type: %s inquiry_return: %s",
            formatted_text(prefix + "plugin_called"),
            plugin.name,
            inquiry_type,
            formatted_json(inquiry_return) if inquiry_return else None,
        )
    else:
        logger.info(
            "%s - %s inquiry_type: %s",
            formatted_text(prefix + "plugin_called"),
            plugin.name,
            inquiry_type,
        )


@receiver(plugin_ready, dispatch_uid="plugin_ready")
def handle_plugin_ready(sender, plugin: PluginBase, **kwargs):
    """Handle plugin ready signal."""

    logger.info("%s - %s", formatted_text(prefix + "plugin_ready"), plugin.name)


@receiver(plugin_selected, dispatch_uid="plugin_selected")
def handle_plugin_selected(sender, *args, **kwargs):
    """Handle plugin selected signal."""
    # plugin: PluginBase, user, messages: list[dict], search_term: str, messages: list[dict] = None
    input_text: str = kwargs.get("input_text")
    plugin: PluginBase = kwargs.get("plugin")
    user = kwargs.get("user")
    messages: list[dict] = kwargs.get("messages", [])
    search_term: str = kwargs.get("search_term", "")
    user_id: int = user.id if user else None

    prompt = input_text if input_text else formatted_json(messages)
    logger.info(
        "signal received for %s - %s search_term: %s prompt(s): %s",
        formatted_text(prefix + "plugin_selected"),
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
    )


# ------------------------------------------------------------------------------
# Django model receivers.
# ------------------------------------------------------------------------------


@receiver(post_save, sender=PluginMeta)
def handle_plugin_meta_created(sender, instance, created, **kwargs):

    if created:
        logger.info("%s %s", formatted_text(prefix + "post_save() PluginMeta() record created:"), instance.name)


@receiver(post_save, sender=PluginSelector)
def handle_plugin_selector_created(sender, instance, created, **kwargs):
    """Handle plugin selector created signal."""

    if created:
        logger.info("%s", formatted_text(prefix + "post_save() PluginSelector() record created."))


@receiver(post_save, sender=PluginPrompt)
def handle_plugin_prompt_created(sender, instance, created, **kwargs):
    """Handle plugin prompt created signal."""

    if created:
        logger.info("%s", formatted_text(prefix + "post_save() PluginPrompt() record created."))


@receiver(post_save, sender=PluginDataStatic)
def handle_plugin_data_created(sender, instance, created, **kwargs):
    """Handle plugin data created signal."""

    if created:
        logger.info("%s", formatted_text(prefix + "post_save() PluginDataStatic() record created."))


@receiver(post_save, sender=PluginSelectorHistory)
def handle_plugin_selector_history_created(sender, instance, created, **kwargs):
    """Handle plugin selector history created signal."""

    if created:
        logger.info(
            "%s - %s",
            formatted_text(prefix + "post_save() PluginSelectorHistory() created"),
            formatted_json(model_to_dict(instance)),
        )


@receiver(post_save, sender=ApiConnection)
def handle_api_connection_created(sender, instance, created, **kwargs):
    """Handle API connection created signal."""

    if created:
        logger.info(
            "%s - %s",
            formatted_text(prefix + "post_save() ApiConnection() created"),
            formatted_json(model_to_dict(instance)),
        )
    else:
        logger.info(
            "%s - %s",
            formatted_text(prefix + "post_save() ApiConnection() updated"),
            formatted_json(model_to_dict(instance)),
        )


@receiver(post_save, sender=SqlConnection)
def handle_sql_connection_created(sender, instance, created, **kwargs):
    """Handle SQL connection created signal."""

    if created:
        logger.info(
            "%s - %s",
            formatted_text(prefix + "post_save() SqlConnection() created"),
            formatted_json(model_to_dict(instance)),
        )
    else:
        logger.info(
            "%s - %s",
            formatted_text(prefix + "post_save() SqlConnection() updated"),
            formatted_json(model_to_dict(instance)),
        )


@receiver(post_save, sender=PluginDataApi)
def handle_plugin_data_api_created(sender, instance, created, **kwargs):
    """Handle plugin data API created signal."""

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
def handle_plugin_data_sql_created(sender, instance, created, **kwargs):
    """Handle plugin data SQL created signal."""

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
        formatted_text(prefix + "plugin_sql_connection_attempted"),
        formatted_json(connection.get_connection_string()),
    )


@receiver(plugin_sql_connection_success, dispatch_uid="plugin_sql_connection_success")
def handle_plugin_sql_connection_success(sender, connection: SqlConnection, **kwargs):
    """Handle plugin SQL connection success signal."""

    logger.info(
        "%s - %s",
        formatted_text(prefix + "plugin_sql_connection_success"),
        formatted_json(connection.get_connection_string()),
    )


@receiver(plugin_sql_connection_failed, dispatch_uid="plugin_sql_connection_failed")
def handle_plugin_sql_connection_failed(sender, connection: SqlConnection, **kwargs):
    """Handle plugin SQL connection failed signal."""

    logger.info(
        "%s - %s",
        formatted_text(prefix + "plugin_sql_connection_failed"),
        formatted_json(connection.get_connection_string()),
    )


@receiver(plugin_sql_connection_query_attempted, dispatch_uid="plugin_sql_connection_query_attempted")
def handle_plugin_sql_connection_query_attempted(sender, connection: SqlConnection, **kwargs):
    """Handle plugin SQL connection query attempted signal."""

    logger.info(
        "%s - %s",
        formatted_text(prefix + "plugin_sql_connection_query_attempted"),
        formatted_json(connection.get_connection_string()),
    )


@receiver(plugin_sql_connection_query_success, dispatch_uid="plugin_sql_connection_query_success")
def handle_plugin_sql_connection_query_success(sender, connection: SqlConnection, **kwargs):
    """Handle plugin SQL connection query success signal."""

    logger.info(
        "%s - %s",
        formatted_text(prefix + "plugin_sql_connection_query_success"),
        formatted_json(connection.get_connection_string()),
    )


@receiver(plugin_sql_connection_query_failed, dispatch_uid="plugin_sql_connection_query_failed")
def handle_plugin_sql_connection_query_failed(sender, connection: SqlConnection, **kwargs):
    """Handle plugin SQL connection query failed signal."""

    logger.info(
        "%s - %s",
        formatted_text(prefix + "plugin_sql_connection_query_failed"),
        formatted_json(connection.get_connection_string()),
    )


@receiver(plugin_api_connection_attempted, dispatch_uid="plugin_api_connection_attempted")
def handle_plugin_api_connection_attempted(sender, connection: ApiConnection, **kwargs):
    """Handle plugin API connection attempted signal."""

    logger.info(
        "%s - %s",
        formatted_text(prefix + "plugin_api_connection_attempted"),
        formatted_json(connection.get_connection_string()),
    )


@receiver(plugin_api_connection_success, dispatch_uid="plugin_api_connection_success")
def handle_plugin_api_connection_success(sender, connection: ApiConnection, **kwargs):
    """Handle plugin API connection success signal."""

    logger.info(
        "%s - %s",
        formatted_text(prefix + "plugin_api_connection_success"),
        formatted_json(connection.get_connection_string()),
    )


@receiver(plugin_api_connection_failed, dispatch_uid="plugin_api_connection_failed")
def handle_plugin_api_connection_failed(sender, connection: ApiConnection, error: Exception = None, **kwargs):
    """Handle plugin API connection failed signal."""

    logger.info(
        "%s - %s",
        formatted_text(prefix + "plugin_api_connection_failed"),
        formatted_json(connection.get_connection_string()),
    )


@receiver(plugin_api_connection_query_attempted, dispatch_uid="plugin_api_connection_query_attempted")
def handle_plugin_api_connection_query_attempted(sender, connection: ApiConnection, **kwargs):
    """Handle plugin API connection query attempted signal."""

    logger.info(
        "%s - %s",
        formatted_text(prefix + "plugin_api_connection_query_attempted"),
        formatted_json(connection.get_connection_string()),
    )


@receiver(plugin_api_connection_query_success, dispatch_uid="plugin_api_connection_query_success")
def handle_plugin_api_connection_query_success(sender, connection: ApiConnection, response: Response = None, **kwargs):
    """Handle plugin API connection query success signal."""

    logger.info(
        "%s - %s - response: %s",
        formatted_text(prefix + "plugin_api_connection_query_success"),
        connection.get_connection_string(),
        formatted_json(response.json()) if response else None,
    )


@receiver(plugin_api_connection_query_failed, dispatch_uid="plugin_api_connection_query_failed")
def handle_plugin_api_connection_query_failed(
    sender, connection: ApiConnection, response: Response = None, error: Exception = None, **kwargs
):
    """Handle plugin API connection query failed signal."""

    logger.info(
        "%s - %s - response: %s - error: %s",
        formatted_text(prefix + "plugin_api_connection_query_failed"),
        formatted_json(connection.get_connection_string()),
        formatted_json(response.json()) if response else None,
        error,
    )
