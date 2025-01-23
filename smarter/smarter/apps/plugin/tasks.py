# pylint: disable=unused-argument

import logging

from django.conf import settings

from smarter.apps.account.utils import user_for_user_id, user_profile_for_user
from smarter.common.helpers.console_helpers import formatted_text
from smarter.smarter_celery import app

from .models import PluginSelectorHistory
from .plugin.static import PluginStatic


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
        user = user_for_user_id(user_id)
        user_profile = user_profile_for_user(user)

    plugin_id = kwargs.get("plugin_id")
    plugin = PluginStatic(plugin_id=plugin_id, user_profile=user_profile)

    logger.info(
        "%s plugin_id: %s, user_profile: %s",
        formatted_text(module_prefix + "create_plugin_selector_history()"),
        plugin.id,
        user_profile,
    )
    input_text: str = kwargs.get("input_text")
    messages: list[dict] = kwargs.get("messages")
    search_term: str = kwargs.get("search_term")
    session_key: str = kwargs.get("session_key")

    PluginSelectorHistory.objects.create(
        plugin_selector=plugin.plugin_selector,
        search_term=search_term,
        messages={"input_text": input_text} if input_text else messages,
        session_key=session_key,
    )
