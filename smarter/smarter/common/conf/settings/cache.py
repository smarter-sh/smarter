# pylint: disable=no-member,no-self-argument,unused-argument,R0801
"""The cache expiration settings."""

from typing import Optional, Union

from pydantic import BaseModel, Field

from smarter.common.conf.defaults import settings_defaults
from smarter.common.conf.util import before_field_validator, parse_int_setting


class CacheSettings(BaseModel):
    """How long cached views, prompts, llmclients and responses are kept."""

    cache_expiration: int = Field(
        settings_defaults.CACHE_EXPIRATION,
        gt=0,
        description="The cache expiration time in seconds for cached data.",
        title="Cache Expiration",
    )
    """
    Default cache expiration time for Django views that use page caching.

    See: django.views.decorators.cache.cache_control and django.views.decorators.cache.cache_page

    The cache expiration time in seconds for cached data.
    This setting defines how long cached data should be considered valid before it is
    refreshed or invalidated. A shorter expiration time may lead to more frequent
    cache refreshes, while a longer expiration time can improve performance by reducing
    the number of cache lookups.
    :type: int
    :default: Value from ``settings_defaults.CACHE_EXPIRATION``
    :raises SmarterConfigurationError: If the value is not a positive integer.
    """

    @before_field_validator("cache_expiration")
    def parse_cache_expiration(cls, v: Optional[Union[int, str]]) -> int:
        """Validates the 'cache_expiration' field.

        Args:
            v (Optional[Union[int, str]]): the cache_expiration value to validate
        Returns:
            int: The validated cache_expiration.
        """
        return parse_int_setting("cache_expiration", v, settings_defaults.CACHE_EXPIRATION, minimum=0)

    chat_cache_expiration: int = Field(
        settings_defaults.CHAT_CACHE_EXPIRATION,
        gt=0,
        description="The prompt cache expiration time in seconds for cached prompt data.",
        title="Prompt Cache Expiration",
    )
    """
    The prompt cache expiration time in seconds for cached prompt data.

    This setting defines how long cached prompt data should be considered valid before it is
    refreshed or invalidated. A shorter expiration time may lead to more frequent
    cache refreshes, while a longer expiration time can improve performance by reducing
    the number of cache lookups.

    :type: int
    :default: Value from ``settings_defaults.CHAT_CACHE_EXPIRATION``
    :raises SmarterConfigurationError: If the value is not a positive integer.

    see: :class:`smarter.apps.prompt.models.PromptHelper`
    """

    @before_field_validator("chat_cache_expiration")
    def parse_chat_cache_expiration(cls, v: Optional[Union[int, str]]) -> int:
        """Validates the 'chat_cache_expiration' field.

        Args:
            v (Optional[Union[int, str]]): the chat_cache_expiration value to validate
        Returns:
            int: The validated chat_cache_expiration.
        """
        return parse_int_setting("chat_cache_expiration", v, settings_defaults.CHAT_CACHE_EXPIRATION, minimum=0)

    prompt_response_cache_expiration: int = Field(
        settings_defaults.PROMPT_RESPONSE_CACHE_EXPIRATION,
        ge=0,
        description="Seconds to cache the LLM's answer to the first message of a conversation. 0 disables the cache.",
        title="Prompt Response Cache Expiration",
    )
    """
    Seconds to cache the LLM's answer to the first message of a conversation.

    0 disables the cache.

    A first message has no conversation before it, so the same message, sent to the same
    LLMClient, gets the same answer, e.g. one of the LLMClient's ``appExamplePrompts``. Later
    messages are never cached, because their answers depend on the conversation. See
    :mod:`smarter.apps.provider.services.text_completion.lib.prompt_cache`.

    :type: int
    :default: Value from ``settings_defaults.PROMPT_RESPONSE_CACHE_EXPIRATION``, one hour
    :raises SmarterConfigurationError: If the value is not a non-negative integer.
    """

    @before_field_validator("prompt_response_cache_expiration")
    def parse_prompt_response_cache_expiration(cls, v: Optional[Union[int, str]]) -> int:
        """Validates the 'prompt_response_cache_expiration' field.

        Args:
            v (Optional[Union[int, str]]): the prompt_response_cache_expiration value to validate
        Returns:
            int: The validated prompt_response_cache_expiration.
        """
        return parse_int_setting(
            "prompt_response_cache_expiration", v, settings_defaults.PROMPT_RESPONSE_CACHE_EXPIRATION, minimum=0
        )

    listview_cache_expiration: int = Field(
        settings_defaults.LISTVIEW_CACHE_EXPIRATION,
        gt=0,
        description="The cache expiration time in seconds for the pages of the web console's list views.",
        title="List View Cache Expiration",
    )
    """
    The cache expiration time in seconds for the pages of the web console's list views.

    Each list api caches the pages that it returns, per user. Saving or deleting a resource
    makes its list's cached pages stale at once (see :mod:`smarter.lib.django.listview`), so this
    expiration only bounds how long a change made without Django's signals, such as a
    ``QuerySet.update()``, can go unnoticed.

    :type: int
    :default: Value from ``settings_defaults.LISTVIEW_CACHE_EXPIRATION``
    :raises SmarterConfigurationError: If the value is not a positive integer.
    """

    @before_field_validator("listview_cache_expiration")
    def parse_listview_cache_expiration(cls, v: Optional[Union[int, str]]) -> int:
        """Validates the 'listview_cache_expiration' field.

        Args:
            v (Optional[Union[int, str]]): the listview_cache_expiration value to validate
        Returns:
            int: The validated listview_cache_expiration.
        """
        return parse_int_setting("listview_cache_expiration", v, settings_defaults.LISTVIEW_CACHE_EXPIRATION, minimum=0)

    llmclient_cache_expiration: int = Field(
        settings_defaults.LLM_CLIENT_CACHE_EXPIRATION,
        gt=0,
        description="The llmclient cache expiration time in seconds for cached llmclient data.",
        title="LLMClient Cache Expiration",
    )
    """
    The llmclient cache expiration time in seconds for cached llmclient data.

    This setting defines how long cached llmclient data should be considered valid before it is
    refreshed or invalidated. A shorter expiration time may lead to more frequent
    cache refreshes, while a longer expiration time can improve performance by reducing
    the number of cache lookups.

    :type: int
    :default: Value from ``settings_defaults.LLM_CLIENT_CACHE_EXPIRATION``
    :raises SmarterConfigurationError: If the value is not a positive integer.
    """

    @before_field_validator("llmclient_cache_expiration")
    def parse_llmclient_cache_expiration(cls, v: Optional[Union[int, str]]) -> int:
        """Validates the 'llmclient_cache_expiration' field.

        Args:
            v (Optional[Union[int, str]]): the llmclient_cache_expiration value to validate
        Returns:
            int: The validated llmclient_cache_expiration.
        """
        return parse_int_setting(
            "llmclient_cache_expiration", v, settings_defaults.LLM_CLIENT_CACHE_EXPIRATION, minimum=0
        )


__all__ = ["CacheSettings"]
