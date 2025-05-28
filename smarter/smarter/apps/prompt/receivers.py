"""Django Signal Receivers for chat app."""

# pylint: disable=W0612,W0613,C0115
import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from smarter.apps.plugin.models import PluginMeta
from smarter.common.const import SmarterWaffleSwitches
from smarter.common.helpers.console_helpers import formatted_json, formatted_text
from smarter.lib.django import waffle

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
    get_current_weather_request,
    get_current_weather_response,
)
from .tasks import create_chat_history
from .views import ChatConfigView, SmarterChatSession


logger = logging.getLogger(__name__)


# chat_session_invoked.send(sender=self.__class__, instance=self, request=request)
@receiver(chat_session_invoked, dispatch_uid="chat_session_invoked")
def handle_chat_session_invoked(sender, instance: SmarterChatSession, request, *args, **kwargs):
    """Handle chat session invoked signal."""
    url: str = None
    if request is not None:
        url = request.build_absolute_uri() if hasattr(request, "build_absolute_uri") else None

    logger.info(
        "%s.%s %s - %s", formatted_text("smarter.apps.prompt.receivers.chat_session_invoked"), sender, instance, url
    )


@receiver(chat_config_invoked, dispatch_uid="chat_config_invoked")
def handle_chat_config_invoked_(sender, instance: ChatConfigView, request, data: dict, *args, **kwargs):
    """Handle chat config invoked signal."""
    url: str = sender.url

    logger.info("%s url=%s", formatted_text("smarter.apps.prompt.receivers.chat_config_invoked"), url)


def get_sender_name(sender):
    return f"{sender.__self__.__class__.__name__}.{sender.__name__}({id(sender)})"


@receiver(chat_started, dispatch_uid="chat_started")
def handle_chat_started(sender, **kwargs):
    """Handle chat started signal."""

    chat: Chat = kwargs.get("chat")
    data = kwargs.get("data")

    sender_name = get_sender_name(sender)
    logger.info(
        "signal received from %s %s for chat %s",
        sender_name,
        formatted_text("chat_started"),
        chat,
    )


@receiver(chat_completion_request, dispatch_uid="chat_completion_request")
def handle_chat_completion_request_sent(sender, **kwargs):
    """Handle chat completion request sent signal."""

    chat: Chat = kwargs.get("chat")
    iteration: int = kwargs.get("iteration")
    request: dict = kwargs.get("request")
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
def handle_chat_completion_response_received(sender, **kwargs):
    """Handle chat completion called signal."""

    chat: Chat = kwargs.get("chat")
    chat_id = chat.id if chat else None
    iteration: int = kwargs.get("iteration")
    request: dict = kwargs.get("request")
    response: dict = kwargs.get("response")
    messages: list[dict] = kwargs.get("messages")
    prefix = formatted_text(f"chat_completion_response for iteration {iteration}")
    sender_name = get_sender_name(sender)

    if waffle.switch_is_active(SmarterWaffleSwitches.CHAT_LOGGING):
        logger.info(
            "signal received from %s %s for chat %s, \nrequest: %s, \nresponse: %s",
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
def handle_chat_completion_plugin_called(sender, **kwargs):
    """Handle chat completion plugin call signal."""
    chat: Chat = kwargs.get("chat")
    plugin: PluginMeta = kwargs.get("plugin")
    input_text: str = kwargs.get("input_text")
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
    sender_name = get_sender_name(sender)

    logger.info(
        "signal received from %s %s for chat: %s",
        sender_name,
        prefix,
        chat_id,
    )


# pylint: disable=W0612
@receiver(chat_finished, dispatch_uid="chat_finished")
def handle_chat_response_success(sender, **kwargs):
    """Handle chat completion returned signal."""

    chat: Chat = kwargs.get("chat")
    request: dict = kwargs.get("request")
    response: dict = kwargs.get("response")
    messages: list[dict] = kwargs.get("messages")
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
    create_chat_history.delay(chat.id, request, response, messages)


@receiver(chat_response_failure, dispatch_uid="chat_response_failure")
def handle_chat_response_failure(sender, **kwargs):
    """Handle chat completion failed signal."""

    iteration: int = kwargs.get("iteration")
    exception = kwargs.get("exception")
    chat: Chat = kwargs.get("chat")
    request_meta_data = kwargs.get("request_meta_data")
    first_iteration = kwargs.get("first_iteration")
    second_iteration = kwargs.get("second_iteration")
    messages = kwargs.get("messages")
    sender_name = get_sender_name(sender)

    logger.error(
        "%s signal received from %s during iteration %s for chat: %s, request_meta_data: %s, exception: %s",
        formatted_text("chat_response_failure"),
        sender_name,
        iteration,
        chat if chat else None,
        formatted_json(request_meta_data),
        exception,
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


# get_current_weather_request.send(sender=get_current_weather, location=location, unit=unit)
@receiver(get_current_weather_request, dispatch_uid="get_current_weather_request")
def handle_get_current_weather_request(sender, **kwargs):
    """Handle get_current_weather() request signal."""

    location = kwargs.get("location")
    unit = kwargs.get("unit")
    sender_name = sender.__name__

    logger.info(
        "signal received from %s %s for location: %s, unit: %s",
        sender_name,
        formatted_text("get_current_weather_request"),
        location,
        unit,
    )


@receiver(get_current_weather_response, dispatch_uid="get_current_weather_response")
def handle_get_current_weather_response(sender, **kwargs):
    """Handle get_current_weather() response signal."""

    location = kwargs.get("location")
    unit = kwargs.get("unit")
    latitude = kwargs.get("latitude")
    longitude = kwargs.get("longitude")
    address = kwargs.get("address")
    params = kwargs.get("params")
    geocode_result = kwargs.get("geocode_result")
    hourly_json = kwargs.get("hourly_json")

    sender_name = sender.__name__

    logger.info(
        "signal received from %s %s for location: %s, unit: %s, latitude: %s, longitude: %s, address: %s",
        sender_name,
        formatted_text("get_current_weather_response"),
        location,
        unit,
        latitude,
        longitude,
        address,
    )
    logger.info(
        "response: %s, params: %s, geocode_result: %s",
        formatted_json(hourly_json),
        formatted_json(params),
        formatted_json(geocode_result),
    )
