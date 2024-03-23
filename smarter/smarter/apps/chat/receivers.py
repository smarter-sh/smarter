# -*- coding: utf-8 -*-
"""Django Signal Receivers for chat app."""
# pylint: disable=W0613,C0115
import json
import logging

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.forms.models import model_to_dict

from .models import ChatHistory, ChatToolCallHistory, PluginUsageHistory
from .signals import (
    chat_completion_called,
    chat_completion_plugin_selected,
    chat_completion_tool_call_created,
    chat_completion_tools_call,
    chat_invoked,
    chat_response_failure,
    chat_response_success,
)


logger = logging.getLogger(__name__)


def formatted_json(json_obj: json) -> str:
    pretty_json = json.dumps(json_obj, indent=4)
    return f"\033[32m{pretty_json}\033[0m"


def formatted_text(text: str) -> str:

    # bright green
    # return f"\033[92m{text}\033[0m"

    # regular green
    # return f"\033[32m{text}\033[0m"

    # dark red
    # return f"\033[31m{text}\033[0m"

    # bold and dark red
    return f"\033[1;31m{text}\033[0m"


@receiver(chat_invoked, dispatch_uid="chat_invoked")
def handle_chat_invoked(sender, **kwargs):
    """Handle chat invoked signal."""

    user = kwargs.get("user")
    data = kwargs.get("data")
    logger.info("%s signal received: %s data: %s", formatted_text("chat_invoked"), user.username, formatted_json(data))


@receiver(chat_completion_called, dispatch_uid="chat_completion_called")
def handle_chat_completion_called(sender, **kwargs):
    """Handle chat completion called signal."""

    user = kwargs.get("user")
    data = kwargs.get("data")
    action = kwargs.get("action")

    logger.info(
        "%s signal received: %s action: %s data: %s",
        formatted_text("chat_completion_called"),
        user.username,
        action,
        formatted_json(data),
    )


@receiver(chat_completion_tools_call, dispatch_uid="chat_completion_tools_call")
def handle_chat_completion_tools_call(sender, **kwargs):

    user = kwargs.get("user")
    model = kwargs.get("model")
    tools = kwargs.get("tools")
    temperature = kwargs.get("temperature")
    max_tokens = kwargs.get("max_tokens")
    response = kwargs.get("response")

    logger.info(
        "%s signal received: %s \nmodel: %s \ntemperature: %s \nmax_tokens: %s \nresponse: %s \ntools: %s",
        formatted_text("chat_completion_tools_call"),
        user,
        model,
        temperature,
        max_tokens,
        formatted_json(response),
        formatted_json(tools),
    )


chat_completion_tools_call.connect(handle_chat_completion_tools_call, dispatch_uid="chat_completion_tools_call")


# pylint: disable=W0612


@receiver(chat_completion_tool_call_created, dispatch_uid="chat_completion_tool_call_created")
def handle_chat_completion_tool_call(sender, **kwargs):
    """Handle chat completion tool call signal."""

    user = kwargs.get("user")
    plugin = kwargs.get("plugin")
    model = kwargs.get("model")
    response = kwargs.get("response")
    response_id = response.get("id") if response else None
    event_type = "received" if "chat_completion_tool_call_received" in sender.__name__ else "called"

    if event_type == "called":
        logger.info(
            "%s %s signal received: %s model: %s",
            formatted_text("chat_completion_tool_call_created"),
            event_type,
            user.username,
            model,
        )
    else:
        logger.info(
            "%s %s signal received: %s model: %s",
            formatted_text("chat_completion_tool_call_received"),
            event_type,
            user.username,
            model,
        )
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


@receiver(chat_completion_plugin_selected, dispatch_uid="chat_completion_plugin_selected")
def handle_chat_completion_plugin_selected(sender, **kwargs):
    """Handle plugin selected signal."""

    plugin = kwargs.get("plugin")
    user = kwargs.get("user")
    data = kwargs.get("data")
    model = kwargs.get("model")
    temperature = kwargs.get("temperature")
    max_tokens = kwargs.get("max_tokens")
    custom_tool = kwargs.get("custom_tool")

    logger.info(
        "%s signal received: %s plugin: %s", formatted_text("chat_completion_plugin_selected"), user.username, plugin
    )

    plugin_selection_history = PluginUsageHistory(
        user=user,
        plugin=plugin,
        event="selected",
        data=data,
        model=model,
        custom_tool=custom_tool,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    plugin_selection_history.save()


@receiver(post_save, sender=ChatToolCallHistory)
def handle_plugin_selection_history_created(sender, **kwargs):
    """Handle plugin selection history created signal."""

    user = kwargs.get("user")
    data = kwargs.get("data")
    data_dict = model_to_dict(data)
    logger.info(
        "%s signal received: %s data: %s",
        formatted_text("chat_completion_plugin_usage_history_created"),
        user.username,
        formatted_json(data_dict),
    )


# pylint: disable=W0612
@receiver(chat_response_success, dispatch_uid="chat_response_success")
def handle_chat_completion_returned(sender, **kwargs):
    """Handle chat completion returned signal."""

    user = kwargs.get("user")
    model = kwargs.get("model")
    tools = kwargs.get("tools")
    temperature = kwargs.get("temperature")
    max_tokens = kwargs.get("max_tokens")
    messages = kwargs.get("messages")
    response = kwargs.get("response")
    chat_id = response.get("id") if response else None

    logger.info(
        "%s signal received:%s %s model: %s", formatted_text("chat_response_success"), chat_id, user.username, model
    )
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


@receiver(chat_response_failure, dispatch_uid="chat_response_failure")
def handle_chat_response_failed(sender, **kwargs):
    """Handle chat completion failed signal."""

    user = kwargs.get("user")
    data = kwargs.get("data")

    logger.info("%s signal received: %s data: %s", formatted_text("chat_response_failure"), user.username, data)


@receiver(post_save, sender=ChatHistory)
def handle_chat_history_created(sender, **kwargs):
    """Handle chat  history created signal."""

    user = kwargs.get("user")
    data = kwargs.get("data")
    data_dict = model_to_dict(data)
    logger.info(
        "%s signal received: %s %s",
        formatted_text("chat_history_created"),
        user.username,
        formatted_json(data_dict),
    )


@receiver(post_save, sender=ChatToolCallHistory)
def handle_chat_tool_call_history_created(sender, **kwargs):
    """Handle chat completion tool call history created signal."""

    user = kwargs.get("user")
    data = kwargs.get("data")
    data_dict = model_to_dict(data)
    logger.info(
        "%s signal received: %s data: %s",
        formatted_text("chat_tool_call_history_created"),
        user.username,
        formatted_json(data_dict),
    )
