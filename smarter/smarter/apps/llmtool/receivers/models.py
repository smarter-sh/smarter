# pylint: disable=W0613
"""Django signal receivers of the llmtool Django models."""

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.forms.models import model_to_dict

from smarter.common.helpers.console_helpers import formatted_json, formatted_text
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

from ..models import (
    PluginDataApi,
    PluginDataSql,
    PluginDataStatic,
    PluginDataWebsearch,
    PluginMeta,
    PluginPrompt,
    PluginSelector,
    PluginSelectorHistory,
)

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.RECEIVER_LOGGING])

prefix = f"{__name__}."


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


@receiver(post_save, sender=PluginDataWebsearch)
def handle_plugin_data_websearch_saved(sender, instance, created, **kwargs):
    """Handle plugin data websearch saved signal."""
    logger.info(
        "%s - %s",
        formatted_text(prefix + f"post_save() PluginDataWebsearch() {'created' if created else 'updated'}"),
        formatted_json(instance.data()),
    )


@receiver(pre_delete, sender=PluginDataWebsearch)
def handle_plugin_data_websearch_pre_delete(sender, instance, **kwargs):
    """Handle pre-delete signal for PluginDataWebsearch."""
    logger.info(
        "%s - %s deleting.",
        formatted_text(prefix + "PluginDataWebsearch().pre_delete()"),
        instance,
    )
