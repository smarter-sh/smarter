"""
A chat provider convenience class. This class is a collection of all the chat providers and their handlers.
It also provides a default provider and handler.

There are a few objectives of this class:
1. To provide a single point of access to all the chat providers.
2. To hide complexity introduced into the provider classes due to Pydantic models.
3. To provide a default provider and handler.
"""

import logging
from functools import cached_property
from typing import Any, List, Optional, Union

from pydantic import SecretStr
from rest_framework.request import Request

from smarter.apps.account.models import User, UserProfile
from smarter.apps.plugin.plugin.base import PluginBase
from smarter.apps.prompt.models import Chat
from smarter.apps.provider.clients import SmarterOpenAIClient
from smarter.apps.provider.models import Provider
from smarter.apps.provider.services.text_completion.const import (
    VALID_CHAT_COMPLETION_MODELS,
)
from smarter.apps.provider.services.text_completion.lib.openai_compatible_chat_provider import (
    SmarterOpenAICompatibleChatProvider,
)
from smarter.common.conf import smarter_settings
from smarter.common.exceptions import SmarterValueError
from smarter.common.mixins import SmarterHelperMixin
from smarter.lib.cache import cache_results
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

from .lib.protocols import (
    OpenAICompatiblePassthroughProtocol,
    SmarterChatCompletionResponseType,
    SmarterChatHandlerProtocol,
)
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

            BASE_URL = "https://api.openai.com/v1/"  # don't forget the trailing slash
            DEFAULT_MODEL = "gpt-4o-mini"

            smarter_openai_compatible_provider = SmarterOpenAICompatibleChatProvider(
                provider=OPENAI_PROVIDER_NAME,
                base_url=BASE_URL,
                api_key=smarter_settings.openai_api_key.get_secret_value(),
                default_model=DEFAULT_MODEL,
                default_system_role=smarter_settings.llm_default_system_role,
                default_temperature=smarter_settings.llm_default_temperature,
                default_max_tokens=smarter_settings.llm_default_max_tokens,
                valid_chat_completion_models=VALID_CHAT_COMPLETION_MODELS,
                add_built_in_tools=False,
            )
            result = smarter_openai_compatible_provider.handler(
                user_profile, chat, data, plugins=plugins, functions=functions
            )
            return result

        return get_handler


smarter_compatible_chat_providers = OpenAICompatibleClientFactory()
openai_compatible_client = OpenAICompatibleClientFactory()
