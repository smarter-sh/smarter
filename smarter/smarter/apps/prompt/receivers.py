"""Django Signal Receivers for chat app."""

# pylint: disable=W0612,W0613,C0115
import logging
from typing import Optional, Union

from django.core.handlers.wsgi import WSGIRequest
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from smarter.apps.plugin.models import PluginMeta
from smarter.apps.plugin.signals import plugin_deleting
from smarter.common.helpers.console_helpers import formatted_json, formatted_text
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

from .models import Chat, ChatHistory, ChatPluginUsage, ChatToolCall
from .signals import (
    chat_completion_plugin_called,
    chat_completion_request,
    chat_completion_response,
    chat_completion_tool_called,
    chat_config_invoked,
    chat_finished,
    chat_handler_console_output,
    chat_provider_initialized,
    chat_response_failure,
    chat_session_invoked,
    chat_started,
    llm_tool_presented,
    llm_tool_requested,
    llm_tool_responded,
)
from .tasks import create_chat_history
from .views.views import ChatConfigView, SmarterChatSession


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.RECEIVER_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)
prefix = "smarter.apps.prompt.receivers"


def get_sender_name(sender):
    return f"{sender.__self__.__class__.__name__}.{sender.__name__}({id(sender)})"


@receiver(plugin_deleting, dispatch_uid=prefix + ".plugin_deleting")
def handle_plugin_deleting(sender, plugin, plugin_meta: PluginMeta, **kwargs):
    """Handle plugin deleting signal."""
    logger.info(
        "%s %s is being deleted. Pruning its usage records.",
        formatted_text(f"{prefix}.plugin_deleting"),
        plugin_meta.name,
    )


# chat_session_invoked.send(sender=self.__class__, instance=self, request=request)
@receiver(chat_session_invoked, dispatch_uid="chat_session_invoked")
def handle_chat_session_invoked(sender, instance: SmarterChatSession, request: WSGIRequest, *args, **kwargs):
    """Handle chat session invoked signal."""
    if isinstance(request, WSGIRequest):
        url: str = request.build_absolute_uri()
    else:
        url = "missing request object"

    logger.info("%s.%s %s - %s", formatted_text(f"{prefix}.chat_session_invoked"), sender, instance, url)


@receiver(chat_config_invoked, dispatch_uid="chat_config_invoked")
def handle_chat_config_invoked_(sender, instance: ChatConfigView, request, data: dict, *args, **kwargs):
    """Handle chat config invoked signal."""
    url: Optional[str] = instance.url

    logger.info("%s url=%s", formatted_text(f"{prefix}.chat_config_invoked"), url)


@receiver(chat_started, dispatch_uid="chat_started")
def handle_chat_started(sender, chat: Optional[Chat] = None, data: Optional[dict] = None, **kwargs):
    """Handle chat started signal."""

    sender_name = get_sender_name(sender)
    logger.info(
        "%s for chat %s",
        formatted_text(f"{prefix}.chat_started"),
        chat,
    )


@receiver(chat_completion_request, dispatch_uid="chat_completion_request")
def handle_chat_completion_request_sent(
    sender, chat: Optional[Chat] = None, iteration: int = 0, data: Optional[dict] = None, **kwargs
):
    """Handle chat completion request sent signal."""

    sender_name = get_sender_name(sender)
    this_prefix = formatted_text(f"{prefix}.chat_completion_request for iteration {iteration}")

    logger.info(
        "%s for chat: %s ",
        this_prefix,
        chat,
    )

    logger.info(
        "%s for chat %s, \nrequest: %s",
        this_prefix,
        chat,
        formatted_json(data) if data else None,
    )


@receiver(chat_completion_response, dispatch_uid="chat_completion_response")
def handle_chat_completion_response_received(
    sender,
    chat: Optional[Chat] = None,
    iteration: int = 0,
    request: Optional[Union[dict, list]] = None,
    response: Optional[Union[dict, list]] = None,
    messages: Optional[list] = None,
    **kwargs,
):
    """Handle chat completion called signal."""

    this_prefix = formatted_text(f"{prefix}.chat_completion_response for iteration {iteration}")
    sender_name = get_sender_name(sender)

    logger.info(
        "%s from %s for chat %s, \nrequest: %s, \nresponse: %s",
        this_prefix,
        sender_name,
        chat,
        formatted_json(request) if request else None,
        formatted_json(response) if response else None,
    )


@receiver(chat_completion_plugin_called, dispatch_uid="chat_completion_plugin_called")
def handle_chat_completion_plugin_called(
    sender, chat: Optional[Chat] = None, plugin: Optional[PluginMeta] = None, input_text: Optional[str] = None, **kwargs
):
    """Handle chat completion plugin call signal."""
    sender_name = get_sender_name(sender)

    logger.info(
        "%s for chat %s, \nplugin: %s, \ninput_text: %s",
        formatted_text(f"{prefix}.chat_completion_plugin_called"),
        chat,
        plugin,
        input_text,
    )


@receiver(chat_completion_tool_called, dispatch_uid="chat_completion_tool_called")
def handle_chat_completion_tool_called(
    sender,
    chat: Optional[Chat] = None,
    plugin: Optional[PluginMeta] = None,
    function_name: Optional[str] = None,
    function_args: Optional[str] = None,
    request: Optional[Union[dict, list]] = None,
    response: Optional[Union[dict, list]] = None,
    **kwargs,
):
    """Handle chat completion tool call signal."""

    chat_id = chat.id if chat else None  # type: ignore
    sender_name = get_sender_name(sender)

    logger.info(
        "%s %s %s for chat: %s",
        formatted_text(f"{prefix}.chat_completion_tool_called"),
        function_name,
        function_args,
        chat_id,
    )


# pylint: disable=W0612
@receiver(chat_finished, dispatch_uid="chat_finished")
def handle_chat_response_success(
    sender,
    chat: Optional[Chat] = None,
    request: Optional[Union[dict, list]] = None,
    response: Optional[Union[dict, list]] = None,
    messages: Optional[list] = None,
    **kwargs,
):
    """Handle chat completion returned signal."""

    sender_name = get_sender_name(sender)

    logger.info(
        "%s for chat %s, \nrequest: %s, \nresponse: %s",
        formatted_text(f"{prefix}.chat_finished"),
        chat,
        formatted_json(request) if request else None,
        formatted_json(response) if response else None,
    )
    if chat:
        create_chat_history.delay(chat.id, request, response, messages)  # type: ignore
    else:
        logger.warning(
            "%s No chat object provided, skipping chat history creation", formatted_text(f"{prefix}.chat_finished")
        )


@receiver(chat_response_failure, dispatch_uid="chat_response_failure")
def handle_chat_response_failure(
    sender,
    iteration: int = 0,
    chat: Optional[Chat] = None,
    request_meta_data: Optional[dict] = None,
    exception: Optional[Exception] = None,
    first_iteration: Optional[dict] = None,
    second_iteration: Optional[dict] = None,
    messages: Optional[list] = None,
    stack_trace: Optional[str] = None,
    **kwargs,
):
    """Handle chat completion failed signal."""

    sender_name = get_sender_name(sender)

    logger.error(
        "%s from %s during iteration %s for chat: %s, request_meta_data: %s, exception: %s %s",
        formatted_text(f"{prefix}.chat_response_failure"),
        sender_name,
        iteration,
        chat if chat else None,
        formatted_json(request_meta_data) if request_meta_data else None,
        exception,
        stack_trace if stack_trace else "",
    )
    if iteration == 1 and first_iteration:
        logger.error(
            "%s %s for chat: %s, first_iteration: %s",
            formatted_text(f"{prefix}.chat_response_failure"),
            formatted_text("dump"),
            chat if chat else None,
            formatted_json(first_iteration) if first_iteration else None,
        )
    if iteration == 2 and second_iteration:
        logger.error(
            "%s %s for chat: %s, second_iteration: %s",
            formatted_text(f"{prefix}.chat_response_failure"),
            formatted_text("dump"),
            chat if chat else None,
            formatted_json(second_iteration) if second_iteration else None,
        )


# ------------------------------------------------------------------------------
# chat provider receivers.
# ------------------------------------------------------------------------------
@receiver(chat_provider_initialized, dispatch_uid="chat_provider_initialized")
def handle_chat_provider_initialized(sender, **kwargs):
    """Handle chat provider initialized signal."""

    logger.info(
        "%s with name: %s, base_url: %s",
        formatted_text(f"{prefix}.chat_provider_initialized"),
        sender.provider,
        sender.base_url,
    )


@receiver(chat_handler_console_output, dispatch_uid="chat_handler_console_output")
def handle_chat_handler_console_output(sender, message, json_obj, **kwargs):
    """Handle chat handler() console output signal."""

    logger.info(
        "%s: %s\n%s",
        formatted_text(f"{prefix}.chat_handler_console_output console output"),
        message,
        formatted_json(json_obj),
    )


# ------------------------------------------------------------------------------
# Custom function receivers.
# ------------------------------------------------------------------------------


@receiver(llm_tool_presented, dispatch_uid="llm_tool_presented")
def handle_llm_tool_presented(sender, tool: dict, **kwargs):
    """Handle llm_tool_presented() signal."""

    sender_name = sender.__name__

    logger.info(
        "%s from %s: %s",
        formatted_text(f"{prefix}.llm_tool_presented"),
        sender_name,
        formatted_json(tool),
    )


# llm_tool_requested.send(sender=get_current_weather, location=location, unit=unit)
@receiver(llm_tool_requested, dispatch_uid="llm_tool_requested")
def handle_tool_requested(sender, tool_call: dict, **kwargs):
    """Handle get_current_weather() request signal."""

    sender_name = sender.__name__

    logger.info(
        "%s from %s: %s",
        formatted_text(f"{prefix}.llm_tool_requested"),
        sender_name,
        formatted_json(tool_call),
    )


@receiver(llm_tool_responded, dispatch_uid="llm_tool_responded")
def handle_llm_tool_responded(sender, tool_call: dict, tool_response: dict, **kwargs):
    """Handle get_current_weather() response signal."""
    sender_name = sender.__name__

    logger.info(
        "%s from %s, tool_call: %s, tool_response: %s",
        formatted_text(f"{prefix}.llm_tool_responded"),
        sender_name,
        formatted_json(tool_call),
        formatted_json(tool_response),
    )


# ------------------------------------------------------------------------------
# Django model receivers.
# ------------------------------------------------------------------------------
@receiver(post_save, sender=Chat)
def handle_chat_post_save(sender, instance, created, **kwargs):

    if created:
        logger.info("%s", formatted_text(prefix + ".Chat() record created."))
    else:
        logger.info("%s", formatted_text(prefix + ".Chat() record updated."))


@receiver(post_save, sender=ChatHistory)
def handle_chat_history_post_save(sender, instance, created, **kwargs):

    if created:
        logger.info("%s", formatted_text(prefix + ".ChatHistory() record created."))
    else:
        logger.info("%s", formatted_text(prefix + ".ChatHistory() record updated."))


@receiver(post_save, sender=ChatToolCall)
def handle_chat_tool_call_post_save(sender, instance, created, **kwargs):

    if created:
        logger.info("%s", formatted_text(prefix + ".ChatToolCall() record created."))
    else:
        logger.info("%s", formatted_text(prefix + ".ChatToolCall() record updated."))


@receiver(post_save, sender=ChatPluginUsage)
def handle_chat_plugin_usage_post_save(sender, instance, created, **kwargs):

    if created:
        logger.info("%s", formatted_text(prefix + ".ChatPluginUsage() record created."))
    else:
        logger.info("%s", formatted_text(prefix + ".ChatPluginUsage() record updated."))


@receiver(pre_delete, sender=ChatToolCall)
def handle_chat_tool_call_post_delete(sender, instance, **kwargs):
    """Handle ChatToolCall post delete signal."""
    logger.info("%s %s deleting", formatted_text(prefix + ".ChatToolCall() record"), instance)


@receiver(pre_delete, sender=ChatPluginUsage)
def handle_chat_plugin_usage_post_delete(sender, instance, **kwargs):
    """Handle ChatPluginUsage post delete signal."""
    logger.info("%s %s deleting", formatted_text(prefix + ".ChatPluginUsage() record"), instance)
