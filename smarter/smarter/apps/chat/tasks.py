# pylint: disable=W0613,C0115,R0913
"""
Celery tasks for chat app.

These tasks are i/o intensive operations for creating chat and plugin history records with
Celery workers in order to avoid blocking the main app thread. This is advance work to lay groundwork for
future high-traffic scenarios.
"""
import logging

from django.conf import settings

from smarter.apps.chatbot.models import ChatBot
from smarter.apps.plugin.models import PluginMeta
from smarter.common.helpers.console_helpers import formatted_text
from smarter.smarter_celery import app

from .models import Chat, ChatHistory, ChatPluginUsage, ChatToolCall


logger = logging.getLogger(__name__)
module_prefix = formatted_text("smarter.apps.chat.tasks.")


@app.task(
    autoretry_for=(Exception,),
    retry_backoff=settings.SMARTER_CHATBOT_TASKS_CELERY_RETRY_BACKOFF,
    max_retries=settings.SMARTER_CHATBOT_TASKS_CELERY_MAX_RETRIES,
    queue=settings.SMARTER_CHATBOT_TASKS_CELERY_TASK_QUEUE,
)
def create_chat_history(chat_id, request, response):
    logger.info("%s chat_id: %s", formatted_text(module_prefix + "create_chat_history()"), chat_id)
    chat = Chat.objects.get(id=chat_id)
    ChatHistory.objects.create(
        chat=chat,
        request=request,
        response=response,
    )


def aggregate_chat_history():
    """summarize detail chatbot history into aggregate records."""
    logger.info("%s", formatted_text(module_prefix + "aggregate_chat_history()"))


@app.task(
    autoretry_for=(Exception,),
    retry_backoff=settings.SMARTER_CHATBOT_TASKS_CELERY_RETRY_BACKOFF,
    max_retries=settings.SMARTER_CHATBOT_TASKS_CELERY_MAX_RETRIES,
    queue=settings.SMARTER_CHATBOT_TASKS_CELERY_TASK_QUEUE,
)
def create_chat(session_key, chatbot_id):
    """
    Create chat record with flattened LLM response.
    DELETE THIS? IT IS NOT USED.
    """
    chatbot = ChatBot.objects.get(id=chatbot_id)
    Chat.objects.create(session_key=session_key, chatbot=chatbot)


@app.task(
    autoretry_for=(Exception,),
    retry_backoff=settings.SMARTER_CHATBOT_TASKS_CELERY_RETRY_BACKOFF,
    max_retries=settings.SMARTER_CHATBOT_TASKS_CELERY_MAX_RETRIES,
    queue=settings.SMARTER_CHATBOT_TASKS_CELERY_TASK_QUEUE,
)
def create_chat_tool_call_history(chat_id, plugin_id, function_name, function_args, request, response):
    """Create chat tool call history record."""
    logger.info("%s", formatted_text(module_prefix + "create_chat_tool_call_history()"))
    try:
        chat = Chat.objects.get(id=chat_id)
    except Chat.DoesNotExist:
        chat = None
    try:
        plugin_meta = PluginMeta.objects.get(id=plugin_id)
    except PluginMeta.DoesNotExist:
        plugin_meta = None

    ChatToolCall.objects.create(
        chat=chat,
        plugin=plugin_meta,
        function_name=function_name,
        function_args=function_args,
        request=request,
        response=response,
    )


@app.task(
    autoretry_for=(Exception,),
    retry_backoff=settings.SMARTER_CHATBOT_TASKS_CELERY_RETRY_BACKOFF,
    max_retries=settings.SMARTER_CHATBOT_TASKS_CELERY_MAX_RETRIES,
    queue=settings.SMARTER_CHATBOT_TASKS_CELERY_TASK_QUEUE,
)
def create_plugin_usage_history(user_id, plugin_id, event, data, model, custom_tool, temperature, max_tokens):
    """Create plugin usage history record."""
    logger.info("%s", formatted_text(module_prefix + "create_plugin_usage_history()"))
    ChatPluginUsage.objects.create(
        user_id=user_id,
        plugin_id=plugin_id,
        event=event,
        data=data,
        model=model,
        custom_tool=custom_tool,
        temperature=temperature,
        max_tokens=max_tokens,
    )


@app.task(
    autoretry_for=(Exception,),
    retry_backoff=settings.SMARTER_CHATBOT_TASKS_CELERY_RETRY_BACKOFF,
    max_retries=settings.SMARTER_CHATBOT_TASKS_CELERY_MAX_RETRIES,
    queue=settings.SMARTER_CHATBOT_TASKS_CELERY_TASK_QUEUE,
)
def create_plugin_selection_history(user_id, plugin_id, event, inquiry_type, inquiry_return):
    """
    Create plugin selection history record.
    NOT IN USE
    """
    logger.info("%s", formatted_text(module_prefix + "create_plugin_selection_history()"))
    ChatPluginUsage.objects.create(
        user_id=user_id, plugin_id=plugin_id, event=event, inquiry_type=inquiry_type, inquiry_return=inquiry_return
    )
