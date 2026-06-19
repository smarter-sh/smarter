"""Django Signal Receivers for prompt app."""

# pylint: disable=W0612,W0613,C0115
import logging
from typing import Any, Optional, Union

from django.core.handlers.asgi import ASGIRequest
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from openai.types.chat.chat_completion import ChatCompletion

from smarter.apps.plugin.models import PluginMeta
from smarter.apps.plugin.signals import plugin_deleting
from smarter.common.helpers.console_helpers import formatted_json, formatted_text
from smarter.common.utils import request_to_json
from smarter.lib.django import waffle
from smarter.lib.django.request import SmarterRequestType
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

from .models import Prompt, PromptHistory, PromptPluginUsage, PromptToolCall
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
from .tasks import create_prompt_history
from .views.detailviews import PromptConfigView, SmarterPromptSession


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.RECEIVER_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)
prefix = "smarter.apps.prompt.receivers"


def get_sender_name(sender: Any) -> str:
    """
    Get a readable name for the sender of a signal, handling both class and.

    instance methods.
    """
    if isinstance(sender, type):
        return f"{sender.__name__}({id(sender)})"
    return f"{sender.__self__.__class__.__name__}.{sender.__name__}({id(sender)})"


@receiver(plugin_deleting, dispatch_uid=prefix + ".plugin_deleting")
def handle_plugin_deleting(sender, plugin, plugin_meta: PluginMeta, **kwargs):
    """Handle plugin deleting signal."""
    logger.info(
        "%s by %s %s is being deleted. Pruning its usage records.",
        formatted_text(f"{prefix}.plugin_deleting"),
        get_sender_name(sender),
        plugin_meta.name,
    )


# chat_session_invoked.send(sender=self.__class__, instance=self, request=request)
@receiver(chat_session_invoked, dispatch_uid="chat_session_invoked")
def handle_chat_session_invoked(sender, instance: SmarterPromptSession, request: ASGIRequest, *args, **kwargs):
    """Handle prompt session invoked signal."""
    if isinstance(request, ASGIRequest):
        url: str = request.build_absolute_uri()
    else:
        url = "missing request object"

    logger.info(
        "%s by %s %s - %s", formatted_text(f"{prefix}.chat_session_invoked"), get_sender_name(sender), instance, url
    )


@receiver(chat_config_invoked, dispatch_uid="chat_config_invoked")
def handle_chat_config_invoked_(
    sender, instance: PromptConfigView, request: SmarterRequestType, data: dict, *args, **kwargs
):
    """
    Handle prompt config invoked signal.

    chat_config_invoked.send(sender=self.__class__, instance=self, request=self.smarter_request, data=retval)
    """
    url: Optional[str] = instance.url

    logger.info("%s by %s url=%s", formatted_text(f"{prefix}.chat_config_invoked"), get_sender_name(sender), url)
    logger.debug("%s data: %s", formatted_text(f"{prefix}.chat_config_invoked"), formatted_json(data))


@receiver(chat_started, dispatch_uid="chat_started")
def handle_chat_started(sender, prompt: Optional[Prompt] = None, data: Optional[dict] = None, **kwargs):
    """Handle prompt started signal."""

    sender_name = get_sender_name(sender)
    logger.info(
        "%s by %s for prompt %s",
        formatted_text(f"{prefix}.chat_started"),
        sender_name,
        prompt,
    )


@receiver(chat_completion_request, dispatch_uid="chat_completion_request")
def handle_chat_completion_request_sent(
    sender, prompt: Optional[Prompt] = None, iteration: int = 0, data: Optional[dict] = None, **kwargs
):
    """Handle prompt completion request sent signal."""

    sender_name = get_sender_name(sender)
    this_prefix = formatted_text(f"{prefix}.chat_completion_request for iteration {iteration}")

    logger.info(
        "%s by %s for prompt: %s ",
        this_prefix,
        sender_name,
        prompt,
    )

    logger.info(
        "%s for prompt %s, \nrequest: %s",
        this_prefix,
        prompt,
        formatted_json(data) if data else None,
    )


@receiver(chat_completion_response, dispatch_uid="chat_completion_response")
def handle_chat_completion_response_received(
    sender,
    prompt: Optional[Prompt] = None,
    iteration: int = 0,
    request: Optional[Union[ASGIRequest, dict, list]] = None,
    response: Optional[Union[ChatCompletion, dict, list]] = None,
    messages: Optional[list] = None,
    **kwargs,
):
    """Handle prompt completion called signal."""
    request_data = request_to_json(request) if request else None
    if isinstance(request_data, (dict, list)):
        formatted_request_data = formatted_json(dict(request_data) if isinstance(request_data, dict) else request_data)
    else:
        formatted_request_data = str(request_data)

    if isinstance(response, ChatCompletion):
        response_data = response.model_dump()
    else:
        response_data = response

    this_prefix = formatted_text(f"{prefix}.chat_completion_response for iteration {iteration}")
    sender_name = get_sender_name(sender)

    logger.info(
        "%s from %s for prompt %s, \nrequest: %s, \nresponse: %s",
        this_prefix,
        sender_name,
        prompt,
        formatted_request_data,
        formatted_json(response_data) if response_data else None,
    )


@receiver(chat_completion_plugin_called, dispatch_uid="chat_completion_plugin_called")
def handle_chat_completion_plugin_called(
    sender,
    prompt: Optional[Prompt] = None,
    plugin: Optional[PluginMeta] = None,
    input_text: Optional[str] = None,
    **kwargs,
):
    """Handle prompt completion plugin call signal."""

    logger.info(
        "%s by %s for prompt %s, \nplugin: %s, \ninput_text: %s",
        formatted_text(f"{prefix}.chat_completion_plugin_called"),
        get_sender_name(sender),
        prompt,
        plugin,
        input_text,
    )


@receiver(chat_completion_tool_called, dispatch_uid="chat_completion_tool_called")
def handle_chat_completion_tool_called(
    sender,
    prompt: Optional[Prompt] = None,
    plugin: Optional[PluginMeta] = None,
    function_name: Optional[str] = None,
    function_args: Optional[str] = None,
    request: Optional[Union[dict, list]] = None,
    response: Optional[Union[dict, list]] = None,
    **kwargs,
):
    """Handle prompt completion tool call signal."""

    chat_id = prompt.id if prompt else None  # type: ignore

    logger.info(
        "%s by %s %s %s for prompt: %s",
        formatted_text(f"{prefix}.chat_completion_tool_called"),
        get_sender_name(sender),
        function_name,
        function_args,
        chat_id,
    )


# pylint: disable=W0612
@receiver(chat_finished, dispatch_uid="chat_finished")
def handle_chat_response_success(
    sender,
    prompt: Optional[Prompt] = None,
    request: Optional[Union[ASGIRequest, dict, list]] = None,
    response: Optional[Union[ChatCompletion, dict, list]] = None,
    messages: Optional[list] = None,
    **kwargs,
):
    """Handle prompt completion returned signal."""

    request_data = request_to_json(request) if request else None
    if isinstance(request_data, (dict, list)):
        formatted_request_data = formatted_json(dict(request_data) if isinstance(request_data, dict) else request_data)
    else:
        formatted_request_data = str(request_data)

    if isinstance(response, ChatCompletion):
        response_data = response.model_dump()
    else:
        response_data = response

    logger.info(
        "%s for prompt %s, sent by %s \nrequest: %s, \nresponse: %s",
        formatted_text(f"{prefix}.chat_finished"),
        prompt,
        get_sender_name(sender),
        formatted_request_data,
        formatted_json(response_data) if response_data else None,
    )
    if prompt:
        create_prompt_history.delay(prompt.id, request_data, response_data, messages)  # type: ignore
    else:
        logger.warning(
            "%s No prompt object provided, skipping prompt history creation", formatted_text(f"{prefix}.chat_finished")
        )


@receiver(chat_response_failure, dispatch_uid="chat_response_failure")
def handle_chat_response_failure(
    sender,
    iteration: int = 0,
    prompt: Optional[Prompt] = None,
    request_meta_data: Optional[dict] = None,
    exception: Optional[Exception] = None,
    first_iteration: Optional[dict] = None,
    second_iteration: Optional[dict] = None,
    messages: Optional[list] = None,
    stack_trace: Optional[str] = None,
    **kwargs,
):
    """Handle prompt completion failed signal."""

    sender_name = get_sender_name(sender)

    logger.error(
        "%s from %s during iteration %s for prompt: %s, request_meta_data: %s, exception: %s %s",
        formatted_text(f"{prefix}.chat_response_failure"),
        sender_name,
        iteration,
        prompt if prompt else None,
        formatted_json(request_meta_data) if request_meta_data else None,
        exception,
        stack_trace if stack_trace else "",
    )
    if iteration == 1 and first_iteration:
        logger.error(
            "%s %s for prompt: %s, first_iteration: %s",
            formatted_text(f"{prefix}.chat_response_failure"),
            formatted_text("dump"),
            prompt if prompt else None,
            formatted_json(first_iteration) if first_iteration else None,
        )
    if iteration == 2 and second_iteration:
        logger.error(
            "%s %s for prompt: %s, second_iteration: %s",
            formatted_text(f"{prefix}.chat_response_failure"),
            formatted_text("dump"),
            prompt if prompt else None,
            formatted_json(second_iteration) if second_iteration else None,
        )


# ------------------------------------------------------------------------------
# prompt provider receivers.
# ------------------------------------------------------------------------------
@receiver(chat_provider_initialized, dispatch_uid="chat_provider_initialized")
def handle_chat_provider_initialized(sender, **kwargs):
    """Handle prompt provider initialized signal."""

    logger.info(
        "%s with name: %s, base_url: %s",
        formatted_text(f"{prefix}.chat_provider_initialized"),
        sender.provider,
        sender.base_url,
    )


@receiver(chat_handler_console_output, dispatch_uid="chat_handler_console_output")
def handle_chat_handler_console_output(sender, message, json_obj, **kwargs):
    """Handle prompt handler() console output signal."""

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
@receiver(post_save, sender=Prompt)
def handle_chat_post_save(sender, instance, created, **kwargs):

    if created:
        logger.info("%s", formatted_text(prefix + ".Prompt() record created."))
    else:
        logger.info("%s", formatted_text(prefix + ".Prompt() record updated."))


@receiver(post_save, sender=PromptHistory)
def handle_chat_history_post_save(sender, instance, created, **kwargs):

    if created:
        logger.info("%s", formatted_text(prefix + ".PromptHistory() record created."))
    else:
        logger.info("%s", formatted_text(prefix + ".PromptHistory() record updated."))


@receiver(post_save, sender=PromptToolCall)
def handle_chat_tool_call_post_save(sender, instance, created, **kwargs):

    if created:
        logger.info("%s", formatted_text(prefix + ".PromptToolCall() record created."))
    else:
        logger.info("%s", formatted_text(prefix + ".PromptToolCall() record updated."))


@receiver(post_save, sender=PromptPluginUsage)
def handle_chat_plugin_usage_post_save(sender, instance, created, **kwargs):

    if created:
        logger.info("%s", formatted_text(prefix + ".PromptPluginUsage() record created."))
    else:
        logger.info("%s", formatted_text(prefix + ".PromptPluginUsage() record updated."))


@receiver(pre_delete, sender=PromptToolCall)
def handle_chat_tool_call_post_delete(sender, instance, **kwargs):
    """Handle PromptToolCall post delete signal."""
    logger.info("%s %s deleting", formatted_text(prefix + ".PromptToolCall() record"), instance)


@receiver(pre_delete, sender=PromptPluginUsage)
def handle_chat_plugin_usage_post_delete(sender, instance, **kwargs):
    """Handle PromptPluginUsage post delete signal."""
    logger.info("%s %s deleting", formatted_text(prefix + ".PromptPluginUsage() record"), instance)
