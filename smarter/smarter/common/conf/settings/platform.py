# pylint: disable=no-member,no-self-argument,unused-argument,R0801
"""The settings that identify a Smarter platform: its environment, root domain and subdomain."""

from functools import cached_property
from typing import Optional

from pydantic import BaseModel, Field

from smarter.common.conf.const import THE_EMPTY_SET
from smarter.common.conf.defaults import settings_defaults
from smarter.common.conf.env import DEFAULT_MISSING_VALUE
from smarter.common.conf.util import before_field_validator
from smarter.common.const import SmarterEnvironments
from smarter.common.exceptions import SmarterConfigurationError


class PlatformSettings(BaseModel):
    """The platform's identity: its environment, root domain, platform subdomain, and shared resources."""

    init_info: Optional[str] = Field(
        None,
    )

    loki_url: str = Field(
        settings_defaults.LOKI_URL,
        description="The base url of the Loki that stores the platform's pod logs, e.g. http://smarter-loki:3100. Empty: there is none.",
        examples=["http://smarter-loki:3100"],
        title="Loki URL",
    )
    """
    The base url of the `Loki <https://grafana.com/oss/loki/>`__ that stores the last 72 hours of the platform's pod logs.

    The Helm chart runs Loki in the platform's namespace, and sets this to its Service, e.g.
    ``http://smarter-loki:3100``. The MCPServer's staff-only log tools query it, through
    :data:`smarter.apps.infrastructure.services.infrastructure` ``.logs``. While it is empty, e.g. in
    local development, the log tools say that there is no log store.
    :type: str
    :default: Value from ``settings_defaults.LOKI_URL``
    :raises SmarterConfigurationError: If the value is not an http or https url.
    """

    @before_field_validator("loki_url")
    def validate_loki_url(cls, v: Optional[str]) -> str:
        """Validates the 'loki_url' field: an http or https url without a trailing slash, or empty.

        Args:
            v (Optional[str]): the url.

        Returns:
            str: The validated url.
        """
        if v is None or str(v).strip() == "":
            return ""
        v = str(v).strip().rstrip("/")
        if not v.startswith(("http://", "https://")):
            raise SmarterConfigurationError(f"loki_url {v} must be an http or https url.")
        return v

    default_missing_value: str = Field(
        DEFAULT_MISSING_VALUE,
        description="Default missing value placeholder string. Used for consistency across settings.",
        examples=["SET-ME-PLEASE"],
        title="Default Missing Value",
    )
    """
    Default missing value placeholder string.

    Used for consistency across settings.
    This string is used as a placeholder for configuration values that have not been set.
    It indicates that the value is missing and should be provided by the user or administrator.
    Using a consistent placeholder helps identify unset values during debugging and configuration reviews.

    :type: str
    :default: Value from ``DEFAULT_MISSING_VALUE``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    environment: str = Field(
        settings_defaults.ENVIRONMENT,
        description="The deployment environment for the platform.",
        examples=SmarterEnvironments.all,
        title="Deployment Environment",
    )
    """
    The deployment environment for the platform.

    This setting indicates the environment in which the platform is running,
    such as development, staging, or production. It can be used to adjust
    behavior and configurations based on the environment.

    :type: str
    :default: Value from ``settings_defaults.ENVIRONMENT``
    :raises SmarterConfigurationError: If the value is not a valid environment name from SmarterEnvironments.all
    """

    @before_field_validator("environment")
    def validate_environment(cls, v: Optional[str]) -> str:
        """Validates the `environment` field.

        Args:
            v (Optional[str]): The environment value to validate.

        Returns:
            Optional[str]: The validated environment.
        """
        if v in THE_EMPTY_SET:
            return settings_defaults.ENVIRONMENT
        if not isinstance(v, str):
            raise SmarterConfigurationError(f"environment of type {type(v)} is not a str: {v}")
        return v

    platform_subdomain: Optional[str] = Field(
        settings_defaults.PLATFORM_SUBDOMAIN,
        description="The subdomain for the platform, used in constructing URLs and email addresses.",
        examples=["platform", "ubc"],
        title="Platform Subdomain",
    )

    root_domain: str = Field(
        settings_defaults.ROOT_DOMAIN,
        description="The root domain for the platform.",
        examples=["example.com"],
        title="Root Domain",
    )
    """
    The root domain for the platform.

    This setting specifies the primary domain name used by the platform.
    It is used for constructing URLs, email addresses, and other domain-related
    configurations.

    :type: str
    :default: Value from ``settings_defaults.ROOT_DOMAIN``
    :raises SmarterConfigurationError: If the value is not a valid domain name.
    """

    @before_field_validator("root_domain")
    def validate_root_domain(cls, v: Optional[str]) -> str:
        """
        Validates the `root_domain` field.

        If the value is not set, returns the default root domain.

        Args:
            v (Optional[str]): The root domain value to validate.

        Returns:
            str: The validated root domain.
        """
        if v in THE_EMPTY_SET:
            return settings_defaults.ROOT_DOMAIN

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"root_domain of type {type(v)} is not a str: {v}")

        return v

    settings_output: bool = Field(
        settings_defaults.SETTINGS_OUTPUT,
        description="Flag to enable or disable output of settings for debugging purposes.",
        examples=[True, False],
        title="Settings Output",
    )
    """
    If True, enables verbose output of Smarter run-time settings during Django startup.

    This will generate a multi-line header in new terminal windows launched from
    Kubernetes pods running Smarter services.

    :type: bool
    :default: Value from ``settings_defaults.SETTINGS_OUTPUT``
    :raises SmarterConfigurationError: If the value is not a boolean.
    """

    @before_field_validator("settings_output")
    def validate_settings_output(cls, v: Optional[bool]) -> bool:
        """Validates the `settings_output` field.

        Args:
            v (Optional[bool]): The settings output value to validate.

        Returns:
            bool: The validated settings output.
        """
        if v is None:
            return settings_defaults.SETTINGS_OUTPUT

        if not isinstance(v, bool):
            raise SmarterConfigurationError(f"settings_output of type {type(v)} is not a bool: {v}")
        return v

    shared_resource_identifier: str = Field(
        settings_defaults.SHARED_RESOURCE_IDENTIFIER,
        description="Smarter 1-word identifier to be used when naming any shared resource.",
        examples=["smarter", "mycompany", "myproject"],
        title="Shared Resource Identifier",
    )
    """
    A single, lowercase word used as a unique identifier for all shared resources across the Smarter platform.

    This value is used as a prefix or namespace when naming resources that are shared between services,
    environments, or deployments—such as S3 buckets, Kubernetes namespaces, or other cloud resources.
    It ensures that resource names are consistent, easily identifiable, and do not conflict with those
    from other projects or organizations.

    .. important::

        - The identifier should be a simple word, using only lowercase letters.
        - Avoid changing this value after initial deployment, as it would likely lead to resource naming conflicts and unintended consequences in Kubernetes, cloud infrastructure, and other services relying on consistent naming conventions.

    **Typical usage:**
        - As a prefix for cloud resource names (e.g., ``smarter-platform-alpha``)
        - To distinguish resources in multi-tenant or multi-environment deployments
        - For automated naming conventions in infrastructure-as-code and deployment scripts

    **Examples:**
        - ``smarter``
        - ``mycompany``
        - ``myproject``

    :type: str
    :default: Value from ``settings_defaults.SHARED_RESOURCE_IDENTIFIER``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("shared_resource_identifier")
    def validate_shared_resource_identifier(cls, v: Optional[str]) -> str:
        """Validates the `shared_resource_identifier` field.

        Uses settings_defaults if no value is received.

        Args:
            v (Optional[str]): The shared resource identifier to validate.

        Returns:
            str: The validated shared resource identifier.
        """
        if v in THE_EMPTY_SET:
            return settings_defaults.SHARED_RESOURCE_IDENTIFIER

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"shared_resource_identifier of type {type(v)} is not a str: {v}")

        return v

    @cached_property
    def protocol(self) -> str:
        """
        Return the protocol: http or https.

        Example:
            >>> print(smarter_settings.protocol)
            'https'

        See Also:
            - smarter_settings.environment
            - SmarterEnvironments()
        """
        if self.environment in SmarterEnvironments.aws_environments:
            return "https"
        return "http"

    @property
    def environment_is_local(self) -> bool:
        """
        Return True if the environment is local.

        Example:
            >>> print(smarter_settings.environment_is_local)
            True

        See Also:
            - smarter_settings.environment
            - SmarterEnvironments()
        """
        return self.environment == SmarterEnvironments.LOCAL


__all__ = ["PlatformSettings"]
