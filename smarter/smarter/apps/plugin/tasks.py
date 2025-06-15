# pylint: disable=unused-argument

import logging
from typing import Optional

from django.conf import settings

from smarter.apps.account.utils import (
    get_cached_user_for_user_id,
    get_cached_user_profile,
)
from smarter.apps.plugin.plugin.base import SmarterPluginError
from smarter.common.const import SMARTER_CHAT_SESSION_KEY_NAME
from smarter.common.helpers.console_helpers import formatted_text
from smarter.smarter_celery import app

from .models import PluginSelectorHistory
from .plugin.static import StaticPlugin


logger = logging.getLogger(__name__)
module_prefix = "smarter.apps.plugin.tasks."


@app.task(
    autoretry_for=(Exception,),
    retry_backoff=settings.SMARTER_CHATBOT_TASKS_CELERY_RETRY_BACKOFF,
    max_retries=settings.SMARTER_CHATBOT_TASKS_CELERY_MAX_RETRIES,
    queue=settings.SMARTER_CHATBOT_TASKS_CELERY_TASK_QUEUE,
)
def create_plugin_selector_history(*args, **kwargs):
    """Create plugin selector history."""

    user = None
    user_profile = None
    user_id = kwargs.get("user_id")
    if user_id:
        user = get_cached_user_for_user_id(user_id)
        user_profile = get_cached_user_profile(user)

    plugin_id = kwargs.get("plugin_id")
    try:
        # to catch a race situation in unit tests.
        plugin = StaticPlugin(plugin_id=plugin_id, user_profile=user_profile)
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
