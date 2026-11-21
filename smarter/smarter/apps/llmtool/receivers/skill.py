# pylint: disable=W0613
"""Django signal receivers of SkillPlugin tool calls, and the retrieval of remote skills."""

from django.dispatch import receiver

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


@receiver(skill_plugin_request_started, dispatch_uid="skill_plugin_request_started")
def handle_skill_plugin_request_started(sender, plugin: PluginBase, function_args=None, **kwargs):
    """
    Handle SkillPlugin request started signal.

    Logs it at INFO.

    :param sender: The class that sent the signal.
    :param plugin: The plugin.
    :param function_args: The arguments that the LLM called the tool with.
    """
    logger.info(
        "%s function_args: %s",
        plugin.name,
        function_args,
    )


@receiver(skill_plugin_responded, dispatch_uid="skill_plugin_responded")
def handle_skill_plugin_responded(sender, plugin: PluginBase, response=None, cached: bool = False, **kwargs):
    """
    Handle SkillPlugin responded signal.

    Logs it at INFO.

    :param sender: The class that sent the signal.
    :param plugin: The plugin.
    :param response: The response, whose length in characters is logged.
    :param cached: Whether the response was served from the cache.
    :param kwargs: The signal's other arguments, of which ``resource`` are logged.
    """
    logger.info(
        "%s resource: %s characters: %s cached: %s",
        plugin.name,
        kwargs.get("resource"),
        response_characters(response),
        cached,
    )


@receiver(skill_plugin_failed, dispatch_uid="skill_plugin_failed")
def handle_skill_plugin_failed(sender, plugin: PluginBase, error: str, **kwargs):
    """
    Handle SkillPlugin failed signal.

    Logs it at WARNING.

    :param sender: The class that sent the signal.
    :param plugin: The plugin.
    :param error: Why it failed.
    """
    logger.warning("%s failed: %s", plugin.name, error)


@receiver(skill_plugin_request_completed, dispatch_uid="skill_plugin_request_completed")
def handle_skill_plugin_request_completed(sender, plugin: PluginBase, success: bool, duration: float, **kwargs):
    """
    Handle SkillPlugin request completed signal.

    Logs it at INFO.

    :param sender: The class that sent the signal.
    :param plugin: The plugin.
    :param success: Whether the request succeeded.
    :param duration: Seconds that the request took.
    """
    logger.info(
        "%s success: %s duration: %.3fs",
        plugin.name,
        success,
        duration,
    )


@receiver(skill_plugin_retrieval_started, dispatch_uid="skill_plugin_retrieval_started")
def handle_skill_plugin_retrieval_started(sender, plugin: PluginBase, url: str, **kwargs):
    """
    Handle SkillPlugin retrieval started signal.

    Logs it at INFO.

    :param sender: The class that sent the signal.
    :param plugin: The plugin.
    :param url: The URL.
    """
    logger.info("%s url: %s", plugin.name, url)


@receiver(skill_plugin_retrieved, dispatch_uid="skill_plugin_retrieved")
def handle_skill_plugin_retrieved(sender, plugin: PluginBase, url: str, **kwargs):
    """
    Handle SkillPlugin retrieved signal.

    Logs it at INFO.

    :param sender: The class that sent the signal.
    :param plugin: The plugin.
    :param url: The URL.
    :param kwargs: The signal's other arguments, of which ``skill_name``, ``resource_count``, ``duration`` are logged.
    """
    logger.info(
        "%s url: %s skill_name: %s resource_count: %s duration: %.3fs",
        plugin.name,
        url,
        kwargs.get("skill_name"),
        kwargs.get("resource_count"),
        kwargs.get("duration", 0.0),
    )


@receiver(skill_plugin_retrieval_failed, dispatch_uid="skill_plugin_retrieval_failed")
def handle_skill_plugin_retrieval_failed(sender, plugin: PluginBase, url: str, error: str, **kwargs):
    """
    Handle SkillPlugin retrieval failed signal.

    Logs it at WARNING.

    :param sender: The class that sent the signal.
    :param plugin: The plugin.
    :param url: The URL.
    :param error: Why it failed.
    """
    logger.warning(
        "%s url: %s failed: %s",
        plugin.name,
        url,
        error,
    )
