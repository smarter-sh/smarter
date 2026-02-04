"""
A chat provider convenience class. This class is a collection of all the chat providers and their handlers.
It also provides a default provider and handler.

There are a few objectives of this class:
1. To provide a single point of access to all the chat providers.
2. To hide complexity introduced into the provider classes due to Pydantic models.
3. To provide a default provider and handler.
"""

import logging
from typing import Any, Dict, List, Optional, Union

from smarter.apps.account.models import User
from smarter.apps.plugin.plugin.base import PluginBase
from smarter.apps.prompt.models import Chat
from smarter.common.exceptions import SmarterValueError
from smarter.common.helpers.console_helpers import formatted_text
from smarter.common.mixins import SmarterHelperMixin
from smarter.lib.cache import lazy_cache as cache
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

from .base_classes import HandlerProtocol
from .googleai.classes import GoogleAIChatProvider
from .googleai.const import PROVIDER_NAME as GOOGLEAI_PROVIDER_NAME
from .metaai.classes import MetaAIChatProvider
from .metaai.const import PROVIDER_NAME as METAAI_PROVIDER_NAME
from .openai.classes import PROVIDER_NAME as OPENAI_PROVIDER_NAME
from .openai.classes import OpenAIChatProvider


# pylint: disable=W0613
def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.PROMPT_LOGGING)


# pylint: disable=W0613
def should_log_caching(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.PROMPT_LOGGING) and waffle.switch_is_active(
        SmarterWaffleSwitches.CACHE_LOGGING
    )


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)
caching_logger = WaffleSwitchedLoggerWrapper(base_logger, should_log_caching)

CACHE_PREFIX = f"{__name__}"
CACHE_TIMEOUT = 10
"""
Cache timeout in seconds for chat providers.
This is to allow for short-term caching of provider instances. For now, this
only benefits inner-process calls that lead to multiple instantiatiaons of the
same provider within a short time frame.

However, the objective to to increase the cache timeout as observed usage
patterns emerge that are confirmed to be cache safe.
"""


class ChatProviders(SmarterHelperMixin):
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
    def default(self) -> OpenAIChatProvider:
        if self._default is None:
            self._default = OpenAIChatProvider()
        return self._default

    def get_cache_key(self, chat: Chat) -> str:
        """
        Get the cache key for the chat object.
        """
        return f"{CACHE_PREFIX}.{chat.session_key}"

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
        self,
        user: User,
        chat: Chat,
        data: Union[dict[str, Any], list],
        plugins: Optional[List[PluginBase]] = None,
        functions: Optional[list[str]] = None,
    ) -> Union[dict, list]:
        """Expose the handler method of the default provider"""
        self.validate_chat(chat)
        cache_key = self.get_cache_key(chat)
        cached_provider: OpenAIChatProvider = cache.get(cache_key)

        if cached_provider is not None:
            caching_logger.debug(
                "%s.openai_handler() returning cached OpenAIChatProvider for chat %s",
                self.formatted_class_name,
                chat.id,  # type: ignore[arg-type]
            )

            if not user:
                raise SmarterValueError(
                    f"{self.formatted_class_name}: user is required to handle OpenAIChatProvider calls."
                )
            # if we have a cached provider, we can use it to invoke the handler
            # with everything preinitialized (from the last invocation) get the response.
            result = cached_provider.handler(user, chat, data, plugins=plugins, functions=functions)

            # the state of the class instance will change after the handler is invoked
            # so we need to update the cache with the new state, and we'll also reset the timeout.
            cache.set(cache_key, cached_provider, timeout=CACHE_TIMEOUT)
            caching_logger.debug(f"caching {cache_key}")
            return result

        result = self.openai.handler(user, chat, data, plugins=plugins, functions=functions)
        # raised Can't pickle <function capfirst at 0x7ffffa408540>: it's not the same object as django.utils.text.capfirst
        # cache.set(cache_key, self.openai, timeout=CACHE_TIMEOUT)
        caching_logger.debug(f"caching {cache_key}")
        self._openai = None
        return result

    def googleai_handler(
        self,
        user: User,
        chat: Chat,
        data: Union[dict[str, Any], list],
        plugins: Optional[List[PluginBase]] = None,
        functions: Optional[list[str]] = None,
    ) -> Union[dict, list]:
        """Expose the handler method of the googleai provider"""
        self.validate_chat(chat)
        cache_key = self.get_cache_key(chat)
        cached_provider: GoogleAIChatProvider = cache.get(cache_key)

        if cached_provider is not None:
            caching_logger.debug(
                "%s.googleai_handler() returning cached GoogleAIChatProvider for chat %s",
                self.formatted_class_name,
                chat.id,  # type: ignore[arg-type]
            )
            if not user:
                raise SmarterValueError(
                    f"{self.formatted_class_name}: user is required to handle GoogleAIChatProvider calls."
                )
            result = cached_provider.handler(user, chat, data, plugins=plugins, functions=functions)
            cache.set(cache_key, cached_provider, timeout=CACHE_TIMEOUT)
            caching_logger.debug(f"caching {cache_key}")
            return result

        result = self.googleai.handler(user, chat, data, plugins=plugins, functions=functions)
        cache.set(cache_key, self.googleai, timeout=CACHE_TIMEOUT)
        caching_logger.debug(f"caching {cache_key}")
        self._googleai = None
        return result

    def metaai_handler(
        self,
        user: User,
        chat: Chat,
        data: Union[dict[str, Any], list],
        plugins: Optional[List[PluginBase]] = None,
        functions: Optional[list[str]] = None,
    ) -> Union[dict, list]:
        """Expose the handler method of the metaai provider"""
        self.validate_chat(chat)
        cache_key = self.get_cache_key(chat)
        cached_provider: MetaAIChatProvider = cache.get(cache_key)

        if cached_provider is not None:
            caching_logger.debug(
                "%s returning cached MetaAIChatProvider for chat %s", formatted_text("metaai_handler()"), chat.id  # type: ignore[arg-type]
            )

            if not user:
                raise SmarterValueError(
                    f"{self.formatted_class_name}: user is required to handle MetaAIChatProvider calls."
                )
            result = cached_provider.handler(user, chat, data, plugins=plugins, functions=functions)
            cache.set(cache_key, cached_provider, timeout=CACHE_TIMEOUT)
            caching_logger.debug(f"caching {cache_key}")
            return result

        result = self.metaai.handler(user, chat, data, plugins=plugins, functions=functions)
        cache.set(cache_key, self.metaai, timeout=CACHE_TIMEOUT)
        caching_logger.debug(f"caching {cache_key}")
        self._metaai = None
        return result

    def default_handler(
        self,
        user: User,
        chat: Chat,
        data: Union[dict[str, Any], list],
        plugins: Optional[List[PluginBase]] = None,
        functions: Optional[list[str]] = None,
    ) -> Union[dict, list]:
        """Expose the handler method of the default provider"""
        return self.openai_handler(user, chat, data, plugins=plugins, functions=functions)

    def logger_helper(self, verb: str, msg: str):
        logger.debug("%s %s %s", self.formatted_class_name, verb, msg)

    @property
    def all_handlers(self) -> Dict[str, HandlerProtocol]:
        """
        A dictionary of all the handler callables.
        handlers must conform to HandlerProtocol.
        """

        googleai_handler: HandlerProtocol = self.googleai_handler
        metaai_handler: HandlerProtocol = self.metaai_handler
        openai_handler: HandlerProtocol = self.openai_handler
        default_handler: HandlerProtocol = self.default_handler

        return {
            GOOGLEAI_PROVIDER_NAME: googleai_handler,
            METAAI_PROVIDER_NAME: metaai_handler,
            OPENAI_PROVIDER_NAME: openai_handler,
            "DEFAULT": default_handler,
        }

    def get_handler(self, provider: Optional[str] = None) -> HandlerProtocol:
        """
        A convenience method to get a handler by provider name.
        """
        if not provider:
            return self.default_handler

        handler = self.all_handlers.get(provider)
        if not handler:
            raise ValueError(f"Handler not found for provider: {provider}")
        return handler

    @property
    def all(self) -> list[str]:
        return [
            self.googleai.provider or "GoogleAi",
            self.metaai.provider or "MetaAI",
            self.openai.provider or "OpenAI",
            self.default.provider or "Default",
        ]


chat_providers = ChatProviders()
