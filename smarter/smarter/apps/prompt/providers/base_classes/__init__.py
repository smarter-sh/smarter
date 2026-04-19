"""
Base classes and utilities for chat providers in the Smarter framework.
"""

from .chat_provider_base import SmarterChatProviderBase
from .exception_map import EXCEPTION_MAP
from .mixins import ChatDbMixin
from .openai_compatible_chat_provider import OpenAICompatibleChatProvider
from .passthrough_chat_provider import OpenAICompatiblePassthroughChatProvider
from .protocols import (
    OpenAICompatibleChatCompletionRequest,
    OpenAICompatibleChatCompletionResponse,
    OpenAICompatiblePassthroughProtocol,
    SmarterChatCompletionResponse,
    SmarterChatHandlerProtocol,
)

__all__ = [
    "SmarterChatHandlerProtocol",
    "EXCEPTION_MAP",
    "OpenAICompatibleChatProvider",
    "OpenAICompatiblePassthroughChatProvider",
    "OpenAICompatiblePassthroughProtocol",
    "OpenAICompatibleChatCompletionRequest",
    "OpenAICompatibleChatCompletionResponse",
    "SmarterChatProviderBase",
    "ChatDbMixin",
    "SmarterChatCompletionResponse",
]
