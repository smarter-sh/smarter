# pylint: disable=no-member,no-self-argument,unused-argument,R0801
"""The cache expiration settings."""

from typing import Optional, Union

from pydantic import BaseModel, Field

from smarter.common.conf.defaults import settings_defaults
from smarter.common.conf.util import before_field_validator, parse_int_setting


class CacheSettings(BaseModel):
    """How long cached views, prompts, llmclients and responses are kept."""

    subsystem_cache_expiration: int = Field(
        settings_defaults.SUBSYSTEM_CACHE_EXPIRATION,
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
    :default: Value from ``settings_defaults.SUBSYSTEM_CACHE_EXPIRATION``
    :raises SmarterConfigurationError: If the value is not a positive integer.
    """

    @before_field_validator("subsystem_cache_expiration")
    def parse_subsystem_cache_expiration(cls, v: Optional[Union[int, str]]) -> int:
        """Validates the 'cache_expiration' field.

        Args:
            v (Optional[Union[int, str]]): the cache_expiration value to validate
        Returns:
            int: The validated cache_expiration.
        """
        return parse_int_setting(
            "subsystem_cache_expiration", v, settings_defaults.SUBSYSTEM_CACHE_EXPIRATION, minimum=0
        )

    subsystem_cache_chat_expiration: int = Field(
        settings_defaults.SUBSYSTEM_CACHE_CHAT_EXPIRATION,
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
    :default: Value from ``settings_defaults.SUBSYSTEM_CACHE_CHAT_EXPIRATION``
    :raises SmarterConfigurationError: If the value is not a positive integer.

    see: :class:`smarter.apps.prompt.models.PromptHelper`
    """

    @before_field_validator("subsystem_cache_chat_expiration")
    def parse_subsystem_cache_chat_expiration(cls, v: Optional[Union[int, str]]) -> int:
        """Validates the 'cache_chat_expiration' field.

        Args:
            v (Optional[Union[int, str]]): the cache_chat_expiration value to validate
        Returns:
            int: The validated cache_chat_expiration.
        """
        return parse_int_setting(
            "subsystem_cache_chat_expiration", v, settings_defaults.SUBSYSTEM_CACHE_CHAT_EXPIRATION, minimum=0
        )

    subsystem_cache_prompt_response_expiration: int = Field(
        settings_defaults.SUBSYSTEM_CACHE_PROMPT_RESPONSE_EXPIRATION,
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
    :default: Value from ``settings_defaults.SUBSYSTEM_CACHE_PROMPT_RESPONSE_EXPIRATION``, one hour
    :raises SmarterConfigurationError: If the value is not a non-negative integer.
    """

    @before_field_validator("subsystem_cache_prompt_response_expiration")
    def parse_subsystem_cache_prompt_response_expiration(cls, v: Optional[Union[int, str]]) -> int:
        """Validates the 'cache_prompt_response_expiration' field.

        Args:
            v (Optional[Union[int, str]]): the cache_prompt_response_expiration value to validate
        Returns:
            int: The validated cache_prompt_response_expiration.
        """
        return parse_int_setting(
            "subsystem_cache_prompt_response_expiration",
            v,
            settings_defaults.SUBSYSTEM_CACHE_PROMPT_RESPONSE_EXPIRATION,
            minimum=0,
        )

    subsystem_cache_listview_expiration: int = Field(
        settings_defaults.SUBSYSTEM_CACHE_LISTVIEW_EXPIRATION,
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
    :default: Value from ``settings_defaults.SUBSYSTEM_CACHE_LISTVIEW_EXPIRATION``
    :raises SmarterConfigurationError: If the value is not a positive integer.
    """

    @before_field_validator("subsystem_cache_listview_expiration")
    def parse_subsystem_cache_listview_expiration(cls, v: Optional[Union[int, str]]) -> int:
        """Validates the 'cache_listview_expiration' field.

        Args:
            v (Optional[Union[int, str]]): the cache_listview_expiration value to validate
        Returns:
            int: The validated cache_listview_expiration.
        """
        return parse_int_setting(
            "subsystem_cache_listview_expiration", v, settings_defaults.SUBSYSTEM_CACHE_LISTVIEW_EXPIRATION, minimum=0
        )

    subsystem_cache_llm_client_expiration: int = Field(
        settings_defaults.SUBSYSTEM_CACHE_LLM_CLIENT_EXPIRATION,
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
    :default: Value from ``settings_defaults.SUBSYSTEM_CACHE_LLM_CLIENT_EXPIRATION``
    :raises SmarterConfigurationError: If the value is not a positive integer.
    """

    @before_field_validator("subsystem_cache_llm_client_expiration")
    def parse_subsystem_cache_llm_client_expiration(cls, v: Optional[Union[int, str]]) -> int:
        """Validates the 'cache_llm_client_expiration' field.

        Args:
            v (Optional[Union[int, str]]): the cache_llm_client_expiration value to validate
        Returns:
            int: The validated cache_llm_client_expiration.
        """
        return parse_int_setting(
            "subsystem_cache_llm_client_expiration",
            v,
            settings_defaults.SUBSYSTEM_CACHE_LLM_CLIENT_EXPIRATION,
            minimum=0,
        )


__all__ = ["CacheSettings"]
