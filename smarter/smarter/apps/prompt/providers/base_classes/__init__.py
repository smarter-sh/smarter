"""
Base classes and utilities for chat providers in the Smarter framework.
"""

from .openai_compatible_chat_provider import OpenAICompatibleChatProvider
from .passthrough_chat_provider import OpenAICompatiblePassthroughChatProvider
from .protocols import (
    OpenAICompatibleChatCompletionRequest,
    OpenAICompatibleChatCompletionResponse,
    OpenAICompatiblePassthroughProtocol,
    SmarterChatCompletionResponseType,
    SmarterChatHandlerProtocol,
)

__all__ = [
    "SmarterChatHandlerProtocol",
    "OpenAICompatibleChatProvider",
    "OpenAICompatiblePassthroughChatProvider",
    "OpenAICompatiblePassthroughProtocol",
    "OpenAICompatibleChatCompletionRequest",
    "OpenAICompatibleChatCompletionResponse",
    "SmarterChatCompletionResponseType",
]
