"""Django Signal Receivers for chat app."""

# pylint: disable=W0612,W0613,C0115
import json
import logging
from typing import Union

from django.core.handlers.wsgi import WSGIRequest
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from smarter.apps.plugin.models import PluginMeta
from smarter.apps.plugin.signals import plugin_deleting
from smarter.common.helpers.console_helpers import formatted_json, formatted_text
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches

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
from .views import ChatConfigView, SmarterChatSession


logger = logging.getLogger(__name__)
prefix = "smarter.apps.prompt.receivers"


@receiver(plugin_deleting, dispatch_uid=prefix + ".plugin_deleting")
def handle_plugin_deleting(sender, plugin, plugin_meta: PluginMeta, **kwargs):
    """Handle plugin deleting signal."""
    logger.info(
        "%s %s is being deleted. Pruning its usage records.",
        formatted_text(f"{prefix}.plugin_deleting"),
        plugin_meta.name,
    )

    ChatPluginUsage.objects.filter(plugin=plugin_meta).delete()
    logger.info(
        "%s %s ChatPluginUsage records deleted.",
        formatted_text(f"{prefix}.plugin_deleting"),
        plugin_meta.name,
    )
    ChatToolCall.objects.filter(plugin=plugin_meta).delete()
    logger.info(
        "%s %s ChatToolCall records deleted.",
        formatted_text(f"{prefix}.plugin_deleting"),
        plugin_meta.name,
    )
    logger.info(
        "%s %s has been pruned from all prompt usage records.",
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
    url: str = instance.url

    logger.info("%s url=%s", formatted_text(f"{prefix}.chat_config_invoked"), url)


def get_sender_name(sender):
    return f"{sender.__self__.__class__.__name__}.{sender.__name__}({id(sender)})"


@receiver(chat_started, dispatch_uid="chat_started")
def handle_chat_started(sender, chat: Chat, data: dict, **kwargs):
    """Handle chat started signal."""

    sender_name = get_sender_name(sender)
    logger.info(
        "signal received from %s %s for chat %s",
        sender_name,
        formatted_text("chat_started"),
        chat,
    )


@receiver(chat_completion_request, dispatch_uid="chat_completion_request")
def handle_chat_completion_request_sent(sender, chat: Chat, iteration: int, request: dict, **kwargs):
    """Handle chat completion request sent signal."""

    sender_name = get_sender_name(sender)
    prefix = formatted_text(f"chat_completion_request for iteration {iteration}")

    logger.info(
        "signal received from %s %s for chat: %s ",
        sender_name,
        prefix,
        chat,
    )

    if waffle.switch_is_active(SmarterWaffleSwitches.CHAT_LOGGING):
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
def handle_chat_completion_response_received(
    sender,
    chat: Chat,
    iteration: int,
    request: Union[dict, list],
    response: Union[dict, list],
    messages: list,
    **kwargs,
):
    """Handle chat completion called signal."""

    this_prefix = formatted_text(f"chat_completion_response for iteration {iteration}")
    sender_name = get_sender_name(sender)

    if waffle.switch_is_active(SmarterWaffleSwitches.CHAT_LOGGING):
        logger.info(
            "%s %s signal received from %s %s for chat %s, \nrequest: %s, \nresponse: %s",
            prefix,
            this_prefix,
            sender_name,
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
def handle_chat_completion_plugin_called(sender, chat: Chat, plugin: PluginMeta, input_text: str, **kwargs):
    """Handle chat completion plugin call signal."""
    sender_name = get_sender_name(sender)

    logger.info(
        "signal received from %s %s for chat %s, \nplugin: %s, \ninput_text: %s",
        sender_name,
        formatted_text("chat_completion_plugin_called"),
        chat,
        plugin,
        input_text,
    )


@receiver(chat_completion_tool_called, dispatch_uid="chat_completion_tool_called")
def handle_chat_completion_tool_called(
    sender,
    chat: Chat,
    plugin: PluginMeta,
    function_name: str,
    function_args: str,
    request: Union[dict, list],
    response: Union[dict, list],
    **kwargs,
):
    """Handle chat completion tool call signal."""

    chat_id = chat.id if chat else None  # type: ignore
    this_prefix = formatted_text("handle_chat_completion_tool_called()")
    sender_name = get_sender_name(sender)

    logger.info(
        "signal received from %s %s %s %s %s for chat: %s",
        sender_name,
        prefix,
        this_prefix,
        function_name,
        function_args,
        chat_id,
    )


# pylint: disable=W0612
@receiver(chat_finished, dispatch_uid="chat_finished")
def handle_chat_response_success(
    sender, chat: Chat, request: Union[dict, list], response: Union[dict, list], messages: list, **kwargs
):
    """Handle chat completion returned signal."""

    sender_name = get_sender_name(sender)

    if waffle.switch_is_active(SmarterWaffleSwitches.CHAT_LOGGING):
        logger.info(
            "signal received from %s %s for chat %s, \nrequest: %s, \nresponse: %s",
            sender_name,
            formatted_text("chat_finished"),
            chat,
            formatted_json(request),
            formatted_json(response),
        )
    else:
        logger.info(
            "signal received from %s %s for chat %s",
            sender_name,
            formatted_text("chat_finished"),
            chat,
        )
    create_chat_history.delay(chat.id, request, response, messages)  # type: ignore


@receiver(chat_response_failure, dispatch_uid="chat_response_failure")
def handle_chat_response_failure(
    sender,
    iteration: int,
    chat: Chat,
    request_meta_data: dict,
    exception: Exception,
    first_iteration: dict,
    second_iteration: dict,
    messages: list,
    stack_trace: str,
    **kwargs,
):
    """Handle chat completion failed signal."""

    sender_name = get_sender_name(sender)

    logger.error(
        "%s signal received from %s during iteration %s for chat: %s, request_meta_data: %s, exception: %s %s",
        formatted_text("chat_response_failure"),
        sender_name,
        iteration,
        chat if chat else None,
        formatted_json(request_meta_data),
        exception,
        stack_trace if stack_trace else "",
    )
    logger.error("chat_response_failure %s %s", formatted_text("messages dump:"), formatted_json(messages))
    if iteration == 1 and first_iteration:
        logger.error(
            "%s for chat: %s, first_iteration: %s",
            formatted_text("dump"),
            chat if chat else None,
            formatted_json(first_iteration),
        )
    if iteration == 2 and second_iteration:
        logger.error(
            "%s for chat: %s, second_iteration: %s",
            formatted_text("dump"),
            chat if chat else None,
            formatted_json(second_iteration),
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
def handle_chat_handler_console_output(sender, message, json_obj, **kwargs):
    """Handle chat handler() console output signal."""

    logger.info(
        "%s: %s\n%s",
        formatted_text(f"{sender.__class__.__name__}().handler() console output"),
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
        "signal received from %s %s: %s",
        sender_name,
        formatted_text("llm_tool_presented"),
        formatted_json(tool),
    )


# llm_tool_requested.send(sender=get_current_weather, location=location, unit=unit)
@receiver(llm_tool_requested, dispatch_uid="llm_tool_requested")
def handle_get_current_weather_request(sender, **kwargs):
    """Handle get_current_weather() request signal."""

    location = kwargs.get("location")
    unit = kwargs.get("unit")
    sender_name = sender.__name__

    logger.info(
        "signal received from %s %s for location: %s, unit: %s",
        sender_name,
        formatted_text("llm_tool_requested"),
        location,
        unit,
    )


@receiver(llm_tool_responded, dispatch_uid="llm_tool_responded")
def handle_llm_tool_responded(sender, **kwargs):
    """Handle get_current_weather() response signal."""

    location = kwargs.get("location")
    unit = kwargs.get("unit")
    latitude = kwargs.get("latitude")
    longitude = kwargs.get("longitude")
    address = kwargs.get("address")
    params = kwargs.get("params")
    geocode_result = kwargs.get("geocode_result")
    hourly_json = kwargs.get("hourly_json")
    hourly_json = json.loads(hourly_json) if isinstance(hourly_json, str) else hourly_json

    sender_name = sender.__name__

    logger.info(
        "signal received from %s %s for location: %s, unit: %s, latitude: %s, longitude: %s, address: %s",
        sender_name,
        formatted_text("llm_tool_responded"),
        location,
        unit,
        latitude,
        longitude,
        address,
    )
    logger.info(
        "response: %s, params: %s, geocode_result: %s",
        formatted_json(hourly_json),  # type: ignore
        formatted_json(params),  # type: ignore
        formatted_json(geocode_result),  # type: ignore
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


@receiver(pre_delete, sender=ChatToolCall)
def handle_chat_tool_call_post_delete(sender, instance, **kwargs):
    """Handle ChatToolCall post delete signal."""
    logger.info("%s %s deleting", formatted_text("ChatToolCall() record"), instance)


@receiver(pre_delete, sender=ChatPluginUsage)
def handle_chat_plugin_usage_post_delete(sender, instance, **kwargs):
    """Handle ChatPluginUsage post delete signal."""
    logger.info("%s %s deleting", formatted_text("ChatPluginUsage() record"), instance)
