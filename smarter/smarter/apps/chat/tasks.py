# pylint: disable=W0613,C0115,R0913
"""
Celery tasks for chat app.

These tasks are i/o intensive operations for creating chat and plugin history records with
Celery workers in order to avoid blocking the main app thread. This is advance work to lay groundwork for
future high-traffic scenarios.
"""
import logging

from django.conf import settings

from smarter.apps.account.models import Account
from smarter.apps.chatbot.models import ChatBot
from smarter.apps.plugin.models import PluginMeta
from smarter.common.exceptions import SmarterValueError
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
def create_chat_history(chat_id, request, response, messages):
    logger.info("%s chat_id: %s", formatted_text(module_prefix + "create_chat_history()"), chat_id)
    chat = Chat.objects.get(id=chat_id)
    ChatHistory.objects.create(chat=chat, request=request, response=response, messages=messages)


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
def update_chat(*args, **kwargs):
    """
    Update chat record with flattened LLM response.
    """
    chat_id = kwargs.get("chat_id", None)
    if chat_id is None:
        return
    try:
        chat = Chat.objects.get(id=chat_id)
    except Chat.DoesNotExist:
        chat = None

    if chat is not None:
        try:
            account_id = kwargs.get("account_id", chat.account.id if chat.account else None)
            if account_id is not None:
                chat.account = Account.objects.get(id=account_id)
        except Account.DoesNotExist:
            chat.account = None

        try:
            chatbot_id = kwargs.get("chatbot_id", chat.chatbot.id if chat.chatbot else None)
            if chatbot_id is not None:
                chat.chatbot = ChatBot.objects.get(id=chatbot_id)
        except ChatBot.DoesNotExist:
            chat.chatbot = None

        chat.ip_address = kwargs.get("ip_address", chat.ip_address)
        chat.user_agent = kwargs.get("user_agent", chat.user_agent)
        chat.url = kwargs.get("url", chat.url)
        chat.request = kwargs.get("request", chat.request)
        chat.response = kwargs.get("response", chat.response)
        chat.save()


@app.task(
    autoretry_for=(Exception,),
    retry_backoff=settings.SMARTER_CHATBOT_TASKS_CELERY_RETRY_BACKOFF,
    max_retries=settings.SMARTER_CHATBOT_TASKS_CELERY_MAX_RETRIES,
    queue=settings.SMARTER_CHATBOT_TASKS_CELERY_TASK_QUEUE,
)
def create_chat_tool_call_history(chat_id, plugin_meta_id, function_name, function_args, request, response):
    """Create chat tool call history record."""
    logger.info("%s", formatted_text(module_prefix + "create_chat_tool_call_history()"))
    chat = None
    plugin_meta = None

    try:
        chat = Chat.objects.get(id=chat_id)
    except Chat.DoesNotExist as e:
        raise SmarterValueError(f"Chat with id {chat_id} does not exist") from e

    try:
        if plugin_meta_id:
            plugin_meta = PluginMeta.objects.get(id=plugin_meta_id)
    except PluginMeta.DoesNotExist as e:
        raise SmarterValueError(f"PluginMeta with id {plugin_meta_id} does not exist") from e

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
def create_chat_plugin_usage(*args, **kwargs):
    """Create plugin usage history record."""
    logger.info("%s", formatted_text(module_prefix + "create_plugin_usage_history()"))
    chat_id = kwargs.get("chat_id", None)
    if chat_id is None:
        raise SmarterValueError("chat_id is required")

    plugin_id = kwargs.get("plugin_id", None)
    if plugin_id is None:
        raise SmarterValueError("plugin_id is required")

    input_text = kwargs.get("input_text", None)
    if input_text is None:
        raise SmarterValueError("input_text is required")
    try:
        chat = Chat.objects.get(id=chat_id)
    except Chat.DoesNotExist as e:
        raise SmarterValueError(f"Chat with id {chat_id} does not exist") from e

    try:
        plugin_meta = PluginMeta.objects.get(id=plugin_id)
    except PluginMeta.DoesNotExist as e:
        raise SmarterValueError(f"PluginMeta with id {plugin_id} does not exist") from e

    ChatPluginUsage.objects.create(
        chat=chat,
        plugin=plugin_meta,
        input_text=input_text,
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
