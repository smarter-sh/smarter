# pylint: disable=W0613
"""Django signal receivers of SkillPlugin tool calls, and the retrieval of remote skills."""

from django.dispatch import receiver

from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

from ..plugin.static import PluginBase
from ..signals.skill import (
    skill_plugin_failed,
    skill_plugin_request_completed,
    skill_plugin_request_started,
    skill_plugin_responded,
    skill_plugin_retrieval_failed,
    skill_plugin_retrieval_started,
    skill_plugin_retrieved,
)
from .utils import response_characters

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.RECEIVER_LOGGING])

prefix = f"{__name__}."


@receiver(skill_plugin_request_started, dispatch_uid="skill_plugin_request_started")
def handle_skill_plugin_request_started(sender, plugin: PluginBase, function_args=None, **kwargs):
    """Handle SkillPlugin request started signal."""
    logger.info(
        "%s - %s function_args: %s", formatted_text(prefix + "skill_plugin_request_started"), plugin.name, function_args
    )


@receiver(skill_plugin_responded, dispatch_uid="skill_plugin_responded")
def handle_skill_plugin_responded(sender, plugin: PluginBase, response=None, cached: bool = False, **kwargs):
    """Handle SkillPlugin responded signal."""
    logger.info(
        "%s - %s resource: %s characters: %s cached: %s",
        formatted_text(prefix + "skill_plugin_responded"),
        plugin.name,
        kwargs.get("resource"),
        response_characters(response),
        cached,
    )


@receiver(skill_plugin_failed, dispatch_uid="skill_plugin_failed")
def handle_skill_plugin_failed(sender, plugin: PluginBase, error: str, **kwargs):
    """Handle SkillPlugin failed signal."""
    logger.warning("%s - %s failed: %s", formatted_text(prefix + "skill_plugin_failed"), plugin.name, error)


@receiver(skill_plugin_request_completed, dispatch_uid="skill_plugin_request_completed")
def handle_skill_plugin_request_completed(sender, plugin: PluginBase, success: bool, duration: float, **kwargs):
    """Handle SkillPlugin request completed signal."""
    logger.info(
        "%s - %s success: %s duration: %.3fs",
        formatted_text(prefix + "skill_plugin_request_completed"),
        plugin.name,
        success,
        duration,
    )


@receiver(skill_plugin_retrieval_started, dispatch_uid="skill_plugin_retrieval_started")
def handle_skill_plugin_retrieval_started(sender, plugin: PluginBase, url: str, **kwargs):
    """Handle SkillPlugin retrieval started signal."""
    logger.info("%s - %s url: %s", formatted_text(prefix + "skill_plugin_retrieval_started"), plugin.name, url)


@receiver(skill_plugin_retrieved, dispatch_uid="skill_plugin_retrieved")
def handle_skill_plugin_retrieved(sender, plugin: PluginBase, url: str, **kwargs):
    """Handle SkillPlugin retrieved signal."""
    logger.info(
        "%s - %s url: %s skill_name: %s resource_count: %s duration: %.3fs",
        formatted_text(prefix + "skill_plugin_retrieved"),
        plugin.name,
        url,
        kwargs.get("skill_name"),
        kwargs.get("resource_count"),
        kwargs.get("duration", 0.0),
    )


@receiver(skill_plugin_retrieval_failed, dispatch_uid="skill_plugin_retrieval_failed")
def handle_skill_plugin_retrieval_failed(sender, plugin: PluginBase, url: str, error: str, **kwargs):
    """Handle SkillPlugin retrieval failed signal."""
    logger.warning(
        "%s - %s url: %s failed: %s",
        formatted_text(prefix + "skill_plugin_retrieval_failed"),
        plugin.name,
        url,
        error,
    )
