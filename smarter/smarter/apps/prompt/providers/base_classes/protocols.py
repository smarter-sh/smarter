"""
Handler protocol for chat providers.
Defines a fixed Protocol for all chat provider handler functions.
Ensures that all handler functions have exactly the same signature.
"""

import logging
from typing import (
    Any,
    List,
    Literal,
    NotRequired,
    Optional,
    Protocol,
    Required,
    TypedDict,
    Union,
)

from openai.types.chat.chat_completion import ChatCompletion
from rest_framework.request import Request

from smarter.apps.account.models import UserProfile
from smarter.apps.plugin.plugin.base import PluginBase
from smarter.apps.prompt.models import Chat
from smarter.lib.django import waffle
from smarter.lib.django.http.shortcuts import (
    SmarterHttpResponseBadRequest,
    SmarterHttpResponseForbidden,
    SmarterHttpResponseNotFound,
)
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.journal.http import (
    SmarterJournaledJsonErrorResponse,
    SmarterJournaledJsonResponse,
)
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

# 3rd party stuff


# pylint: disable=W0613
def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.PROMPT_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)

OpenAICompatibleChatCompletionResponseType = Union[
    ChatCompletion,
    SmarterHttpResponseForbidden,
    SmarterHttpResponseNotFound,
    SmarterHttpResponseBadRequest,
    SmarterJournaledJsonErrorResponse,
    SmarterJournaledJsonResponse,
]

SmarterChatCompletionResponseType = Union[
    dict[str, Any],
    SmarterHttpResponseForbidden,
    SmarterHttpResponseNotFound,
    SmarterHttpResponseBadRequest,
    SmarterJournaledJsonErrorResponse,
    SmarterJournaledJsonResponse,
]


class OpenAICompatibleChatMessage(TypedDict, total=False):
    """
    A TypedDict abstraction of a chat message, compatible with OpenAI and Smarter extensions.
    """

    role: Required[Literal["system", "user", "assistant", "tool"]]
    content: Required[Union[str, list[dict]]]

    # OpenAI optional fields
    name: NotRequired[str]
    tool_call_id: NotRequired[str]
    tool_calls: NotRequired[list[dict]]
    function_call: NotRequired[dict]
    audio: NotRequired[str]
    refusal: NotRequired[str]

    # Smarter/proprietary extensions (used internally, not sent to OpenAI)
    smarter_is_new: NotRequired[bool]


class OpenAICompatibleChatCompletionRequest(TypedDict, total=False):
    """
    A TypedDict representing the structure of an OpenAI-compatible chat
    completion request.
    """

    model: Required[str]

    messages: Required[List[OpenAICompatibleChatMessage]]

    temperature: NotRequired[float]

    top_p: NotRequired[float]

    max_tokens: NotRequired[int]

    stop: NotRequired[Union[str, List[str]]]

    stream: NotRequired[bool]

    # optional fields

    tools: NotRequired[list[dict]]

    tool_choice: NotRequired[Union[str, dict]]


class OpenAICompatiblePassthroughProtocol(Protocol):
    """
    A Protocol for OpenAI compatible passthrough functions.
    Ensures that passthrough function call signature conforms to
    this exact standard.

    :param request: The DRF request object.
    :type request: Request
    :param user_profile: The user profile making the request.
    :type user_profile: UserProfile
    :param data: The OpenAI-compatible chat completion request data.
    :type data: OpenAICompatibleChatCompletionRequest

    :returns: The response data.
    :rtype: OpenAICompatibleChatCompletionResponseType
    """

    def __call__(
        self,
        request: Request,
        user_profile: UserProfile,
        data: OpenAICompatibleChatCompletionRequest,
    ) -> OpenAICompatibleChatCompletionResponseType: ...


class SmarterChatHandlerProtocol(Protocol):
    """
    A fixed Protocol for all Smarter chat provider handler functions.
    Ensures that handler function call signature conforms to
    this exact standard.

    :param user_profile: The user profile making the request.
    :type user_profile: UserProfile
    :param chat: The chat object.
    :type chat: Chat
    :param data: The Smarter chat API request data.
    :type data: Union[dict[str, Any], list]
    :param plugins: Optional list of plugins to use.
    :type plugins: Optional[List[PluginBase]]
    :param functions: Optional list of function names to use.
    :type functions: Optional[list[str]]

    :returns: The response data.
    :rtype: Union[dict[str, Any], list]
    """

    def __call__(
        self,
        user_profile: UserProfile,
        chat: Chat,
        data: Union[dict[str, Any], list],
        plugins: Optional[List[PluginBase]] = None,
        functions: Optional[list[str]] = None,
    ) -> SmarterChatCompletionResponseType: ...


__all__ = [
    "SmarterChatHandlerProtocol",
    "OpenAICompatiblePassthroughProtocol",
    "OpenAICompatibleChatCompletionRequest",
    "OpenAICompatibleChatCompletionResponseType",
    "SmarterChatCompletionResponseType",
]
