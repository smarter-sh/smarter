# pylint: disable=no-member,no-self-argument,unused-argument,R0801
"""The settings of LLM requests, prompts, tools, plugins, extensions and the MCP server."""

from typing import Optional, Union

from pydantic import BaseModel, Field

from smarter.common.conf.const import THE_EMPTY_SET
from smarter.common.conf.defaults import settings_defaults
from smarter.common.conf.util import before_field_validator, parse_int_setting
from smarter.common.exceptions import SmarterConfigurationError


class LLMSettings(BaseModel):
    """LLM defaults, prompts, tools, plugins, extensions and the MCP server."""

    max_tool_rounds: int = Field(
        settings_defaults.MAX_TOOL_ROUNDS,
        ge=1,
        description="The most requests of one prompt that offer the LLM its tools.",
        title="Max Tool Rounds",
    )
    """
    The most requests of one prompt that offer the LLM its tools.

    An LLM often needs more than one round of tool calls, e.g. a forecast, and then an image
    search with the forecast's place, or a chain of MCP tool calls, each using the last one's
    result. One round can hold several tool calls. After this many requests with tools, the LLM
    is sent the tool results without tools, so that it answers with what it has.

    :type: int
    :default: Value from ``settings_defaults.MAX_TOOL_ROUNDS``, 5
    :raises SmarterConfigurationError: If the value is not a positive integer.

    see: :meth:`smarter.apps.provider.services.text_completion.lib.openai_compatible_chat_provider.OpenAISmarterClient.handler`
    """

    @before_field_validator("max_tool_rounds")
    def parse_max_tool_rounds(cls, v: Optional[Union[int, str]]) -> int:
        """Validates the 'max_tool_rounds' field.

        Args:
            v (Optional[Union[int, str]]): the max_tool_rounds value to validate
        Returns:
            int: The validated max_tool_rounds.
        """
        return parse_int_setting("max_tool_rounds", v, settings_defaults.MAX_TOOL_ROUNDS, minimum=1)

    prompt_history_max_age: int = Field(
        settings_defaults.PROMPT_HISTORY_MAX_AGE,
        ge=1,
        description="Days to keep chat sessions and their prompt history before they are deleted.",
        title="Prompt History Max Age",
    )
    """
    Days to keep chat sessions and their prompt history before they are deleted.

    Every prompt of a chat session (a :class:`~smarter.apps.prompt.models.Prompt`) saves a
    :class:`~smarter.apps.prompt.models.PromptHistory` row with the request, the response and
    the conversation's messages, plus a :class:`~smarter.apps.prompt.models.PromptToolCall` or
    :class:`~smarter.apps.prompt.models.PromptPluginUsage` row for each tool or plugin it used.
    Celery Beat runs :func:`~smarter.apps.prompt.tasks.purge_prompt_history` once a day, which
    deletes these rows when they are older than this, then the sessions that are older than this
    and have none left. A session that is still in use keeps its recent rows.

    Set it with ``SMARTER_PROMPT_HISTORY_MAX_AGE``.

    :type: int
    :default: Value from ``settings_defaults.PROMPT_HISTORY_MAX_AGE``, 90
    :raises SmarterConfigurationError: If the value is not a positive integer.
    """

    @before_field_validator("prompt_history_max_age")
    def parse_prompt_history_max_age(cls, v: Optional[Union[int, str]]) -> int:
        """Validates the 'prompt_history_max_age' field.

        Args:
            v (Optional[Union[int, str]]): the prompt_history_max_age value to validate
        Returns:
            int: The validated prompt_history_max_age.
        """
        return parse_int_setting("prompt_history_max_age", v, settings_defaults.PROMPT_HISTORY_MAX_AGE, minimum=1)

    plugin_max_data_results: int = Field(
        settings_defaults.PLUGIN_MAX_DATA_RESULTS,
        gt=0,
        description="A global maximum number of data row results that can be returned by any Smarter plugin.",
        title="Plugin Max Data Results",
    )
    """
    A global maximum number of data row results that can be returned by any Smarter plugin.

    This setting helps to prevent excessive data retrieval that could impact performance
    or lead to resource exhaustion. Plugins should respect this limit when querying
    data sources and returning results to ensure efficient operation of the platform.
    :type: int
    :default: Value from ``settings_defaults.PLUGIN_MAX_DATA_RESULTS``
    :raises SmarterConfigurationError: If the value is not a positive integer.
    """

    @before_field_validator("plugin_max_data_results")
    def parse_plugin_max_data_results(cls, v: Optional[Union[int, str]]) -> int:
        """Validates the 'plugin_max_data_results' field.

        Args:
            v (Optional[Union[int, str]]): the plugin_max_data_results value to validate
        Returns:
            int: The validated plugin_max_data_results.
        """
        return parse_int_setting("plugin_max_data_results", v, settings_defaults.PLUGIN_MAX_DATA_RESULTS, minimum=0)

    extension_registry_url: str = Field(
        settings_defaults.EXTENSION_REGISTRY_URL,
        description="The url of the Smarter Extension registry's signed index, index.json.",
        examples=["https://smarter-sh.github.io/extensions-registry/index.json"],
        title="Extension Registry URL",
    )
    """
    The url of the Smarter Extension registry's index.

    The registry lists the extensions that administrators may install from the Django admin
    console, their versions, and their publishers' trust badges. The platform checks it daily
    for updates to installed extensions. Its signature, at the same url with ``.sig``
    appended, is verified with :attr:`extension_registry_public_key`.
    :type: str
    :default: Value from ``settings_defaults.EXTENSION_REGISTRY_URL``
    """

    @before_field_validator("extension_registry_url")
    def validate_extension_registry_url(cls, v: Optional[str]) -> str:
        """Validates the 'extension_registry_url' field: an https url, or the default if empty.

        Args:
            v (Optional[str]): the url.

        Returns:
            str: The validated url.
        """
        if v is None or str(v).strip() == "":
            return settings_defaults.EXTENSION_REGISTRY_URL
        v = str(v).strip()
        if not v.startswith("https://"):
            raise SmarterConfigurationError(f"extension_registry_url {v} must be an https url.")
        return v

    extension_registry_public_key: str = Field(
        settings_defaults.EXTENSION_REGISTRY_PUBLIC_KEY,
        description="The base64 Ed25519 public key that verifies the extension registry's index. Empty disables the registry.",
        title="Extension Registry Public Key",
    )
    """
    The Ed25519 public key, base64, that verifies the signature of the extension registry's index.

    It is public, not a secret. While it is empty, the registry is disabled: extensions can
    only be installed from uploaded archives, and updates are not checked.
    :type: str
    :default: Value from ``settings_defaults.EXTENSION_REGISTRY_PUBLIC_KEY``
    """

    mcpserver_rate_limit: int = Field(
        settings_defaults.MCPSERVER_RATE_LIMIT,
        ge=0,
        description="The maximum number of requests per minute that one client IP address may send to the MCPServer's endpoints. 0 disables the limit.",
        title="MCP Server Rate Limit",
    )
    """
    The maximum number of requests per minute that one client IP address may send to the MCPServer's endpoints.

    The MCPServer, :mod:`smarter.apps.mcpserver`, serves its public tools without authentication, so the limit
    protects the platform's database from a client that floods it. Requests beyond the limit
    are answered ``429 Too Many Requests`` until the minute ends. The platform's own
    MCPClients count too: they connect from the platform's egress addresses, and each tool
    call is about three requests, so set the limit well above the platform's own traffic.
    0 disables the limit.
    :type: int
    :default: Value from ``settings_defaults.MCPSERVER_RATE_LIMIT``
    :raises SmarterConfigurationError: If the value is not a non-negative integer.
    """

    @before_field_validator("mcpserver_rate_limit")
    def parse_mcpserver_rate_limit(cls, v: Optional[Union[int, str]]) -> int:
        """Validates the 'mcpserver_rate_limit' field.

        Args:
            v (Optional[Union[int, str]]): the mcpserver_rate_limit value to validate
        Returns:
            int: The validated mcpserver_rate_limit.
        """
        return parse_int_setting("mcpserver_rate_limit", v, settings_defaults.MCPSERVER_RATE_LIMIT, minimum=0)

    llm_default_provider: str = Field(
        settings_defaults.LLM_DEFAULT_PROVIDER,
        description="The default LLM provider to use for language model interactions.",
        examples=["openai", "anthropic", "gemini", "llama"],
        title="Default LLM Provider",
    )
    """
    The default LLM provider to use for language model interactions.

    This setting specifies which language model provider should be used by default
    for processing natural language tasks. It determines the backend service that
    will handle requests for language generation, understanding, and other related functions.

    :type: str
    :default: Value from ``settings_defaults.LLM_DEFAULT_PROVIDER``
    :raises SmarterConfigurationError: If the value is not a valid LLM provider name
    """

    @before_field_validator("llm_default_provider")
    def validate_llm_default_provider(cls, v: Optional[str]) -> Optional[str]:
        """Validates the `llm_default_provider` field.

        Args:
            v (Optional[str]): The LLM default provider value to validate.

        Returns:
            Optional[str]: The validated LLM default provider.
        """
        if str(v) in THE_EMPTY_SET and settings_defaults.LLM_DEFAULT_PROVIDER is not None:
            return settings_defaults.LLM_DEFAULT_PROVIDER

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"llm_default_provider of type {type(v)} is not a str: {v}")
        return v

    llm_default_system_role: str = Field(
        settings_defaults.LLM_DEFAULT_SYSTEM_ROLE,
        description="The default system role prompt to use for language model interactions.",
        examples=["You are a helpful llmclient..."],
        title="Default LLM System Role",
    )
    """
    The default system role prompt to use for language model interactions.

    This setting provides the default system role prompt that guides the behavior
    of the language model during interactions. It helps define the context and
    tone of the responses generated by the model.

    :type: str
    :default: Value from ``settings_defaults.LLM_DEFAULT_SYSTEM_ROLE``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("llm_default_system_role")
    def validate_llm_default_system_role(cls, v: Optional[str]) -> Optional[str]:
        """Validates the `llm_default_system_role` field.

        Args:
            v (Optional[str]): The LLM default system role value to validate.

        Returns:
            Optional[str]: The validated LLM default system role.
        """
        if str(v) in THE_EMPTY_SET and settings_defaults.LLM_DEFAULT_SYSTEM_ROLE is not None:
            return settings_defaults.LLM_DEFAULT_SYSTEM_ROLE

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"llm_default_system_role of type {type(v)} is not a str: {v}")
        return v

    llm_default_temperature: float = Field(
        settings_defaults.LLM_DEFAULT_TEMPERATURE,
        description="The default temperature to use for language model interactions.",
        examples=[0.0, 0.5, 1.0],
        title="Default LLM Temperature",
    )
    """
    The default temperature to use for language model interactions.

    This setting controls the randomness of the language model's output.
    A lower temperature (e.g., 0.0) results in more deterministic and focused
    responses, while a higher temperature (e.g., 1.0) produces more diverse
    and creative outputs.

    :type: float
    :default: Value from ``settings_defaults.LLM_DEFAULT_TEMPERATURE``
    :raises SmarterConfigurationError: If the value is not a float between 0.
    """

    @before_field_validator("llm_default_temperature")
    def validate_openai_default_temperature(cls, v: Optional[float]) -> float:
        """Validates the `llm_default_temperature` field.

        Args:
            v (Optional[float]): The LLM default temperature value to validate.
        Returns:
            float: The validated LLM default temperature.
        """
        if isinstance(v, float):
            return v
        if v in THE_EMPTY_SET:
            return settings_defaults.LLM_DEFAULT_TEMPERATURE
        try:
            retval = float(v)  # type: ignore
            return retval
        except (TypeError, ValueError) as e:
            raise SmarterConfigurationError(f"llm_default_temperature of type {type(v)} is not a float: {v}") from e

    llm_default_max_tokens: int = Field(
        settings_defaults.LLM_DEFAULT_MAX_TOKENS,
        ge=1,
        description="The default maximum number of tokens to generate for language model interactions.",
        examples=[256, 512, 1024, 2048],
        title="Default LLM Max Tokens",
    )
    """
    The default maximum number of tokens to generate for language model interactions.

    This setting specifies the upper limit on the number of tokens that the language
    model can generate in response to a single request. It helps control the length
    of the output and manage resource usage.

    :type: int
    :default: Value from ``settings_defaults.LLM_DEFAULT_MAX_TOKENS``
    :raises SmarterConfigurationError: If the value is not a positive integer.
    """

    @before_field_validator("llm_default_max_tokens")
    def validate_openai_default_max_completion_tokens(cls, v: Optional[Union[int, str]]) -> int:
        """Validates the `llm_default_max_tokens` field.

        Args:
            v (Optional[int]): The LLM default max tokens value to validate.

        Returns:
            int: The validated LLM default max tokens.
        """
        return parse_int_setting("llm_default_max_tokens", v, settings_defaults.LLM_DEFAULT_MAX_TOKENS)

    prompt_threads: int = Field(
        settings_defaults.PROMPT_THREADS,
        ge=1,
        description="The threads in each web server process that run streamed chat prompts.",
        title="Prompt Threads",
    )
    """
    The threads in each web server process that run streamed chat prompts, at most.

    A prompt holds its thread for as long as it runs, mostly waiting on the LLM and its tools, so
    the threads are cheap. A process runs this many prompts at once, and queues the next ones. The
    pool is the prompts' own, apart from the event loop's default executor, where Django renders
    error pages and asyncio resolves host names. See :func:`smarter.apps.prompt.progress.prompt_executor`.

    Set it with ``SMARTER_PROMPT_THREADS``.

    :type: int
    :default: Value from ``settings_defaults.PROMPT_THREADS``, 32 if it is not set.
    :raises SmarterConfigurationError: If the value is not a positive integer.
    """

    @before_field_validator("prompt_threads")
    def parse_prompt_threads(cls, v: Optional[Union[int, str]]) -> int:
        """Validates the 'prompt_threads' field.

        Args:
            v (Optional[Union[int, str]]): the prompt_threads value to validate
        Returns:
            int: The validated prompt_threads.
        """
        return parse_int_setting("prompt_threads", v, settings_defaults.PROMPT_THREADS)


__all__ = ["LLMSettings"]
