"""
Handler protocol for chat providers.
Defines a fixed Protocol for all chat provider handler functions.
Ensures that all handler functions have exactly the same signature.

typing.Protocol is used to define a structural type that specifies the expected
signature of the handler functions, without enforcing a specific class
hierarchy. This allows for maximum flexibility in how the handler functions are
implemented, while still ensuring that they conform to the expected interface.
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


# Type alias for OpenAI-compatible chat completion request data
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
    :type data: dict[str, Any]

    :returns: The response data.
    :rtype: OpenAICompatibleChatCompletionResponseType
    """

    def __call__(
        self,
        request: Request,
        user_profile: UserProfile,
        data: dict[str, Any],
        *args,
        **kwargs,
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
    "OpenAICompatibleChatCompletionResponseType",
    "SmarterChatCompletionResponseType",
]
