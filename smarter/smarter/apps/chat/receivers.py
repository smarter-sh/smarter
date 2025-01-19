"""Django Signal Receivers for chat app."""

# pylint: disable=W0612,W0613,C0115
import logging

import waffle
from django.db.models.signals import post_save
from django.dispatch import receiver

from smarter.apps.plugin.models import PluginMeta
from smarter.common.const import SMARTER_WAFFLE_SWITCH_CHAT_LOGGING
from smarter.common.helpers.console_helpers import (
    formatted_json,
    formatted_text,
    formatted_text_green,
)

from .models import Chat, ChatHistory, ChatPluginUsage, ChatToolCall
from .providers.const import (
    OpenAIMessageKeys,
    OpenAIRequestKeys,
    OpenAIResponseChoices,
    OpenAIResponseChoicesMessage,
    OpenAIResponseKeys,
)
from .signals import (
    chat_completion_request,
    chat_completion_response,
    chat_completion_tool_called,
    chat_handler_console_output,
    chat_invocation_finished,
    chat_invocation_start,
    chat_provider_initialized,
    chat_response_failure,
)
from .tasks import create_chat_history, create_chat_tool_call_history


logger = logging.getLogger(__name__)


@receiver(chat_invocation_start, dispatch_uid="chat_invocation_start")
def handle_chat_invoked(sender, **kwargs):
    """Handle chat invoked signal."""

    chat: Chat = kwargs.get("chat")
    data = kwargs.get("data")

    logger.info(
        "%s for chat %s",
        formatted_text("chat_invocation_start"),
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
    prefix = formatted_text(f"chat_completion_response for iteration {iteration}")

    logger.info(
        "%s for chat: %s",
        prefix,
        chat,
    )

    # mcdaniel: add the most recent response to the messages list
    # so that the chatbot can display the most recent response
    # to the user.
    if response:
        message: dict = None
        response_choices = response.get(OpenAIResponseKeys.CHOICES_KEY)
        if response_choices and isinstance(response_choices, list):
            for choice in response_choices:
                finish_reason = choice.get(OpenAIResponseChoices.FINISH_REASON_KEY, "")
                message = choice.get(OpenAIResponseChoices.MESSAGE_KEY, {})
                if finish_reason == OpenAIResponseChoicesMessage.TOOL_CALLS_KEY:
                    logger.info("%s %s", prefix, formatted_text_green("Tool calls detected in response."))
                    tool_calls = message.get(OpenAIResponseChoicesMessage.TOOL_CALLS_KEY)
                    for tool_call in tool_calls:
                        function = tool_call.get("function")
                        function_name = function.get("name")
                        function_args = function.get("arguments", "")
                        tool_called = {
                            OpenAIMessageKeys.MESSAGE_ROLE_KEY: OpenAIMessageKeys.SMARTER_MESSAGE_KEY,
                            OpenAIMessageKeys.MESSAGE_CONTENT_KEY: f"Tool call: {function_name}({function_args})",
                        }
                        request[OpenAIRequestKeys.MESSAGES_KEY].append(tool_called)
                        logger.info("%s Added tool call to messages: %s", prefix, tool_called)

        create_chat_history(chat_id, request, response)


@receiver(chat_completion_tool_called, dispatch_uid="chat_completion_tool_called")
def handle_chat_completion_tool_called(sender, **kwargs):
    """Handle chat completion tool call signal."""

    chat: Chat = kwargs.get("chat")
    chat_id = chat.id if chat else None
    tool_calls: list[dict] = kwargs.get("tool_calls")
    request: dict = kwargs.get("request")
    response: dict = kwargs.get("response")
    prefix = formatted_text("handle_chat_completion_tool_called()")

    logger.info(
        "%s for chat: %s",
        prefix,
        chat_id,
    )

    for tool_call in tool_calls:
        plugin_meta: PluginMeta = tool_call.get("plugin_meta")
        plugin_meta_id: int = plugin_meta.id if plugin_meta else None
        function_name: str = tool_call.get("function_name")
        function_args: str = tool_call.get("function_args")
        create_chat_tool_call_history(chat_id, plugin_meta_id, function_name, function_args, request, response)


# pylint: disable=W0612
@receiver(chat_invocation_finished, dispatch_uid="chat_invocation_finished")
def handle_chat_response_success(sender, **kwargs):
    """Handle chat completion returned signal."""

    chat: Chat = kwargs.get("chat")
    request: dict = kwargs.get("request")
    response: dict = kwargs.get("response")

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

    create_chat_history(chat.id, request, response)

    if waffle.switch_is_active(SMARTER_WAFFLE_SWITCH_CHAT_LOGGING):
        logger.info(
            "%s for chat %s, \nrequest: %s, \nresponse: %s",
            formatted_text("chat_invocation_finished"),
            chat,
            formatted_json(request),
            formatted_json(response),
        )
    else:
        logger.info(
            "%s for chat %s",
            formatted_text("chat_invocation_finished"),
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
        sender.name,
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
