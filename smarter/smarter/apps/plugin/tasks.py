# pylint: disable=unused-argument
"""
Celery tasks for the plugin app.
"""

import logging
from typing import Optional

from django.conf import settings

from smarter.apps.account.utils import (
    get_cached_user_for_user_id,
    get_cached_user_profile,
)
from smarter.apps.plugin.manifest.controller import PluginController
from smarter.apps.plugin.models import PluginMeta
from smarter.apps.plugin.plugin.base import SmarterPluginError
from smarter.common.conf import settings as smarter_settings
from smarter.common.const import SMARTER_CHAT_SESSION_KEY_NAME
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper
from smarter.workers.celery import app

from .models import PluginSelectorHistory


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return (
        waffle.switch_is_active(SmarterWaffleSwitches.TASK_LOGGING)
        and waffle.switch_is_active(SmarterWaffleSwitches.PLUGIN_LOGGING)
        and level >= smarter_settings.log_level
    )


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)
module_prefix = "smarter.apps.plugin.tasks."


@app.task(
    autoretry_for=(Exception,),
    retry_backoff=settings.SMARTER_CHATBOT_TASKS_CELERY_RETRY_BACKOFF,
    max_retries=settings.SMARTER_CHATBOT_TASKS_CELERY_MAX_RETRIES,
    queue=settings.SMARTER_CHATBOT_TASKS_CELERY_TASK_QUEUE,
)
def create_plugin_selector_history(*args, **kwargs):
    """
    Create plugin selector history.

    This Celery task records a user's plugin selection event, including search terms, input text, messages,
    and session key. It is typically called when a user interacts with the plugin selector UI.

    :param args: Positional arguments (unused).
    :type args: tuple
    :param kwargs: Keyword arguments containing context for the selector history.
    :type kwargs: dict

    **Expected kwargs:**
        - user_id (int): The ID of the user performing the selection.
        - plugin_id (int): The ID of the selected plugin.
        - input_text (str, optional): The user's input text.
        - messages (list[dict], optional): List of message objects.
        - search_term (str, optional): The search term used by the user.
        - session_key (str, optional): The chat session key.

    :return: None

    .. important::

        - invoked by the ``plugin_selected`` signal.
        - This task will not create a history record if the plugin or user profile cannot be resolved.
        - If the plugin controller cannot be instantiated, an error is logged and no history is created.

    .. seealso::

        - :class:`PluginSelectorHistory`
        - :class:`PluginController`
        - :class:`SmarterPluginError`

    **Example usage**:

    .. code-block:: python

        from smarter.apps.plugin.tasks import create_plugin_selector_history

        create_plugin_selector_history.apply_async(
            kwargs={
                "user_id": 42,
                "plugin_id": 7,
                "input_text": "Show me weather plugins",
                "search_term": "weather",
                "session_key": "abc123"
            }
        )

    """

    user = None
    user_profile = None
    user_id = kwargs.get("user_id")
    if user_id:
        user = get_cached_user_for_user_id(user_id)
        user_profile = get_cached_user_profile(user) if user else None

    plugin_id = kwargs.get("plugin_id")
    plugin_meta = PluginMeta.objects.get(id=plugin_id) if plugin_id else None
    try:
        # to catch a race situation in unit tests.
        plugin_controller = PluginController(
            user_profile=user_profile,
            account=user_profile.account,  # type: ignore[arg-type]
            user=user,  # type: ignore[arg-type]
            plugin_meta=plugin_meta,
        )
        if not plugin_controller or not plugin_controller.plugin:
            raise SmarterPluginError(
                f"PluginController could not be created for plugin_id: {plugin_id}, user_profile: {user_profile}"
            )
        plugin = plugin_controller.plugin
    except SmarterPluginError as e:
        logger.error(
            "%s plugin_id: %s, user_profile: %s, error: %s",
            formatted_text(module_prefix + "create_plugin_selector_history()"),
            plugin_id,
            user_profile,
            e,
        )
        return

    logger.info(
        "%s plugin_id: %s, user_profile: %s",
        formatted_text(module_prefix + "create_plugin_selector_history()"),
        plugin.id,
        user_profile,
    )
    input_text: Optional[str] = kwargs.get("input_text")
    messages: Optional[list[dict]] = kwargs.get("messages")
    search_term: Optional[str] = kwargs.get("search_term")
    session_key: Optional[str] = kwargs.get(SMARTER_CHAT_SESSION_KEY_NAME)

    PluginSelectorHistory.objects.create(
        plugin_selector=plugin.plugin_selector,
        search_term=search_term,
        messages={"input_text": input_text} if input_text else messages,
        session_key=session_key,
    )
