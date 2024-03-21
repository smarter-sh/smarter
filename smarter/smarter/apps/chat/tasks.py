# -*- coding: utf-8 -*-
# pylint: disable=W0613,C0115,R0913
"""
Celery tasks for chat app.

These tasks are i/o intensive operations for creating chat and plugin history records with
Celery workers in order to avoid blocking the main app thread. This is advance work to lay groundwork for
future high-traffic scenarios.
"""
import logging

from django.contrib.auth import get_user_model
from django.db.utils import IntegrityError

from smarter.apps.plugin.models import PluginMeta
from smarter.celery import celery_app as app

from .models import ChatHistory, ChatToolCallHistory, PluginUsageHistory


User = get_user_model()
logger = logging.getLogger(__name__)


def get_user(user_id):
    """Get user by user_id."""

    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return None


def get_plugin(plugin_id):
    """Get plugin by plugin_id."""
    try:
        return PluginMeta.objects.get(id=plugin_id)
    except PluginMeta.DoesNotExist:
        return None


@app.task
def create_chat_history(chat_id, user_id, model, tools, temperature, messages, response, max_tokens):
    """Create chat history record with flattened LLM response."""
    logger.info("Creating chat history record for chat_id: %s user_id: %s", chat_id, user_id)

    user = get_user(user_id)
    try:
        if user:
            chat_history = ChatHistory(
                chat_id=chat_id,
                user=user,
                model=model,
                tools=tools,
                temperature=temperature,
                messages=messages,
                response=response,
                max_tokens=max_tokens,
            )
            chat_history.save()
            return None
    except IntegrityError as e:
        # seems to happen due to race conditions during unit tests
        logger.warning("Couldn't save Chat history due to foreign key violation %s", e)

    # ditto
    logger.warning("Couldn't save Chat history. None existent user_id %s", user_id)
    return None


@app.task
def create_chat_tool_call_history(event_type, user_id, plugin_id, model, response, response_id):
    """Create chat tool call history record."""
    logger.info("Creating chat tool call history record for event_type: %s user_id: %s", event_type, user_id)

    user = get_user(user_id)
    plugin = get_plugin(plugin_id)
    chat_tool_call_history = ChatToolCallHistory(
        event=event_type,
        user=user,
        plugin=plugin,
        model=model,
        response=response,
        response_id=response_id,
    )

    if event_type == "received":
        chat_tool_call_history.response = response

    chat_tool_call_history.save()


@app.task
def create_plugin_usage_history(user_id, plugin_id, event, data, model, custom_tool, temperature, max_tokens):
    """Create plugin usage history record."""

    user = get_user(user_id)
    plugin = get_plugin(plugin_id)
    logger.info("Creating plugin usage history record for event: %s user_id: %s", event, user)

    plugin_selection_history = PluginUsageHistory(
        user=user,
        plugin=plugin,
        event=event,
        data=data,
        model=model,
        custom_tool=custom_tool,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    plugin_selection_history.save()


@app.task
def create_plugin_selection_history(user_id, plugin_id, event, inquiry_type, inquiry_return):
    """Create plugin selection history record."""
    logger.info("Creating plugin selection history record for event: %s user_id: %s", event, user_id)

    user = get_user(user_id)
    plugin = get_plugin(plugin_id)
    plugin_selection_history = PluginUsageHistory(
        user=user, plugin=plugin, event=event, inquiry_type=inquiry_type, inquiry_return=inquiry_return
    )
    plugin_selection_history.save()
