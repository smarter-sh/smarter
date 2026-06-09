"""
===============================
Chat Provider Handler Protocols
===============================

This module defines protocols for chat provider handler functions, ensuring a
consistent interface across all implementations.

Overview
--------
These protocols use :class:`typing.Protocol` to specify the expected function
signatures for chat provider handlers. This approach enforces structural typing,
allowing maximum flexibility in implementation while guaranteeing that all
handlers conform to the required interface.

Key Points:

- All handler functions must have the same signature as defined by the protocols
   in this module.
- :class:`typing.Protocol` is used to define these structural types, without
   enforcing a specific class hierarchy.
- This ensures interoperability and consistency across different chat provider integrations.
"""

from typing import (
    Any,
    List,
    Optional,
    Protocol,
    Union,
)

from openai.types.chat.chat_completion import ChatCompletion
from rest_framework.request import Request

from smarter.apps.account.models import UserProfile
from smarter.apps.plugin.plugin.base import PluginBase
from smarter.apps.prompt.models import Chat
from smarter.lib.django.http.shortcuts import (
    SmarterHttpResponseBadRequest,
    SmarterHttpResponseForbidden,
    SmarterHttpResponseNotFound,
)
from smarter.lib.journal.http import (
    SmarterJournaledJsonErrorResponse,
    SmarterJournaledJsonResponse,
)

OpenAICompatibleChatCompletionResponseType = Union[
    ChatCompletion,
    SmarterHttpResponseForbidden,
    SmarterHttpResponseNotFound,
    SmarterHttpResponseBadRequest,
    SmarterJournaledJsonErrorResponse,
    SmarterJournaledJsonResponse,
]
"""
OpenAICompatibleChatCompletionResponseType is a type alias that defines the expected
return type for OpenAI-compatible chat provider handler functions. It can be either a
ChatCompletion object (representing a successful response) or one of several specific
error response types, including HTTP 403 Forbidden, HTTP 404 Not Found,
HTTP 400 Bad Request, or journaled JSON error/response types. This allows
for consistent handling of both successful and error responses across all
chat provider handlers that implement the OpenAICompatiblePassthroughProtocol.
"""

SmarterChatCompletionResponseType = Union[
    dict[str, Any],
    SmarterHttpResponseForbidden,
    SmarterHttpResponseNotFound,
    SmarterHttpResponseBadRequest,
    SmarterJournaledJsonErrorResponse,
    SmarterJournaledJsonResponse,
]
"""
SmarterChatCompletionResponseType is a type alias that defines the expected
return type for Smarter chat provider handler functions. It can be either a
dictionary (representing a successful response) or one of several specific
error response types, including HTTP 403 Forbidden, HTTP 404 Not Found,
HTTP 400 Bad Request, or journaled JSON error/response types. This allows
for consistent handling of both successful and error responses across all
chat provider handlers that implement the SmarterChatHandlerProtocol.
"""


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
