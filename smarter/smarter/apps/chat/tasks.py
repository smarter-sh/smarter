# pylint: disable=W0613,C0115,R0913
"""
Celery tasks for chat app.

These tasks are i/o intensive operations for creating chat and plugin history records with
Celery workers in order to avoid blocking the main app thread. This is advance work to lay groundwork for
future high-traffic scenarios.
"""
import logging

from smarter.smarter_celery import app

from .models import Chat, ChatToolCall, PluginUsage


logger = logging.getLogger(__name__)


def aggregate_chat_history():
    """summarize detail chatbot history into aggregate records."""

    # FIX NOTE: implement me.
    logger.info("Aggregating chat history.")


@app.task()
def create_chat_history(model, tools, temperature, max_tokens):
    """Create chat history record with flattened LLM response."""

    Chat(model=model, tools=tools, temperature=temperature, max_tokens=max_tokens)


@app.task()
def create_chat_tool_call_history(chat_id, plugin_id, tool_call, request, response):
    """Create chat tool call history record."""
    chat_tool_call_history = ChatToolCall(
        chat_id=chat_id, plugin_id=plugin_id, tool_call=tool_call, request=request, response=response
    )
    chat_tool_call_history.save()


@app.task()
def create_plugin_usage_history(user_id, plugin_id, event, data, model, custom_tool, temperature, max_tokens):
    """Create plugin usage history record."""

    plugin_selection_history = PluginUsage(
        user_id=user_id,
        plugin_id=plugin_id,
        event=event,
        data=data,
        model=model,
        custom_tool=custom_tool,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    plugin_selection_history.save()


@app.task()
def create_plugin_selection_history(user_id, plugin_id, event, inquiry_type, inquiry_return):
    """Create plugin selection history record."""
    plugin_selection_history = PluginUsage(
        user_id=user_id, plugin_id=plugin_id, event=event, inquiry_type=inquiry_type, inquiry_return=inquiry_return
    )
    plugin_selection_history.save()
