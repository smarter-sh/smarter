"""
=================================
Prompt Provider Handler Protocols
=================================

This module defines protocols for prompt provider handler functions, ensuring a
consistent interface across all implementations.

Overview
--------
These protocols use :class:`typing.Protocol` to specify the expected function
signatures for prompt provider handlers. This approach enforces structural typing,
allowing maximum flexibility in implementation while guaranteeing that all
handlers conform to the required interface.

Key Points:

- All handler functions must have the same signature as defined by the protocols
   in this module.
- :class:`typing.Protocol` is used to define these structural types, without
   enforcing a specific class hierarchy.
- This ensures interoperability and consistency across different prompt provider integrations.
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
from smarter.apps.llmtool.plugin.base import PluginBase
from smarter.apps.prompt.models import Prompt
from smarter.lib.django.http.shortcuts import (
    SmarterHttpResponseBadRequest,
    SmarterHttpResponseForbidden,
    SmarterHttpResponseNotFound,
)
from smarter.lib.journal.http import (
    SmarterJournaledJsonErrorResponse,
    SmarterJournaledJsonResponse,
)
from smarter.lib.typing import SmarterDictType

OpenAICompatibleChatCompletionResponseType = Union[
    ChatCompletion,
    SmarterHttpResponseForbidden,
    SmarterHttpResponseNotFound,
    SmarterHttpResponseBadRequest,
    SmarterJournaledJsonErrorResponse,
    SmarterJournaledJsonResponse,
]
"""
OpenAICompatibleChatCompletionResponseType is a type alias that defines the expected.

return type for OpenAI-compatible prompt provider handler functions. It can be either a
ChatCompletion object (representing a successful response) or one of several specific
error response types, including HTTP 403 Forbidden, HTTP 404 Not Found,
HTTP 400 Bad Request, or journaled JSON error/response types. This allows
for consistent handling of both successful and error responses across all
prompt provider handlers that implement the OpenAICompatiblePassthroughProtocol.
"""

SmarterChatCompletionResponseType = Union[
    SmarterDictType,
    SmarterHttpResponseForbidden,
    SmarterHttpResponseNotFound,
    SmarterHttpResponseBadRequest,
    SmarterJournaledJsonErrorResponse,
    SmarterJournaledJsonResponse,
]
"""
SmarterChatCompletionResponseType is a type alias that defines the expected.

return type for Smarter prompt provider handler functions. It can be either a
dictionary (representing a successful response) or one of several specific
error response types, including HTTP 403 Forbidden, HTTP 404 Not Found,
HTTP 400 Bad Request, or journaled JSON error/response types. This allows
for consistent handling of both successful and error responses across all
prompt provider handlers that implement the SmarterChatHarnessProtocol.
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
    :param data: The OpenAI-compatible prompt completion request data.
    :type data: SmarterDictType

    :returns: The response data.
    :rtype: OpenAICompatibleChatCompletionResponseType
    """

    def __call__(
        self,
        request: Request,
        user_profile: UserProfile,
        data: SmarterDictType,
        *args,
        **kwargs,
    ) -> OpenAICompatibleChatCompletionResponseType: ...


class SmarterChatHarnessProtocol(Protocol):
    """
    A fixed Protocol for all Smarter prompt provider handler functions.

    Ensures that handler function call signature conforms to
    this exact standard.

    :param user_profile: The user profile making the request.
    :type user_profile: UserProfile
    :param prompt: The prompt object.
    :type prompt: Prompt
    :param data: The Smarter prompt API request data.
    :type data: Union[SmarterDictType, list]
    :param plugins: Optional list of plugins to use.
    :type plugins: Optional[List[PluginBase]]

    :returns: The response data.
    :rtype: Union[SmarterDictType, list]
    """

    def __call__(
        self,
        user_profile: UserProfile,
        prompt: Prompt,
        data: Union[SmarterDictType, list],
        plugins: Optional[List[PluginBase]] = None,
    ) -> SmarterChatCompletionResponseType: ...


__all__ = [
    "SmarterChatHarnessProtocol",
    "OpenAICompatiblePassthroughProtocol",
    "OpenAICompatibleChatCompletionResponseType",
    "SmarterChatCompletionResponseType",
]
