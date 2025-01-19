"""
A chat provider convenience class. This class is a collection of all the chat providers and their handlers.
It also provides a default provider and handler.

There are a few objectives of this class:
1. To provide a single point of access to all the chat providers.
2. To hide complexity introduced into the provider classes due to Pydantic models.
3. To provide a default provider and handler.
"""

from typing import Callable, Dict, List, Optional, Type

from django.core.cache import cache

from smarter.apps.chat.models import Chat
from smarter.apps.plugin.plugin.static import PluginStatic
from smarter.common.classes import Singleton
from smarter.common.exceptions import SmarterValueError
from smarter.lib.django.user import UserType

from .base_classes import OpenAICompatibleChatProvider
from .googleai.classes import GoogleAIChatProvider
from .googleai.const import PROVIDER_NAME as GOOGLEAI_PROVIDER_NAME
from .metaai.classes import MetaAIChatProvider
from .metaai.const import PROVIDER_NAME as METAAI_PROVIDER_NAME
from .openai.classes import PROVIDER_NAME as OPENAI_PROVIDER_NAME
from .openai.classes import OpenAIChatProvider


CACHE_PREFIX = "smarter.apps.chat.providers"
CACHE_TIMEOUT = 600


class ChatProviders(metaclass=Singleton):
    """
    Collection of all the chat providers.
    """

    _default = None
    _googleai = None
    _metaai = None
    _openai = None

    # -------------------------------------------------------------------------
    # all providers
    # -------------------------------------------------------------------------
    @property
    def googleai(self) -> GoogleAIChatProvider:
        if self._googleai is None:
            self._googleai = GoogleAIChatProvider()
        return self._googleai

    @property
    def metaai(self) -> MetaAIChatProvider:
        if self._metaai is None:
            self._metaai = MetaAIChatProvider()
        return self._metaai

    @property
    def openai(self) -> OpenAIChatProvider:
        if self._openai is None:
            self._openai = OpenAIChatProvider()
        return self._openai

    @property
    def default(self) -> Type[OpenAICompatibleChatProvider]:
        if self._default is None:
            self._default = OpenAIChatProvider()
        return self._default

    def validate_chat(self, chat: Chat) -> None:
        """
        Validate the chat object.
        """
        if not chat:
            raise SmarterValueError("Chat object is required to get the handler")
        if not chat.session_key:
            raise SmarterValueError("Chat session key is required to get the handler")

    # -------------------------------------------------------------------------
    # all handlers
    # -------------------------------------------------------------------------
    def openai_handler(
        self, chat: Chat, data: dict, plugins: Optional[List[PluginStatic]] = None, user: Optional[UserType] = None
    ) -> Callable:
        """Expose the handler method of the default provider"""
        self.validate_chat(chat)

        cache_key = f"{CACHE_PREFIX}.openai_handler_{chat.session_key}"
        cached_result = cache.get(cache_key)

        if cached_result is not None:
            return cached_result

        result = self.default.handler(chat=chat, data=data, plugins=plugins, user=user)
        cache.set(cache_key, result, timeout=CACHE_TIMEOUT)

        return result

    def googleai_handler(
        self, chat: Chat, data: dict, plugins: Optional[List[PluginStatic]] = None, user: Optional[UserType] = None
    ) -> Callable:
        """Expose the handler method of the googleai provider"""
        self.validate_chat(chat)

        cache_key = f"{CACHE_PREFIX}.googleai_handler{chat.session_key}"
        cached_result = cache.get(cache_key)

        if cached_result is not None:
            return cached_result

        result = self.googleai.handler(chat=chat, data=data, plugins=plugins, user=user)
        cache.set(cache_key, result, timeout=CACHE_TIMEOUT)

        return result

    def metaai_handler(
        self, chat: Chat, data: dict, plugins: Optional[List[PluginStatic]] = None, user: Optional[UserType] = None
    ) -> Callable:
        """Expose the handler method of the metaai provider"""
        self.validate_chat(chat)

        cache_key = f"{CACHE_PREFIX}.metaai_handler{chat.session_key}"
        cached_result = cache.get(cache_key)

        if cached_result is not None:
            return cached_result

        result = self.metaai.handler(chat=chat, data=data, plugins=plugins, user=user)
        cache.set(cache_key, result, timeout=CACHE_TIMEOUT)

        return result

    def default_handler(
        self, chat: Chat, data: dict, plugins: Optional[List[PluginStatic]] = None, user: Optional[UserType] = None
    ) -> Callable:
        """Expose the handler method of the default provider"""
        return self.openai_handler(chat=chat, data=data, plugins=plugins, user=user)

    @property
    def all_handlers(self) -> Dict[str, Callable]:
        """
        A dictionary of all the handler callables
        """
        return {
            GOOGLEAI_PROVIDER_NAME: self.googleai_handler,
            METAAI_PROVIDER_NAME: self.metaai_handler,
            OPENAI_PROVIDER_NAME: self.openai_handler,
            "DEFAULT": self.default_handler,
        }

    def get_handler(self, name: str = None) -> Callable:
        """
        A convenience method to get a handler by name.
        """
        if not name:
            return self.default_handler

        handler = self.all_handlers.get(name)
        if not handler:
            raise ValueError(f"Handler not found for provider: {name}")
        return handler

    @property
    def all(self) -> list[str]:
        return list({self.googleai.name, self.metaai.name, self.openai.name, self.default.name})


chat_providers = ChatProviders()
