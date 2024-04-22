"""Django Signal Receivers for chat app."""

# pylint: disable=W0613,C0115
import logging

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.forms.models import model_to_dict

from smarter.common.helpers.console_helpers import formatted_json, formatted_text
from smarter.lib.django.user import User

from .models import Chat, ChatHistory, ChatToolCall, PluginMeta, PluginUsage
from .signals import (
    chat_completion_called,
    chat_completion_plugin_selected,
    chat_completion_tool_call_created,
    chat_invoked,
    chat_response_failure,
    chat_response_success,
)


logger = logging.getLogger(__name__)


@receiver(chat_invoked, dispatch_uid="chat_invoked")
def handle_chat_invoked(sender, **kwargs):
    """Handle chat invoked signal."""

    user = kwargs.get("user")
    user = User.objects.get(id=user.id) if user else None

    data = kwargs.get("data")

    logger.info(
        "%s signal received for chat by user %s with data: %s",
        formatted_text("chat_invoked"),
        user.username if user else "unknown",
        formatted_json(data),
    )


@receiver(chat_completion_called, dispatch_uid="chat_completion_called")
def handle_chat_completion_called(sender, **kwargs):
    """Handle chat completion called signal."""

    chat: Chat = kwargs.get("chat")
    request: dict = kwargs.get("request")
    response: dict = kwargs.get("response")

    logger.info(
        "%s signal received for chat: %s, request: %s, response: %s",
        formatted_text("chat_completion_called"),
        chat.id,
        formatted_json(request),
        formatted_json(response),
    )

    chat_history = ChatHistory(
        chat=chat,
        request=request,
        response=response,
    )
    chat_history.save()


# pylint: disable=W0612


@receiver(chat_completion_tool_call_created, dispatch_uid="chat_completion_tool_call_created")
def handle_chat_completion_tool_call(sender, **kwargs):
    """Handle chat completion tool call signal."""

    chat: Chat = kwargs.get("chat")
    tool_calls: dict = kwargs.get("tool_call")
    plugin: PluginMeta = kwargs.get("plugin")
    request: dict = kwargs.get("request")
    response: dict = kwargs.get("response")

    chat_tool_call_history = ChatToolCall(
        chat=chat,
        plugin=plugin,
        tool_calls=tool_calls,
        request=request,
        response=response,
    )
    chat_tool_call_history.save()


@receiver(chat_completion_plugin_selected, dispatch_uid="chat_completion_plugin_selected")
def handle_chat_completion_plugin_selected(sender, **kwargs):
    """Handle plugin selected signal."""

    plugin: PluginMeta = kwargs.get("plugin")
    chat: Chat = kwargs.get("chat")
    input_text = kwargs.get("input_text")

    logger.info(
        "%s signal received for chat %s, plugin: %s, input_text: %s",
        formatted_text("chat_completion_plugin_selected"),
        chat,
        plugin,
        input_text,
    )

    plugin_selection_history = PluginUsage(
        plugin=plugin,
        chat=chat,
        input_text=input_text,
        event="selected",
    )
    plugin_selection_history.save()


@receiver(post_save, sender=ChatToolCall)
def handle_plugin_selection_history_created(sender, **kwargs):
    """Handle plugin selection history created signal."""

    # FIX NOTE: This is a temporary fix to get tests to pass again
    user = kwargs.get("user")
    data = kwargs.get("data")
    data_dict = model_to_dict(data) if data else {}

    logger.info(
        "%s signal received for chat: %s data: %s",
        formatted_text("chat_completion_plugin_usage_history_created"),
        user.username if user else "unknown",
        formatted_json(data_dict),
    )


# pylint: disable=W0612
@receiver(chat_response_success, dispatch_uid="chat_response_success")
def handle_chat_completion_returned(sender, **kwargs):
    """Handle chat completion returned signal."""

    chat_id = kwargs.get("chat_id")
    request = kwargs.get("request")
    response = kwargs.get("response")

    logger.info(
        "%s signal received for chat: %s,  input_text: %s, response: %s",
        formatted_text("chat_response_success"),
        chat_id,
        request,
        response,
    )
    chat_history = ChatHistory(
        chat=chat_id,
        request=request,
        response=response,
    )
    chat_history.save()


@receiver(chat_response_failure, dispatch_uid="chat_response_failure")
def handle_chat_response_failed(sender, **kwargs):
    """Handle chat completion failed signal."""

    user = kwargs.get("user")
    data = kwargs.get("data")

    logger.info(
        "%s signal received for chat: %s data: %s",
        formatted_text("chat_response_failure"),
        user.username if user else "unknown",
        data,
    )


@receiver(post_save, sender=Chat)
def handle_chat_history_created(sender, **kwargs):
    """Handle chat  history created signal."""

    # FIX NOTE: This is a temporary fix to get tests to pass again
    # we're missing the user and data arguments in the signal
    user = kwargs.get("user")
    data = kwargs.get("data")

    data_dict = model_to_dict(data) if data else {}
    logger.info(
        "%s signal received for chat: %s %s",
        formatted_text("chat_history_created"),
        user.username if user else "unknown",
        formatted_json(data_dict),
    )


@receiver(post_save, sender=ChatToolCall)
def handle_chat_tool_call_history_created(sender, **kwargs):
    """Handle chat completion tool call history created signal."""

    # FIX NOTE: This is a temporary fix to get tests to pass again
    user = kwargs.get("user")
    data = kwargs.get("data")
    data_dict = model_to_dict(data) if data else {}

    logger.info(
        "%s signal received for chat: %s data: %s",
        formatted_text("chat_tool_call_history_created"),
        user.username if user else "unknown",
        formatted_json(data_dict),
    )
