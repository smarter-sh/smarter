# pylint: disable=no-member,no-self-argument,unused-argument,R0801
"""The cache settings: Redis's password, and how long cached data is kept."""

from typing import Annotated, Optional, Union

from pydantic import BaseModel, Field, SecretStr, model_validator

from smarter.common.conf.const import THE_EMPTY_SET
from smarter.common.conf.credentials import RestrictedWorkerCredential
from smarter.common.conf.env import is_missing_value
from smarter.common.conf.util import (
    before_field_validator,
    field_default,
    has_field,
    input_value,
    parse_int_setting,
    with_derived_default,
)
from smarter.common.const import SmarterEnvironments
from smarter.common.exceptions import SmarterConfigurationError

LOCAL_REDIS_PASSWORD = "smarter"
"""The password of docker-compose.yml's smarter-redis service, the local environment's default."""

TOOL_WORKER_REDIS_USERNAME = "tools"
"""
The Redis ACL user of the tool worker, ``smarter-worker-tools`` (ADR-030, rule 8).

The Helm chart's ``redis.master.preExecCmds`` and both docker-compose files define it, with the same rules.
"""

LOCAL_TOOL_WORKER_REDIS_PASSWORD = "smarter-tools"
"""The password of :data:`TOOL_WORKER_REDIS_USERNAME` in docker-compose.yml and docker-compose.shard.yml."""

EXTENSION_WORKER_REDIS_USERNAME = "extensions"
"""
The Redis ACL user of the Extension worker, ``smarter-worker-extensions`` (issue #1077).

It reaches only the Extensions queue, the results and Extensions' archives, so an Extension's code can't read the
tool worker's queue, where API, SQL and MCP calls wait with their credentials. Defined like
:data:`TOOL_WORKER_REDIS_USERNAME`.
"""

LOCAL_EXTENSION_WORKER_REDIS_PASSWORD = "smarter-extensions"
"""The password of :data:`EXTENSION_WORKER_REDIS_USERNAME` in docker-compose.yml and docker-compose.shard.yml."""


class CacheSettings(BaseModel):
    """Redis's password, and how long cached views, prompts, llmclients and responses are kept."""

    subsystem_redis_username: Optional[str] = Field(
        None,
        description="The Redis ACL user that this process authenticates as, or empty for Redis's default user.",
        examples=["tools"],
        title="Redis Username",
    )
    """
    The Redis ACL user that this process authenticates as.

    Every process but the tool worker uses Redis's ``default`` user, which may do anything. The tool worker
    is given its own user, ``tools`` (:data:`TOOL_WORKER_REDIS_USERNAME`), which may touch only its own
    queue, its results, Extensions' archives and a few cache keys (ADR-030, rule 8), with
    :attr:`subsystem_redis_password` set to that user's password.

    Set it with ``SMARTER_SUBSYSTEM_REDIS_USERNAME``.

    :type: Optional[str]
    :default: None, Redis's ``default`` user.
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("subsystem_redis_username")
    def validate_subsystem_redis_username(cls, v: Optional[str]) -> Optional[str]:
        """
        Validate ``subsystem_redis_username``.

        :param v: The username, or empty for the ``default`` user.
        :returns: The username, or None.
        :raises SmarterConfigurationError: If the value is not a string.
        """
        if v in THE_EMPTY_SET or is_missing_value(v):
            return None
        if not isinstance(v, str):
            raise SmarterConfigurationError(f"subsystem_redis_username of type {type(v)} is not a str")
        username = v.strip()
        if not username:
            return None
        return username

    # the one credential that the tool worker and the Extension worker may hold: their own Redis user's password.
    subsystem_redis_password: Annotated[Optional[SecretStr], RestrictedWorkerCredential()] = Field(
        None,
        description="The password of the platform's Redis: the Celery broker, the cache and the sessions.",
        examples=["your-redis-password"],
        title="Redis Password",
    )
    """
    The password of the platform's Redis, which holds the Celery broker, RedBeat's schedule, the cache and the.

    sessions.

    Set it with ``SMARTER_SUBSYSTEM_REDIS_PASSWORD``. On a cluster that smarter-infrastructure built, the Helm
    chart reads it from the Kubernetes Secret ``smarter-redis-password``, which smarter-infrastructure
    generates, and gives the same Secret to its Redis. :mod:`smarter.settings.base_aws` builds the broker's,
    RedBeat's and the caches' urls from it, and :meth:`~smarter.common.conf.settings.Settings.require_redis_password`
    refuses to start without it outside the local environment (ADR-030, rule 5).

    In the local environment it defaults to the password of docker-compose.yml's smarter-redis service.
    Elsewhere there is no default: a missing password, or a placeholder such as ``SET-ME-PLEASE``, is None.

    :type: Optional[SecretStr]
    :default: ``"smarter"`` in the local environment, and None elsewhere. See :meth:`derive_cache_defaults`.
    :raises SmarterConfigurationError: If the value is not a SecretStr.
    """

    @before_field_validator("subsystem_redis_password")
    def validate_subsystem_redis_password(cls, v: Optional[Union[SecretStr, str]]) -> Optional[SecretStr]:
        """
        Validate ``subsystem_redis_password``.

        :param v: The password, or empty for the default.
        :returns: The password, or None if it is missing or a placeholder.
        :raises SmarterConfigurationError: If the value is not a SecretStr.
        """
        if v in THE_EMPTY_SET:
            v = field_default(cls, "subsystem_redis_password")
        if isinstance(v, str):
            v = SecretStr(v)
        if is_missing_value(v):
            return None
        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError(f"subsystem_redis_password of type {type(v)} is not a SecretStr")
        return v

    @model_validator(mode="before")
    @classmethod
    def derive_cache_defaults(cls, data: object) -> object:
        """
        Derive the local environment's Redis password, unless it is set.

        In the local environment, the password is docker-compose.yml's smarter-redis service's,
        ``smarter``. Elsewhere there is no default.

        :param data: The values to validate: the constructor's and the environment's.
        :returns: The values, with the derived default added in the local environment.
        """
        if not has_field(cls, "environment"):
            return data
        environment = input_value(cls, data, "environment")
        if environment != SmarterEnvironments.LOCAL:
            return data
        return with_derived_default(data, "subsystem_redis_password", LOCAL_REDIS_PASSWORD)

    subsystem_cache_expiration: int = Field(
        60 * 1,
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
    :default: ``60 * 1``
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
            "subsystem_cache_expiration", v, field_default(cls, "subsystem_cache_expiration"), minimum=0
        )

    subsystem_cache_chat_expiration: int = Field(
        60 * 5,
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
    :default: ``60 * 5``
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
            "subsystem_cache_chat_expiration", v, field_default(cls, "subsystem_cache_chat_expiration"), minimum=0
        )

    subsystem_cache_prompt_response_expiration: int = Field(
        60 * 60,
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
    :default: one hour
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
            field_default(cls, "subsystem_cache_prompt_response_expiration"),
            minimum=0,
        )

    subsystem_cache_listview_expiration: int = Field(
        60 * 60,
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
    :default: ``60 * 60``
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
            "subsystem_cache_listview_expiration",
            v,
            field_default(cls, "subsystem_cache_listview_expiration"),
            minimum=0,
        )

    subsystem_cache_llm_client_expiration: int = Field(
        60 * 5,
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
    :default: ``60 * 5``
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
            field_default(cls, "subsystem_cache_llm_client_expiration"),
            minimum=0,
        )


__all__ = [
    "EXTENSION_WORKER_REDIS_USERNAME",
    "LOCAL_EXTENSION_WORKER_REDIS_PASSWORD",
    "LOCAL_REDIS_PASSWORD",
    "LOCAL_TOOL_WORKER_REDIS_PASSWORD",
    "TOOL_WORKER_REDIS_USERNAME",
    "CacheSettings",
]
