"""Django Signal Receivers for chat app."""

# pylint: disable=W0613,C0115
import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from smarter.common.helpers.console_helpers import formatted_json, formatted_text

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

    chat: Chat = kwargs.get("chat")

    data = kwargs.get("data")

    logger.info(
        "%s signal received for chat %s with data: %s",
        formatted_text("chat_invoked"),
        chat.id,
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
    tool_call: dict = kwargs.get("tool_call")
    plugin: PluginMeta = kwargs.get("plugin")
    request: dict = kwargs.get("request")
    response: dict = kwargs.get("response")

    logger.info("request: %s", request)
    logger.info("response: %s", response)

    chat_tool_call_history = ChatToolCall(
        chat=chat,
        plugin=plugin,
        tool_call=tool_call,
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
    )
    plugin_selection_history.save()


# pylint: disable=W0612
@receiver(chat_response_success, dispatch_uid="chat_response_success")
def handle_chat_completion_returned(sender, **kwargs):
    """Handle chat completion returned signal."""

    chat: Chat = kwargs.get("chat")
    request: dict = kwargs.get("request")
    response: dict = kwargs.get("response")

    logger.info(
        "%s signal received for chat: %s,  input_text: %s, response: %s",
        formatted_text("chat_response_success"),
        chat.id,
        request,
        response,
    )
    ChatHistory(
        chat=chat,
        request=request,
        response=response,
    ).save()


@receiver(chat_response_failure, dispatch_uid="chat_response_failure")
def handle_chat_response_failed(sender, **kwargs):
    """Handle chat completion failed signal."""

    exception = kwargs.get("exception")
    chat: Chat = kwargs.get("chat")
    request_meta_data = kwargs.get("request_meta_data")

    logger.info(
        "%s signal received for chat: %s, request_meta_data: %s, exception: %s",
        formatted_text("chat_response_failure"),
        chat.id,
        formatted_json(request_meta_data),
        exception,
    )


# ------------------------------------------------------------------------------
# Django model receivers.
# ------------------------------------------------------------------------------


@receiver(post_save, sender=Chat)
def handle_chat_created(sender, **kwargs):

    logger.info("%s", formatted_text("Chat() record created."))


@receiver(post_save, sender=ChatHistory)
def handle_chat_history_created(sender, **kwargs):

    logger.info("%s", formatted_text("ChatHistory() record created."))


@receiver(post_save, sender=ChatToolCall)
def handle_chat_tool_call_created(sender, **kwargs):

    logger.info("%s", formatted_text("ChatToolCall() record created."))


@receiver(post_save, sender=PluginUsage)
def handle_plugin_usage_created(sender, **kwargs):

    logger.info("%s", formatted_text("PluginUsage() record created."))
