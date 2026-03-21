# pylint: disable=no-member,no-self-argument,unused-argument,R0801,too-many-lines
"""
The Smarter Project - configuration settings.

This module is used to generate smarter_settings, a singleton instance of
Pydantic BaseSettings that provides strongly typed and validated settings values
from environment variables, `.env` file, and default values. for all
Pydantic settings fields, custom field validations are performed prior
to Pydantic's built-in validation.

It uses the pydantic_settings v2 library to strongly type, and to validate
the configuration values. The configuration values are initialized according to the following
prioritization sequence:

    1. Settings constructor
    2. `.env` file. Loads any variable with ``SMARTER_`` prefix.
    3. environment variables. Loads any variable with ``SMARTER_`` prefix.
    4. default values defined in settings_defaults.

.. note::

    You can also set any Django settings value from environment variables
    and/or `.env` file variables. For example, to set the Django
    ``SECRET_KEY`` setting, you can set the environment variable ``SECRET_KEY=MYSECRET``.

.. warning::

    DO NOT import Django or any Django modules in this module. This module
    sits upstream of Django and is intended to be used independently of Django.

"""

# python stuff
import base64  # library for base64 encoding and decoding
import logging  # library for logging messages
import os  # library for interacting with the operating system
import re  # library for regular expressions
import warnings  # library for issuing warning messages
from functools import cached_property, lru_cache
from typing import Any, List, Optional, Pattern, Union  # type hint utilities
from urllib.parse import urljoin, urlparse  # library for URL manipulation

# 3rd party stuff
import requests
from pydantic import (
    AnyUrl,
    EmailStr,
    Field,
    HttpUrl,
    SecretStr,
    ValidationError,
    ValidationInfo,
)
from pydantic import __version__ as pydantic_version
from pydantic_settings import BaseSettings, SettingsConfigDict

# smarter stuff
from smarter.common.api import SmarterApiVersions
from smarter.common.conf.const import DEFAULT_ROOT_DOMAIN, DOT_ENV_LOADED, THE_EMPTY_SET
from smarter.common.const import (
    SMARTER_API_KEY_MAX_LIFETIME_DAYS,
    SMARTER_API_SUBDOMAIN,
    SMARTER_DEFAULT_REACTJS_APP_LOADER_URL,
    SMARTER_LOCAL_PORT,
    SMARTER_PROJECT_CDN_URL,
    SMARTER_PROJECT_DOCS_URL,
    SMARTER_PROJECT_WEBSITE_URL,
    SmarterEnvironments,
)
from smarter.common.exceptions import SmarterConfigurationError, SmarterValueError
from smarter.common.helpers.console_helpers import (
    formatted_text,
    formatted_text_green,
    formatted_text_red,
)
from smarter.common.utils import (
    get_diagnostics,
    get_semantic_version,
    recursive_sort_dict,
)
from smarter.lib.django.validators import SmarterValidator

# smarter.common.conf stuff
from .defaults import settings_defaults
from .env import DEFAULT_MISSING_VALUE
from .services import AWS_REGIONS, services
from .util import before_field_validator

logger = logging.getLogger(__name__)
logger_prefix = formatted_text(__name__ + ".Settings()")


# pylint: disable=too-many-instance-attributes,too-many-public-methods
class Settings(BaseSettings):
    """
    see: https://docs.pydantic.dev/latest/concepts/pydantic_settings/.

    Smarter derived settings. This is intended to be instantiated as
    an immutable singleton object called `smarter_settings`. smarter_settings
    contains superseding, validated, and derived settings values for the platform.

    This class implements a consistent set of rules for initializing configuration
    values from multiple sources, including environment variables, `.env` file,
    and default values defined in this class. It additionally ensures that all
    configuration values are strongly typed and validated.

    Where applicable, smarter_settings supersede Django settings values. That is,
    smarter_settings should be used in preference to Django settings wherever
    possible. Django settings are initialized from smarter_settings values where
    applicable.

    Notes:
    -----------------
    - smarter_settings values are immutable after instantiation.
    - Every property/attribute in smarter_settings has a value.
      If a value is None then it is intentionally None.
    - Sensitive values are stored as pydantic SecretStr types.
    - smarter_settings values are initialized according to the following prioritization sequence:
        1. constructor. This is discouraged. prefer to use .env file or environment variables.
        2. `.env` file. When sourced, these override existing environment variables.
        3. environment variables.
        4. settings_defaults
    - The dump property returns a dictionary of all configuration values.
    - smarter_settings values should be accessed via the smarter_settings singleton instance when possible.
    """

    model_config = SettingsConfigDict(
        strict=True,
        frozen=True,
        # env_file=".env",
        # env_prefix="SMARTER_",
        extra="forbid",
        validate_default=True,
    )
    """
    Pydantic v2 Configuration class for the Settings model. This configuration enforces strict type checking,
    immutability, and environment variable loading behavior for the Settings class.
    see https://docs.pydantic.dev/latest/concepts/pydantic_settings/

    .. note::

        We're not currently using env_file and env_prefix here because we're
        handling that in settings_defaults for backward compatibility. There
        are type conversions and defaulting behavior in the legacy code
        that is slightly more robust than in Pydantic v2.

    :param strict: Enforce strict type checking for all fields.
    :param frozen: Make the settings instance immutable after instantiation.
    :param env_file: Load environment variables from the specified .env file.
    :param env_prefix: Prefix to use for environment variables.
    :param extra: Forbid extra fields not defined in the model.
    :param validate_default: Validate default values defined in the model.

    :type: SettingsConfigDict
    """

    _ready: bool

    def __init__(self, **data: Any):
        super().__init__(**data)
        self._to_json = None
        self._ready = False
        # need to be mindful that __init__ is called before Django startup has begun.
        # one consequence is that logging is not yet configured, so have have to
        # use janky logging levels in order to ensure that these log messages are seen.
        msg = f"{formatted_text(__name__)} Pydantic version: {pydantic_version} pydantic_settings.BaseSettings."
        if self.ready():
            ready_msg = formatted_text_green("READY")
        else:
            ready_msg = formatted_text_red("NOT_READY")
        logger.warning("%s Settings are %s.", msg, ready_msg)

    init_info: Optional[str] = Field(
        None,
    )

    @cached_property
    def allowed_hosts(self) -> List[str]:
        """
        A list of strings representing the host/domain names that this Django site can serve.
        Smarter implements its own middleware to validate host names.
        See smarter.apps.chatbot.middleware.security.SmarterSecurityMiddleware.

        See: https://docs.djangoproject.com/en/stable/ref/settings/#allowed-hosts

        Supplemental list of allowed host/domain names for Smarter ChatBots/Agents.
        This is specicific to Smarter and not officially part of Django settings.

        List of allowed host/domain names for this Django site.
        This setting specifies which hostnames the Django application is allowed to serve.
        It is a security measure to prevent HTTP Host header attacks.

        :type: List[str]
        :default: Value from ``settings_defaults.ALLOWED_HOSTS``
        :raises SmarterConfigurationError: If the value is not a list of strings.
        :examples: ["example.com", "www.example.com"]
        """
        default_allowed_hosts = settings_defaults.ALLOWED_HOSTS.copy() or []
        if not isinstance(default_allowed_hosts, list):
            raise SmarterConfigurationError(f"allowed_hosts of type {type(default_allowed_hosts)} is not a list.")
        if not all(isinstance(host, str) for host in default_allowed_hosts):
            raise SmarterConfigurationError("allowed_hosts must be a list of strings.")
        if not isinstance(self.environment_platform_domain, str):
            raise SmarterConfigurationError(
                f"environment_platform_domain of type {type(self.environment_platform_domain)} is not a string."
            )
        if not isinstance(self.environment_api_domain, str):
            raise SmarterConfigurationError(
                f"environment_api_domain of type {type(self.environment_api_domain)} is not a string."
            )
        if self.environment_platform_domain is None:
            raise SmarterConfigurationError("environment_platform_domain is None.")
        if self.environment_api_domain is None:
            raise SmarterConfigurationError("environment_api_domain is None.")

        retval = [
            self.environment_platform_domain,
            self.environment_api_domain,
            f".{self.environment_api_domain}",
        ] + default_allowed_hosts
        # For each host, append the hostname (without port) if not already present
        for host in retval:
            parsed = urlparse(f"//{host}")
            if parsed.hostname and parsed.hostname not in retval:
                retval.append(parsed.hostname)
        for host in retval:
            SmarterValidator.validate_hostname(host)

        return list(set(retval))

    anthropic_api_key: SecretStr = Field(
        settings_defaults.ANTHROPIC_API_KEY,
        description="The API key for Anthropic services. Masked by pydantic SecretStr.",
        examples=["sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"],
        title="Anthropic API Key",
    )
    """
    The API key for Anthropic services. Masked by pydantic SecretStr.
    This setting provides the API key used to authenticate with Anthropic services.
    It is required for accessing Anthropic's APIs and services.

    :type: SecretStr
    :default: Value from ``settings_defaults.ANTHROPIC_API_KEY``
    :raises SmarterConfigurationError: If the value is not a valid API key.
    """

    @before_field_validator("anthropic_api_key")
    def validate_anthropic_api_key(cls, v: Optional[SecretStr]) -> SecretStr:
        """Validates the `anthropic_api_key` field.

        Args:
            v (Optional[SecretStr]): The Anthropic API key value to validate.

        Returns:
            SecretStr: The validated Anthropic API key.
        """
        if v is None:
            return settings_defaults.ANTHROPIC_API_KEY

        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError(f"anthropic_api_key of type {type(v)} is not a SecretStr.")

        return v

    api_description: str = Field(
        settings_defaults.API_DESCRIPTION,
        description="The description of the API.",
        examples=["A declarative AI resource management platform and developer framework"],
        title="API Description",
    )
    """
    The description of the API.
    This setting provides a brief description of the API's purpose and functionality.
    It is used in various contexts, such as Swagger Api documentation site, logging, and user interfaces.
    :type: str
    :default: Value from ``settings_defaults.API_DESCRIPTION``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("api_description")
    def validate_api_description(cls, v: str) -> str:
        """Validates the `api_description` field.

        Args:
            v (str): The API description value to validate.

        Returns:
            str: The validated API description.
        """
        if not isinstance(v, str):
            raise SmarterConfigurationError(f"api_description of type {type(v)} is not a string.")
        return v

    api_name: str = Field(
        settings_defaults.API_NAME,
        description="The name of the API.",
        examples=["Smarter API", "My Custom API"],
        title="API Name",
    )
    """
    The name of the API.
    This setting specifies the name of the API used in various contexts,
    such as Swagger Api documentation site, logging, and user interfaces.

    :type: str
    :default: Value from ``settings_defaults.API_NAME``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("api_name")
    def validate_api_name(cls, v: str) -> str:
        """Validates the `api_name` field.

        Args:
            v (str): The API name value to validate.

        Returns:
            str: The validated API name.
        """
        if not isinstance(v, str):
            raise SmarterConfigurationError(f"api_name of type {type(v)} is not a string.")
        return v

    @cached_property
    def api_schema(self) -> str:
        """
        The schema to use for API URLs (http or https).
        This setting specifies the URL schema to be used when constructing API endpoints.
        It determines whether the API URLs will use HTTP or HTTPS.
        :type: str
        :default: Value from ``settings_defaults.API_SCHEMA``
        :raises SmarterConfigurationError: If the value is not 'http' or 'https'.
        :examples: ["http", "https"],
        """
        if self.environment_is_local:
            return "http"
        else:
            return settings_defaults.API_SCHEMA

    aws_profile: Optional[str] = Field(
        settings_defaults.AWS_PROFILE,
        description="The AWS profile to use for authentication. If present, this will take precedence over AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY.",
        examples=["default", "smarter-profile"],
        title="AWS Profile",
    )
    """
    The AWS profile to use for authentication. If present, this will take precedence over AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY.
    This setting specifies which AWS credentials profile to use when connecting to AWS services.
    Profiles are defined in the AWS credentials file (typically located at ~/.aws/credentials)
    and allow for managing multiple sets of credentials for different environments or accounts.

    :type: Optional[str]
    :default: Value from ``settings_defaults.AWS_PROFILE``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("aws_profile")
    def validate_aws_profile(cls, v: Optional[str]) -> Optional[str]:
        """Validates the `aws_profile` field.
        Uses settings_defaults if no value is received.

        Args:
            v (Optional[str]): The AWS profile value to validate.

        Returns:
            Optional[str]: The validated AWS profile.
        """
        if v in THE_EMPTY_SET:
            if settings_defaults.AWS_PROFILE == DEFAULT_MISSING_VALUE:
                return None
            return settings_defaults.AWS_PROFILE
        return v

    aws_access_key_id: Optional[SecretStr] = Field(
        settings_defaults.AWS_ACCESS_KEY_ID,
        description="The AWS access key ID for authentication. Used if AWS_PROFILE is not set. Masked by pydantic SecretStr.",
        examples=["^AKIA[0-9A-Z]{16}$"],
        title="AWS Access Key ID",
    )
    """
    The AWS access key ID for authentication. Used if AWS_PROFILE is not set. Masked by pydantic SecretStr.
    This setting provides the access key ID used to authenticate with AWS services.
    It is used in conjunction with the AWS secret access key to sign requests to AWS APIs.

    :type: SecretStr
    :default: Value from ``settings_defaults.AWS_ACCESS_KEY_ID``
    :raises SmarterConfigurationError: If the value is not a valid AWS access key ID
    """

    @before_field_validator("aws_access_key_id")
    def validate_aws_access_key_id(cls, v: Optional[SecretStr], values: ValidationInfo) -> Optional[SecretStr]:
        """Validates the `aws_access_key_id` field.
        Uses settings_defaults if no value is received.


        Args:
            v (Optional[SecretStr]): The AWS access key ID value to validate.
            values (ValidationInfo): The validation info containing other field values.

        Returns:
            SecretStr: The validated AWS access key ID.
        """
        if v is None:
            return None
        if isinstance(v, str):
            v = SecretStr(v)
        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError("could not convert aws_access_key_id value to SecretStr")

        if v.get_secret_value() in [None, "", DEFAULT_MISSING_VALUE]:
            return None
        aws_profile = values.data.get("aws_profile", None)
        if aws_profile and len(aws_profile) > 0 and aws_profile != DEFAULT_MISSING_VALUE:
            logger.warning("aws_access_key_id is being ignored. using aws_profile %s.", aws_profile)
            return None

        # validate the pattern of the access key id
        pattern = r"^AKIA[0-9A-Z]{16}$"
        if not re.match(pattern, v.get_secret_value()):
            raise SmarterConfigurationError("aws_access_key_id is not a valid AWS access key ID format.")

        return v

    aws_secret_access_key: Optional[SecretStr] = Field(
        settings_defaults.AWS_SECRET_ACCESS_KEY,
        description="The AWS secret access key for authentication. Used if AWS_PROFILE is not set. Masked by pydantic SecretStr.",
        examples=["^[0-9a-zA-Z/+]{40}$"],
        title="AWS Secret Access Key",
    )
    """
    The AWS secret access key for authentication. Used if AWS_PROFILE is not set. Masked by pydantic SecretStr.
    This setting provides the secret access key used to authenticate with AWS services.
    It is used in conjunction with the AWS access key ID to sign requests to AWS APIs.

    :type: SecretStr
    :default: Value from ``settings_defaults.AWS_SECRET_ACCESS_KEY``
    :raises SmarterConfigurationError: If the value is not a valid AWS secret access key
    """

    @before_field_validator("aws_secret_access_key")
    def validate_aws_secret_access_key(cls, v: Optional[SecretStr], values: ValidationInfo) -> Optional[SecretStr]:
        """Validates the `aws_secret_access_key` field.
        Uses settings_defaults if no value is received.

        Args:
            v (Optional[SecretStr]): The AWS secret access key value to validate.
            values (ValidationInfo): The validation info containing other field values.

        Returns:
            SecretStr: The validated AWS secret access key.
        """
        if v is None:
            return None
        if isinstance(v, str):
            v = SecretStr(v)
        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError("could not convert aws_secret_access_key value to SecretStr")

        if v.get_secret_value() in [None, "", DEFAULT_MISSING_VALUE]:
            return None
        aws_profile = values.data.get("aws_profile", None)
        if aws_profile and len(aws_profile) > 0 and aws_profile != DEFAULT_MISSING_VALUE:
            logger.warning("aws_secret_access_key is being ignored. using aws_profile %s.", aws_profile)
            return None

        # validate the pattern of the secret access key
        pattern = r"^[0-9a-zA-Z/+]{40}$"
        if not re.match(pattern, v.get_secret_value()):
            raise SmarterConfigurationError("aws_secret_access_key is not a valid AWS secret access key format.")

        return v

    aws_regions: List[str] = Field(
        AWS_REGIONS,
        description="A list of AWS regions considered valid for this platform.",
        examples=["us-east-1", "us-west-2", "eu-west-1"],
        title="AWS Regions",
    )
    """
    A list of AWS regions considered valid for this platform.
    This setting defines the AWS regions that the platform is configured to operate in.
    It can be used to restrict operations to specific regions, ensuring that resources
    are created and managed only in approved locations.

    :type: List[str]
    :default: Value from ``AWS_REGIONS``
    :raises SmarterConfigurationError: If the value is not a list of valid AWS region names.
    """
    aws_region: Optional[str] = Field(
        settings_defaults.AWS_REGION,
        description="The single AWS region in which all AWS service clients will operate.",
        examples=["us-east-1", "us-west-2", "eu-west-1"],
        title="AWS Region",
    )
    """
    The single AWS region in which all AWS service clients will operate.
    This setting specifies the default AWS region for the platform.
    All AWS service clients will be configured to use this region unless
    overridden on a per-client basis.

    :type: str
    :default: Value from ``settings_defaults.AWS_REGION``
    :raises SmarterConfigurationError: If the value is not a valid AWS region name.
    """

    @before_field_validator("aws_region")
    def validate_aws_region(cls, v: Optional[str], values: ValidationInfo, **kwargs) -> Optional[str]:
        """Validates the `aws_region` field.
        Uses settings_defaults if no value is received.

        Args:
            v (Optional[str]): The AWS region value to validate.
            values (ValidationInfo): The validation info containing other field values.

        Returns:
            Optional[str]: The validated AWS region.
        """

        valid_regions = values.data.get("aws_regions", ["us-east-1"])
        if v in THE_EMPTY_SET:
            if settings_defaults.AWS_REGION == DEFAULT_MISSING_VALUE:
                return None
            return settings_defaults.AWS_REGION
        if v not in valid_regions:
            raise SmarterValueError(f"aws_region {v} not in aws_regions: {valid_regions}")
        return v

    def ready(self) -> bool:
        """
        Returns True if the settings instance has been fully initialized and is ready for use.
        This method can be used to check if the settings instance is fully configured
        and ready to be used by the application.

        - is the root domain set?
        - is AWS configured?
        - is SMTP configured?
        - is OpenAI API key configured?
        - is Google Maps API key configured? (used for get_current_weather() function)

        :type: bool
        """
        retval = True
        if self.root_domain == DEFAULT_ROOT_DOMAIN:
            print(
                formatted_text_red(
                    "\n"
                    + "=" * 80
                    + "\n[WARNING] ROOT_DOMAIN is set to the default value 'example.com'.\n"
                    + "This is not recommended for production deployments. Please set ROOT_DOMAIN to your actual domain.\n"
                    + "=" * 80
                    + "\n"
                )
            )
            logger.warning(
                "ROOT_DOMAIN is set to the default value 'example.com'. This is not recommended for production deployments."
            )
            retval = False

        if not self.aws_is_configured:
            print(
                formatted_text_red(
                    "\n"
                    + "=" * 80
                    + "\n[WARNING] AWS is not configured properly. Some features may not work as expected.\n"
                    + "Ensure that AWS credentials are set in environment variables, .env file, or AWS config files.\n"
                    + "=" * 80
                    + "\n"
                )
            )
            logger.warning("AWS is not configured properly. Some features may not work as expected.")
            retval = False

        if not self.smtp_is_configured:
            print(
                formatted_text_red(
                    "\n"
                    + "=" * 80
                    + "\n[WARNING] SMTP is not configured properly. Email features may not work as expected.\n"
                    + "Ensure that SMTP settings are set in environment variables or .env file.\n"
                    + "=" * 80
                    + "\n"
                )
            )
            logger.warning("SMTP is not configured properly. Email features may not work as expected.")
            retval = False

        if self.openai_api_key and self.openai_api_key.get_secret_value() == self.default_missing_value:
            print(
                formatted_text_red(
                    "\n"
                    + "=" * 80
                    + "\n[WARNING] OPENAI_API_KEY is not configured properly. OpenAI features may not work as expected.\n"
                    + "Ensure that OPENAI_API_KEY is set in environment variables or .env file.\n"
                    + "=" * 80
                    + "\n"
                )
            )
            logger.warning("OPENAI_API_KEY is not configured properly. OpenAI features may not work as expected.")
            retval = False

        if self.google_maps_api_key and self.google_maps_api_key.get_secret_value() == self.default_missing_value:
            print(
                formatted_text_red(
                    "\n"
                    + "=" * 80
                    + "\n[WARNING] GOOGLE_MAPS_API_KEY is not configured properly. Google Maps features may not work as expected.\n"
                    + "Ensure that GOOGLE_MAPS_API_KEY is set in environment variables or .env file.\n"
                    + "=" * 80
                    + "\n"
                )
            )
            logger.warning(
                "GOOGLE_MAPS_API_KEY is not configured properly. Google Maps features may not work as expected."
            )
            retval = False

        self._ready = retval
        return self._ready

    @property
    def aws_is_configured(self) -> bool:
        """
        True if AWS is configured. This is determined by the presence of either AWS_PROFILE or both AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY.
        This setting indicates whether the platform has sufficient AWS credentials
        configured to connect to AWS services. If AWS is not configured, attempts
        to use AWS services will fail.

        :type: bool
        """
        return services.is_connected_to_aws()

    aws_eks_cluster_name: str = Field(
        settings_defaults.AWS_EKS_CLUSTER_NAME,
        description="The name of the AWS EKS cluster used for hosting applications.",
        examples=["apps-hosting-service"],
        title="AWS EKS Cluster Name",
    )
    """
    The name of the AWS EKS cluster used for hosting applications.
    This setting specifies the Amazon EKS cluster that the platform will use
    for deploying and managing containerized applications. The cluster name
    should correspond to an existing EKS cluster in the configured AWS account.

    :type: str
    :default: Value from ``settings_defaults.AWS_EKS_CLUSTER_NAME``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("aws_eks_cluster_name")
    def validate_aws_eks_cluster_name(cls, v: Optional[str]) -> str:
        """Validates the `aws_eks_cluster_name` field.

        Args:
            v (Optional[str]): The AWS EKS cluster name value to validate.

        Returns:
            str: The validated AWS EKS cluster name.
        """
        if v in THE_EMPTY_SET:
            return settings_defaults.AWS_EKS_CLUSTER_NAME

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"aws_eks_cluster_name of type {type(v)} is not a str.")

        return v

    aws_db_instance_identifier: str = Field(
        settings_defaults.AWS_RDS_DB_INSTANCE_IDENTIFIER,
        description="The RDS database instance identifier used for the platform's primary database.",
        examples=["apps-hosting-service"],
        title="AWS RDS DB Instance Identifier",
    )
    """
    The RDS database instance identifier used for the platform's primary database.
    This setting specifies the Amazon RDS database instance that the platform
    will connect to for data storage and retrieval. The instance identifier should
    correspond to an existing RDS instance in the configured AWS account.

    :type: str
    :default: Value from ``settings_defaults.AWS_RDS_DB_INSTANCE_IDENTIFIER``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("aws_db_instance_identifier")
    def validate_aws_db_instance_identifier(cls, v: Optional[str]) -> str:
        """Validates the `aws_db_instance_identifier` field.

        Args:
            v (Optional[str]): The AWS RDS DB instance identifier value to validate.

        Returns:
            str: The validated AWS RDS DB instance identifier.
        """
        if v in THE_EMPTY_SET:
            return settings_defaults.AWS_RDS_DB_INSTANCE_IDENTIFIER

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"aws_db_instance_identifier of type {type(v)} is not a str.")

        return v

    branding_corporate_name: str = Field(
        settings_defaults.BRANDING_CORPORATE_NAME,
        description="The corporate name used for branding purposes throughout the platform.",
        examples=["Acme Corporation"],
        title="Branding Corporate Name",
    )
    """
    The corporate name used for branding purposes throughout the platform.
    This setting specifies the name of the organization or company that owns
    or operates the platform. It is used in various branding contexts,
    such as email templates, user interfaces, and documentation.
    :type: str
    :default: Value from ``settings_defaults.BRANDING_CORPORATE_NAME``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("branding_corporate_name")
    def validate_branding_corporate_name(cls, v: Optional[str]) -> str:
        """Validates the `branding_corporate_name` field.

        Args:
            v (Optional[str]): The branding corporate name value to validate.

        Returns:
            str: The validated branding corporate name.
        """
        if v in THE_EMPTY_SET:
            return settings_defaults.BRANDING_CORPORATE_NAME

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"branding_corporate_name of type {type(v)} is not a str.")

        return v

    branding_support_phone_number: str = Field(
        settings_defaults.BRANDING_SUPPORT_PHONE_NUMBER,
        description="The support phone number used for branding purposes throughout the platform.",
        examples=["+1-800-555-1234"],
        title="Branding Support Phone Number",
    )
    """
    The support phone number used for branding purposes throughout the platform.
    This setting specifies the phone number that users can call for support
    or assistance related to the platform. It is used in various branding contexts,
    such as email templates, user interfaces, and documentation.
    :type: str
    :default: Value from ``settings_defaults.BRANDING_SUPPORT_PHONE_NUMBER``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("branding_support_phone_number")
    def validate_branding_support_phone_number(cls, v: Optional[str]) -> str:
        """Validates the `branding_support_phone_number` field.

        Args:
            v (Optional[str]): The branding support phone number value to validate.

        Returns:
            str: The validated branding support phone number.
        """
        if v in THE_EMPTY_SET:
            return settings_defaults.BRANDING_SUPPORT_PHONE_NUMBER

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"branding_support_phone_number of type {type(v)} is not a str.")

        return v

    branding_support_email: EmailStr = Field(
        settings_defaults.BRANDING_SUPPORT_EMAIL,
        description="The support email address used for branding purposes throughout the platform.",
        title="Branding Support Email",
    )
    """
    The support email address used for branding purposes throughout the platform.
    This setting specifies the email address that users can contact for support
    or assistance related to the platform. It is used in various branding contexts,
    such as email templates, user interfaces, and documentation.
    :type: EmailStr
    :default: Value from ``settings_defaults.BRANDING_SUPPORT_EMAIL``
    :raises SmarterConfigurationError: If the value is not a EmailStr.
    """

    @before_field_validator("branding_support_email")
    def validate_branding_support_email(cls, v: Optional[EmailStr]) -> EmailStr:
        """Validates the `branding_support_email` field.

        Args:
            v (Optional[EmailStr]): The branding support email value to validate.
        Returns:
            EmailStr: The validated branding support email.
        """
        if v in THE_EMPTY_SET:
            return settings_defaults.BRANDING_SUPPORT_EMAIL

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"branding_support_email of type {type(v)} is not a EmailStr.")
        SmarterValidator.validate_email(v)

        return v

    branding_address1: str = Field(
        settings_defaults.BRANDING_ADDRESS1,
        description="The corporate address used for branding purposes throughout the platform.",
        examples=["123 Main St, Anytown, USA"],
        title="Branding Address",
    )
    """
    The corporate address used for branding purposes throughout the platform.
    This setting specifies the physical address of the organization or company that owns
    or operates the platform. It is used in various branding contexts,
    such as email templates, user interfaces, and documentation.
    :type: str
    :default: Value from ``settings_defaults.BRANDING_ADDRESS1``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("branding_address1")
    def validate_branding_address(cls, v: Optional[str]) -> str:
        """Validates the `branding_address1` field.

        Args:
            v (Optional[str]): The branding address value to validate.

        Returns:
            str: The validated branding address.
        """
        if v in THE_EMPTY_SET:
            return settings_defaults.BRANDING_ADDRESS1

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"branding_address1 of type {type(v)} is not a str.")

        return v

    branding_address2: Optional[str] = Field(
        settings_defaults.BRANDING_ADDRESS2,
        description="The second line of the corporate address used for branding purposes throughout the platform.",
        examples=["Suite 100"],
        title="Branding Address Line 2",
    )
    """
    The second line of the corporate address used for branding purposes throughout the platform.
    This setting specifies the second line of the physical address of the organization or company that owns
    or operates the platform. It is used in various branding contexts,
    such as email templates, user interfaces, and documentation.
    :type: Optional[str]
    :default: Value from ``settings_defaults.BRANDING_ADDRESS2``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("branding_address2")
    def validate_branding_address2(cls, v: Optional[str]) -> Optional[str]:
        """Validates the `branding_address2` field.

        Args:
            v (Optional[str]): The branding address line 2 value to validate.

        Returns:
            Optional[str]: The validated branding address line 2.
        """
        if v in THE_EMPTY_SET:
            return None

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"branding_address2 of type {type(v)} is not a str.")

        return v

    branding_city: str = Field(
        settings_defaults.BRANDING_CITY,
        description="The corporate city used for branding purposes throughout the platform.",
        examples=["Anytown"],
        title="Branding City",
    )
    """
    The corporate city used for branding purposes throughout the platform.
    This setting specifies the city of the physical address of the organization or company that owns
    or operates the platform. It is used in various branding contexts,
    such as email templates, user interfaces, and documentation.
    :type: str
    :default: Value from ``settings_defaults.BRANDING_CITY``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("branding_city")
    def validate_branding_city(cls, v: Optional[str]) -> str:
        """Validates the `branding_city` field.

        Args:
            v (Optional[str]): The branding city value to validate.

        Returns:
            str: The validated branding city.
        """
        if v in THE_EMPTY_SET:
            return settings_defaults.BRANDING_CITY

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"branding_city of type {type(v)} is not a str.")

        return v

    branding_state: str = Field(
        settings_defaults.BRANDING_STATE,
        description="The corporate state used for branding purposes throughout the platform.",
        examples=["CA"],
        title="Branding State",
    )
    """
    The corporate state used for branding purposes throughout the platform.
    This setting specifies the state of the physical address of the organization or company that owns
    or operates the platform. It is used in various branding contexts,
    such as email templates, user interfaces, and documentation.
    :type: str
    :default: Value from ``settings_defaults.BRANDING_STATE``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("branding_state")
    def validate_branding_state(cls, v: Optional[str]) -> str:
        """Validates the `branding_state` field.

        Args:
            v (Optional[str]): The branding state value to validate.

        Returns:
            str: The validated branding state.
        """
        if v in THE_EMPTY_SET:
            return settings_defaults.BRANDING_STATE

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"branding_state of type {type(v)} is not a str.")

        return v

    branding_postal_code: str = Field(
        settings_defaults.BRANDING_POSTAL_CODE,
        description="The corporate postal code used for branding purposes throughout the platform.",
        examples=["12345"],
        title="Branding Postal Code",
    )
    """
    The corporate postal code used for branding purposes throughout the platform.
    This setting specifies the postal code of the physical address of the organization or company that owns
    or operates the platform. It is used in various branding contexts,
    such as email templates, user interfaces, and documentation.
    :type: str
    :default: Value from ``settings_defaults.BRANDING_POSTAL_CODE``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("branding_postal_code")
    def validate_branding_postal_code(cls, v: Optional[str]) -> str:
        """Validates the `branding_postal_code` field.

        Args:
            v (Optional[str]): The branding postal code value to validate.

        Returns:
            str: The validated branding postal code.
        """
        if v in THE_EMPTY_SET:
            return settings_defaults.BRANDING_POSTAL_CODE

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"branding_postal_code of type {type(v)} is not a str.")

        return v

    branding_country: str = Field(
        settings_defaults.BRANDING_COUNTRY,
        description="The corporate country used for branding purposes throughout the platform.",
        examples=["USA"],
        title="Branding Country",
    )
    """
    The corporate country used for branding purposes throughout the platform.
    This setting specifies the country of the physical address of the organization or company that owns
    or operates the platform. It is used in various branding contexts,
    such as email templates, user interfaces, and documentation.
    :type: str
    :default: Value from ``settings_defaults.BRANDING_COUNTRY``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("branding_country")
    def validate_branding_country(cls, v: Optional[str]) -> str:
        """Validates the `branding_country` field.

        Args:
            v (Optional[str]): The branding country value to validate.

        Returns:
            str: The validated branding country.
        """
        if v in THE_EMPTY_SET:
            return settings_defaults.BRANDING_COUNTRY

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"branding_country of type {type(v)} is not a str.")

        return v

    branding_currency: str = Field(
        settings_defaults.BRANDING_CURRENCY,
        description="The currency used for branding purposes throughout the platform.",
        examples=["USD"],
        title="Branding Currency",
    )
    """
    The currency used for branding purposes throughout the platform.
    This setting specifies the currency that is used in various branding contexts,
    such as email templates, user interfaces, and documentation. It can be used to
    indicate the currency in which prices, billing, or financial information
    is presented to users.
    :type: str
    :default: Value from ``settings_defaults.BRANDING_CURRENCY``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("branding_currency")
    def validate_branding_currency(cls, v: Optional[str]) -> str:
        """Validates the `branding_currency` field.

        Args:
            v (Optional[str]): The branding currency value to validate.

        Returns:
            str: The validated branding currency.
        """
        if v in THE_EMPTY_SET:
            return settings_defaults.BRANDING_CURRENCY

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"branding_currency of type {type(v)} is not a str.")

        return v

    branding_timezone: str = Field(
        settings_defaults.BRANDING_TIMEZONE,
        description="The timezone used for branding purposes throughout the platform.",
        examples=["America/New_York"],
        title="Branding Timezone",
    )
    """
    The timezone used for branding purposes throughout the platform.
    This setting specifies the timezone that is used in various branding contexts,
    such as email templates, user interfaces, and documentation. It can be used to
    indicate the timezone in which dates and times are presented to users.
    :type: str
    :default: Value from ``settings_defaults.BRANDING_TIMEZONE``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("branding_timezone")
    def validate_branding_timezone(cls, v: Optional[str]) -> str:
        """Validates the `branding_timezone` field.

        Args:
            v (Optional[str]): The branding timezone value to validate.

        Returns:
            str: The validated branding timezone.
        """
        if v in THE_EMPTY_SET:
            return settings_defaults.BRANDING_TIMEZONE

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"branding_timezone of type {type(v)} is not a str.")

        return v

    branding_contact_url: Optional[HttpUrl] = Field(
        settings_defaults.BRANDING_CONTACT_URL,
        description="The contact URL used for branding purposes throughout the platform.",
        examples=["https://www.example.com/contact"],
        title="Branding Contact URL",
    )
    """
    The contact URL used for branding purposes throughout the platform.
    This setting specifies the URL that users can visit to contact
    the organization or company that owns or operates the platform.
    It is used in various branding contexts, such as email templates,
    user interfaces, and documentation.
    :type: str
    :default: Value from ``settings_defaults.BRANDING_CONTACT_URL``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("branding_contact_url")
    def validate_branding_contact_url(cls, v: Optional[HttpUrl]) -> Optional[HttpUrl]:
        """Validates the `branding_contact_url` field.

        Args:
            v (Optional[HttpUrl]): The branding contact URL value to validate.

        Returns:
            Optional[HttpUrl]: The validated branding contact URL.
        """
        if v is None or v == "":
            return settings_defaults.BRANDING_CONTACT_URL
        return v

    branding_support_hours: str = Field(
        settings_defaults.BRANDING_SUPPORT_HOURS,
        description="The support hours used for branding purposes throughout the platform.",
        examples=["Mon-Fri 9am-5pm EST"],
        title="Branding Support Hours",
    )
    """
    The support hours used for branding purposes throughout the platform.
    This setting specifies the hours during which support is available
    for users of the platform. It is used in various branding contexts,
    such as email templates, user interfaces, and documentation.
    :type: str
    :default: Value from ``settings_defaults.BRANDING_SUPPORT_HOURS``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("branding_support_hours")
    def validate_branding_support_hours(cls, v: Optional[str]) -> str:
        """Validates the `branding_support_hours` field.

        Args:
            v (Optional[str]): The branding support hours value to validate.

        Returns:
            str: The validated branding support hours.
        """
        if v in THE_EMPTY_SET:
            return settings_defaults.BRANDING_SUPPORT_HOURS

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"branding_support_hours of type {type(v)} is not a str.")

        return v

    branding_url_facebook: Optional[HttpUrl] = Field(
        settings_defaults.BRANDING_URL_FACEBOOK,
        description="The Facebook URL used for branding purposes throughout the platform.",
        examples=["https://www.facebook.com/example"],
        title="Branding URL Facebook",
    )
    """
    The Facebook URL used for branding purposes throughout the platform.
    This setting specifies the Facebook page URL of the organization or company that owns
    or operates the platform. It is used in various branding contexts,
    such as email templates, user interfaces, and documentation.
    :type: Optional[HttpUrl]
    :default: Value from ``settings_defaults.BRANDING_URL_FACEBOOK``
    :raises SmarterConfigurationError: If the value is not a valid HttpUrl.
    """

    @before_field_validator("branding_url_facebook")
    def validate_branding_url_facebook(cls, v: Optional[HttpUrl]) -> Optional[HttpUrl]:
        """Validates the `branding_url_facebook` field.
        Args:
            v (Optional[HttpUrl]): The branding URL Facebook value to validate.
        Returns:
            Optional[HttpUrl]: The validated branding URL Facebook.
        """
        if v is None or v == "":
            return settings_defaults.BRANDING_URL_FACEBOOK
        return v

    branding_url_twitter: Optional[HttpUrl] = Field(
        settings_defaults.BRANDING_URL_TWITTER,
        description="The Twitter URL used for branding purposes throughout the platform.",
        examples=["https://www.twitter.com/example"],
        title="Branding URL Twitter",
    )
    """
    The Twitter URL used for branding purposes throughout the platform.
    This setting specifies the Twitter profile URL of the organization or company that owns
    or operates the platform. It is used in various branding contexts,
    such as email templates, user interfaces, and documentation.
    :type: Optional[HttpUrl]
    :default: Value from ``settings_defaults.BRANDING_URL_TWITTER``
    :raises SmarterConfigurationError: If the value is not a valid HttpUrl.
    """

    @before_field_validator("branding_url_twitter")
    def validate_branding_url_twitter(cls, v: Optional[HttpUrl]) -> Optional[HttpUrl]:
        """Validates the `branding_url_twitter` field.
        Args:
            v (Optional[HttpUrl]): The branding URL Twitter value to validate.
        Returns:
            Optional[HttpUrl]: The validated branding URL Twitter.
        """
        if v is None or v == "":
            return settings_defaults.BRANDING_URL_TWITTER
        return v

    branding_url_linkedin: Optional[HttpUrl] = Field(
        settings_defaults.BRANDING_URL_LINKEDIN,
        description="The LinkedIn URL used for branding purposes throughout the platform.",
        examples=["https://www.linkedin.com/company/example"],
        title="Branding URL LinkedIn",
    )
    """
    The LinkedIn URL used for branding purposes throughout the platform.
    This setting specifies the LinkedIn profile URL of the organization or company that owns
    or operates the platform. It is used in various branding contexts,
    such as email templates, user interfaces, and documentation.
    :type: Optional[HttpUrl]
    :default: Value from ``settings_defaults.BRANDING_URL_LINKEDIN``
    :raises SmarterConfigurationError: If the value is not a valid HttpUrl.
    """

    @before_field_validator("branding_url_linkedin")
    def validate_branding_url_linkedin(cls, v: Optional[HttpUrl]) -> Optional[HttpUrl]:
        """Validates the `branding_url_linkedin` field.
        Args:
            v (Optional[HttpUrl]): The branding URL LinkedIn value to validate.
        Returns:
            Optional[HttpUrl]: The validated branding URL LinkedIn.
        """
        if v is None or v == "":
            return settings_defaults.BRANDING_URL_LINKEDIN
        return v

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
        if isinstance(v, int):
            return v
        if v in THE_EMPTY_SET:
            return settings_defaults.CACHE_EXPIRATION
        try:
            int_value = int(v)  # type: ignore[reportArgumentType]
            if int_value < 0:
                raise SmarterConfigurationError(f"cache_expiration {int_value} must be a positive integer.")
            return int_value
        except ValueError as e:
            raise SmarterConfigurationError("could not validate cache_expiration") from e

    chat_cache_expiration: int = Field(
        settings_defaults.CHAT_CACHE_EXPIRATION,
        gt=0,
        description="The chat cache expiration time in seconds for cached chat data.",
        title="Chat Cache Expiration",
    )
    """
    The chat cache expiration time in seconds for cached chat data.
    This setting defines how long cached chat data should be considered valid before it is
    refreshed or invalidated. A shorter expiration time may lead to more frequent
    cache refreshes, while a longer expiration time can improve performance by reducing
    the number of cache lookups.

    :type: int
    :default: Value from ``settings_defaults.CHAT_CACHE_EXPIRATION``
    :raises SmarterConfigurationError: If the value is not a positive integer.

    see: :class:`smarter.apps.prompt.models.ChatHelper`
    """

    @before_field_validator("chat_cache_expiration")
    def parse_chat_cache_expiration(cls, v: Optional[Union[int, str]]) -> int:
        """Validates the 'chat_cache_expiration' field.
        Args:
            v (Optional[Union[int, str]]): the chat_cache_expiration value to validate
        Returns:
            int: The validated chat_cache_expiration.
        """
        if isinstance(v, int):
            return v
        if v in THE_EMPTY_SET:
            return settings_defaults.CHAT_CACHE_EXPIRATION
        try:
            int_value = int(v)  # type: ignore[reportArgumentType]
            if int_value < 0:
                raise SmarterConfigurationError(f"chat_cache_expiration {int_value} must be a positive integer.")
            return int_value
        except ValueError as e:
            raise SmarterConfigurationError("could not validate chat_cache_expiration") from e

    chatbot_cache_expiration: int = Field(
        settings_defaults.CHATBOT_CACHE_EXPIRATION,
        gt=0,
        description="The chatbot cache expiration time in seconds for cached chatbot data.",
        title="Chatbot Cache Expiration",
    )
    """
    The chatbot cache expiration time in seconds for cached chatbot data.
    This setting defines how long cached chatbot data should be considered valid before it is
    refreshed or invalidated. A shorter expiration time may lead to more frequent
    cache refreshes, while a longer expiration time can improve performance by reducing
    the number of cache lookups.

    :type: int
    :default: Value from ``settings_defaults.CHATBOT_CACHE_EXPIRATION``
    :raises SmarterConfigurationError: If the value is not a positive integer.
    """

    @before_field_validator("chatbot_cache_expiration")
    def parse_chatbot_cache_expiration(cls, v: Optional[Union[int, str]]) -> int:
        """Validates the 'chatbot_cache_expiration' field.
        Args:
            v (Optional[Union[int, str]]): the chatbot_cache_expiration value to validate
        Returns:
            int: The validated chatbot_cache_expiration.
        """
        if isinstance(v, int):
            return v
        if v in THE_EMPTY_SET:
            return settings_defaults.CHATBOT_CACHE_EXPIRATION
        try:
            int_value = int(v)  # type: ignore[reportArgumentType]
            if int_value < 0:
                raise SmarterConfigurationError(f"chatbot_cache_expiration {int_value} must be a positive integer.")
            return int_value
        except ValueError as e:
            raise SmarterConfigurationError("could not validate chatbot_cache_expiration") from e

    chatbot_max_returned_history: int = Field(
        settings_defaults.CHATBOT_MAX_RETURNED_HISTORY,
        gt=0,
        description="The maximum number of chat history messages to return from the chatbot.",
        title="Chatbot Max Returned History",
    )
    """
    The maximum number of chat history messages to return from the chatbot.
    This setting defines the maximum number of previous chat messages that the chatbot
    will include in its responses. Limiting the number of returned messages can help
    improve performance and reduce response times.
    :type: int
    :default: Value from ``settings_defaults.CHATBOT_MAX_RETURNED_HISTORY``
    :raises SmarterConfigurationError: If the value is not a positive integer.
    """

    @before_field_validator("chatbot_max_returned_history")
    def parse_chatbot_max_returned_history(cls, v: Optional[Union[int, str]]) -> int:
        """Validates the 'chatbot_max_returned_history' field.
        Args:
            v (Optional[Union[int, str]]): the chatbot_max_returned_history value to validate
        Returns:
            int: The validated chatbot_max_returned_history.
        """
        if isinstance(v, int):
            return v
        if v in THE_EMPTY_SET:
            return settings_defaults.CHATBOT_MAX_RETURNED_HISTORY
        try:
            int_value = int(v)  # type: ignore[reportArgumentType]
            if int_value < 0:
                raise SmarterConfigurationError(f"chatbot_max_returned_history {int_value} must be a positive integer.")
            return int_value
        except ValueError as e:
            raise SmarterConfigurationError("could not validate chatbot_max_returned_history") from e

    chatbot_tasks_create_dns_record: bool = Field(
        settings_defaults.CHATBOT_TASKS_CREATE_DNS_RECORD,
        description="True if DNS records should be created for chatbot tasks.",
        title="Chatbot Tasks Create DNS Record",
    )
    """
    Set these to true if we *DO NOT* place a wildcard A record in the customer API domain
    requiring that every chatbot have its own A record. This is the default behavior.
    For programmatically creating DNS records in AWS Route53 during ChatBot deployment.

    :type: bool
    :default: Value from ``settings_defaults.CHATBOT_TASKS_CREATE_DNS_RECORD``
    :raises SmarterConfigurationError: If the value is not a boolean.
    """

    @before_field_validator("chatbot_tasks_create_dns_record")
    def parse_chatbot_tasks_create_dns_record(cls, v: Optional[Union[bool, str]]) -> bool:
        """Validates the 'chatbot_tasks_create_dns_record' field.

        Args:
            v (Optional[Union[bool, str]]): the chatbot_tasks_create_dns_record value to validate

        Returns:
            bool: The validated chatbot_tasks_create_dns_record.
        """
        if isinstance(v, bool):
            return v
        if v in THE_EMPTY_SET:
            return settings_defaults.CHATBOT_TASKS_CREATE_DNS_RECORD
        if isinstance(v, str):
            return v.lower() in ["true", "1", "t", "y", "yes"]

        raise SmarterConfigurationError(f"could not validate chatbot_tasks_create_dns_record: {v}")

    chatbot_tasks_create_ingress_manifest: bool = Field(
        settings_defaults.CHATBOT_TASKS_CREATE_INGRESS_MANIFEST,
        description="True if ingress manifests should be created for chatbot tasks.",
        title="Chatbot Tasks Create Ingress Manifest",
    )
    """
    True if ingress manifests should be created for chatbot tasks.
    For programmatically creating ingress manifests during ChatBot deployment.
    :type: bool
    :default: Value from ``settings_defaults.CHATBOT_TASKS_CREATE_INGRESS_MANIFEST``
    :raises SmarterConfigurationError: If the value is not a boolean.
    """

    @before_field_validator("chatbot_tasks_create_ingress_manifest")
    def parse_chatbot_tasks_create_ingress_manifest(cls, v: Optional[Union[bool, str]]) -> bool:
        """Validates the 'chatbot_tasks_create_ingress_manifest' field.
        Args:
            v (Optional[Union[bool, str]]): the chatbot_tasks_create_ingress_manifest value to validate
        Returns:
            bool: The validated chatbot_tasks_create_ingress_manifest.
        """
        if isinstance(v, bool):
            return v
        if v in THE_EMPTY_SET:
            return settings_defaults.CHATBOT_TASKS_CREATE_INGRESS_MANIFEST
        if isinstance(v, str):
            return v.lower() in ["true", "1", "t", "y", "yes"]

        raise SmarterConfigurationError(f"could not validate chatbot_tasks_create_ingress_manifest: {v}")

    chatbot_tasks_default_ttl: int = Field(
        settings_defaults.CHATBOT_TASKS_DEFAULT_TTL,
        description="Default TTL (time to live) for DNS records created in AWS Route53 during ChatBot deployment.",
        title="Chatbot Tasks Default TTL",
        ge=0,
    )
    """
    Default TTL (time to live) for DNS records created in AWS Route53 during ChatBot deployment.
    :type: int
    :default: Value from ``settings_defaults.CHATBOT_TASKS_DEFAULT_TTL``
    :raises SmarterConfigurationError: If the value is not a non-negative integer.
    """

    @before_field_validator("chatbot_tasks_default_ttl")
    def parse_chatbot_tasks_default_ttl(cls, v: Optional[Union[int, str]]) -> int:
        """Validates the 'chatbot_tasks_default_ttl' field.
        Args:
            v (Optional[Union[int, str]]): the chatbot_tasks_default_ttl value to validate
        Returns:
            int: The validated chatbot_tasks_default_ttl.
        """
        if isinstance(v, int):
            return v
        if v in THE_EMPTY_SET:
            return settings_defaults.CHATBOT_TASKS_DEFAULT_TTL
        try:
            int_value = int(v)  # type: ignore[reportArgumentType]
            if int_value < 0:
                raise SmarterConfigurationError(
                    f"chatbot_tasks_default_ttl {int_value} must be a non-negative integer."
                )
            return int_value
        except ValueError as e:
            raise SmarterConfigurationError(f"could not validate chatbot_tasks_default_ttl: {v}") from e

    chatbot_tasks_celery_max_retries: int = Field(
        settings_defaults.CHATBOT_TASKS_CELERY_MAX_RETRIES,
        gt=0,
        description="Maximum number of retries for chatbot tasks in Celery.",
        title="Chatbot Tasks Celery Max Retries",
    )
    """
    Maximum number of retries for chatbot tasks in Celery.
    :type: int
    :default: Value from ``settings_defaults.CHATBOT_TASKS_CELERY_MAX_RETRIES``
    :raises SmarterConfigurationError: If the value is not a non-negative integer.
    """

    @before_field_validator("chatbot_tasks_celery_max_retries")
    def parse_chatbot_tasks_celery_max_retries(cls, v: Optional[Union[int, str]]) -> int:
        """Validates the 'chatbot_tasks_celery_max_retries' field.
        Args:
            v (Optional[Union[int, str]]): the chatbot_tasks_celery_max_retries value to validate
        Returns:
            int: The validated chatbot_tasks_celery_max_retries.
        """
        if isinstance(v, int):
            return v
        if v in THE_EMPTY_SET:
            return settings_defaults.CHATBOT_TASKS_CELERY_MAX_RETRIES
        try:
            int_value = int(v)  # type: ignore[reportArgumentType]
            return int_value
        except ValueError as e:
            raise SmarterConfigurationError(f"could not validate chatbot_tasks_celery_max_retries: {v}") from e

    chatbot_tasks_celery_retry_backoff: bool = Field(
        settings_defaults.CHATBOT_TASKS_CELERY_RETRY_BACKOFF,
        description="If True, enables exponential backoff for Celery task retries related to ChatBot deployment and management",
        title="Chatbot Tasks Celery Retry Backoff",
    )
    """
    If True, enables exponential backoff for Celery task retries related to ChatBot deployment and management.
    :type: bool
    :default: Value from ``settings_defaults.CHATBOT_TASKS_CELERY_RETRY_BACKOFF``
    :raises SmarterConfigurationError: If the value is not a boolean.
    """

    @before_field_validator("chatbot_tasks_celery_retry_backoff")
    def parse_chatbot_tasks_celery_retry_backoff(cls, v: Optional[Union[bool, str]]) -> bool:
        """Validates the 'chatbot_tasks_celery_retry_backoff' field.
        Args:
            v (Optional[Union[bool, str]]): the chatbot_tasks_celery_retry_backoff value to validate
        Returns:
            bool: The validated chatbot_tasks_celery_retry_backoff.
        """
        if isinstance(v, bool):
            return v
        if v in THE_EMPTY_SET:
            return settings_defaults.CHATBOT_TASKS_CELERY_RETRY_BACKOFF
        if isinstance(v, str):
            return v.lower() in ["true", "1", "t", "y", "yes"]

        raise SmarterConfigurationError(f"could not validate chatbot_tasks_celery_retry_backoff: {v}")

    chatbot_tasks_celery_task_queue: str = Field(
        settings_defaults.CHATBOT_TASKS_CELERY_TASK_QUEUE,
        description="The Celery task queue name for chatbot tasks.",
        title="Chatbot Tasks Celery Task Queue",
    )
    """
    The Celery task queue name for chatbot tasks.
    :type: str
    :default: Value from ``settings_defaults.CHATBOT_TASKS_CELERY_TASK_QUEUE``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("chatbot_tasks_celery_task_queue")
    def validate_chatbot_tasks_celery_task_queue(cls, v: Optional[str]) -> str:
        """Validates the `chatbot_tasks_celery_task_queue` field.
        Args:
            v (Optional[str]): The chatbot tasks celery task queue value to validate.
        Returns:
            str: The validated chatbot tasks celery task queue.
        """
        if v in THE_EMPTY_SET:
            return settings_defaults.CHATBOT_TASKS_CELERY_TASK_QUEUE

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"chatbot_tasks_celery_task_queue of type {type(v)} is not a str: {v}")

        return v

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
        if isinstance(v, int):
            return v
        if v in THE_EMPTY_SET:
            return settings_defaults.PLUGIN_MAX_DATA_RESULTS
        try:
            int_value = int(v)  # type: ignore[reportArgumentType]
            if int_value < 0:
                raise SmarterConfigurationError(f"plugin_max_data_results {int_value} must be a positive integer.")
            return int_value
        except ValueError as e:
            raise SmarterConfigurationError(f"could not validate plugin_max_data_results: {v}") from e

    sensitive_files_amnesty_patterns: List[Pattern] = Field(
        settings_defaults.SENSITIVE_FILES_AMNESTY_PATTERNS,
        description="List of regex patterns for sensitive file amnesty.",
        title="Sensitive Files Amnesty Patterns",
        examples=[
            re.compile(r"^/dashboard/account/password-reset-link/[^/]+/[^/]+/$"),
            re.compile(r"^/api(/.*)?$"),
            re.compile(r"^/admin(/.*)?$"),
        ],
    )
    """
    Sensitive file amnesty patterns used by smarter.lib.django.middleware.sensitive_files.SensitiveFileAccessMiddleware.
    Requests matching these patterns will be allowed even if they match sensitive file names.

    .. note::

        Do not modify this setting unless you fully understand the implications of doing so.

    List of regex patterns for sensitive file amnesty.
    This setting defines a list of regular expression patterns that identify files
    considered sensitive. Files matching these patterns may be subject to special handling,
    such as exclusion from certain operations or additional security measures.

    :type: List[Pattern]
    :default: Value from ``settings_defaults.SENSITIVE_FILES_AMNESTY_PATTERNS``
    :raises SmarterConfigurationError: If the value is not a list of valid regex patterns.
    """

    @before_field_validator("sensitive_files_amnesty_patterns")
    def parse_sensitive_files_amnesty_patterns(cls, v: Optional[Union[List[str], str]]) -> List[Pattern]:
        """Validates the 'sensitive_files_amnesty_patterns' field.
        Args:
            v (Optional[Union[List[str], str]]): the sensitive_files_amnesty_patterns value to validate
        Returns:
            List[Pattern]: The validated sensitive_files_amnesty_patterns.
        Examples:
            >>> parse_sensitive_files_amnesty_patterns([r"^/api(/.*)?$", r"^/admin(/.*)?$"])
            [re.compile('^/api(/.*)?$'), re.compile('^/admin(/.*)?$')]
        """
        if isinstance(v, list):
            patterns = []
            for item in v:
                if isinstance(item, str):
                    try:
                        patterns.append(re.compile(item))
                    except re.error as e:
                        raise SmarterConfigurationError(f"Invalid regex pattern: {item}") from e
                elif hasattr(item, "pattern") and hasattr(item, "match"):
                    patterns.append(item)
                else:
                    raise SmarterConfigurationError(
                        "sensitive_files_amnesty_patterns must be a list of strings or compiled regex patterns."
                    )
            return patterns
        if v in THE_EMPTY_SET:
            return settings_defaults.SENSITIVE_FILES_AMNESTY_PATTERNS
        if isinstance(v, str):
            try:
                return [re.compile(v)]
            except re.error as e:
                raise SmarterConfigurationError(f"Invalid regex pattern: {v}") from e

        raise SmarterConfigurationError(f"could not validate sensitive_files_amnesty_patterns: {v}")

    debug_mode: bool = Field(
        settings_defaults.DEBUG_MODE,
        description="True if debug mode is enabled. This enables verbose logging and other debug features.",
        title="Debug Mode",
    )
    """
    True if debug mode is enabled. This enables verbose logging and other debug features.

    When debug mode is enabled, the platform will log additional information useful for
    troubles hooting and development. This may include detailed error messages, stack traces, and
    other diagnostic data that can help identify issues during development or testing.

    :type: bool
    :default: Value from ``settings_defaults.DEBUG_MODE``
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
            return settings_defaults.DEBUG_MODE
        if isinstance(v, str):
            return v.lower() in ["true", "1", "t", "y", "yes"]

        raise SmarterConfigurationError(f"could not validate debug_mode: {v}")

    dump_defaults: bool = Field(
        settings_defaults.DUMP_DEFAULTS,
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
    :default: Value from ``settings_defaults.DUMP_DEFAULTS``
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
            return settings_defaults.DUMP_DEFAULTS
        if isinstance(v, str):
            return v.lower() in ["true", "1", "t", "y", "yes"]

        raise SmarterConfigurationError(f"could not validate dump_defaults: {v}")

    default_missing_value: str = Field(
        DEFAULT_MISSING_VALUE,
        description="Default missing value placeholder string. Used for consistency across settings.",
        examples=["SET-ME-PLEASE"],
        title="Default Missing Value",
    )
    """
    Default missing value placeholder string. Used for consistency across settings.
    This string is used as a placeholder for configuration values that have not been set.
    It indicates that the value is missing and should be provided by the user or administrator.
    Using a consistent placeholder helps identify unset values during debugging and configuration reviews.

    :type: str
    :default: Value from ``DEFAULT_MISSING_VALUE``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    # new in 0.13.26
    # True if developer mode is enabled. Used as a means to configure a production
    # Docker container to run locally for student use.
    developer_mode: bool = Field(
        settings_defaults.DEVELOPER_MODE,
        description="True if developer mode is enabled. Used as a means to configure a production Docker container to run locally for student use.",
        title="Developer Mode",
    )
    """
    True if developer mode is enabled. Used as a means to configure a production Docker container to run locally for student use.
    When developer mode is enabled, certain restrictions or configurations that are typical
    of a production environment may be relaxed or altered to facilitate local development
    and testing. This allows developers to work with a production-like setup without the
    constraints that would normally apply in a live environment.

    :type: bool
    :default: Value from ``settings_defaults.DEVELOPER_MODE``
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
            return settings_defaults.DEVELOPER_MODE
        if isinstance(v, str):
            return v.lower() in ["true", "1", "t", "y", "yes"]

        raise SmarterConfigurationError(f"could not validate developer_mode: {v}")

    django_default_file_storage: str = Field(
        settings_defaults.DJANGO_DEFAULT_FILE_STORAGE,
        description="The default Django file storage backend.",
        examples=["storages.backends.s3boto3.S3Boto3Storage", "django.core.files.storage.FileSystemStorage"],
        title="Django Default File Storage Backend",
    )
    """
    The default Django file storage backend.
    This setting determines where Django will store uploaded files by default.
    It can be configured to use different storage backends, such as Amazon S3 or the local file system,
    depending on the needs of the application and its deployment environment.

    :type: str
    :default: Value from ``settings_defaults.DJANGO_DEFAULT_FILE_STORAGE``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    email_admin: EmailStr = Field(
        settings_defaults.EMAIL_ADMIN,
        description="The administrator email address used for system notifications and alerts.",
        examples=["admin@example.com"],
        title="Administrator Email Address",
    )
    """
    The administrator email address used for system notifications and alerts.
    This email address is used as the primary contact for system notifications,
    alerts, and other administrative communications related to the platform.

    :type: str
    :default: Value from ``settings_defaults.EMAIL_ADMIN``
    :raises SmarterConfigurationError: If the value is not a valid email address.
    """

    @before_field_validator("email_admin")
    def validate_email_admin(cls, v: Optional[EmailStr]) -> EmailStr:
        """Validates the `email_admin` field.

        Args:
            v (Optional[EmailStr]): The administrator email address value to validate.

        Returns:
            EmailStr: The validated administrator email address.
        """
        if v in THE_EMPTY_SET:
            return settings_defaults.EMAIL_ADMIN
        if not isinstance(v, str):
            raise SmarterConfigurationError(f"email_admin is not a valid EmailStr: {v}")
        return v

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

    fernet_encryption_key: SecretStr = Field(
        settings_defaults.FERNET_ENCRYPTION_KEY,
        description="The Fernet encryption key used for encrypting Smarter Secrets data.",
        examples=["gAAAAABh..."],
        title="Fernet Encryption Key",
    )
    """
    The Fernet encryption key used for encrypting Smarter Secrets data.
    This setting provides the key used for symmetric encryption and decryption
    of sensitive data within the platform. The key should be a URL-safe base64-encoded
    32-byte key.

    :type: str
    :default: Value from ``settings_defaults.FERNET_ENCRYPTION_KEY``
    :raises SmarterConfigurationError: If the value is not a valid Fernet key.
    """

    file_drop_zone_enabled: bool = Field(
        settings_defaults.FILE_DROP_ZONE_ENABLED,
        description="True if the file drop zone feature is enabled based on the current environment.",
        title="File Drop Zone Enabled",
    )
    """Determines if the file drop zone feature is enabled based on the current environment.

    Returns:
        bool: True if the file drop zone is enabled, False otherwise.
    """

    @before_field_validator("fernet_encryption_key")
    def validate_fernet_encryption_key(cls, v: Optional[SecretStr]) -> Optional[SecretStr]:
        """Validates the `fernet_encryption_key` field.

        Args:
            v (Optional[SecretStr]): The Fernet encryption key value to validate.
        Raises:
            ValueError: If the Fernet encryption key is invalid.
            SmarterValueError: If the Fernet encryption key is not found.

        Returns:
            Optional[str]: The validated Fernet encryption key.
        """

        if v is None:
            return settings_defaults.FERNET_ENCRYPTION_KEY

        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError(f"fernet_encryption_key of type {type(v)} is not a SecretStr: {v}")
        try:
            # Decode the key using URL-safe base64
            encryption_key = v.get_secret_value()
            decoded_key = base64.urlsafe_b64decode(encryption_key)
            # Ensure the decoded key is exactly 32 bytes
            if len(decoded_key) != 32:
                raise ValueError("Fernet key must be exactly 32 bytes when decoded.")
        except (TypeError, ValueError, base64.binascii.Error) as e:  # type: ignore[catch-base-exception]

            raise SmarterValueError(f"Invalid Fernet encryption key: {encryption_key}. Error: {e}") from e

        return v

    gemini_api_key: SecretStr = Field(
        settings_defaults.GEMINI_API_KEY,
        description="The API key for Google Gemini services. Masked by pydantic SecretStr.",
        examples=["sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"],
        title="Google Gemini API Key",
    )
    """
    The API key for Google Gemini services. Masked by pydantic SecretStr.
    This setting provides the API key used to authenticate with Google Gemini services.
    It is required for accessing Gemini's APIs and services.

    :type: SecretStr
    :default: Value from ``settings_defaults.GEMINI_API_KEY``
    :raises SmarterConfigurationError: If the value is not a valid API key.
    """

    @before_field_validator("gemini_api_key")
    def validate_gemini_api_key(cls, v: Optional[SecretStr]) -> SecretStr:
        """Validates the `gemini_api_key` field.

        Args:
            v (Optional[SecretStr]): The Gemini API key value to validate.

        Returns:
            SecretStr: The validated Gemini API key.
        """
        if str(v) in THE_EMPTY_SET:
            return settings_defaults.GEMINI_API_KEY
        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError(f"gemini_api_key of type {type(v)} is not a SecretStr.")

        return v

    google_maps_api_key: SecretStr = Field(
        settings_defaults.GOOGLE_MAPS_API_KEY,
        description="The API key for Google Maps services. Masked by pydantic SecretStr. Used for geocoding, maps, and places APIs, for the OpenAI get_weather() example function.",
        examples=["AIzaSy..."],
        title="Google Maps API Key",
    )
    """
    The API key for Google Maps services. Masked by pydantic SecretStr. Used for geocoding, maps, and places APIs, for the OpenAI get_weather() example function.
    This setting provides the API key used to authenticate with Google Maps services.
    It is required for accessing Google Maps APIs such as geocoding, maps rendering,
    and places information.

    :type: SecretStr
    :default: Value from ``settings_defaults.GOOGLE_MAPS_API_KEY``
    :raises SmarterConfigurationError: If the value is not a valid API key.
    """

    @before_field_validator("google_maps_api_key")
    def validate_google_maps_api_key(cls, v: Optional[SecretStr]) -> SecretStr:
        """Validates the `google_maps_api_key` field.

        Args:
            v (Optional[SecretStr]): The Google Maps API key value to validate.

        Returns:
            SecretStr: The validated Google Maps API key.
        """
        if str(v) in THE_EMPTY_SET:
            return settings_defaults.GOOGLE_MAPS_API_KEY
        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError(f"google_maps_api_key of type {type(v)} is not a SecretStr.")
        return v

    google_service_account: SecretStr = Field(
        settings_defaults.GOOGLE_SERVICE_ACCOUNT,
        description="The Google service account credentials as a dictionary. Used for Google Cloud services integration.",
        examples=[{"type": "service_account", "project_id": "my-project", "...": "..."}],
        title="Google Service Account Credentials",
    )
    """
    The Google service account credentials as a dictionary. Used for Google Cloud services integration.
    This setting contains the credentials for a Google service account in JSON format.
    It is used to authenticate and authorize access to Google Cloud services on behalf
    of the platform.

    :type: dict
    :default: Value from ``settings_defaults.GOOGLE_SERVICE_ACCOUNT``
    :raises SmarterConfigurationError: If the value is not a valid service account JSON.
    """

    @before_field_validator("google_service_account")
    def validate_google_service_account(cls, v: Optional[SecretStr]) -> Optional[SecretStr]:
        """Validates the `google_service_account` field.

        Args:
            v (Optional[SecretStr]): The Google service account value to validate.
        Returns:
            SecretStr: The validated Google service account.
        """
        if v is None:
            return settings_defaults.GOOGLE_SERVICE_ACCOUNT

        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError(f"google_service_account of type {type(v)} is not a SecretStr.")
        return v

    internal_ip_prefixes: List[str] = Field(
        settings_defaults.INTERNAL_IP_PREFIXES,
        description="A list of internal IP prefixes used for security and middleware features.",
        examples=settings_defaults.INTERNAL_IP_PREFIXES,
        title="Internal IP Prefixes",
    )
    """
    Supplemental list of internal IP prefixes used in smarter.apps.chatbot.middleware.security.SmarterSecurityMiddleware
    and smarter.lib.django.middleware security features.

    The default value is based on the default internal IP range used by Kubernetes clusters
    by default unless otherwise configured.

    A list of internal IP prefixes used for security and middleware features.
    This setting defines IP address prefixes that are considered internal to the platform.
    It is used to identify requests originating from trusted internal sources,
    enabling specific security measures and middleware behaviors.

    :type: List[str]
    :default: Value from ``settings_defaults.INTERNAL_IP_PREFIXES``
    :raises SmarterConfigurationError: If the value is not a list of strings matching settings_defaults.INTERNAL_IP_PREFIXES
    """

    @before_field_validator("internal_ip_prefixes")
    def validate_internal_ip_prefixes(cls, v: Optional[List[str]]) -> List[str]:
        """Validates the `internal_ip_prefixes` field.

        Args:
            v (Optional[List[str]]): The internal IP prefixes value to validate.

        Returns:
            List[str]: The validated internal IP prefixes.
        """
        if v in THE_EMPTY_SET:
            return settings_defaults.INTERNAL_IP_PREFIXES

        if not isinstance(v, list):
            raise SmarterConfigurationError(f"internal_ip_prefixes of type {type(v)} is not a list: {v}")
        return v

    log_level: int = Field(
        settings_defaults.LOG_LEVEL,
        ge=0,
        le=50,
        description="The logging level for the platform based on Python logging levels: logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL",
        examples=[logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL],
        title="Logging Level",
    )

    llama_api_key: SecretStr = Field(
        settings_defaults.LLAMA_API_KEY,
        description="The API key for LLaMA services. Masked by pydantic SecretStr.",
        examples=["sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"],
        title="LLaMA API Key",
    )
    """
    The API key for LLaMA services. Masked by pydantic SecretStr.
    This setting provides the API key used to authenticate with LLaMA services.
    It is required for accessing LLaMA's APIs and services.

    :type: SecretStr
    :default: Value from ``settings_defaults.LLAMA_API_KEY``
    :raises SmarterConfigurationError: If the value is not a valid API key.
    """

    @before_field_validator("llama_api_key")
    def validate_llama_api_key(cls, v: Optional[SecretStr]) -> SecretStr:
        """Validates the `llama_api_key` field.

        Args:
            v (Optional[SecretStr]): The Llama API key value to validate.

        Returns:
            SecretStr: The validated Llama API key.
        """
        if str(v) in THE_EMPTY_SET:
            return settings_defaults.LLAMA_API_KEY

        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError(f"llama_api_key of type {type(v)} is not a SecretStr")
        return v

    local_hosts: List[str] = Field(
        settings_defaults.LOCAL_HOSTS,
        description="A list of hostnames considered local for development and testing purposes.",
        examples=settings_defaults.LOCAL_HOSTS,
        title="Local Hosts",
    )
    """
    A list of hostnames considered local for development and testing purposes.
    This setting defines hostnames that are treated as local addresses by the platform.
    It is useful for distinguishing between local and remote requests, especially
    during development and testing.

    :type: List[str]
    :default: Value from ``settings_defaults.LOCAL_HOSTS``
    :raises SmarterConfigurationError: If the value is not a list of strings matching settings_defaults.LOCAL_HOSTS
    """

    @before_field_validator("local_hosts")
    def validate_local_hosts(cls, v: Optional[List[str]]) -> List[str]:
        """Validates the `local_hosts` field.

        Args:
            v (Optional[List[str]]): The local hosts value to validate.

        Returns:
            List[str]: The validated local hosts.
        """
        if v in THE_EMPTY_SET:
            return settings_defaults.LOCAL_HOSTS

        if not isinstance(v, list):
            raise SmarterConfigurationError(f"local_hosts of type {type(v)} is not a list: {v}")
        return v

    langchain_memory_key: Optional[str] = Field(
        settings_defaults.LANGCHAIN_MEMORY_KEY,
        description="The key used for LangChain memory storage.",
        examples=["langchain_memory"],
        title="LangChain Memory Key",
    )
    """
    The key used for LangChain memory storage.
    This setting specifies the key under which LangChain memory data is stored.
    It is used to manage and retrieve memory data within LangChain applications.

    .. note::

        LangChain is not currently in use in Smarter and might be deprecated
        in a future release.

    :type: Optional[str]
    :default: Value from ``settings_defaults.LANGCHAIN_MEMORY_KEY``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("langchain_memory_key")
    def validate_langchain_memory_key(cls, v: Optional[str]) -> str:
        """Validates the `langchain_memory_key` field.

        Args:
            v (Optional[str]): The Langchain memory key value to validate.
        Returns:
            str: The validated Langchain memory key.
        """
        if str(v) in THE_EMPTY_SET and settings_defaults.LANGCHAIN_MEMORY_KEY is not None:
            return settings_defaults.LANGCHAIN_MEMORY_KEY
        return str(v)

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

    llm_default_model: str = Field(
        settings_defaults.LLM_DEFAULT_MODEL,
        description="The default LLM model to use for language model interactions.",
        examples=["gpt-4o-mini", "claude-2", "gemini"],
        title="Default LLM Model",
    )
    """
    The default LLM model to use for language model interactions.
    This setting specifies which specific language model should be used by default
    for processing natural language tasks. It determines the model variant that
    will handle requests for language generation, understanding, and other related functions.

    :type: str
    :default: Value from ``settings_defaults.LLM_DEFAULT_MODEL``
    :raises SmarterConfigurationError: If the value is not a valid LLM model name
    """

    @before_field_validator("llm_default_model")
    def validate_llm_default_model(cls, v: Optional[str]) -> Optional[str]:
        """Validates the `llm_default_model` field.

        Args:
            v (Optional[str]): The LLM default model value to validate.

        Returns:
            Optional[str]: The validated LLM default model.
        """
        if str(v) in THE_EMPTY_SET and settings_defaults.LLM_DEFAULT_MODEL is not None:
            return settings_defaults.LLM_DEFAULT_MODEL

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"llm_default_model of type {type(v)} is not a str: {v}")
        return v

    llm_default_system_role: str = Field(
        settings_defaults.LLM_DEFAULT_SYSTEM_ROLE,
        description="The default system role prompt to use for language model interactions.",
        examples=["You are a helpful chatbot..."],
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
    def validate_openai_default_max_completion_tokens(cls, v: Optional[int]) -> int:
        """Validates the `llm_default_max_tokens` field.

        Args:
            v (Optional[int]): The LLM default max tokens value to validate.

        Returns:
            int: The validated LLM default max tokens.
        """
        if isinstance(v, int):
            return v
        if v in THE_EMPTY_SET:
            return settings_defaults.LLM_DEFAULT_MAX_TOKENS

        try:
            retval = int(v)  # type: ignore
            return retval
        except (TypeError, ValueError) as e:
            raise SmarterConfigurationError(f"llm_default_max_tokens of type {type(v)} is not an int: {v}") from e

    logo: Optional[AnyUrl] = Field(
        settings_defaults.LOGO,
        description="The URL to the platform's logo image.",
        examples=["https://cdn.example.com/logo.png"],
        title="Platform Logo URL",
    )
    """
    The URL to the platform's logo image.
    This setting specifies the web address of the logo image used in the platform's user interface.
    It should be a valid URL pointing to an external image resource accessible by the frontend.

    :type: Optional[str]
    :default: Value from ``settings_defaults.LOGO``
    :raises SmarterConfigurationError: If the value is not a valid URL string.
    """

    @before_field_validator("logo")
    def validate_logo(cls, v: Optional[AnyUrl]) -> AnyUrl:
        """Validates the `logo` field.

        Args:
            v (Optional[AnyUrl]): The logo value to validate.

        Returns:
            HttpUrl: The validated logo.
        """
        if v is None:
            return settings_defaults.LOGO
        return v

    mailchimp_api_key: Optional[SecretStr] = Field(
        settings_defaults.MAILCHIMP_API_KEY,
        description="The API key for Mailchimp services. Masked by pydantic SecretStr.",
        examples=["sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"],
        title="Mailchimp API Key",
    )
    """
    The API key for Mailchimp services. Masked by pydantic SecretStr.
    This setting provides the API key used to authenticate with Mailchimp services.
    It is required for accessing Mailchimp's APIs and services.

    :type: Optional[SecretStr]
    :default: Value from ``settings_defaults.MAILCHIMP_API_KEY``
    :raises SmarterConfigurationError: If the value is not a valid API key.
    """

    @before_field_validator("mailchimp_api_key")
    def validate_mailchimp_api_key(cls, v: Optional[SecretStr]) -> SecretStr:
        """Validates the `mailchimp_api_key` field.

        Args:
            v (Optional[SecretStr]): The Mailchimp API key value to validate.

        Returns:
            SecretStr: The validated Mailchimp API key.
        """
        if str(v) in THE_EMPTY_SET and settings_defaults.MAILCHIMP_API_KEY is not None:
            return settings_defaults.MAILCHIMP_API_KEY

        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError(f"mailchimp_api_key of type {type(v)} is not a SecretStr")
        return v

    mailchimp_list_id: Optional[str] = Field(
        settings_defaults.MAILCHIMP_LIST_ID,
        description="The Mailchimp list ID for managing email subscribers.",
        examples=["a1b2c3d4e5"],
        title="Mailchimp List ID",
    )
    """
    The Mailchimp list ID for managing email subscribers.
    This setting specifies the unique identifier of the Mailchimp list
    used for managing email subscribers. It is required for adding, removing,
    and managing subscribers within Mailchimp.

    :type: Optional[str]
    :default: Value from ``settings_defaults.MAILCHIMP_LIST_ID``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("mailchimp_list_id")
    def validate_mailchimp_list_id(cls, v: Optional[str]) -> Optional[str]:
        """Validates the `mailchimp_list_id` field.

        Args:
            v (Optional[str]): The Mailchimp list ID value to validate.

        Returns:
            Optional[str]: The validated Mailchimp list ID.
        """
        if str(v) in THE_EMPTY_SET and settings_defaults.MAILCHIMP_LIST_ID is not None:
            return settings_defaults.MAILCHIMP_LIST_ID
        return v

    marketing_site_url: Optional[HttpUrl] = Field(
        settings_defaults.MARKETING_SITE_URL,
        description="The URL to the platform's marketing site.",
        examples=["https://www.example.com"],
        title="Marketing Site URL",
    )
    """
    The URL to the platform's marketing site.
    This setting specifies the web address of the marketing site associated
    with the platform. It should be a valid URL pointing to an external website.

    :type: Optional[httpHttpUrl]
    :default: Value from ``settings_defaults.MARKETING_SITE_URL``
    :raises SmarterConfigurationError: If the value is not a valid URL string.
    """

    @before_field_validator("marketing_site_url")
    def validate_marketing_site_url(cls, v: Optional[HttpUrl]) -> HttpUrl:
        """Validates the `marketing_site_url` field.

        Args:
            v (Optional[HttpUrl]): The marketing site URL value to validate.
        Returns:
            HttpUrl: The validated marketing site URL.
        """
        if str(v) in THE_EMPTY_SET and settings_defaults.MARKETING_SITE_URL is not None:
            return settings_defaults.MARKETING_SITE_URL
        return v  # type: ignore

    openai_api_organization: Optional[str] = Field(
        settings_defaults.OPENAI_API_ORGANIZATION,
        description="The OpenAI API organization ID.",
        examples=["org-xxxxxxxxxxxxxxxx"],
        title="OpenAI API Organization ID",
    )
    """
    The OpenAI API organization ID.
    This setting specifies the organization ID used when making requests to the OpenAI API.
    It is used to associate API requests with a specific organization account.

    :type: Optional[str]
    :default: Value from ``settings_defaults.OPENAI_API_ORGANIZATION``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("openai_api_organization")
    def validate_openai_api_organization(cls, v: Optional[str]) -> Optional[str]:
        """Validates the `openai_api_organization` field.

        Args:
            v (Optional[str]): The OpenAI API organization value to validate.

        Returns:
            Optional[str]: The validated OpenAI API organization.
        """
        if str(v) in THE_EMPTY_SET and settings_defaults.OPENAI_API_ORGANIZATION is not None:
            return settings_defaults.OPENAI_API_ORGANIZATION

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"openai_api_organization of type {type(v)} is not a str: {v}")
        return v

    openai_api_key: SecretStr = Field(
        settings_defaults.OPENAI_API_KEY,
        description="The API key for OpenAI services. Masked by pydantic SecretStr.",
        examples=["sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"],
        title="OpenAI API Key",
    )
    """
    The API key for OpenAI services. Masked by pydantic SecretStr.
    This setting provides the API key used to authenticate with OpenAI services.
    It is required for accessing OpenAI's APIs and services.

    :type: SecretStr
    :default: Value from ``settings_defaults.OPENAI_API_KEY``
    :raises SmarterConfigurationError: If the value is not a valid API key.
    """

    @before_field_validator("openai_api_key")
    def validate_openai_api_key(cls, v: Optional[SecretStr]) -> SecretStr:
        """Validates the `openai_api_key` field.

        Args:
            v (Optional[SecretStr]): The OpenAI API key value to validate.
        Returns:
            SecretStr: The validated OpenAI API key.
        """
        if str(v) in THE_EMPTY_SET and settings_defaults.OPENAI_API_KEY is not None:
            return settings_defaults.OPENAI_API_KEY

        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError(f"openai_api_key of type {type(v)} is not a SecretStr")

        return v

    openai_endpoint_image_n: Optional[int] = Field(
        settings_defaults.OPENAI_ENDPOINT_IMAGE_N,
        description="The number of images to generate per request to the OpenAI image endpoint.",
        examples=[1, 2, 4],
        title="OpenAI Endpoint Image Number",
    )
    """
    The number of images to generate per request to the OpenAI image endpoint.
    This setting specifies how many images should be generated in response to
    a single request to the OpenAI image generation API.

    :type: Optional[int]
    :default: Value from ``settings_defaults.OPENAI_ENDPOINT_IMAGE_N``
    :raises SmarterConfigurationError: If the value is not a positive integer.
    """

    @before_field_validator("openai_endpoint_image_n")
    def validate_openai_endpoint_image_n(cls, v: Optional[int]) -> int:
        """Validates the `openai_endpoint_image_n` field.

        Args:
            v (Optional[int]): The OpenAI endpoint image number value to validate.
        Returns:
            int: The validated OpenAI endpoint image number.
        """
        if isinstance(v, int):
            return v
        if str(v) in THE_EMPTY_SET and settings_defaults.OPENAI_ENDPOINT_IMAGE_N is not None:
            return settings_defaults.OPENAI_ENDPOINT_IMAGE_N
        if isinstance(v, str):
            try:
                v = int(v)
                return v
            except (TypeError, ValueError) as e:
                raise SmarterConfigurationError(f"openai_endpoint_image_n of type {type(v)} is not an int: {v}") from e
        if not isinstance(v, int):
            raise SmarterConfigurationError(f"openai_endpoint_image_n of type {type(v)} is not an int: {v}")

        return int(v)

    openai_endpoint_image_size: Optional[str] = Field(
        settings_defaults.OPENAI_ENDPOINT_IMAGE_SIZE,
        description="The size of images to generate from the OpenAI image endpoint.",
        examples=["256x256", "512x512", "1024x768"],
        title="OpenAI Endpoint Image Size",
    )
    """
    The size of images to generate from the OpenAI image endpoint.
    This setting specifies the dimensions of the images to be generated
    by the OpenAI image generation API.

    :type: Optional[str]
    :default: Value from ``settings_defaults.OPENAI_ENDPOINT_IMAGE_SIZE``
    :raises SmarterConfigurationError: If the value is not a valid image size string.
    """

    platform_subdomain: Optional[str] = Field(
        settings_defaults.PLATFORM_SUBDOMAIN,
        description="The subdomain for the platform, used in constructing URLs and email addresses.",
        examples=["platform", "ubc"],
        title="Platform Subdomain",
    )

    @before_field_validator("openai_endpoint_image_size")
    def validate_openai_endpoint_image_size(cls, v: Optional[str]) -> str:
        """Validates the `openai_endpoint_image_size` field.

        Args:
            v (Optional[str]): The OpenAI endpoint image size value to validate.

        Returns:
            str: The validated OpenAI endpoint image size.
        """
        if str(v) in THE_EMPTY_SET and settings_defaults.OPENAI_ENDPOINT_IMAGE_SIZE is not None:
            return settings_defaults.OPENAI_ENDPOINT_IMAGE_SIZE

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"openai_endpoint_image_size of type {type(v)} is not a str: {v}")

        return v

    pinecone_api_key: SecretStr = Field(
        settings_defaults.PINECONE_API_KEY,
        description="The API key for Pinecone services. Masked by pydantic SecretStr.",
        examples=["xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"],
        title="Pinecone API Key",
    )
    """
    The API key for Pinecone services. Masked by pydantic SecretStr.
    This setting provides the API key used to authenticate with Pinecone services.
    It is required for accessing Pinecone's APIs and services.

    :type: SecretStr
    :default: Value from ``settings_defaults.PINECONE_API_KEY``
    :raises SmarterConfigurationError: If the value is not a valid API key.
    """

    @before_field_validator("pinecone_api_key")
    def validate_pinecone_api_key(cls, v: Optional[SecretStr]) -> Optional[SecretStr]:
        """Validates the `pinecone_api_key` field.

        Args:
            v (Optional[SecretStr]): The Pinecone API key value to validate.

        Returns:
            SecretStr: The validated Pinecone API key.
        """
        if str(v) in THE_EMPTY_SET and settings_defaults.PINECONE_API_KEY is not None:
            return settings_defaults.PINECONE_API_KEY

        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError(f"pinecone_api_key of type {type(v)} is not a SecretStr")

        return v

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

    secret_key: Optional[SecretStr] = Field(
        settings_defaults.SECRET_KEY,
        description="The Django secret key for cryptographic signing.",
        examples=["your-django-secret-key"],
        title="Django Secret Key",
    )
    """
    The Django secret key for cryptographic signing.
    This setting provides the secret key used by Django for cryptographic signing.
    It is essential for maintaining the security of sessions, cookies, and other
    cryptographic operations within the Django framework.

    :type: Optional[str]
    :default: Value from ``settings_defaults.SECRET_KEY``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("secret_key")
    def validate_secret_key(cls, v: Optional[SecretStr]) -> SecretStr:
        """Validates the `secret_key` field.

        Args:
            v (Optional[SecretStr]): The secret key value to validate.
        Returns:
            SecretStr: The validated secret key.
        """
        if v is None:
            return settings_defaults.SECRET_KEY

        if isinstance(v, str):
            try:
                v = SecretStr(v)
            except ValidationError as e:
                raise SmarterConfigurationError(f"secret_key {v} is not a valid SecretStr.") from e

        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError(f"secret_key {type(v)} is not a SecretStr.")
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

    smarter_mysql_test_database_secret_name: Optional[str] = Field(
        settings_defaults.MYSQL_TEST_DATABASE_SECRET_NAME,
        description="The secret name for the Smarter MySQL test database. Used for example Smarter Plugins that are pre-installed on new installations.",
        examples=["smarter-mysql-test-db-secret"],
        title="Smarter MySQL Test Database Secret Name",
    )
    """
    The secret name for the Smarter MySQL test database. Used for example Smarter Plugins that are pre-installed on new installations.
    This setting specifies the name of the secret in AWS Secrets Manager
    that contains the credentials for the Smarter MySQL test database.
    It is used by example Smarter Plugins that require access to a test database.

    :type: Optional[str]
    :default: Value from ``settings_defaults.MYSQL_TEST_DATABASE_SECRET_NAME`
    :raises SmarterConfigurationError: If the value is not a string.
    """

    smarter_mysql_test_database_password: Optional[SecretStr] = Field(
        settings_defaults.MYSQL_TEST_DATABASE_PASSWORD,
        description="The password for the Smarter MySQL test database. Used for example Smarter Plugins that are pre-installed on new installations.",
        examples=["your_password_here"],
        title="Smarter MySQL Test Database Password",
    )
    """
    The password for the Smarter MySQL test database. Used for example Smarter Plugins that are pre-installed on new installations.
    This setting provides the password used to connect to the Smarter MySQL test database.
    It is used by example Smarter Plugins that require access to a test database.

    :type: Optional[str]
    :default: Value from ``settings_defaults.MYSQL_TEST_DATABASE_PASSWORD``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    smarter_reactjs_app_loader_path: str = Field(
        settings_defaults.REACTJS_APP_LOADER_PATH,
        description="The path to the ReactJS app loader script.",
        examples=["/ui-chat/app-loader.js"],
        title="Smarter ReactJS App Loader Path",
    )
    """
    The path to the ReactJS app loader script.
    This setting specifies the URL path where the ReactJS application loader script is located.
    It is used to load the ReactJS frontend for the platform.

    :type: str
    :default: Value from ``settings_defaults.REACTJS_APP_LOADER_PATH``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("smarter_reactjs_app_loader_path")
    def validate_smarter_reactjs_app_loader_path(cls, v: Optional[str]) -> str:
        """Validates the `smarter_reactjs_app_loader_path` field. Needs
        to start with a slash (/) and end with '.js'. The final string value
        should be url friendly. example: /ui-chat/app-loader.js

        Args:
            v (Optional[str]): The Smarter ReactJS app loader path value to validate.

        Returns:
            str: The validated Smarter ReactJS app loader path.
        """
        if v in THE_EMPTY_SET:
            return settings_defaults.REACTJS_APP_LOADER_PATH

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"smarter_reactjs_app_loader_path of type {type(v)} is not a str: {v}")

        if not v.startswith("/"):
            raise SmarterConfigurationError(f"smarter_reactjs_app_loader_path must start with '/': {v}")
        if not v.endswith(".js"):
            raise SmarterConfigurationError(f"smarter_reactjs_app_loader_path must end with '.js': {v}")
        return v

    social_auth_google_oauth2_key: SecretStr = Field(
        settings_defaults.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY,
        description="The OAuth2 key for Google social authentication. Masked by pydantic SecretStr.",
        examples=["your-google-oauth2-key"],
        title="Google OAuth2 Key",
    )
    """
    The OAuth2 key for Google social authentication. Masked by pydantic SecretStr.
    This setting provides the OAuth2 client ID used for Google social authentication.
    It is required for enabling users to log in using their Google accounts.

    :type: SecretStr
    :default: Value from ``settings_defaults.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY``
    :raises SmarterConfigurationError: If the value is not a valid OAuth2 client ID.
    """

    @before_field_validator("social_auth_google_oauth2_key")
    def validate_social_auth_google_oauth2_key(cls, v: Optional[SecretStr]) -> SecretStr:
        """Validates the `social_auth_google_oauth2_key` field.

        Args:
            v (Optional[SecretStr]): The Google OAuth2 key value to validate.
        Returns:
            SecretStr: The validated Google OAuth2 key.
        """
        if str(v) in THE_EMPTY_SET and settings_defaults.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY:
            return settings_defaults.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY

        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError(f"social_auth_google_oauth2_key of type {type(v)} is not a SecretStr")
        return v

    social_auth_google_oauth2_secret: SecretStr = Field(
        settings_defaults.SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET,
        description="The OAuth2 secret for Google social authentication. Masked by pydantic SecretStr.",
        examples=["your-google-oauth2-secret"],
        title="Google OAuth2 Secret",
    )
    """
    The OAuth2 secret for Google social authentication. Masked by pydantic SecretStr.
    This setting provides the OAuth2 client secret used for Google social authentication.
    It is required for enabling users to log in using their Google accounts.

    :type: SecretStr
    :default: Value from ``settings_defaults.SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET``
    :raises SmarterConfigurationError: If the value is not a valid OAuth2 client secret
    """

    @before_field_validator("social_auth_google_oauth2_secret")
    def validate_social_auth_google_oauth2_secret(cls, v: Optional[SecretStr]) -> SecretStr:
        """Validates the `social_auth_google_oauth2_secret` field.

        Args:
            v (Optional[SecretStr]): The Google OAuth2 secret value to validate.

        Returns:
            SecretStr: The validated Google OAuth2 secret.
        """
        if str(v) in THE_EMPTY_SET and settings_defaults.SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET is not None:
            return settings_defaults.SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET

        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError(f"social_auth_google_oauth2_secret of type {type(v)} is not a SecretStr.")
        return v

    social_auth_github_key: SecretStr = Field(
        settings_defaults.SOCIAL_AUTH_GITHUB_KEY,
        description="The OAuth2 key for GitHub social authentication. Masked by pydantic SecretStr.",
        examples=["your-github-oauth2-key"],
        title="GitHub OAuth2 Key",
    )
    """
    The OAuth2 key for GitHub social authentication. Masked by pydantic SecretStr.
    This setting provides the OAuth2 client ID used for GitHub social authentication.
    It is required for enabling users to log in using their GitHub accounts.

    :type: SecretStr
    :default: Value from ``settings_defaults.SOCIAL_AUTH_GITHUB_KEY``
    :raises SmarterConfigurationError: If the value is not a valid OAuth2 client ID
    """

    @before_field_validator("social_auth_github_key")
    def validate_social_auth_github_key(cls, v: Optional[SecretStr]) -> SecretStr:
        """Validates the `social_auth_github_key` field.

        Args:
            v (Optional[SecretStr]): The GitHub OAuth2 key value to validate.
        Returns:
            SecretStr: The validated GitHub OAuth2 key.
        """
        if str(v) in THE_EMPTY_SET and settings_defaults.SOCIAL_AUTH_GITHUB_KEY is not None:
            return settings_defaults.SOCIAL_AUTH_GITHUB_KEY

        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError(f"social_auth_github_key of type {type(v)} is not a SecretStr")

        return v

    social_auth_github_secret: SecretStr = Field(
        settings_defaults.SOCIAL_AUTH_GITHUB_SECRET,
        description="The OAuth2 secret for GitHub social authentication. Masked by pydantic SecretStr.",
        examples=["your-github-oauth2-secret"],
        title="GitHub OAuth2 Secret",
    )
    """
    The OAuth2 secret for GitHub social authentication. Masked by pydantic SecretStr.
    This setting provides the OAuth2 client secret used for GitHub social authentication.
    It is required for enabling users to log in using their GitHub accounts.

    :type: SecretStr
    :default: Value from ``settings_defaults.SOCIAL_AUTH_GITHUB_SECRET``
    :raises SmarterConfigurationError: If the value is not a valid OAuth2 client secret
    """

    @before_field_validator("social_auth_github_secret")
    def validate_social_auth_github_secret(cls, v: Optional[SecretStr]) -> SecretStr:
        """Validates the `social_auth_github_secret` field.

        Args:
            v (Optional[SecretStr]): The GitHub OAuth2 secret value to validate.
        Returns:
            SecretStr: The validated GitHub OAuth2 secret.
        """
        if str(v) in THE_EMPTY_SET and settings_defaults.SOCIAL_AUTH_GITHUB_SECRET is not None:
            return settings_defaults.SOCIAL_AUTH_GITHUB_SECRET

        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError(f"social_auth_github_secret of type {type(v)} is not a SecretStr.")
        return v

    social_auth_linkedin_oauth2_key: SecretStr = Field(
        settings_defaults.SOCIAL_AUTH_LINKEDIN_OAUTH2_KEY,
        description="The OAuth2 key for LinkedIn social authentication. Masked by pydantic SecretStr.",
        examples=["your-linkedin-oauth2-key"],
        title="LinkedIn OAuth2 Key",
    )
    """
    .. deprecated:: 0.13.35
        This setting is deprecated and will be removed in a future release. LinkedIn social authentication is no longer supported or recommended for new deployments.

    The OAuth2 key for LinkedIn social authentication. Masked by pydantic SecretStr.
    This setting provides the OAuth2 client ID used for LinkedIn social authentication.
    It was required for enabling users to log in using their LinkedIn accounts.

    :type: SecretStr
    :default: Value from ``settings_defaults.SOCIAL_AUTH_LINKEDIN_OAUTH2``
    :raises SmarterConfigurationError: If the value is not a valid OAuth2 client ID
    """

    @before_field_validator("social_auth_linkedin_oauth2_key")
    def validate_social_auth_linkedin_oauth2_key(cls, v: Optional[SecretStr]) -> SecretStr:
        """Validates the `social_auth_linkedin_oauth2_key` field.

        Args:
            v (Optional[SecretStr]): The LinkedIn OAuth2 key value to validate.
        Returns:
            SecretStr: The validated LinkedIn OAuth2 key.
        """
        if str(v) in THE_EMPTY_SET and settings_defaults.SOCIAL_AUTH_LINKEDIN_OAUTH2_KEY is not None:
            return settings_defaults.SOCIAL_AUTH_LINKEDIN_OAUTH2_KEY
        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError(f"social_auth_linkedin_oauth2_key of type {type(v)} is not a SecretStr.")
        return v

    social_auth_linkedin_oauth2_secret: SecretStr = Field(
        settings_defaults.SOCIAL_AUTH_LINKEDIN_OAUTH2_SECRET,
        description="The OAuth2 secret for LinkedIn social authentication. Masked by pydantic SecretStr.",
        examples=["your-linkedin-oauth2-secret"],
        title="LinkedIn OAuth2 Secret",
    )
    """
    .. deprecated:: 0.13.35
        This setting is deprecated and will be removed in a future release. LinkedIn social authentication is no longer supported or recommended for new deployments.

    The OAuth2 secret for LinkedIn social authentication. Masked by pydantic SecretStr.
    This setting provides the OAuth2 client secret used for LinkedIn social authentication.
    It was required for enabling users to log in using their LinkedIn accounts.

    :type: SecretStr
    :default: Value from ``settings_defaults.SOCIAL_AUTH_LINKEDIN_OAUTH2_SECRET``
    :raises SmarterConfigurationError: If the value is not a valid OAuth2 client secret
    """

    @before_field_validator("social_auth_linkedin_oauth2_secret")
    def validate_social_auth_linkedin_oauth2_secret(cls, v: Optional[SecretStr]) -> SecretStr:
        """Validates the `social_auth_linkedin_oauth2_secret` field.

        Args:
            v (Optional[SecretStr]): The LinkedIn OAuth2 secret value to validate.

        Returns:
            SecretStr: The validated LinkedIn OAuth2 secret.
        """
        if str(v) in THE_EMPTY_SET and settings_defaults.SOCIAL_AUTH_LINKEDIN_OAUTH2_SECRET is not None:
            return settings_defaults.SOCIAL_AUTH_LINKEDIN_OAUTH2_SECRET
        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError(f"social_auth_linkedin_oauth2_secret of type {type(v)} is not a SecretStr.")
        return v

    smtp_sender: Optional[EmailStr] = Field(
        settings_defaults.SMTP_SENDER,
        description="The sender email address for SMTP emails.",
        examples=["sender@example.com"],
        title="SMTP Sender Email Address",
    )
    """
    The sender email address for SMTP emails.
    This setting specifies the email address that will appear as the sender
    in outgoing SMTP emails sent by the platform.

    :type: Optional[EmailStr]
    :default: Value from ``settings_defaults.SMTP_SENDER``
    :raises SmarterConfigurationError: If the value is not a valid email address.
    """

    smarter_mysql_test_database_secret_name: Optional[str] = Field(
        settings_defaults.MYSQL_TEST_DATABASE_SECRET_NAME,
        description="The secret name for the Smarter MySQL test database. Used for example Smarter Plugins that are pre-installed on new installations.",
        examples=["smarter_test_db"],
        title="Smarter MySQL Test Database Secret Name",
    )
    """
    The secret name for the Smarter MySQL test database. Used for example Smarter Plugins that are pre-installed on new installations.
    This setting specifies the name of the secret in AWS Secrets Manager
    that contains the credentials for the Smarter MySQL test database.
    It is used by example Smarter Plugins that require access to a test database.
    :type: Optional[str]
    :default: Value from ``settings_defaults.MYSQL_TEST_DATABASE_SECRET_NAME``
    :raises SmarterConfigurationError: If the value is not a string. SMARTER_MYSQL_TEST_DATABASE_PASSWORD
    """

    smarter_mysql_test_database_password: Optional[SecretStr] = Field(
        settings_defaults.MYSQL_TEST_DATABASE_PASSWORD,
        description="The password for the Smarter MySQL test database. Used for example Smarter Plugins that are pre-installed on new installations.",
        examples=["smarter_test_user"],
        title="Smarter MySQL Test Database Password",
    )
    """
    The password for the Smarter MySQL test database. Used for example Smarter Plugins that are pre-installed on new installations.
    This setting provides the password used to connect to the Smarter MySQL test database.
    It is used by example Smarter Plugins that require access to a test database.
    :type: Optional[SecretStr]
    :default: Value from ``settings_defaults.MYSQL_TEST_DATABASE_PASSWORD``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("smtp_sender")
    def validate_smtp_sender(cls, v: Optional[str]) -> str:
        """Validates the `smtp_sender` field.

        Args:
            v (Optional[str]): The SMTP sender email address to validate.

        Returns:
            Optional[str]: The validated SMTP sender email address.
        """
        if v in THE_EMPTY_SET:
            v = settings_defaults.SMTP_SENDER
            SmarterValidator.validate_domain(v)

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"smtp_sender of type {type(v)} is not a str: {v}")
        return v

    smtp_password: Optional[SecretStr] = Field(
        settings_defaults.SMTP_PASSWORD,
        description="The SMTP password for authentication. Assumed to be an AWS SES-generated IAM keypair secret.",
        examples=["your-smtp-password"],
        title="SMTP Password",
    )
    """
    The SMTP password for authentication.
    This setting provides the password used to authenticate with the SMTP server.
    It is required for sending emails through the SMTP server.

    :type: Optional[SecretStr]
    :default: Value from ``settings_defaults.SMTP_PASSWORD``
    :raises SmarterConfigurationError: If the value is not a valid password.
    """

    @before_field_validator("smtp_password")
    def validate_smtp_password(cls, v: Optional[SecretStr]) -> Optional[SecretStr]:
        """Validates the `smtp_password` field.

        Args:
            v (Optional[SecretStr]): The SMTP password to validate.
        Returns:
            Optional[SecretStr]: The validated SMTP password.
        """
        if v in THE_EMPTY_SET:
            return settings_defaults.SMTP_PASSWORD

        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError(f"smtp_password of type {type(v)} is not a SecretStr")
        return v

    smtp_port: Optional[int] = Field(
        settings_defaults.SMTP_PORT,
        description="The SMTP port for sending emails.",
        examples=[25, 465, 587],
        title="SMTP Port Number",
    )
    """
    The SMTP port for sending emails.
    This setting specifies the port number used to connect to the SMTP server
    for sending outgoing emails.

    :type: Optional[int]
    :default: Value from ``settings_defaults.SMTP_PORT``
    :raises SmarterConfigurationError: If the value is not a valid port number.
    """

    @before_field_validator("smtp_port")
    def validate_smtp_port(cls, v: Optional[int]) -> Optional[int]:
        """Validates the `smtp_port` field.

        Args:
            v (Optional[int]): The SMTP port to validate.

        Returns:
            int: The validated SMTP port.
        """
        if v in THE_EMPTY_SET:
            v = settings_defaults.SMTP_PORT
        try:
            retval = int(v)  # type: ignore
        except ValueError as e:
            raise SmarterValueError("Could not convert port number to int.") from e

        if not str(retval).isdigit() or not 1 <= int(retval) <= 65535:
            raise SmarterValueError("Invalid port number")

        return retval

    smtp_use_ssl: Optional[bool] = Field(
        settings_defaults.SMTP_USE_SSL,
        description="Whether to use SSL for SMTP connections.",
        examples=[True, False],
        title="SMTP Use SSL",
    )
    """
    Whether to use SSL for SMTP connections.
    This setting indicates whether SSL (Secure Sockets Layer) should be used
    when connecting to the SMTP server for sending emails.

    :type: Optional[bool]
    :default: Value from ``settings_defaults.SMTP_USE_SSL``
    :raises SmarterConfigurationError: If the value is not a boolean.
    """

    @before_field_validator("smtp_use_ssl")
    def validate_smtp_use_ssl(cls, v: Optional[Union[bool, str]]) -> bool:
        """Validates the `smtp_use_ssl` field.

        Args:
            v (Optional[Union[bool, str]]): The SMTP use SSL flag to validate.

        Returns:
            bool: The validated SMTP use SSL flag.
        """
        if isinstance(v, bool):
            return v
        if v in THE_EMPTY_SET:
            return settings_defaults.SMTP_USE_SSL
        return str(v).lower() in ["true", "1", "yes", "on"]

    smtp_use_tls: Optional[bool] = Field(
        settings_defaults.SMTP_USE_TLS,
        description="Whether to use TLS for SMTP connections.",
        examples=[True, False],
        title="SMTP Use TLS",
    )
    """
    Whether to use TLS for SMTP connections.
    This setting indicates whether TLS (Transport Layer Security) should be used
    when connecting to the SMTP server for sending emails.

    :type: Optional[bool]
    :default: Value from ``settings_defaults.SMTP_USE_TLS``
    :raises SmarterConfigurationError: If the value is not a boolean.
    """

    @before_field_validator("smtp_use_tls")
    def validate_smtp_use_tls(cls, v: Optional[Union[bool, str]]) -> bool:
        """Validates the `smtp_use_tls` field.

        Args:
            v (Optional[Union[bool, str]]): The SMTP use TLS flag to validate.
        Returns:
            bool: The validated SMTP use TLS flag.
        """
        if isinstance(v, bool):
            return v
        if v in THE_EMPTY_SET:
            return settings_defaults.SMTP_USE_TLS
        return str(v).lower() in ["true", "1", "yes", "on"]

    smtp_username: Optional[SecretStr] = Field(
        settings_defaults.SMTP_USERNAME,
        description="The SMTP username for authentication. Assumed to be an AWS SES-generatred IAM keypair username.",
        examples=["your-smtp-username"],
        title="SMTP Username",
    )
    """
    The SMTP username for authentication.
    This setting provides the username used to authenticate with the SMTP server.
    It is required for sending emails through the SMTP server.

    :type: Optional[str]
    :default: Value from ``settings_defaults.SMTP_USERNAME``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("smtp_username")
    def validate_smtp_username(cls, v: Optional[SecretStr]) -> SecretStr:
        """Validates the `smtp_username` field.

        Args:
            v (Optional[str]): The SMTP username to validate.

        Returns:
            Optional[str]: The validated SMTP username.
        """
        if v is None:
            return settings_defaults.SMTP_USERNAME
        return v

    stripe_live_secret_key: Optional[SecretStr] = Field(
        settings_defaults.STRIPE_LIVE_SECRET_KEY,
        description="DEPRECATED: The secret key for Stripe live environment.",
        examples=["sk_live_xxxxxxxxxxxxxxxxxxxxxxxx"],
        title="Stripe Live Secret Key",
    )
    """
    .. deprecated:: 0.13.0
        This setting is deprecated and will be removed in a future release. Please use the new payment processing configuration settings.

    The secret key for Stripe live environment.
    This setting provides the secret key used to authenticate with Stripe's live environment.
    It is used for processing real transactions and payments.

    :type: Optional[str]
    :default: Value from ``settings_defaults.STRIPE_LIVE_SECRET_KEY``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("stripe_live_secret_key")
    def validate_stripe_live_secret_key(cls, v: Optional[SecretStr]) -> SecretStr:
        """Validates the `stripe_live_secret_key` field.

        Args:
            v (Optional[SecretStr]): The Stripe live secret key to validate.
        Returns:
            SecretStr: The validated Stripe live secret key.
        """
        if v is None:
            warnings.warn(
                "The 'stripe_live_secret_key' field is deprecated and will be removed in a future release.",
                DeprecationWarning,
                stacklevel=2,
            )
            return settings_defaults.STRIPE_LIVE_SECRET_KEY

        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError(f"stripe_live_secret_key of type {type(v)} is not a SecretStr.")
        return v

    stripe_test_secret_key: Optional[SecretStr] = Field(
        settings_defaults.STRIPE_TEST_SECRET_KEY,
        description="DEPRECATED: The secret key for Stripe test environment.",
        examples=["sk_test_xxxxxxxxxxxxxxxxxxxxxxxx"],
        title="Stripe Test Secret Key",
    )
    """
    .. deprecated:: 0.13.0
        This setting is deprecated and will be removed in a future release. Please use the new payment processing configuration settings.

    The secret key for Stripe test environment.
    This setting provides the secret key used to authenticate with Stripe's test environment.
    It is used for processing test transactions and payments.

    :type: Optional[str]
    :default: Value from ``settings_defaults.STRIPE_TEST_SECRET_KEY``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("stripe_test_secret_key")
    def validate_stripe_test_secret_key(cls, v: Optional[SecretStr]) -> SecretStr:
        """Validates the `stripe_test_secret_key` field.

        Args:
            v (Optional[SecretStr]): The Stripe test secret key to validate.
        Returns:
            SecretStr: The validated Stripe test secret key.
        """
        if v is None:
            warnings.warn(
                "The 'stripe_test_secret_key' field is deprecated and will be removed in a future release.",
                DeprecationWarning,
                stacklevel=2,
            )
            return settings_defaults.STRIPE_TEST_SECRET_KEY

        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError(f"stripe_test_secret_key of type {type(v)} is not a SecretStr.")
        return v

    ###########################################################################
    # Properties
    ###########################################################################

    @cached_property
    def smarter_project_website_url(self) -> str:
        """
        Return the URL for the Smarter project website.

        Example:
            >>> print(smarter_settings.smarter_project_website_url)
            https://www.smarter.sh
        """
        return SMARTER_PROJECT_WEBSITE_URL

    @cached_property
    def smarter_project_cdn_url(self) -> str:
        """
        Return the URL for the Smarter project CDN.

        Example:
            >>> print(smarter_settings.smarter_project_cdn_url)
            https://cdn.smarter.sh
        """
        return SMARTER_PROJECT_CDN_URL

    @cached_property
    def smarter_project_docs_url(self) -> str:
        """
        Return the URL for the Smarter project documentation.

        Example:
            >>> print(smarter_settings.smarter_project_docs_url)
            https://docs.smarter.sh
        """
        return SMARTER_PROJECT_DOCS_URL

    @cached_property
    def smtp_is_configured(self) -> bool:
        """
        Return True if SMTP is configured. All required smtp fields must be set.

        Example:
            >>> print(smarter_settings.smtp_is_configured)
            True

        See Also:
            - smarter_settings.smtp_host
            - smarter_settings.smtp_port
            - smarter_settings.smtp_username
            - smarter_settings.smtp_password
            - smarter_settings.smtp_from_email
        """
        required_fields = [
            self.smtp_host,
            self.smtp_port,
            self.smtp_username,
            self.smtp_password,
            self.smtp_from_email,
        ]
        return all(field not in [None, "", DEFAULT_MISSING_VALUE] for field in required_fields)

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

    @property
    def data_directory(self) -> str:
        """
        Return the path to the data directory:

        Example:
            >>> print(smarter_settings.data_directory)
            '/home/smarter_user/data'

        Note:
            This is based on the Dockerfile located in the root of the repository.
            See https://github.com/smarter-sh/smarter/blob/main/Dockerfile
        """
        return "/home/smarter_user/data"

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

    @cached_property
    def environment_cdn_domain(self) -> str:
        """
        Return the CDN domain based on the environment domain.

        Examples:
            >>> print(smarter_settings.environment_cdn_domain)
            'cdn.alpha.platform.example.com'
            >>> print(smarter_settings.environment_cdn_domain)
            'cdn.localhost:9357'

        See Also:
            - smarter_settings.platform_subdomain
            - smarter_settings.environment_platform_domain
            - smarter_settings.environment
            - SmarterEnvironments()
        """
        if self.environment_is_local:
            # returns cdn.local.example.com
            return f"cdn.{SmarterEnvironments.LOCAL}.{self.root_domain}"
        return f"cdn.{self.environment_platform_domain}"

    @cached_property
    def environment_cdn_url(self) -> str:
        """
        Return the CDN URL for the environment.

        Example:
            >>> print(smarter_settings.environment_cdn_url)
            https://cdn.alpha.platform.example.com
            >>> print(smarter_settings.environment_cdn_url)
            https://cdn.localhost:9357

        Raises:
            SmarterConfigurationError: If the constructed URL is invalid.

        Note:
            See https://github.com/smarter-sh/smarter-infrastructure for CDN setup details.
            Based on AWS CloudFront, AWS S3 and AWS Route 53. But, there are many details
            with regard to bucket policies, CNAME setup, SSL certificates, and so forth
            that are outside the scope of this comment. Please refer to the Terraform
            infrastructure repository for more information.

        See Also:
            - SmarterValidator.urlify()
            - smarter_settings.environment_cdn_domain
            - smarter_settings.environment
        """
        retval = SmarterValidator.urlify(self.environment_cdn_domain, environment=self.environment)
        if retval is None:
            raise SmarterConfigurationError(
                f"Invalid environment_cdn_domain: {self.environment_cdn_domain}. "
                "Please check your environment settings."
            )
        return retval

    @cached_property
    def root_platform_domain(self) -> str:
        """
        Return the platform domain name for the root domain.

        Example:
            >>> print(smarter_settings.root_platform_domain)
            'platform.example.com'

        See Also:
            - smarter_settings.platform_subdomain
            - smarter_settings.root_domain
        """
        return f"{self.platform_subdomain}.{self.root_domain}"

    @cached_property
    def root_proxy_domain(self) -> str:
        """
        Return the proxy domain name for the root domain.
        Used for proxying local requests inside of AWS Kubernetes environments
        during unit testing.

        Example:
            >>> print(smarter_settings.root_proxy_domain)
            'local.example.com'

        """
        return f"{SmarterEnvironments.LOCAL}.{self.root_domain}"

    @cached_property
    def platform_url(self) -> str:
        """
        Return the platform URL for the root platform domain and environment.

        Example:
            >>> print(smarter_settings.platform_url)
            https://platform.example.com

        Raises:
            SmarterConfigurationError: If the constructed URL is invalid.

        See Also:
            - SmarterValidator.urlify()
            - smarter_settings.root_platform_domain
            - smarter_settings.environment
        """
        retval = SmarterValidator.urlify(self.root_platform_domain, environment=self.environment)
        if retval is None:
            raise SmarterConfigurationError(
                f"Invalid root_platform_domain: {self.root_platform_domain}. " "Please check your environment settings."
            )
        return retval

    @cached_property
    def environment_platform_domain(self) -> str:
        """
        Return the complete domain name, including environment prefix if applicable.

        Examples:
            >>> print(smarter_settings.environment_platform_domain)
            'alpha.platform.example.com'
            >>> print(smarter_settings.environment_platform_domain)
            'localhost:9357'

        Note:
            Returns the root domain for the production environment. Otherwise,
            the returned domain is based on the environment and platform configuration.

        See Also:
            - smarter_settings.root_platform_domain
            - SmarterEnvironments()
            - self.environment
        """
        if self.environment == SmarterEnvironments.PROD:
            return self.root_platform_domain
        if self.environment in SmarterEnvironments.aws_environments:
            return f"{self.environment}.{self.root_platform_domain}"
        if self.environment_is_local:
            return f"localhost:{SMARTER_LOCAL_PORT}"
        # default domain format
        return f"{self.environment}.{self.root_platform_domain}"

    @cached_property
    def all_domains(self) -> List[str]:
        """
        Return all domains for the environment. Domains are
        generated from the root domain, subdomains, and environments and
        are returned as a sorted list.

        Example::

            [
                'api.example.com',
                'api.alpha.platform.example.com',
                'api.beta.platform.example.com',
                'api.localhost:9357',
                'api.next.platform.example.com',
                'example.com',
                'platform.example.com',
                'alpha.platform.example.com',
                'beta.platform.example.com',
                'localhost:9357',
                'next.platform.example.com'
            ]

        See Also:
            - SmarterEnvironments()
            - smarter_settings.platform_subdomain
            - smarter_settings.api_subdomain
            - smarter_settings.root_domain
            - smarter_settings.root_api_domain
            - smarter_settings.root_platform_domain
        """
        environments = [
            None,  # for root domains (no environment prefix)
            SmarterEnvironments.ALPHA,
            SmarterEnvironments.BETA,
            SmarterEnvironments.NEXT,
        ]
        subdomains = [
            self.platform_subdomain,
            self.api_subdomain,
        ]
        domains = set()
        # Add root domains
        domains.add(self.root_domain)
        domains.add(self.root_api_domain)
        domains.add(self.root_platform_domain)
        # Add environment/subdomain combinations
        for subdomain in subdomains:
            # example: platform.example.com, api.platform.example.com
            domains.add(f"{subdomain}.{self.root_domain}")
            for environment in environments[1:]:  # skip None for env-prefixed
                # example: alpha.platform.example.com, alpha.api.platform.example.com
                domains.add(f"{environment}.{subdomain}.{self.root_domain}")
        return sorted(domains)

    @cached_property
    def environment_url(self) -> str:
        """
        Return the environment URL, derived from the environment platform domain.

        Example:
            >>> print(smarter_settings.environment_url)
            https://alpha.platform.example.com

        Raises:
            SmarterConfigurationError: If the constructed URL is invalid.

        See Also:
            - SmarterValidator.urlify()
            - smarter_settings.environment_platform_domain
            - smarter_settings.environment
        """
        retval = SmarterValidator.urlify(self.environment_platform_domain, environment=self.environment)
        if retval is None:
            raise SmarterConfigurationError(
                f"Invalid environment_platform_domain: {self.environment_platform_domain}. "
                "Please check your environment settings."
            )
        return retval

    @cached_property
    def platform_name(self) -> str:
        """
        Return the platform name, derived from the root domain.

        Example:
            >>> print(smarter_settings.platform_name)
            'smarter'

        See Also:
            - smarter_settings.root_domain
        """
        return self.root_domain.split(".")[0]

    @cached_property
    def function_calling_identifier_prefix(self) -> str:
        """
        Return the prefix for function calling identifiers.

        Example:
            >>> print(smarter_settings.function_calling_identifier_prefix)
            'smarter_plugin'

        See Also:
            - smarter_settings.platform_name
        """
        return f"{self.platform_name}_plugin"

    @cached_property
    def environment_namespace(self) -> str:
        """
        Return the Kubernetes namespace for the environment.

        Example:
            >>> print(smarter_settings.environment_namespace)
            'smarter-platform-alpha'

        See Also:
            - smarter_settings.platform_subdomain
            - smarter_settings.platform_name
            - smarter_settings.environment
        """
        if self.environment_is_local:
            return f"{self.platform_name}-{SmarterEnvironments.LOCAL}"
        if self.environment in SmarterEnvironments.aws_environments:
            return f"{self.platform_name}-{self.platform_subdomain}-{self.environment}"
        raise SmarterConfigurationError(
            f"Invalid environment: {self.environment}. Please check your environment settings."
        )

    @property
    def api_subdomain(self) -> str:
        """
        Return the API subdomain for the platform.

        Example:
            >>> print(smarter_settings.api_subdomain)
            'api'
        return SMARTER_API_SUBDOMAIN
        See Also:
            - SMARTER_API_SUBDOMAIN
        """
        return SMARTER_API_SUBDOMAIN

    @cached_property
    def root_api_domain(self) -> str:
        """
        Return the root API domain name, generated
        from the system constant `SMARTER_API_SUBDOMAIN` and the root platform domain.

        Example:
            >>> print(smarter_settings.root_api_domain)
            'api.platform.example.com'

        See Also:
            - SMARTER_API_SUBDOMAIN
            - smarter_settings.environment_platform_domain
            - smarter_settings.api_subdomain
        """
        return f"{self.api_subdomain}.{self.platform_subdomain}.{self.root_domain}"

    @cached_property
    def proxy_api_domain(self) -> str:
        """
        Return the proxy API domain name for the root domain.
        Used for proxying local requests inside of AWS Kubernetes environments
        during unit testing.

        Example:
            >>> print(smarter_settings.proxy_api_domain)
            'api.local.example.com'

        """
        return f"{self.api_subdomain}.{self.root_proxy_domain}"

    @cached_property
    def environment_api_domain(self) -> str:
        """
        Return the API domain name for the current environment.

        Example:
            >>> print(smarter_settings.environment_api_domain)
            'alpha.api.platform.example.com'
            >>> print(smarter_settings.environment_api_domain)
            'api.localhost:9357'

        Note:
            Returns the root domain for the production environment. Otherwise,
            the returned domain is based on the environment and platform configuration.
            In production, this will be the root API domain; in local or other environments,
            it will be prefixed accordingly.

        See Also:
            - smarter_settings.root_api_domain
            - smarter_settings.aws_environments
            - SmarterEnvironments()
            - SMARTER_API_SUBDOMAIN
        """
        if self.environment == SmarterEnvironments.PROD:
            return self.root_api_domain
        if self.environment in SmarterEnvironments.aws_environments:
            return f"{self.environment}.{self.root_api_domain}"
        if self.environment_is_local:
            return f"{self.api_subdomain}.localhost:{SMARTER_LOCAL_PORT}"
        # default domain format
        return f"{self.environment}.{self.root_api_domain}"

    @cached_property
    def environment_api_url(self) -> str:
        """
        Creates a valid url from smarter_settings.environment_api_domain.
        Based on the Smarter shared resource identifier and the root platform domain.
        Uses urlify() to ensure consistency in http protocol and formatting and
        trailing slash.

        Example:
            >>> print(smarter_settings.environment_api_url)
            'https://alpha.api.platform.example.com'

        Raises:
            SmarterConfigurationError: If the constructed URL is invalid.

        See Also:
            - SmarterValidator.urlify()
            - smarter_settings.environment_api_domain
            - smarter_settings.environment
        """
        retval = SmarterValidator.urlify(self.environment_api_domain, environment=self.environment)
        if retval is None:
            raise SmarterConfigurationError(
                f"Invalid environment_api_domain: {self.environment_api_domain}. "
                "Please check your environment settings."
            )
        return retval

    @cached_property
    def aws_s3_bucket_name(self) -> str:
        """
        Returns the AWS S3 bucket name for the current environment.
        The bucket name is constructed from the Smarter shared resource identifier
        and the root platform domain.

        Example:
            >>> print(smarter_settings.aws_s3_bucket_name)
            'alpha.platform.example.com'

        Note:
            In local environments, this returns 'alpha.platform.example.com' as a proxy.

        See Also:
            - smarter_settings.shared_resource_identifier
            - smarter_settings.root_platform_domain
            - SmarterEnvironments()
            - smarter_settings.environment_platform_domain
        """
        if self.environment_is_local:
            return self.root_proxy_domain
        return self.environment_platform_domain

    @property
    def smtp_from_email(self) -> str:
        """
        Return the email address that will appear in the "From" field of outgoing SMTP emails.

        Example:
            >>> print(smarter_settings.smtp_from_email)
            'no-reply@platform.example.com'
        """
        return f"no-reply@{self.platform_subdomain}.{self.root_domain}"

    @property
    def smtp_host(self) -> str:
        """
        Return the SMTP host address for sending emails.

        Example:
            >>> print(smarter_settings.smtp_host)
            'email-smtp.us-east-1.amazonaws.com'
        """
        return f"email-smtp.{self.aws_region}.amazonaws.com"

    @property
    def is_using_dotenv_file(self) -> bool:
        """
        Indicates whether a `.env` file was loaded for this instance of smarter_settings.

        Returns:
            bool: True if a `.env` file was loaded, False otherwise.

        Example:
            >>> print(smarter_settings.is_using_dotenv_file)
            True

        Note:
            This property reflects the state at the time the settings object was created.
            It would gemnerally only be expected to be True in local development environments.

        See Also:
            - DOT_ENV_LOADED
        """
        return DOT_ENV_LOADED

    @cached_property
    def environment_variables(self) -> List[str]:
        """
        Lists all environment variables.

        Returns:
            List[str]: A list of the environment variable names currently set in the OS environment
                in which the application is running (e.g., the Linux process environment,
                the operating Kubernetes Pod).
        Example:
            >>> settings.environment_variables
            [
                'PAT',
                'SECRET_KEY',
                'FERNET_ENCRYPTION_KEY',
                'MYSQL_TEST_DATABASE_SECRET_NAME',
                'MYSQL_TEST_DATABASE_PASSWORD',
                'ENVIRONMENT',
                'PYTHONPATH',
                'DEVELOPER_MODE',
                'GEMINI_API_KEY',
                'ANTHROPIC_API_KEY',
                'COHERE_API_KEY',
                'FIREWORKS_API_KEY',
                'LLAMA_API_KEY',
                'MISTRAL_API_KEY',
                'OPENAI_API_KEY',
                'TOGETHERAI_API_KEY',
                'GOOGLE_SERVICE_ACCOUNT_B64',
                'GOOGLE_MAPS_API_KEY',
                'SOCIAL_AUTH_GOOGLE_OAUTH2_KEY',
                'SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET',
                'SOCIAL_AUTH_GITHUB_KEY',
                'SOCIAL_AUTH_GITHUB_SECRET',
                'SOCIAL_AUTH_LINKEDIN_OAUTH2_KEY',
                'SOCIAL_AUTH_LINKEDIN_OAUTH2_SECRET',
                'MAILCHIMP_API_KEY',
                'MAILCHIMP_LIST_ID',
                'PINECONE_API_KEY',
                'PINECONE_ENVIRONMENT',
                'ROOT_DOMAIN',
                'NAMESPACE',
                'MYSQL_HOST',
                'MYSQL_PORT',
                'MYSQL_DATABASE',
                'MYSQL_PASSWORD',
                'MYSQL_USERNAME',
                'MYSQL_ROOT_USERNAME',
                'MYSQL_ROOT_PASSWORD',
                'LOGIN_URL',
                'ADMIN_PASSWORD',
                'ADMIN_USERNAME',
                'DOCKER_IMAGE'
            ]

        Note:
            This list reflects the environment at the time the settings object was created.
        """
        return list(os.environ.keys())

    @property
    def smarter_api_key_max_lifetime_days(self) -> int:
        """Maximum lifetime for Smarter API keys in days.

        Returns:
            int: The number of days.

        Example:
            >>> print(smarter_settings.smarter_api_key_max_lifetime_days)
            90

        Warning:
            Changing this value requires a platform rebuild/redeploy.
            Expired API keys still function but will log warnings.

        See Also:
            - SMARTER_API_KEY_MAX_LIFETIME_DAYS
        """
        return SMARTER_API_KEY_MAX_LIFETIME_DAYS

    @cached_property
    def smarter_reactjs_app_loader_url(self) -> str:
        """
        Return the full URL to the ReactJS app loader script.
        This is used for loading the ReactJS Chat frontend component into html
        web pages. Attempts to validate the URL by checking for HTTP 200 status.
        Provides a fallback URL if the primary URL is not reachable.

        Example:
            >>> print(smarter_settings.smarter_reactjs_app_loader_url)
            'https://alpha.platform.example.com/ui-chat/app-loader.js'

        See Also:
            - smarter_settings.environment_cdn_url
            - smarter_settings.smarter_reactjs_app_loader_path
        """

        def check_smarter_reactjs_app_loader_url(url, timeout: float = 1.50) -> bool:
            """
            Checks if the smarter_reactjs_app_loader_url returns HTTP 200 status.
            Returns True if status code is 200, False otherwise.
            Uses requests if available, else falls back to urllib.
            """
            try:
                resp = requests.get(url, timeout=timeout)
                return resp.status_code == 200
            # pylint: disable=broad-except
            except Exception:
                return False

        intended_url = urljoin(self.environment_cdn_url, self.smarter_reactjs_app_loader_path)
        fallback_url = SMARTER_DEFAULT_REACTJS_APP_LOADER_URL
        if check_smarter_reactjs_app_loader_url(intended_url):
            logger.debug(
                "%s.smarter_reactjs_app_loader_url() is %s.",
                logger_prefix,
                formatted_text_green("READY"),
            )
            return intended_url
        elif check_smarter_reactjs_app_loader_url(fallback_url):
            logger.debug(
                "%s.smarter_reactjs_app_loader_url() is %s. ",
                logger_prefix,
                formatted_text_green("READY"),
            )
            return fallback_url
        else:
            logger.error(
                "%s.smarter_reactjs_app_loader_url() is %s. Could not retrieve the ReactJS app loader from either %s or %s. Please check your CDN configuration and internet connectivity. See https://github.com/smarter-sh/web-integration-example for details on configuring Smarter Chat.",
                logger_prefix,
                formatted_text_red("NOT_READY"),
                intended_url,
                fallback_url,
            )
            return intended_url  # return intended URL even if unreachable

    @cached_property
    def smarter_reactjs_root_div_id(self) -> str:
        """
        Return the HTML div ID used as the root for the ReactJS Chat app.
        Start with a string like: "example.com/v1/ui-chat/root", then
        convert it into an html safe id like: "example-com-v1-ui-chat-root"

        Example:
            >>> print(smarter_settings.smarter_reactjs_root_div_id)
            'example-com-v1-ui-chat-root'
        """
        APP_LOADER_FILENAME = "app-loader.js"

        loader_path = self.smarter_reactjs_app_loader_path
        if APP_LOADER_FILENAME not in loader_path:
            raise SmarterConfigurationError(
                f"Expected 'app-loader.js' in smarter_reactjs_app_loader_path, got: {loader_path}"
            )

        div_root_id = SmarterApiVersions.V1 + self.smarter_reactjs_app_loader_path.replace(APP_LOADER_FILENAME, "root")
        div_root_id = div_root_id.replace(".", "-").replace("/", "-")

        return div_root_id

    @cached_property
    def version(self) -> str:
        """
        Current version of the Smarter platform codebase
        based on the semantic version currently persisted
        to smarter.__version__.py.

        Example:
            >>> print(smarter_settings.version)
            '0.13.35'

        Note:
            This value is managed by the NPM semantic-release tooling
            process and should not be modified manually. Versions are
            bumped automatically via a GitHub Actions workflow that is
            executed on merges to the main branch. The nature of the
            version bump is based on commit messages in the merge.
            See https://github.com/smarter-sh/smarter/blob/main/docs/legacy/SEMANTIC_VERSIONING.md for more information.
        """
        return get_semantic_version()

    def to_json(self) -> dict[str, Any]:
        """
        Dump all settings. Useful for debugging and logging.

        Returns:
            dict: A dictionary containing all settings and their values.

        Example:
            >>> from smarter.lib import json
            >>> from smarter.common.conf import smarter_settings
            >>> print(json.dumps(smarter_settings.to_json(), indent=2))
            {
              "environment": {
                "is_using_dotenv_file": true,
                "os": "posix",
                ....
                },

        .. note::

            Sensitive values are masked by Pydantic SecretStr and will not be displayed in full.
            The dump is cached after the first call for performance.

        """

        retval = {
            **get_diagnostics(),
            "smarter_settings": {
                **self.model_dump(),
            },
        }
        if self.dump_defaults:
            retval["settings_defaults"] = settings_defaults.to_dict()

        if self.is_using_dotenv_file:
            retval["environment"]["dotenv"] = self.environment_variables

        retval = recursive_sort_dict(retval)
        return retval


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get the singleton settings instance."""
    try:
        return Settings()
    except ValidationError as e:
        raise SmarterConfigurationError("Invalid configuration: " + str(e)) from e


smarter_settings = get_settings()

__all__ = ["smarter_settings", "Settings"]
