# pylint: disable=W0613
"""Django signal receivers of the llmtool Django models."""

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.forms.models import model_to_dict

from smarter.common.helpers.console_helpers import SmarterFormattedText
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


@receiver(post_save, sender=PluginMeta)
def handle_plugin_meta_saved(sender, instance, created, **kwargs):
    """
    Handle plugin meta saved signal.

    Logs it at INFO.

    :param sender: The model class.
    :param instance: The row.
    :param created: True if the row was created, False if it was updated.
    """

    if created:
        logger.info("PluginMeta record created: %s", instance.name)
    else:
        logger.info(
            "PluginMeta record updated: %s",
            instance.name,
        )


@receiver(post_save, sender=PluginSelector)
def handle_plugin_selector_saved(sender, instance, created, **kwargs):
    """
    Handle plugin selector saved signal.

    Logs it at INFO.

    :param sender: The model class.
    :param instance: The row.
    :param created: True if the row was created, False if it was updated.
    """

    if created:
        logger.info("PluginSelector record created.")
    else:
        logger.info(
            "PluginSelector record updated: %s",
            SmarterFormattedText.json(model_to_dict(instance)),
        )


@receiver(post_save, sender=PluginPrompt)
def handle_plugin_prompt_saved(sender, instance, created, **kwargs):
    """
    Handle plugin prompt saved signal.

    Logs it at INFO.

    :param sender: The model class.
    :param instance: The row.
    :param created: True if the row was created, False if it was updated.
    """

    if created:
        logger.info("PluginPrompt record created.")
    else:
        logger.info(
            "PluginPrompt record updated: %s",
            SmarterFormattedText.json(model_to_dict(instance)),
        )


@receiver(post_save, sender=PluginDataStatic)
def handle_plugin_data_saved(sender, instance, created, **kwargs):
    """
    Handle plugin data saved signal.

    Logs it at INFO.

    :param sender: The model class.
    :param instance: The row.
    :param created: True if the row was created, False if it was updated.
    """

    if created:
        logger.info("PluginDataStatic record created.")
    else:
        logger.info(
            "PluginDataStatic record updated: %s",
            SmarterFormattedText.json(model_to_dict(instance)),
        )


@receiver(post_save, sender=PluginSelectorHistory)
def handle_plugin_selector_history_saved(sender, instance, created, **kwargs):
    """
    Handle plugin selector history saved signal.

    Logs it at INFO.

    :param sender: The model class.
    :param instance: The row.
    :param created: True if the row was created, False if it was updated.
    """

    if created:
        logger.info(
            "PluginSelectorHistory created: %s",
            SmarterFormattedText.json(model_to_dict(instance)),
        )
    else:
        logger.info(
            "PluginSelectorHistory updated: %s",
            SmarterFormattedText.json(model_to_dict(instance)),
        )


@receiver(post_save, sender=PluginDataApi)
def handle_plugin_data_api_saved(sender, instance, created, **kwargs):
    """
    Handle plugin data API saved signal.

    Logs it at INFO.

    :param sender: The model class.
    :param instance: The row.
    :param created: True if the row was created, False if it was updated.
    """

    if created:
        logger.info(
            "PluginDataApi created: %s",
            SmarterFormattedText.json(model_to_dict(instance)),
        )
    else:
        logger.info(
            "PluginDataApi updated: %s",
            SmarterFormattedText.json(model_to_dict(instance)),
        )


@receiver(post_save, sender=PluginDataSql)
def handle_plugin_data_sql_saved(sender, instance, created, **kwargs):
    """
    Handle plugin data SQL saved signal.

    Logs it at INFO.

    :param sender: The model class.
    :param instance: The row.
    :param created: True if the row was created, False if it was updated.
    """

    if created:
        logger.info(
            "PluginDataSql created: %s",
            SmarterFormattedText.json(model_to_dict(instance)),
        )
    else:
        logger.info(
            "PluginDataSql updated: %s",
            SmarterFormattedText.json(model_to_dict(instance)),
        )


@receiver(pre_delete, sender=PluginDataApi)
def handle_plugin_data_api_pre_delete(sender, instance, **kwargs):
    """
    Handle pre-delete signal for PluginDataApi.

    Logs it at INFO.

    :param sender: The model class.
    :param instance: The row.
    """
    logger.info(
        "PluginDataApi %s deleting.",
        instance,
    )


@receiver(pre_delete, sender=PluginDataSql)
def handle_plugin_data_sql_pre_delete(sender, instance, **kwargs):
    """
    Handle pre-delete signal for PluginDataSql.

    Logs it at INFO.

    :param sender: The model class.
    :param instance: The row.
    """
    logger.info(
        "PluginDataSql %s deleting.",
        instance,
    )


@receiver(pre_delete, sender=PluginDataStatic)
def handle_plugin_data_static_pre_delete(sender, instance, **kwargs):
    """
    Handle pre-delete signal for PluginDataStatic.

    Logs it at INFO.

    :param sender: The model class.
    :param instance: The row.
    """
    logger.info(
        "PluginDataStatic %s deleting.",
        instance,
    )


@receiver(pre_delete, sender=PluginMeta)
def handle_plugin_meta_pre_delete(sender, instance, **kwargs):
    """
    Handle pre-delete signal for PluginMeta.

    Logs it at INFO.

    :param sender: The model class.
    :param instance: The row.
    """
    logger.info(
        "PluginMeta %s deleting.",
        instance,
    )


@receiver(pre_delete, sender=PluginPrompt)
def handle_plugin_prompt_pre_delete(sender, instance, **kwargs):
    """
    Handle pre-delete signal for PluginPrompt.

    Logs it at INFO.

    :param sender: The model class.
    :param instance: The row.
    """
    logger.info(
        "PluginPrompt %s deleting.",
        instance,
    )


@receiver(pre_delete, sender=PluginSelector)
def handle_plugin_selector_pre_delete(sender, instance, **kwargs):
    """
    Handle pre-delete signal for PluginSelector.

    Logs it at INFO.

    :param sender: The model class.
    :param instance: The row.
    """
    logger.info(
        "PluginSelector %s deleting.",
        instance,
    )


@receiver(pre_delete, sender=PluginSelectorHistory)
def handle_plugin_selector_history_pre_delete(sender, instance, **kwargs):
    """
    Handle pre-delete signal for PluginSelectorHistory.

    Logs it at INFO.

    :param sender: The model class.
    :param instance: The row.
    """
    logger.info(
        "PluginSelectorHistory %s deleting.",
        instance,
    )


@receiver(post_save, sender=PluginDataWebsearch)
def handle_plugin_data_websearch_saved(sender, instance, created, **kwargs):
    """
    Handle plugin data websearch saved signal.

    Logs it at INFO.

    :param sender: The model class.
    :param instance: The row.
    :param created: True if the row was created, False if it was updated.
    """
    logger.info(
        "PluginDataWebsearch %s: %s",
        "created" if created else "updated",
        SmarterFormattedText.json(instance.data()),
    )


@receiver(pre_delete, sender=PluginDataWebsearch)
def handle_plugin_data_websearch_pre_delete(sender, instance, **kwargs):
    """
    Handle pre-delete signal for PluginDataWebsearch.

    Logs it at INFO.

    :param sender: The model class.
    :param instance: The row.
    """
    logger.info(
        "PluginDataWebsearch %s deleting.",
        instance,
    )
