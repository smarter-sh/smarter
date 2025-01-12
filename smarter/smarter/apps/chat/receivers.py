"""Django Signal Receivers for chat app."""

# pylint: disable=W0613,C0115
import logging

from django.db.models.signals import post_save
from django.db.utils import Error as DjangoDbError
from django.dispatch import receiver

from smarter.common.helpers.console_helpers import (
    formatted_json,
    formatted_text,
    formatted_text_green,
)

from .models import Chat, ChatHistory, ChatPluginUsage, ChatToolCall, PluginMeta
from .providers.openai.const import (
    OpenAIMessageKeys,
    OpenAIRequestKeys,
    OpenAIResponseChoices,
    OpenAIResponseChoicesMessage,
    OpenAIResponseKeys,
)
from .signals import (
    chat_completion_called,
    chat_completion_plugin_selected,
    chat_completion_tool_call_created,
    chat_handler_console_output,
    chat_invoked,
    chat_provider_initialized,
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
        "%s for chat %s with data: %s",
        formatted_text("chat_invoked"),
        chat,
        formatted_json(data),
    )


@receiver(chat_completion_called, dispatch_uid="chat_completion_called")
def handle_chat_completion_called(sender, **kwargs):
    """Handle chat completion called signal."""

    chat: Chat = kwargs.get("chat")
    iteration: int = kwargs.get("iteration")
    request: dict = kwargs.get("request")
    response: dict = kwargs.get("response")

    logger.info(
        "%s for chat: %s \nrequest: %s \nresponse: %s",
        formatted_text(f"chat_completion_called for iteration {iteration}"),
        chat,
        formatted_json(request),
        formatted_json(response),
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
                    logger.info(formatted_text_green("Tool calls detected in response."))
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
                        logger.info("Added tool call to messages: %s", tool_called)

    chat_history = ChatHistory(
        chat=chat,
        request=request,
        response=response,
    )
    try:
        chat_history.save()
    except DjangoDbError as exc:
        logger.error("Error saving chat history: %s", exc)


# pylint: disable=W0612


@receiver(chat_completion_tool_call_created, dispatch_uid="chat_completion_tool_call_created")
def handle_chat_completion_tool_call_created(sender, **kwargs):
    """Handle chat completion tool call signal."""

    chat: Chat = kwargs.get("chat")
    tool_calls: list[dict] = kwargs.get("tool_calls")
    request: dict = kwargs.get("request")
    response: dict = kwargs.get("response")

    for tool_call in tool_calls:
        plugin_meta: PluginMeta = tool_call.get("plugin_meta")
        function_name: str = tool_call.get("function_name")
        function_args: str = tool_call.get("function_args")

        try:
            ChatToolCall(
                chat=chat,
                plugin=plugin_meta,
                function_name=function_name,
                function_args=function_args,
                request=request,
                response=response,
            ).save()
        except DjangoDbError as exc:
            logger.error("Error saving chat tool call: %s", exc)


@receiver(chat_completion_plugin_selected, dispatch_uid="chat_completion_plugin_selected")
def handle_chat_completion_plugin_selected(sender, **kwargs):
    """Handle plugin selected signal."""

    plugin: PluginMeta = kwargs.get("plugin")
    chat: Chat = kwargs.get("chat")
    input_text = kwargs.get("input_text")

    logger.info(
        "%s for chat %s, plugin: %s, input_text: %s",
        formatted_text("chat_completion_plugin_selected"),
        chat,
        plugin,
        input_text,
    )

    plugin_selection_history = ChatPluginUsage(
        plugin=plugin,
        chat=chat,
        input_text=input_text,
    )

    try:
        plugin_selection_history.save()
    except DjangoDbError as exc:
        logger.error("Error saving plugin usage: %s", exc)


# pylint: disable=W0612
@receiver(chat_response_success, dispatch_uid="chat_response_success")
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

    try:
        ChatHistory(
            chat=chat,
            request=request,
            response=response,
        ).save()
    except DjangoDbError as exc:
        logger.error("Error saving chat history: %s", exc)

    logger.info(
        "%s for chat %s, \nrequest: %s, \nresponse: %s",
        formatted_text("chat_response_success"),
        chat,
        formatted_json(request),
        formatted_json(response),
    )


@receiver(chat_response_failure, dispatch_uid="chat_response_failure")
def handle_chat_response_failure(sender, **kwargs):
    """Handle chat completion failed signal."""

    exception = kwargs.get("exception")
    chat: Chat = kwargs.get("chat")
    request_meta_data = kwargs.get("request_meta_data")
    first_response = kwargs.get("first_response")
    second_response = kwargs.get("second_response")

    logger.info(
        "%s for chat: %s, request_meta_data: %s, exception: %s",
        formatted_text("chat_response_failure"),
        chat if chat else None,
        formatted_json(request_meta_data),
        exception,
    )
    if first_response:
        logger.info(
            "%s for chat: %s, first_response: %s",
            formatted_text("chat_response_dump"),
            chat if chat else None,
            formatted_json(first_response),
        )
    if second_response:
        logger.info(
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
        logger.info("%s", formatted_text("Chat() record created."))


@receiver(post_save, sender=ChatHistory)
def handle_chat_history_post_save(sender, instance, created, **kwargs):

    if created:
        logger.info("%s", formatted_text("ChatHistory() record created."))


@receiver(post_save, sender=ChatToolCall)
def handle_chat_tool_call_post_save(sender, instance, created, **kwargs):

    if created:
        logger.info("%s", formatted_text("ChatToolCall() record created."))


@receiver(post_save, sender=ChatPluginUsage)
def handle_chat_plugin_usage_post_save(sender, instance, created, **kwargs):

    if created:
        logger.info("%s", formatted_text("ChatPluginUsage() record created."))
