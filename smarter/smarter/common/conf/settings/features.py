# pylint: disable=no-member,no-self-argument,unused-argument,R0801
"""The settings that turn platform features, debugging and logging on and off."""

import logging
from typing import Optional, Union

from pydantic import BaseModel, Field, ValidationInfo, model_validator

from smarter.common.conf.const import THE_EMPTY_SET
from smarter.common.conf.util import before_field_validator, field_default
from smarter.common.exceptions import SmarterConfigurationError


class FeatureSettings(BaseModel):
    """Feature flags, debugging and logging."""

    debug_mode: bool = Field(
        False,
        description="True if debug mode is enabled. This enables verbose logging and other debug features.",
        title="Debug Mode",
    )
    """
    True if debug mode is enabled.

    This enables verbose logging and other debug features.

    When debug mode is enabled, the platform will log additional information useful for
    troubles hooting and development. This may include detailed error messages, stack traces, and
    other diagnostic data that can help identify issues during development or testing.

    :type: bool
    :default: ``False``
    :raises SmarterConfigurationError: If the value is not a boolean.
    """

    @before_field_validator("debug_mode")
    def parse_debug_mode(cls, v: Optional[Union[bool, str]]) -> bool:
        """Validates the 'debug_mode' field.

        Args:
            v (Union[bool, str]): the debug_mode value to validate

        Returns:
            bool: The validated debug_mode.
        """
        if isinstance(v, bool):
            return v
        if v in THE_EMPTY_SET:
            return field_default(cls, "debug_mode")
        if isinstance(v, str):
            return v.lower() in ["true", "1", "t", "y", "yes"]

        raise SmarterConfigurationError(f"could not validate debug_mode: {v}")

    dump_defaults: bool = Field(
        False,
        description="True if default values should be dumped for debugging purposes.",
        title="Dump Defaults",
    )
    """
    True if default values should be dumped for debugging purposes.

    When enabled, the platform will log or output the default configuration values
    used during initialization. This can help developers and administrators
    understand the effective configuration of the system, especially when
    trouble shooting issues related to settings.

    :type: bool
    :default: ``False``
    :raises SmarterConfigurationError: If the value is not a boolean.
    """

    @before_field_validator("dump_defaults")
    def parse_dump_defaults(cls, v: Optional[Union[bool, str]]) -> bool:
        """Validates the 'dump_defaults' field.

        Args:
            v (Optional[Union[bool, str]]): the dump_defaults value to validate

        Returns:
            bool: The validated dump_defaults.
        """
        if isinstance(v, bool):
            return v
        if v in THE_EMPTY_SET:
            return field_default(cls, "dump_defaults")
        if isinstance(v, str):
            return v.lower() in ["true", "1", "t", "y", "yes"]

        raise SmarterConfigurationError(f"could not validate dump_defaults: {v}")

    # new in 0.13.26
    # True if developer mode is enabled. Used as a means to configure a production
    # Docker container to run locally for student use.
    developer_mode: bool = Field(
        False,
        description="True if developer mode is enabled. Used as a means to configure a production Docker container to run locally for student use.",
        title="Developer Mode",
    )
    """
    True if developer mode is enabled.

    Used as a means to configure a production Docker container to run locally for student use.
    When developer mode is enabled, certain restrictions or configurations that are typical
    of a production environment may be relaxed or altered to facilitate local development
    and testing. This allows developers to work with a production-like setup without the
    constraints that would normally apply in a live environment.

    :type: bool
    :default: ``False``
    :raises SmarterConfigurationError: If the value is not a boolean.
    """

    @before_field_validator("developer_mode")
    def parse_developer_mode(cls, v: Optional[Union[bool, str]]) -> bool:
        """Validates the 'developer_mode' field.

        Args:
            v (Optional[Union[bool, str]]): the developer_mode value to validate
        Returns:
            bool: The validated developer_mode.
        """
        if isinstance(v, bool):
            return v
        if v in THE_EMPTY_SET:
            return field_default(cls, "developer_mode")
        if isinstance(v, str):
            return v.lower() in ["true", "1", "t", "y", "yes"]

        raise SmarterConfigurationError(f"could not validate developer_mode: {v}")

    app_dashboard_manifest_dropzone_enable: bool = Field(
        True,
        description="True if the file drop zone feature is enabled based on the current environment.",
        title="Enable File Drop Zone",
    )
    """Determines if the file drop zone feature is enabled based on the current environment.

    Returns:
        bool: True if the file drop zone is enabled, False otherwise.
    """

    @before_field_validator("app_dashboard_manifest_dropzone_enable")
    def parse_app_dashboard_manifest_dropzone_enable(cls, v: Optional[Union[bool, str]]) -> bool:
        """Validates the 'app_dashboard_manifest_dropzone_enable' field.

        Args:
            v (Optional[Union[bool, str]]): the app_dashboard_manifest_dropzone_enable value to validate
        Returns:
            bool: The validated app_dashboard_manifest_dropzone_enable.
        """
        if isinstance(v, bool):
            return v
        if v in THE_EMPTY_SET:
            return field_default(cls, "app_dashboard_manifest_dropzone_enable")
        if isinstance(v, str):
            return v.lower() in ["true", "1", "t", "y", "yes"]

        raise SmarterConfigurationError(f"could not validate app_dashboard_manifest_dropzone_enable: {v}")

    # -------------------------------------------------------------------------
    # One flag per SAM resource app. Each one mounts, or leaves out, the app's
    # web console urls. See smarter.urls.console. All of them default to True.
    # -------------------------------------------------------------------------
    app_connection_enable: bool = Field(
        True,
        description="True if the web console serves the Connection pages. Set with SMARTER_APP_CONNECTION_ENABLE.",
        title="Enable Connection",
    )
    """True if the web console serves the Connection pages, under ``/connection/``.

    :type: bool
    :default: True unless ``SMARTER_APP_CONNECTION_ENABLE`` is false.
    """

    app_guardrail_enable: bool = Field(
        True,
        description="True if the web console serves the Guardrail pages. Set with SMARTER_APP_GUARDRAIL_ENABLE.",
        title="Enable Guardrail",
    )
    """True if the web console serves the Guardrail pages, under ``/guardrail/``.

    :type: bool
    :default: True unless ``SMARTER_APP_GUARDRAIL_ENABLE`` is false.
    """

    app_llmclient_enable: bool = Field(
        True,
        description="True if the web console serves the LLMClient pages. Set with SMARTER_APP_LLMCLIENT_ENABLE.",
        title="Enable LLMClient",
    )
    """True if the web console serves the LLMClient pages, under ``/llmclient/``.

    It doesn't affect the chat and config endpoints of LLMClients on their custom domains.

    :type: bool
    :default: True unless ``SMARTER_APP_LLMCLIENT_ENABLE`` is false.
    """

    app_llmhost_enable: bool = Field(
        True,
        description="True if the web console serves the LLMHost pages. Set with SMARTER_APP_LLMHOST_ENABLE.",
        title="Enable LLMHost",
    )
    """True if the web console serves the LLMHost pages, under ``/llmhost/``.

    :type: bool
    :default: True unless ``SMARTER_APP_LLMHOST_ENABLE`` is false.
    """

    app_llmtool_enable: bool = Field(
        True,
        description="True if the web console serves the LLMTool and Extension pages. Set with SMARTER_APP_LLMTOOL_ENABLE.",
        title="Enable LLMTool",
    )
    """True if the web console serves the LLMTool pages, under ``/llm-tools/``, and the Extension pages.

    :type: bool
    :default: True unless ``SMARTER_APP_LLMTOOL_ENABLE`` is false.
    """

    app_mcpclient_enable: bool = Field(
        True,
        description="True if the web console serves the MCPClient pages. Set with SMARTER_APP_MCPCLIENT_ENABLE.",
        title="Enable MCPClient",
    )
    """True if the web console serves the MCPClient pages, under ``/mcpclient/``.

    :type: bool
    :default: True unless ``SMARTER_APP_MCPCLIENT_ENABLE`` is false.
    """

    app_orchestrator_enable: bool = Field(
        True,
        description="True if the web console serves the Orchestrator pages. Set with SMARTER_APP_ORCHESTRATOR_ENABLE.",
        title="Enable Orchestrator",
    )
    """True if the web console serves the Orchestrator pages, under ``/orchestrator/``.

    :type: bool
    :default: True unless ``SMARTER_APP_ORCHESTRATOR_ENABLE``
        is false.
    """

    app_provider_enable: bool = Field(
        True,
        description="True if the web console serves the Provider pages. Set with SMARTER_APP_PROVIDER_ENABLE.",
        title="Enable Provider",
    )
    """True if the web console serves the Provider pages, under ``/provider/``.

    :type: bool
    :default: True unless ``SMARTER_APP_PROVIDER_ENABLE`` is false.
    """

    app_secret_enable: bool = Field(
        True,
        description="True if the web console serves the Secret pages. Set with SMARTER_APP_SECRET_ENABLE.",
        title="Enable Secret",
    )
    """True if the web console serves the Secret pages, under ``/secret/``.

    :type: bool
    :default: True unless ``SMARTER_APP_SECRET_ENABLE`` is false.
    """

    app_vectorsearch_enable: bool = Field(
        True,
        description="True if the web console serves the VectorSearch pages. Set with SMARTER_APP_VECTORSEARCH_ENABLE.",
        title="Enable VectorSearch",
    )
    """True if the web console serves the VectorSearch pages, under ``/vectorsearch/``.

    :type: bool
    :default: True unless ``SMARTER_APP_VECTORSEARCH_ENABLE``
        is false.
    """

    app_vectorstore_enable: bool = Field(
        True,
        description="True if the vectorstore feature is enabled based on the current environment.",
        title="Enable Vectorstore",
    )
    """Determines if the vectorstore feature is enabled based on the current environment.

    It mounts the VectorStore web console pages, under ``/vectorstore/``, and its api endpoints.

    Returns:
        bool: True if the vectorstore is enabled, False otherwise.
    """

    app_proxy_enable: bool = Field(
        True,
        description="True if the proxy feature is enabled based on the current environment.",
        title="Enable Proxy",
    )
    """Determines if the proxy feature is enabled based on the current environment.

    It mounts the Proxy web console pages, under ``/proxy/``, and its api endpoints.

    Returns:
        bool: True if the proxy is enabled, False otherwise.
    """

    @before_field_validator(
        "app_connection_enable",
        "app_guardrail_enable",
        "app_llmclient_enable",
        "app_llmhost_enable",
        "app_llmtool_enable",
        "app_mcpclient_enable",
        "app_orchestrator_enable",
        "app_provider_enable",
        "app_proxy_enable",
        "app_secret_enable",
        "app_vectorsearch_enable",
        "app_vectorstore_enable",
    )
    def parse_enable_sam_app(cls, v: Optional[Union[bool, str]], info: ValidationInfo) -> bool:
        """
        Validate one of the SAM apps' ``enable_<app>`` flags.

        An empty value falls back to the field's default, True for every one of them.

        :param v: The value to validate.
        :param info: Pydantic's validation info, which names the field.
        :returns: The validated flag.
        :raises SmarterConfigurationError: If the value is neither a boolean nor a string.
        """
        field_name = str(info.field_name)
        if isinstance(v, bool):
            return v
        if v in THE_EMPTY_SET:
            default = field_default(cls, field_name)
            return bool(default)
        if isinstance(v, str):
            return v.lower() in ["true", "1", "t", "y", "yes"]

        raise SmarterConfigurationError(f"could not validate {field_name}: {v}")

    app_dashboard_server_logs_enable: bool = Field(
        True,
        description="True if the terminal app feature is enabled based on the current environment.",
        title="Enabled Terminal App",
    )
    """Determines if the terminal app feature is enabled based on the current environment.

    Returns:
        bool: True if the terminal app is enabled, False otherwise.
    """

    @before_field_validator("app_dashboard_server_logs_enable")
    def parse_enabled_terminal_app(cls, v: Optional[Union[bool, str]]) -> bool:
        """Validates the 'app_dashboard_server_logs_enable' field.

        Args:
            v (Optional[Union[bool, str]]): the app_dashboard_server_logs_enable value to validate
        Returns:
            bool: The validated app_dashboard_server_logs_enable.
        """
        if isinstance(v, bool):
            return v
        if v in THE_EMPTY_SET:
            return field_default(cls, "app_dashboard_server_logs_enable")
        if isinstance(v, str):
            return v.lower() in ["true", "1", "t", "y", "yes"]

        raise SmarterConfigurationError(f"could not validate app_dashboard_server_logs_enable: {v}")

    app_dashboard_web_console_terminal_enable: bool = Field(
        False,
        description=(
            "True if superusers can open a bash shell inside the server's container from the web console's "
            "Terminal page. Off by default."
        ),
        title="Enable Web Console Terminal",
    )
    """Determines whether superusers can open a bash shell inside the server's container from the web console.

    The shell runs as the server's own operating system user, with the server's environment and
    credentials, inside whichever server process (and so whichever pod or container) accepted the
    connection. See :mod:`smarter.apps.dashboard.views.terminal_emulator.api.consumers`.

    Set with ``SMARTER_APP_DASHBOARD_WEB_CONSOLE_TERMINAL_ENABLE``. Defaults to False.

    Returns:
        bool: True if the web console terminal is enabled, False otherwise.
    """

    @before_field_validator("app_dashboard_web_console_terminal_enable")
    def parse_app_dashboard_web_console_terminal_enable(cls, v: Optional[Union[bool, str]]) -> bool:
        """Validates the 'app_dashboard_web_console_terminal_enable' field.

        Args:
            v (Optional[Union[bool, str]]): the app_dashboard_web_console_terminal_enable value to validate
        Returns:
            bool: The validated app_dashboard_web_console_terminal_enable.
        """
        if isinstance(v, bool):
            return v
        if v in THE_EMPTY_SET:
            return field_default(cls, "app_dashboard_web_console_terminal_enable")
        if isinstance(v, str):
            return v.lower() in ["true", "1", "t", "y", "yes"]

        raise SmarterConfigurationError(f"could not validate app_dashboard_web_console_terminal_enable: {v}")

    platform_static_files_on_cdn: bool = Field(
        False,
        description=(
            "True if the platform's static files, the web console's scripts among them, are uploaded to the "
            "environment's S3 bucket and served from its CDN. Off by default: the server serves them."
        ),
        title="Static Files on the CDN",
    )
    """Determines whether the static files are served from the environment's CDN, rather than by the server.

    When true, ``initialize_platform`` uploads them to the environment's S3 bucket, under ``static/``, on each
    deployment, and ``STATIC_URL`` is the CDN's, e.g. ``https://cdn.platform.example.com/static/``. Pages,
    cookies and the api stay on the platform's own host: only static files come from the CDN. It needs AWS,
    and is ignored, with a warning, without it. See :doc:`ADR-035 </adr/035-single-page-app>`.

    Set with ``SMARTER_PLATFORM_STATIC_FILES_ON_CDN``. Defaults to False.

    Returns:
        bool: True if the static files are served from the CDN, False otherwise.
    """

    @before_field_validator("platform_static_files_on_cdn")
    def parse_platform_static_files_on_cdn(cls, v: Optional[Union[bool, str]]) -> bool:
        """Validates the 'static_files_on_cdn' field.

        Args:
            v (Optional[Union[bool, str]]): the static_files_on_cdn value to validate
        Returns:
            bool: The validated static_files_on_cdn.
        """
        if isinstance(v, bool):
            return v
        if v in THE_EMPTY_SET:
            return field_default(cls, "platform_static_files_on_cdn")
        if isinstance(v, str):
            return v.lower() in ["true", "1", "t", "y", "yes"]

        raise SmarterConfigurationError(f"could not validate static_files_on_cdn: {v}")

    app_dashboard_passthrough_prompt_enable: bool = Field(
        True,
        description="True if the passthrough prompt feature is enabled based on the current environment.",
        title="Enable Passthrough Prompt",
    )
    """Determines if the passthrough prompt feature is enabled based on the current environment.

    Returns:
        bool: True if the passthrough prompt is enabled, False otherwise.
    """

    @before_field_validator("app_dashboard_passthrough_prompt_enable")
    def parse_app_dashboard_passthrough_prompt_enable(cls, v: Optional[Union[bool, str]]) -> bool:
        """Validates the 'app_dashboard_passthrough_prompt_enable' field.

        Args:
            v (Optional[Union[bool, str]]): the app_dashboard_passthrough_prompt_enable value to validate
        Returns:
            bool: The validated app_dashboard_passthrough_prompt_enable.
        """
        if isinstance(v, bool):
            return v
        if v in THE_EMPTY_SET:
            return field_default(cls, "app_dashboard_passthrough_prompt_enable")
        if isinstance(v, str):
            return v.lower() in ["true", "1", "t", "y", "yes"]

        raise SmarterConfigurationError(f"could not validate app_dashboard_passthrough_prompt_enable: {v}")

    log_level: int = Field(
        logging.INFO,
        ge=0,
        le=50,
        description="The platform's Python logging level: DEBUG, INFO, WARNING, ERROR or CRITICAL, or its number. Set with SMARTER_LOG_LEVEL.",
        examples=["DEBUG", "INFO", logging.WARNING],
        title="Logging Level",
    )
    """
    The platform's Python logging level, e.g. ``logging.INFO``.

    Set it with ``SMARTER_LOG_LEVEL``, a level's name, e.g. ``DEBUG``, or its number, e.g. ``10``.
    Unless it is set, it is derived from :attr:`debug_mode`: ``logging.DEBUG`` in debug mode, and
    ``logging.INFO`` otherwise. See :meth:`derive_log_level`.

    :type: int
    :default: ``logging.INFO``, or ``logging.DEBUG`` in debug mode
    :raises SmarterConfigurationError: If the value is neither a level's name nor its number.
    """

    @before_field_validator("log_level")
    def parse_log_level(cls, v: Optional[Union[int, str]]) -> int:
        """Validates the 'log_level' field: a level's name, e.g. ``DEBUG``, or its number.

        Args:
            v (Optional[Union[int, str]]): the level.
        Returns:
            int: The level's number.
        """
        if isinstance(v, bool):
            raise SmarterConfigurationError(f"log_level {v} is a bool, not a logging level.")
        if isinstance(v, int):
            return v
        if not isinstance(v, str):
            raise SmarterConfigurationError(f"log_level of type {type(v)} is not a logging level.")
        text = v.strip()
        if text.isdigit():
            return int(text)
        level = logging.getLevelNamesMapping().get(text.upper())
        if level is None:
            raise SmarterConfigurationError(f"log_level {v} is not one of DEBUG, INFO, WARNING, ERROR or CRITICAL.")
        return level

    @model_validator(mode="before")
    @classmethod
    def derive_log_level(cls, data: object) -> object:
        """
        Derive ``log_level`` from ``debug_mode``, unless it is set.

        :param data: The values to validate, before any field's validators: the constructor's and the
            environment's.
        :returns: The values, with ``log_level`` added when it is missing.
        """
        if not isinstance(data, dict):
            return data
        if "log_level" in data:
            return data
        debug_mode = data.get("debug_mode", field_default(cls, "debug_mode"))
        if isinstance(debug_mode, str):
            debug_mode = debug_mode.lower() in ["true", "1", "t", "y", "yes"]
        derived = dict(data)
        if debug_mode is True:
            derived["log_level"] = logging.DEBUG
        else:
            derived["log_level"] = logging.INFO
        return derived

    verbose_logging: bool = Field(
        False,
        description="Whether to enable verbose logging for debugging purposes.",
        examples=[True, False],
        title="Verbose Logging",
    )
    """
    Whether to enable verbose logging for debugging purposes.

    If True, enables verbose logging throughout the Smarter platform for debugging purposes.
    :type: bool
    :default: ``False``
    :raises SmarterConfigurationError: If the value is not a boolean.
    """

    @property
    def log_level_name(self) -> str:
        """
        Return the log level name.

        Example:
            >>> print(smarter_settings.log_level_name)
            'INFO'

        See Also:
            - smarter_settings.log_level
        """
        return logging.getLevelName(self.log_level)


__all__ = ["FeatureSettings"]
