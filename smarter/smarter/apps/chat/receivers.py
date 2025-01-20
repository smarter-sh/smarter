"""Django Signal Receivers for chat app."""

# pylint: disable=W0612,W0613,C0115
import logging

import waffle
from django.db.models.signals import post_save
from django.dispatch import receiver

from smarter.apps.plugin.models import PluginMeta
from smarter.common.const import SMARTER_WAFFLE_SWITCH_CHAT_LOGGING
from smarter.common.helpers.console_helpers import formatted_json, formatted_text

from .models import Chat, ChatHistory, ChatPluginUsage, ChatToolCall
from .signals import (
    chat_completion_plugin_called,
    chat_completion_request,
    chat_completion_response,
    chat_completion_tool_called,
    chat_finished,
    chat_handler_console_output,
    chat_provider_initialized,
    chat_response_failure,
    chat_started,
)
from .tasks import (
    create_chat_history,
    create_chat_plugin_usage,
    create_chat_tool_call_history,
)


logger = logging.getLogger(__name__)


@receiver(chat_started, dispatch_uid="chat_started")
def handle_chat_started(sender, **kwargs):
    """Handle chat started signal."""

    chat: Chat = kwargs.get("chat")
    data = kwargs.get("data")

    logger.info(
        "%s for chat %s",
        formatted_text("chat_started"),
        chat,
    )


@receiver(chat_completion_request, dispatch_uid="chat_completion_request")
def handle_chat_completion_request_sent(sender, **kwargs):
    """Handle chat completion request sent signal."""

    chat: Chat = kwargs.get("chat")
    iteration: int = kwargs.get("iteration")
    request: dict = kwargs.get("request")
    prefix = formatted_text(f"chat_completion_request for iteration {iteration}")

    logger.info(
        "%s for chat: %s",
        prefix,
        chat,
    )

    if waffle.switch_is_active(SMARTER_WAFFLE_SWITCH_CHAT_LOGGING):
        logger.info(
            "%s for chat %s, \nrequest: %s",
            formatted_text("chat_completion_request"),
            chat,
            formatted_json(request),
        )
    else:
        logger.info(
            "%s for chat: %s",
            prefix,
            chat,
        )


@receiver(chat_completion_response, dispatch_uid="chat_completion_response")
def handle_chat_completion_response_received(sender, **kwargs):
    """Handle chat completion called signal."""

    chat: Chat = kwargs.get("chat")
    chat_id = chat.id if chat else None
    iteration: int = kwargs.get("iteration")
    request: dict = kwargs.get("request")
    response: dict = kwargs.get("response")
    messages: list[dict] = kwargs.get("messages")
    prefix = formatted_text(f"chat_completion_response for iteration {iteration}")

    if waffle.switch_is_active(SMARTER_WAFFLE_SWITCH_CHAT_LOGGING):
        logger.info(
            "%s for chat %s, \nrequest: %s, \nresponse: %s",
            formatted_text("chat_completion_response"),
            chat,
            formatted_json(request),
            formatted_json(response),
        )
    else:
        logger.info(
            "%s for chat %s",
            formatted_text("chat_completion_response"),
            chat,
        )


@receiver(chat_completion_plugin_called, dispatch_uid="chat_completion_plugin_called")
def handle_chat_completion_plugin_called(sender, **kwargs):
    """Handle chat completion plugin call signal."""
    chat: Chat = kwargs.get("chat")
    plugin: PluginMeta = kwargs.get("plugin")
    input_text: str = kwargs.get("input_text")

    logger.info(
        "%s for chat %s, \nplugin: %s, \ninput_text: %s",
        formatted_text("chat_completion_plugin_called"),
        chat,
        plugin,
        input_text,
    )
    create_chat_plugin_usage.delay(chat_id=chat.id, plugin_id=plugin.id, input_text=input_text)


@receiver(chat_completion_tool_called, dispatch_uid="chat_completion_tool_called")
def handle_chat_completion_tool_called(sender, **kwargs):
    """Handle chat completion tool call signal."""

    chat: Chat = kwargs.get("chat")
    chat_id = chat.id if chat else None
    plugin_meta_id = None
    function_name: str = kwargs.get("function_name")
    function_args: str = kwargs.get("function_args")
    request: dict = kwargs.get("request")
    response: dict = kwargs.get("response")
    prefix = formatted_text("handle_chat_completion_tool_called()")

    logger.info(
        "%s for chat: %s",
        prefix,
        chat_id,
    )

    create_chat_tool_call_history.delay(chat_id, plugin_meta_id, function_name, function_args, request, response)


# pylint: disable=W0612
@receiver(chat_finished, dispatch_uid="chat_finished")
def handle_chat_response_success(sender, **kwargs):
    """Handle chat completion returned signal."""

    chat: Chat = kwargs.get("chat")
    request: dict = kwargs.get("request")
    response: dict = kwargs.get("response")
    messages: list[dict] = kwargs.get("messages")

    # mcdaniel: add the most recent response to the messages list
    # so that the chatbot can display the most recent response
    # to the user.
    # mcdaniel jan-2025: DEPRECATED: this is no longer needed as the
    # if response:
    #     content: str = None
    #     message: dict = None
    #     response_choices = response.get(OpenAIResponseKeys.CHOICES_KEY)
    #     if response_choices and isinstance(response_choices, list):
    #         for choice in response_choices:
    #             finish_reason = choice.get(OpenAIResponseChoices.FINISH_REASON_KEY, "")
    #             message = choice.get(OpenAIResponseChoices.MESSAGE_KEY, {})
    #             if finish_reason == "stop":
    #                 logger.info("Stop detected in response.")
    #                 content = message.get(OpenAIMessageKeys.MESSAGE_CONTENT_KEY)
    #                 role = message.get(OpenAIMessageKeys.MESSAGE_ROLE_KEY)
    #                 assistant_message = {
    #                     OpenAIMessageKeys.MESSAGE_ROLE_KEY: role,
    #                     OpenAIMessageKeys.MESSAGE_CONTENT_KEY: content,
    #                 }
    #                 request[OpenAIRequestKeys.MESSAGES_KEY].append(assistant_message)
    #                 logger.info("Added assistant response to messages.")

    create_chat_history.delay(chat.id, request, response, messages)

    if waffle.switch_is_active(SMARTER_WAFFLE_SWITCH_CHAT_LOGGING):
        logger.info(
            "%s for chat %s, \nrequest: %s, \nresponse: %s",
            formatted_text("chat_finished"),
            chat,
            formatted_json(request),
            formatted_json(response),
        )
    else:
        logger.info(
            "%s for chat %s",
            formatted_text("chat_finished"),
            chat,
        )


@receiver(chat_response_failure, dispatch_uid="chat_response_failure")
def handle_chat_response_failure(sender, **kwargs):
    """Handle chat completion failed signal."""

    iteration: int = kwargs.get("iteration")
    exception = kwargs.get("exception")
    chat: Chat = kwargs.get("chat")
    request_meta_data = kwargs.get("request_meta_data")
    first_response = kwargs.get("first_response")
    second_response = kwargs.get("second_response")

    logger.error(
        "%s during iteration %s for chat: %s, request_meta_data: %s, exception: %s",
        formatted_text("chat_response_failure"),
        iteration,
        chat if chat else None,
        formatted_json(request_meta_data),
        exception,
    )
    if iteration == 1 and first_response:
        logger.error(
            "%s for chat: %s, first_response: %s",
            formatted_text("chat_response_dump"),
            chat if chat else None,
            formatted_json(first_response),
        )
    if iteration == 2 and second_response:
        logger.error(
            "%s for chat: %s, second_response: %s",
            formatted_text("chat_response_dump"),
            chat if chat else None,
            formatted_json(second_response),
        )


# ------------------------------------------------------------------------------
# chat provider receivers.
# ------------------------------------------------------------------------------
@receiver(chat_provider_initialized, dispatch_uid="chat_provider_initialized")
def handle_chat_provider_initialized(sender, **kwargs):
    """Handle chat provider initialized signal."""

    logger.info(
        "%s with name: %s, base_url: %s",
        formatted_text(f"{sender.__class__.__name__}() initialized"),
        sender.provider,
        sender.base_url,
    )


@receiver(chat_handler_console_output, dispatch_uid="chat_handler_console_output")
def handle_chat_handler_console_output(sender, **kwargs):
    """Handle chat handler() console output signal."""

    message = kwargs.get("message")
    json_obj = kwargs.get("json_obj")

    logger.info(
        "%s: %s\n%s",
        formatted_text(f"{sender.__class__.__name__}().handler() console output"),
        message,
        formatted_json(json_obj),
    )


# ------------------------------------------------------------------------------
# Django model receivers.
# ------------------------------------------------------------------------------


@receiver(post_save, sender=Chat)
def handle_chat_post_save(sender, instance, created, **kwargs):

    if created:
        logger.debug("%s", formatted_text("Chat() record created."))


@receiver(post_save, sender=ChatHistory)
def handle_chat_history_post_save(sender, instance, created, **kwargs):

    if created:
        logger.debug("%s", formatted_text("ChatHistory() record created."))


@receiver(post_save, sender=ChatToolCall)
def handle_chat_tool_call_post_save(sender, instance, created, **kwargs):

    if created:
        logger.debug("%s", formatted_text("ChatToolCall() record created."))


@receiver(post_save, sender=ChatPluginUsage)
def handle_chat_plugin_usage_post_save(sender, instance, created, **kwargs):

    if created:
        logger.debug("%s", formatted_text("ChatPluginUsage() record created."))
