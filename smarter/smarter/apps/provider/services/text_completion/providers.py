"""
A chat provider convenience class. This class is a collection of all the chat providers and their handlers.
It also provides a default provider and handler.

There are a few objectives of this class:
1. To provide a single point of access to all the chat providers.
2. To hide complexity introduced into the provider classes due to Pydantic models.
3. To provide a default provider and handler.
"""

import logging
import warnings
from functools import cached_property
from typing import Any, Dict, List, Optional, Union

from pydantic import SecretStr
from rest_framework.request import Request
from typing_extensions import deprecated

from smarter.apps.account.models import User, UserProfile
from smarter.apps.plugin.plugin.base import PluginBase
from smarter.apps.prompt.models import Chat
from smarter.apps.provider.clients import SmarterOpenAIClient
from smarter.apps.provider.models import Provider
from smarter.common.exceptions import SmarterValueError
from smarter.common.helpers.console_helpers import formatted_text
from smarter.common.mixins import SmarterHelperMixin
from smarter.lib.cache import cache_results
from smarter.lib.cache import lazy_cache as cache
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

from .googleai.classes import (
    GoogleAISmarterChatProvider,
)
from .googleai.const import PROVIDER_NAME as GOOGLEAI_PROVIDER_NAME
from .lib.protocols import (
    OpenAICompatibleChatCompletionResponseType,
    OpenAICompatiblePassthroughProtocol,
    SmarterChatCompletionResponseType,
    SmarterChatHandlerProtocol,
)
from .metaai.classes import MetaAISmarterChatProvider
from .metaai.const import PROVIDER_NAME as METAAI_PROVIDER_NAME
from .openai.classes import OpenAISmarterChatProvider
from .openai.const import PROVIDER_NAME as OPENAI_PROVIDER_NAME


# pylint: disable=W0613
def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.PROMPT_LOGGING)


# pylint: disable=W0613
def should_log_caching(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.PROMPT_LOGGING) or waffle.switch_is_active(
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


@deprecated(
    "SmarterCompatibleChatProviders is deprecated and will be removed in a future release. Please use SmarterCompatibleChatProvidersV2 instead."
)
class SmarterCompatibleChatProviders(SmarterHelperMixin):
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
    def googleai(self) -> GoogleAISmarterChatProvider:
        if self._googleai is None:
            self._googleai = GoogleAISmarterChatProvider()
        return self._googleai

    @property
    def metaai(self) -> MetaAISmarterChatProvider:
        if self._metaai is None:
            self._metaai = MetaAISmarterChatProvider()
        return self._metaai

    @property
    def openai(self) -> OpenAISmarterChatProvider:
        if self._openai is None:
            self._openai = OpenAISmarterChatProvider()
        return self._openai

    @property
    def default(self) -> OpenAISmarterChatProvider:
        if self._default is None:
            self._default = OpenAISmarterChatProvider()
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
        user_profile: UserProfile,
        chat: Chat,
        data: Union[dict[str, Any], list],
        plugins: Optional[List[PluginBase]] = None,
        functions: Optional[list[str]] = None,
    ) -> SmarterChatCompletionResponseType:
        """Expose the handler method of the default provider"""
        self.validate_chat(chat)
        cache_key = self.get_cache_key(chat)
        cached_provider: OpenAISmarterChatProvider = cache.get(cache_key)

        if cached_provider is not None:
            caching_logger.debug(
                "%s.openai_handler() returning cached OpenAISmarterChatProvider for chat %s",
                self.formatted_class_name,
                chat.id,  # type: ignore[arg-type]
            )

            if not user_profile:
                raise SmarterValueError(
                    f"{self.formatted_class_name}: user_profile is required to handle OpenAISmarterChatProvider calls."
                )
            # if we have a cached provider, we can use it to invoke the handler
            # with everything preinitialized (from the last invocation) get the response.
            result = cached_provider.handler(user_profile, chat, data, plugins=plugins, functions=functions)

            # the state of the class instance will change after the handler is invoked
            # so we need to update the cache with the new state, and we'll also reset the timeout.
            cache.set(cache_key, cached_provider, timeout=CACHE_TIMEOUT)
            caching_logger.debug(f"caching {cache_key}")
            return result

        result = self.openai.handler(user_profile, chat, data, plugins=plugins, functions=functions)
        # raised Can't pickle <function capfirst at 0x7ffffa408540>: it's not the same object as django.utils.text.capfirst
        # cache.set(cache_key, self.openai, timeout=CACHE_TIMEOUT)
        caching_logger.debug(f"caching {cache_key}")
        self._openai = None
        return result

    def googleai_handler(
        self,
        user_profile: UserProfile,
        chat: Chat,
        data: Union[dict[str, Any], list],
        plugins: Optional[List[PluginBase]] = None,
        functions: Optional[list[str]] = None,
    ) -> SmarterChatCompletionResponseType:
        """Expose the handler method of the googleai provider"""
        self.validate_chat(chat)
        cache_key = self.get_cache_key(chat)
        cached_provider: GoogleAISmarterChatProvider = cache.get(cache_key)

        if cached_provider is not None:
            caching_logger.debug(
                "%s.googleai_handler() returning cached GoogleAISmarterChatProvider for chat %s",
                self.formatted_class_name,
                chat.id,  # type: ignore[arg-type]
            )
            if not user_profile:
                raise SmarterValueError(
                    f"{self.formatted_class_name}: user_profile is required to handle GoogleAISmarterChatProvider calls."
                )
            result = cached_provider.handler(user_profile, chat, data, plugins=plugins, functions=functions)
            cache.set(cache_key, cached_provider, timeout=CACHE_TIMEOUT)
            caching_logger.debug(f"caching {cache_key}")
            return result

        result = self.googleai.handler(user_profile, chat, data, plugins=plugins, functions=functions)
        cache.set(cache_key, self.googleai, timeout=CACHE_TIMEOUT)
        caching_logger.debug(f"caching {cache_key}")
        self._googleai = None
        return result

    def metaai_handler(
        self,
        user_profile: UserProfile,
        chat: Chat,
        data: Union[dict[str, Any], list],
        plugins: Optional[List[PluginBase]] = None,
        functions: Optional[list[str]] = None,
    ) -> SmarterChatCompletionResponseType:
        """Expose the handler method of the metaai provider"""
        self.validate_chat(chat)
        cache_key = self.get_cache_key(chat)
        cached_provider: MetaAISmarterChatProvider = cache.get(cache_key)

        if cached_provider is not None:
            caching_logger.debug(
                "%s returning cached MetaAISmarterChatProvider for chat %s", formatted_text("metaai_handler()"), chat.id  # type: ignore[arg-type]
            )

            if not user_profile:
                raise SmarterValueError(
                    f"{self.formatted_class_name}: user_profile is required to handle MetaAISmarterChatProvider calls."
                )
            result = cached_provider.handler(user_profile, chat, data, plugins=plugins, functions=functions)
            cache.set(cache_key, cached_provider, timeout=CACHE_TIMEOUT)
            caching_logger.debug(f"caching {cache_key}")
            return result

        result = self.metaai.handler(user_profile, chat, data, plugins=plugins, functions=functions)
        cache.set(cache_key, self.metaai, timeout=CACHE_TIMEOUT)
        caching_logger.debug(f"caching {cache_key}")
        self._metaai = None
        return result

    def default_handler(
        self,
        user_profile: UserProfile,
        chat: Chat,
        data: Union[dict[str, Any], list],
        plugins: Optional[List[PluginBase]] = None,
        functions: Optional[list[str]] = None,
    ) -> SmarterChatCompletionResponseType:
        """Expose the handler method of the default provider"""
        return self.openai_handler(user_profile, chat, data, plugins=plugins, functions=functions)

    def logger_helper(self, verb: str, msg: str):
        logger.debug("%s.default_handler() %s %s", self.formatted_class_name, verb, msg)

    @property
    def all_handlers(self) -> Dict[str, SmarterChatHandlerProtocol]:
        """
        A dictionary of all the handler callables.
        handlers must conform to SmarterChatHandlerProtocol.
        """

        googleai_handler: SmarterChatHandlerProtocol = self.googleai_handler
        metaai_handler: SmarterChatHandlerProtocol = self.metaai_handler
        openai_handler: SmarterChatHandlerProtocol = self.openai_handler
        default_handler: SmarterChatHandlerProtocol = self.default_handler

        return {
            GOOGLEAI_PROVIDER_NAME: googleai_handler,
            METAAI_PROVIDER_NAME: metaai_handler,
            OPENAI_PROVIDER_NAME: openai_handler,
            "DEFAULT": default_handler,
        }

    @deprecated(
        "SmarterCompatibleChatProviders is deprecated and will be removed in a future release. Please use SmarterCompatibleChatProvidersV2 instead."
    )
    def get_smarter_handler(self, provider: Optional[str] = None) -> SmarterChatHandlerProtocol:
        """
        A convenience method to get a handler by provider name.
        """
        warnings.warn(
            f"{self.formatted_class_name}.get_smarter_handler() is deprecated and will be removed in a future release. Please use SmarterCompatibleChatProvidersV2.get_smarter_handler() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        if not provider:
            return self.default_handler

        handler = self.all_handlers.get(provider)
        if not handler:
            raise SmarterValueError(f"Handler not found for provider: {provider}")
        return handler

    @property
    def all(self) -> list[str]:
        return [
            self.googleai.provider or "GoogleAi",
            self.metaai.provider or "MetaAI",
            self.openai.provider or "OpenAI",
            self.default.provider or "Default",
        ]


class OpenAICompatibleClientFactory(SmarterHelperMixin):
    """
    A newer version of the OpenAICompatiblePassthroughChatProviders class.
    """

    @cached_property
    def default_handler_name(self) -> str:
        """
        Returns the name of the platform-wide default provider.
        If no default provider is found, it falls back to OpenAI.
        """

        @cache_results()
        def get_cached_provider_name() -> Optional[str]:
            provider = Provider.objects.filter(is_default=True).first()  # type: ignore
            if not provider:
                logger.warning("Default provider not found for user. Falling back to OpenAI.")
                return OPENAI_PROVIDER_NAME
            return provider.name

        return get_cached_provider_name()

    def get_openai_client_for_provider(self, provider_name: str, user: User) -> SmarterOpenAIClient:

        @cache_results()
        def get_cached_openai_client_for_provider(provider_name: str, username: str) -> SmarterOpenAIClient:

            try:
                provider_orm = (
                    Provider.objects.filter(name=provider_name)
                    .with_read_permission_for(user)  # type: ignore
                    .only("name", "base_url", "api_key")
                    .first()
                )  # type: ignore
                if not provider_orm:
                    raise Provider.DoesNotExist
            except Provider.DoesNotExist:
                logger.warning(f"Default provider not found for user. Falling back to {self.default_handler_name}.")
                provider_orm = Provider.objects.filter(name=self.default_handler_name).first()  # type: ignore
            except Provider.MultipleObjectsReturned:
                provider_orm = Provider.objects.filter(is_default=True).first()  # type: ignore
                logger.warning(
                    f"Multiple default providers found for user {username}. Choosing the first one: {provider_orm}."
                )

            if not provider_orm:
                raise SmarterValueError("provider not found")
            api_key = SecretStr(provider_orm.api_key.get_secret()) if provider_orm.api_key else None

            retval = SmarterOpenAIClient(
                provider=provider_orm.name,
                base_url=provider_orm.base_url,
                api_key=api_key.get_secret_value() if api_key else "",
            )
            return retval

        return get_cached_openai_client_for_provider(provider_name, user.username)  # type: ignore

    def get_passthrough_handler(
        self, request: Request, provider_name: Optional[str] = None, **kwargs
    ) -> OpenAICompatiblePassthroughProtocol:
        """
        Instantiates a SmarterOpenAIClient for the given provider name and
        returns its passthrough handler. The key thing is that whatever handler we use
        here must implement the OpenAICompatiblePassthroughProtocol.
        """
        provider_name = provider_name or self.default_handler_name
        retval = self.get_openai_client_for_provider(provider_name=provider_name, user=request.user)  # type: ignore
        return retval.passthrough_handler

    def get_smarter_handler(self, provider: Optional[str] = None) -> SmarterChatHandlerProtocol:
        """
        Instantiates a SmarterOpenAIClient for the given provider name and
        returns its smarter compatible handler. The key thing is that whatever
        handler we use here must implement the SmarterChatHandlerProtocol.
        """
        pass


smarter_compatible_chat_providers = SmarterCompatibleChatProviders()
openai_compatible_client = OpenAICompatibleClientFactory()
