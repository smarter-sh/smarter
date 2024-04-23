# pylint: disable=W0613,C0115,R0913
"""
Celery tasks for chat app.

These tasks are i/o intensive operations for creating chat and plugin history records with
Celery workers in order to avoid blocking the main app thread. This is advance work to lay groundwork for
future high-traffic scenarios.
"""
import logging

from smarter.apps.chatbot.models import ChatBot
from smarter.smarter_celery import app

from .models import Chat, ChatPluginUsage, ChatToolCall


logger = logging.getLogger(__name__)


def aggregate_chat_history():
    """summarize detail chatbot history into aggregate records."""

    # FIX NOTE: implement me.
    logger.info("Aggregating chat history.")


@app.task()
def create_chat_history(session_key, chatbot_id):
    """Create chat history record with flattened LLM response."""
    chatbot = ChatBot.objects.get(id=chatbot_id)
    Chat(session_key=session_key, chatbot=chatbot).save()


@app.task()
def create_chat_tool_call_history(chat_id, plugin_id, tool_call, request, response):
    """Create chat tool call history record."""
    ChatToolCall(chat_id=chat_id, plugin_id=plugin_id, tool_call=tool_call, request=request, response=response).save()


@app.task()
def create_plugin_usage_history(user_id, plugin_id, event, data, model, custom_tool, temperature, max_tokens):
    """Create plugin usage history record."""

    ChatPluginUsage(
        user_id=user_id,
        plugin_id=plugin_id,
        event=event,
        data=data,
        model=model,
        custom_tool=custom_tool,
        temperature=temperature,
        max_tokens=max_tokens,
    ).save()


@app.task()
def create_plugin_selection_history(user_id, plugin_id, event, inquiry_type, inquiry_return):
    """Create plugin selection history record."""
    ChatPluginUsage(
        user_id=user_id, plugin_id=plugin_id, event=event, inquiry_type=inquiry_type, inquiry_return=inquiry_return
    ).save()
