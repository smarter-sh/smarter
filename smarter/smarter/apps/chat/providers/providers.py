"""
A chat provider convenience class. This class is a collection of all the chat providers and their handlers.
It also provides a default provider and handler.

There are a few objectives of this class:
1. To provide a single point of access to all the chat providers.
2. To hide complexity introduced into the provider classes due to Pydantic models.
3. To provide a default provider and handler.
"""

from typing import Callable, Dict, List, Optional, Type

from smarter.apps.chat.models import Chat
from smarter.apps.plugin.plugin.static import PluginStatic
from smarter.lib.django.user import UserType

from .base import ChatProviderBase
from .openai import PROVIDER_NAME as OPENAI_PROVIDER_NAME
from .openai import OpenAIChatProvider, OpenAIHandlerInput


class ChatProviders:
    """
    Collection of all the chat providers.
    """

    _openai = None
    _default = None

    # -------------------------------------------------------------------------
    # all providers
    # -------------------------------------------------------------------------
    @property
    def openai(self) -> OpenAIChatProvider:
        if self._openai is None:
            self._openai = OpenAIChatProvider()
        return self._openai

    @property
    def default(self) -> Type[ChatProviderBase]:
        if self._default is None:
            self._default = OpenAIChatProvider()
        return self._default

    # -------------------------------------------------------------------------
    # all handlers
    # -------------------------------------------------------------------------
    def openai_handler(
        self, chat: Chat, data: dict, plugins: Optional[List[PluginStatic]] = None, user: Optional[UserType] = None
    ) -> dict:
        """Expose the handler method of the default provider"""
        handler_inputs = OpenAIHandlerInput(
            chat=chat,
            data=data,
            plugins=plugins,
            user=user,
        )
        return self.default.handler(handler_inputs=handler_inputs)

    def default_handler(
        self, chat: Chat, data: dict, plugins: Optional[List[PluginStatic]] = None, user: Optional[UserType] = None
    ) -> dict:
        """Expose the handler method of the default provider"""
        return self.openai_handler(chat=chat, data=data, plugins=plugins, user=user)

    @property
    def all_handlers(self) -> Dict[str, Callable]:
        """
        A dictionary of all the handler callables
        """
        return {OPENAI_PROVIDER_NAME: self.openai_handler, "DEFAULT": self.default_handler}

    def get_handler(self, name: str = None) -> Callable:
        """
        A convenience method to get a handler by name.
        """
        if not name:
            return self.default_handler

        fnc = self.all_handlers.get(name)
        if not fnc:
            raise ValueError(f"Handler not found for provider: {name}")
        return fnc

    @property
    def all(self):
        return list({self.openai.name, self.default.name})
