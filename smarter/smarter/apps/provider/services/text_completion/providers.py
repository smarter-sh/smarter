"""
smarter.apps.provider.services.text_completion.providers
==================================================================

Service-level entry point for text completions supporting multiple LLM provider companies.
This module provides a unified interface for accessing and managing chat completion providers,
enabling seamless integration with a variety of large language model (LLM) backends.

**Protocols Supported:**

1. **Smarter Chat Protocol**
    - Implements: SmarterChatHandlerProtocol
    - Returns: SmarterChatCompletionResponseType
    - Used for native Smarter chat API requests, supporting advanced features and proprietary extensions.

2. **OpenAI-Compatible Passthrough Protocol**
    - Implements: OpenAICompatiblePassthroughProtocol
    - Returns: OpenAICompatibleChatCompletionResponseType
    - Used for OpenAI-compatible API passthrough, enabling direct proxying to third-party LLM providers.

**Key Features:**

- Centralized access to all configured chat providers and their handlers.
- Supports both Smarter-native and OpenAI-compatible request/response formats.
- Provides default provider selection and handler resolution.
- Abstracts provider-specific complexities, including authentication and model selection.
- Enables dynamic handler retrieval for both protocols, facilitating flexible integration patterns.

"""

import logging
from functools import cached_property
from typing import Any, List, Optional, Union

from pydantic import SecretStr
from rest_framework.request import Request

from smarter.apps.account.models import User, UserProfile
from smarter.apps.plugin.plugin.base import PluginBase
from smarter.apps.prompt.models import Chat
from smarter.apps.provider.clients import OpenAIPassthroughClient
from smarter.apps.provider.models import Provider
from smarter.apps.provider.services.text_completion.lib.openai_compatible_chat_provider import (
    OpenAISmarterClient,
)
from smarter.common.enum import SmarterEnumAbstract
from smarter.common.exceptions import SmarterValueError
from smarter.common.mixins import SmarterHelperMixin
from smarter.lib.cache import cache_results
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

from .lib.protocols import (
    OpenAICompatibleChatCompletionResponseType,
    OpenAICompatiblePassthroughProtocol,
    SmarterChatCompletionResponseType,
    SmarterChatHandlerProtocol,
)


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


class ClientTypeEnum(SmarterEnumAbstract):
    """
    Client type distinguishes between the kind of handler we want
    from the provider.
    """

    SMARTER = OpenAISmarterClient.__name__
    PASSTHROUGH = OpenAIPassthroughClient.__name__


class OpenAICompatibleClientFactory(SmarterHelperMixin):
    """
    A newer version of the OpenAICompatiblePassthroughChatProviders class.
    """

    _client_type: ClientTypeEnum

    def __init__(self, client_type: Optional[ClientTypeEnum] = ClientTypeEnum.SMARTER):
        super().__init__()
        if client_type is not None and client_type not in list(ClientTypeEnum):
            raise ValueError(f"Invalid client type: {client_type}. Must be one of {list(ClientTypeEnum)}")
        self._client_type = client_type or ClientTypeEnum.SMARTER

    @property
    def client_type(self) -> ClientTypeEnum:
        return self._client_type

    @cached_property
    def default_handler_name(self) -> str:
        """
        Returns the name of the platform-wide default provider.
        If no default provider is found, it raises a SmarterValueError.
        """

        provider = Provider.objects.filter(is_default=True, is_active=True).first()  # type: ignore
        if not provider:
            raise SmarterValueError("Default provider not found")
        return provider.name

    def get_client_orm_by_provider_name_and_user(self, provider_name: str, user: User) -> Provider:

        @cache_results()
        def get_cached_provider_orm_by_name_and_username(provider_name: str, username: str) -> Provider:

            try:
                provider_orm = (
                    Provider.objects.filter(name=provider_name, is_active=True)
                    .with_read_permission_for(user)  # type: ignore
                    .only("name", "base_url", "api_key")
                    .first()
                )  # type: ignore
                if not provider_orm:
                    raise Provider.DoesNotExist
            except Provider.DoesNotExist as e:
                raise SmarterValueError(f"Provider {provider_name} not found for user {user}.") from e
            except Provider.MultipleObjectsReturned:
                provider_orm = Provider.objects.filter(is_default=True, is_active=True).first()  # type: ignore
                logger.warning(
                    f"Multiple default providers found for user {username}. Choosing the first one: {provider_orm}."
                )

            if not provider_orm:
                raise SmarterValueError(f"Provider {provider_name} not found for user {user}.")
            return provider_orm

        return get_cached_provider_orm_by_name_and_username(provider_name, user.username)  # type: ignore

    def get_openai_client_for_provider(self, provider_name: str, user: User) -> OpenAIPassthroughClient:

        @cache_results()
        def get_cached_openai_client_for_provider(provider_name: str, username: str) -> OpenAIPassthroughClient:

            provider_orm = self.get_client_orm_by_provider_name_and_user(provider_name, user)
            api_key = SecretStr(provider_orm.api_key.get_secret()) if provider_orm.api_key else None

            retval = OpenAIPassthroughClient(
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
        Instantiates a OpenAIPassthroughClient for the given provider name and
        returns its passthrough handler. The key thing is that whatever handler we use
        here must implement the OpenAICompatiblePassthroughProtocol which
        returns OpenAICompatibleChatCompletionResponseType
        """

        def get_handler(
            request: Request,
            user_profile: UserProfile,
            data: dict[str, Any],
            *args,
            **kwargs,
        ) -> OpenAICompatibleChatCompletionResponseType:
            """Expose the handler method of the default provider"""

            client = self.get_openai_client_for_provider(provider_name=provider_name or self.default_handler_name, user=request.user)  # type: ignore
            handler = client.handler(request, user_profile, data, *args, **kwargs)
            return handler

        provider_name = provider_name or self.default_handler_name
        return get_handler

    def get_smarter_handler(
        self, request: Request, provider_name: Optional[str] = None, **kwargs
    ) -> SmarterChatHandlerProtocol:
        """
        A convenience method to get a handler by provider name.
        """

        def get_handler(
            user_profile: UserProfile,
            chat: Chat,
            data: Union[dict[str, Any], list],
            plugins: Optional[List[PluginBase]] = None,
            functions: Optional[list[str]] = None,
        ) -> SmarterChatCompletionResponseType:
            """Expose the handler method of the default provider"""

            client_orm = self.get_client_orm_by_provider_name_and_user(
                provider_name=provider_name or self.default_handler_name, user=request.user  # type: ignore
            )
            api_key = SecretStr(client_orm.api_key.get_secret()) if client_orm.api_key else None
            smarter_openai_compatible_provider = OpenAISmarterClient(
                provider=client_orm,
                provider_name=client_orm.name,
                base_url=client_orm.base_url,
                api_key=api_key,
                default_model=client_orm.default_model,
            )
            handler = smarter_openai_compatible_provider.handler(
                user_profile, chat, data, plugins=plugins, functions=functions
            )
            return handler

        return get_handler

    @cached_property
    def all(self) -> List[str]:
        """
        Returns a list of all provider names.
        """
        return list(Provider.objects.filter(is_active=True).values_list("name", flat=True))  # type: ignore

    def handler(
        self, request: Request, provider_name: Optional[str] = None, **kwargs
    ) -> Union[SmarterChatHandlerProtocol, OpenAICompatiblePassthroughProtocol]:
        """
        A convenience method to get a handler by provider name.
        """
        if self.client_type == ClientTypeEnum.PASSTHROUGH:
            return self.get_passthrough_handler(request=request, provider_name=provider_name, **kwargs)
        return self.get_smarter_handler(request=request, provider_name=provider_name, **kwargs)

    def default_handler(
        self, request: Request, **kwargs
    ) -> Union[SmarterChatHandlerProtocol, OpenAICompatiblePassthroughProtocol]:
        """
        A convenience method to get the default handler.
        """
        return self.handler(request=request, provider_name=self.default_handler_name, **kwargs)


smarter_compatible_client = OpenAICompatibleClientFactory(ClientTypeEnum.SMARTER)
openai_compatible_client = OpenAICompatibleClientFactory(ClientTypeEnum.PASSTHROUGH)
