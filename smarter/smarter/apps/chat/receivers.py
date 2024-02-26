# -*- coding: utf-8 -*-
"""Django Signal Receivers for chat app."""
# pylint: disable=W0613,C0115
import logging

from django.dispatch import receiver

from smarter.apps.chat.models import (
    ChatHistory,
    ChatToolCallHistory,
    PluginUsageHistory,
)
from smarter.apps.plugin.signals import plugin_called

from .signals import (
    chat_completion_called,
    chat_completion_failed,
    chat_completion_history_created,
    chat_completion_returned,
    chat_completion_tool_call_created,
    chat_completion_tool_call_history_created,
    chat_completion_tool_call_received,
    chat_invoked,
    plugin_selected,
    plugin_selection_history_created,
)


logger = logging.getLogger(__name__)


@receiver(chat_invoked)
def handle_chat_invoked(sender, **kwargs):
    """Handle chat invoked signal."""

    user = kwargs.get("user")
    data = kwargs.get("data")
    logger.info("Chat invoked signal received: %s - %s", user.username, data)


@receiver(chat_completion_called)
def handle_chat_completion_called(sender, **kwargs):
    """Handle chat completion called signal."""

    user = kwargs.get("user")
    data = kwargs.get("data")
    logger.info("Chat completion called signal received: %s - %s", user.username, data)


@receiver(chat_completion_tool_call_created)
@receiver(chat_completion_tool_call_received)
def handle_chat_completion_tool_call(sender, **kwargs):
    """Handle chat completion tool call signal."""

    user = kwargs.get("user")
    plugin = kwargs.get("plugin")
    input_text = kwargs.get("input_text")
    model = kwargs.get("model")
    messages = kwargs.get("messages")
    response = kwargs.get("response")
    response_id = response.get("id") if response else None
    event_type = "received" if "chat_completion_tool_call_received" in sender.__name__ else "called"

    logger.info(
        "Chat completion tool call %s signal received: %s - %s - %s", event_type, user.username, input_text, model
    )

    chat_tool_call_history = ChatToolCallHistory(
        event=event_type,
        user=user,
        plugin=plugin,
        input_text=input_text,
        model=model,
        messages=messages,
        response=response,
        response_id=response_id,
    )

    if event_type == "received":
        chat_tool_call_history.response = response

    chat_tool_call_history.save()


@receiver(plugin_selected)
def handle_plugin_selected(sender, **kwargs):
    """Handle plugin selected signal."""

    plugin = kwargs.get("plugin")
    user = kwargs.get("user")
    data = kwargs.get("data")
    model = kwargs.get("model")
    temperature = kwargs.get("temperature")
    max_tokens = kwargs.get("max_tokens")
    messages = kwargs.get("messages")
    custom_tool = kwargs.get("custom_tool")
    input_text = kwargs.get("input_text")

    logger.info("Plugin selected signal received: %s - %s - %s", user.username, plugin, input_text)

    plugin_selection_history = PluginUsageHistory(
        user=user,
        plugin=plugin,
        event="selected",
        data=data,
        model=model,
        messages=messages,
        custom_tool=custom_tool,
        temperature=temperature,
        max_tokens=max_tokens,
        custom_tool=custom_tool,
        input_text=input_text,
    )
    plugin_selection_history.save()


@receiver(plugin_called)
def handle_plugin_called(sender, **kwargs):
    """Handle plugin called signal."""

    user = kwargs.get("user")
    plugin = kwargs.get("plugin")
    inquiry_type = kwargs.get("inquiry_type")
    inquiry_return = kwargs.get("inquiry_return")
    logger.info("Plugin called signal received: %s - %s", user.username, inquiry_type)

    plugin_selection_history = PluginUsageHistory(
        user=user, plugin=plugin, event="called", inquiry_type=inquiry_type, inquiry_return=inquiry_return
    )
    plugin_selection_history.save()


@receiver(plugin_selection_history_created)
def handle_plugin_selection_history_created(sender, **kwargs):
    """Handle plugin selection history created signal."""

    user = kwargs.get("user")
    data = kwargs.get("data")
    logger.info("Plugin selection history created signal received: %s - %s", user.username, data)


@receiver(chat_completion_returned)
def handle_chat_completion_returned(sender, **kwargs):
    """Handle chat completion returned signal."""

    user = kwargs.get("user")
    input_text = kwargs.get("input_text")
    model = kwargs.get("model")
    messages = kwargs.get("messages")
    tools = kwargs.get("tools")
    temperature = kwargs.get("temperature")
    max_tokens = kwargs.get("max_tokens")
    response = kwargs.get("response")
    response_id = response.get("id") if response else None

    logger.info("Chat completion returned signal received: %s - %s - %s", user.username, input_text, model)

    chat_history = ChatHistory(
        user=user,
        input_text=input_text,
        model=model,
        messages=messages,
        tools=tools,
        temperature=temperature,
        response=response,
        response_id=response_id,
        max_tokens=max_tokens,
    )
    chat_history.save()


@receiver(chat_completion_failed)
def handle_chat_completion_failed(sender, **kwargs):
    """Handle chat completion failed signal."""

    user = kwargs.get("user")
    data = kwargs.get("data")

    logger.info("Chat completion failed signal received: %s - %s", user.username, data)


@receiver(chat_completion_history_created)
def handle_chat_completion_history_created(sender, **kwargs):
    """Handle chat completion history created signal."""

    user = kwargs.get("user")
    data = kwargs.get("data")
    input_text = data.input_text if data else None
    logger.info("Chat completion history created signal received: %s - %s", user.username, input_text)


@receiver(chat_completion_tool_call_history_created)
def handle_chat_completion_tool_call_history_created(sender, **kwargs):
    """Handle chat completion tool call history created signal."""

    user = kwargs.get("user")
    data = kwargs.get("data")
    input_text = data.input_text if data else None
    logger.info("Chat completion tool call history created signal received: %s - %s", user.username, input_text)
