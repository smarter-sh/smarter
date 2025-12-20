# pylint: disable=no-member,no-self-argument,unused-argument,R0801,too-many-lines
"""
Smarter platform configuration settings.

This module is used to generate strongly typed settings values for the platform.
It uses the pydantic_settings library to validate the configuration values.
The configuration values are initialized according to the following
prioritization sequence:

    1. constructor
    2. `.env` file
    3. environment variables (if present, these are overridden by .env file values)
    4. defaults

The Settings class also provides a dump property that returns a dictionary of all
configuration values. This is useful for debugging and logging.
"""

# -------------------- WARNING --------------------
# DO NOT IMPORT DJANGO OR ANY DJANGO MODULES. THIS
# ENTIRE MODULE SITS UPSTREAM OF DJANGO AND IS
# INTENDED TO BE USED INDEPENDENTLY OF DJANGO.
# ------------------------------------------------

# python stuff
import base64
import logging
import os  # library for interacting with the operating system
import platform  # library to view information about the server host this module runs on
import re
import warnings
from functools import lru_cache
from importlib.metadata import distributions
from typing import Any, List, Optional, Tuple, Union
from urllib.parse import urljoin

# 3rd party stuff
import boto3  # AWS SDK for Python https://boto3.amazonaws.com/v1/documentation/api/latest/index.html
from botocore.exceptions import NoCredentialsError, ProfileNotFound
from dotenv import load_dotenv
from pydantic import (
    EmailStr,
    Field,
    HttpUrl,
    SecretStr,
    ValidationError,
    ValidationInfo,
    field_validator,
)
from pydantic_settings import BaseSettings

from smarter.common.api import SmarterApiVersions
from smarter.common.const import SmarterEnvironments
from smarter.lib import json

from ..lib.django.validators import SmarterValidator

# our stuff
from .const import (
    SMARTER_API_KEY_MAX_LIFETIME_DAYS,
    SMARTER_API_SUBDOMAIN,
    SMARTER_DEFAULT_APP_LOADER_PATH,
    SMARTER_PLATFORM_SUBDOMAIN,
    VERSION,
    SmarterEnvironments,
)
from .exceptions import SmarterConfigurationError, SmarterValueError


logger = logging.getLogger(__name__)
DEFAULT_MISSING_VALUE = "SET-ME-PLEASE"
DOT_ENV_LOADED = load_dotenv()


def bool_environment_variable(var_name: str, default: bool) -> bool:
    """Get a boolean environment variable"""
    value = os.environ.get(var_name)
    if value is None:
        return default
    return value.lower() in ["true", "1", "t", "y", "yes"]


def get_env(var_name, default: Any = DEFAULT_MISSING_VALUE, prefixed=True) -> Any:
    """Get environment variable with SMARTER_ prefix fallback."""
    SMARTER_ENVIRONMENT_VARIABLE_PREFIX = "SMARTER_"

    if prefixed:
        retval = os.environ.get(f"{SMARTER_ENVIRONMENT_VARIABLE_PREFIX}{var_name}", default)
    else:
        retval = os.environ.get(var_name, default)
    if isinstance(default, str):
        return retval.strip()
    if isinstance(default, bool):
        return str(retval).lower() in ["true", "1", "t", "y", "yes"]
    if isinstance(default, int):
        try:
            return int(retval)
        except (ValueError, TypeError):
            logger.error(
                "Environment variable %s value '%s' cannot be converted to int. Using default %s.",
                var_name,
                retval,
                default,
            )
            return default
    if isinstance(default, float):
        try:
            return float(retval)
        except (ValueError, TypeError):
            logger.error(
                "Environment variable %s value '%s' cannot be converted to float. Using default %s.",
                var_name,
                retval,
                default,
            )
            return default
    if isinstance(default, list):
        if isinstance(retval, str):
            return [item.strip() for item in retval.split(",") if item.strip()]
        elif isinstance(retval, list):
            return retval
        else:
            logger.error(
                "Environment variable %s value '%s' cannot be converted to list. Using default %s.",
                var_name,
                retval,
                default,
            )
            return default
    if isinstance(default, dict):
        try:
            if isinstance(retval, str):
                return json.loads(retval)
            elif isinstance(retval, dict):
                return retval
            else:
                logger.error(
                    "Environment variable %s value '%s' cannot be converted to dict. Using default %s.",
                    var_name,
                    retval,
                    default,
                )
                return default
        except json.JSONDecodeError:
            logger.error(
                "Environment variable %s value '%s' is not valid JSON. Using default %s.", var_name, retval, default
            )
            return default
    return retval


def recursive_sort_dict(d):
    """Recursively sort a dictionary by key."""
    return {k: recursive_sort_dict(v) if isinstance(v, dict) else v for k, v in sorted(d.items())}


def get_semantic_version() -> str:
    """
    Return the semantic version number.

    Example valid values of __version__.py are:
    0.1.17
    0.1.17-alpha.1
    0.1.17-beta.1
    0.1.17-next.1
    0.1.17-next.2
    0.1.17-next.123456
    0.1.17-next-major.1
    0.1.17-next-major.2
    0.1.17-next-major.123456

    Note:
    - pypi does not allow semantic version numbers to contain a dash.
    - pypi does not allow semantic version numbers to contain a 'v' prefix.
    - pypi does not allow semantic version numbers to contain a 'next' suffix.
    """
    if not isinstance(VERSION, dict):
        return "unknown"

    version = VERSION.get("__version__")
    if not version:
        return "unknown"
    version = re.sub(r"-next\.\d+", "", version)
    return re.sub(r"-next-major\.\d+", "", version)


class DjangoPermittedStorages:
    """Django permitted storage backends"""

    AWS_S3 = "storages.backends.s3boto3.S3Boto3Storage"
    FILE_SYSTEM = "django.core.files.storage.FileSystemStorage"


# pylint: disable=too-few-public-methods
class SettingsDefaults:
    """
    Default values for Settings. This takes care of most of what we're interested in.
    It initializes from the following prioritization sequence:
      1. environment variables
      2. defaults.
    """

    ROOT_DOMAIN = get_env("ROOT_DOMAIN", "example.com")

    ANTHROPIC_API_KEY: SecretStr = SecretStr(get_env("ANTHROPIC_API_KEY"))

    # aws auth
    AWS_PROFILE = get_env("AWS_PROFILE")
    AWS_ACCESS_KEY_ID: SecretStr = SecretStr(get_env("AWS_ACCESS_KEY_ID"))
    AWS_SECRET_ACCESS_KEY: SecretStr = SecretStr(get_env("AWS_SECRET_ACCESS_KEY"))
    AWS_REGION = get_env("AWS_REGION", "us-east-1")
    AWS_IS_CONFIGURED = bool(
        AWS_PROFILE
        or (
            AWS_ACCESS_KEY_ID.get_secret_value() != DEFAULT_MISSING_VALUE
            and AWS_SECRET_ACCESS_KEY.get_secret_value() != DEFAULT_MISSING_VALUE
        )
    )

    AWS_EKS_CLUSTER_NAME = get_env("AWS_EKS_CLUSTER_NAME")
    AWS_RDS_DB_INSTANCE_IDENTIFIER = get_env("AWS_RDS_DB_INSTANCE_IDENTIFIER")
    DEBUG_MODE: bool = bool(get_env("DEBUG_MODE", False))
    DEVELOPER_MODE: bool = bool(get_env("DEVELOPER_MODE", False))

    DJANGO_DEFAULT_FILE_STORAGE = get_env("DJANGO_DEFAULT_FILE_STORAGE", DjangoPermittedStorages.AWS_S3)
    if DJANGO_DEFAULT_FILE_STORAGE == DjangoPermittedStorages.AWS_S3 and not AWS_IS_CONFIGURED:
        DJANGO_DEFAULT_FILE_STORAGE = DjangoPermittedStorages.FILE_SYSTEM
        logger.warning(
            "AWS is not configured properly. Falling back to FileSystemStorage for Django default file storage."
        )

    DUMP_DEFAULTS: bool = bool(get_env("DUMP_DEFAULTS", False))
    ENVIRONMENT = get_env("ENVIRONMENT", SmarterEnvironments.LOCAL)

    FERNET_ENCRYPTION_KEY: SecretStr = SecretStr(get_env("FERNET_ENCRYPTION_KEY"))

    GOOGLE_MAPS_API_KEY: SecretStr = SecretStr(get_env("GOOGLE_MAPS_API_KEY"))

    try:
        GOOGLE_SERVICE_ACCOUNT_B64 = get_env("GOOGLE_SERVICE_ACCOUNT_B64", "")
        GOOGLE_SERVICE_ACCOUNT: SecretStr = SecretStr(
            json.loads(base64.b64decode(GOOGLE_SERVICE_ACCOUNT_B64).decode("utf-8"))
        )
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.error("Failed to load Google service account: %s", e)
        logger.error(
            "See https://console.cloud.google.com/projectselector2/iam-admin/serviceaccounts?supportedpurview=project"
        )
        GOOGLE_SERVICE_ACCOUNT = SecretStr(json.dumps({}))

    GEMINI_API_KEY: SecretStr = SecretStr(get_env("GEMINI_API_KEY"))
    LANGCHAIN_MEMORY_KEY = get_env("LANGCHAIN_MEMORY_KEY", "chat_history")

    LLAMA_API_KEY: SecretStr = SecretStr(get_env("LLAMA_API_KEY"))

    LLM_DEFAULT_PROVIDER = "openai"
    LLM_DEFAULT_MODEL = "gpt-4o-mini"
    LLM_DEFAULT_SYSTEM_ROLE = (
        "You are a helpful chatbot. When given the opportunity to utilize "
        "function calling, you should always do so. This will allow you to "
        "provide the best possible responses to the user. If you are unable to "
        "provide a response, you should prompt the user for more information. If "
        "you are still unable to provide a response, you should inform the user "
        "that you are unable to help them at this time."
    )
    LLM_DEFAULT_TEMPERATURE = 0.5
    LLM_DEFAULT_MAX_TOKENS = 2048

    LOCAL_HOSTS = ["localhost", "127.0.0.1"]
    LOCAL_HOSTS += [host + ":8000" for host in LOCAL_HOSTS]
    LOCAL_HOSTS.append("testserver")

    LOG_LEVEL: int = logging.DEBUG if DEBUG_MODE else logging.INFO

    LOGO: HttpUrl = get_env("OPENAI_API_ORGANIZATION", "https://cdn.platform.smarter.sh/images/logo/smarter-crop.png")
    MAILCHIMP_API_KEY: SecretStr = SecretStr(get_env("MAILCHIMP_API_KEY"))
    MAILCHIMP_LIST_ID = get_env("MAILCHIMP_LIST_ID")

    MARKETING_SITE_URL: HttpUrl = get_env("OPENAI_API_ORGANIZATION", f"https://{ROOT_DOMAIN}")

    OPENAI_API_ORGANIZATION = get_env("OPENAI_API_ORGANIZATION")
    OPENAI_API_KEY: SecretStr = SecretStr(get_env("OPENAI_API_KEY"))
    OPENAI_ENDPOINT_IMAGE_N = 4
    OPENAI_ENDPOINT_IMAGE_SIZE = "1024x768"
    PINECONE_API_KEY: SecretStr = SecretStr(get_env("PINECONE_API_KEY"))

    SHARED_RESOURCE_IDENTIFIER = get_env("SHARED_RESOURCE_IDENTIFIER", "smarter")

    SMARTER_MYSQL_TEST_DATABASE_SECRET_NAME = get_env(
        "SMARTER_MYSQL_TEST_DATABASE_SECRET_NAME",
        "smarter_test_db",
    )
    SMARTER_MYSQL_TEST_DATABASE_PASSWORD: SecretStr = SecretStr(get_env("SMARTER_MYSQL_TEST_DATABASE_PASSWORD"))
    SMARTER_REACTJS_APP_LOADER_PATH = get_env("SMARTER_REACTJS_APP_LOADER_PATH", SMARTER_DEFAULT_APP_LOADER_PATH)

    # -------------------------------------------------------------------------
    # see: https://console.cloud.google.com/apis/credentials/oauthclient/231536848926-egabg8jas321iga0nmleac21ccgbg6tq.apps.googleusercontent.com?project=smarter-sh
    # -------------------------------------------------------------------------
    SOCIAL_AUTH_GOOGLE_OAUTH2_KEY: SecretStr = SecretStr(get_env("SOCIAL_AUTH_GOOGLE_OAUTH2_KEY"))
    SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET: SecretStr = SecretStr(get_env("SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET"))
    # -------------------------------------------------------------------------
    # see: https://github.com/settings/applications/2620957
    # -------------------------------------------------------------------------
    SOCIAL_AUTH_GITHUB_KEY: SecretStr = SecretStr(get_env("SOCIAL_AUTH_GITHUB_KEY"))
    SOCIAL_AUTH_GITHUB_SECRET: SecretStr = SecretStr(get_env("SOCIAL_AUTH_GITHUB_SECRET"))
    # -------------------------------------------------------------------------
    # see:  https://www.linkedin.com/developers/apps/221422881/settings
    #       https://www.linkedin.com/developers/apps/221422881/products?refreshKey=1734980684455
    # verification url: https://www.linkedin.com/developers/apps/verification/3ac34414-09a4-433b-983a-0d529fa486f1
    # -------------------------------------------------------------------------
    SOCIAL_AUTH_LINKEDIN_OAUTH2_KEY: SecretStr = SecretStr(get_env("SOCIAL_AUTH_LINKEDIN_OAUTH2_KEY"))
    SOCIAL_AUTH_LINKEDIN_OAUTH2_SECRET: SecretStr = SecretStr(get_env("SOCIAL_AUTH_LINKEDIN_OAUTH2_SECRET"))

    SECRET_KEY: SecretStr = SecretStr(get_env("SECRET_KEY"))

    SMTP_SENDER = get_env("SMTP_SENDER", f"admin@{ROOT_DOMAIN}")
    SMTP_FROM_EMAIL = get_env("SMTP_FROM_EMAIL", f"no-reply@{ROOT_DOMAIN}")
    SMTP_HOST = get_env("SMTP_HOST", "email-smtp.us-east-2.amazonaws.com")
    SMTP_PORT = int(get_env("SMTP_PORT", "587"))
    SMTP_USE_SSL = bool(get_env("SMTP_USE_SSL", False))
    SMTP_USE_TLS = bool(get_env("SMTP_USE_TLS", True))
    SMTP_PASSWORD: SecretStr = SecretStr(get_env("SMTP_PASSWORD"))
    SMTP_USERNAME: SecretStr = SecretStr(get_env("SMTP_USERNAME"))

    STRIPE_LIVE_SECRET_KEY: SecretStr = SecretStr(get_env("STRIPE_LIVE_SECRET_KEY"))
    STRIPE_TEST_SECRET_KEY: SecretStr = SecretStr(get_env("STRIPE_TEST_SECRET_KEY"))

    @classmethod
    def to_dict(cls):
        """Convert SettingsDefaults to dict"""
        return {
            key: value
            for key, value in SettingsDefaults.__dict__.items()
            if not key.startswith("__") and not callable(key) and key != "to_dict"
        }


class Services:
    """Services enabled for this solution. This is intended to be permanently read-only"""

    # enabled
    AWS_CLI = ("aws-cli", True)
    AWS_ROUTE53 = ("route53", True)
    AWS_S3 = ("s3", True)
    AWS_EC2 = ("ec2", True)
    AWS_IAM = ("iam", True)
    AWS_CLOUDWATCH = ("cloudwatch", True)
    AWS_SES = ("ses", True)
    AWS_RDS = ("rds", True)
    AWS_EKS = ("eks", True)

    # disabled
    AWS_LAMBDA = ("lambda", False)
    AWS_APIGATEWAY = ("apigateway", False)
    AWS_SNS = ("sns", False)
    AWS_SQS = ("sqs", False)
    AWS_REKOGNITION = ("rekognition", False)
    AWS_DYNAMODB = ("dynamodb", False)

    @classmethod
    def is_connected_to_aws(cls):
        return bool(boto3.Session().get_credentials())

    @classmethod
    def enabled(cls, service: Union[str, Tuple[str, bool]]) -> bool:
        """Is the service enabled?"""
        if not cls.is_connected_to_aws():
            return False
        if isinstance(service, tuple):
            service = service[0]
        return service in cls.enabled_services()

    @classmethod
    def raise_error_on_disabled(cls, service: Union[str, Tuple[str, bool]]) -> None:
        """Raise an error if the service is disabled"""
        if not cls.enabled(service):
            if SettingsDefaults.AWS_IS_CONFIGURED:
                raise SmarterConfigurationError(f"{service} is not enabled. See conf.Services")
            else:
                logger.warning("AWS is not configured. %s is not enabled.", service)

    @classmethod
    def to_dict(cls):
        """Convert Services to dict"""
        return {
            key: value
            for key, value in Services.__dict__.items()
            if not key.startswith("__")
            and not callable(key)
            and key not in ["enabled", "raise_error_on_disabled", "to_dict", "enabled_services"]
        }

    @classmethod
    def enabled_services(cls) -> List[str]:
        """Return a list of enabled services"""
        return [
            getattr(cls, key)[0]
            for key in dir(cls)
            if not key.startswith("__")
            and not callable(getattr(cls, key))
            and key not in ["enabled", "raise_error_on_disabled", "to_dict", "enabled_services"]
            and getattr(cls, key)[1] is True
        ]


AWS_REGIONS = ["us-east-1"]
if Services.enabled(Services.AWS_EC2):
    try:
        ec2 = boto3.Session(region_name=SettingsDefaults.AWS_REGION).client("ec2")
        regions = ec2.describe_regions()
        AWS_REGIONS = [region["RegionName"] for region in regions["Regions"]]
    except (ProfileNotFound, NoCredentialsError):
        logger.warning("could not initialize ec2 client")


def empty_str_to_bool_default(v: str, default: bool) -> bool:
    """Convert empty string to default boolean value"""
    if v in [None, ""]:
        return default
    return v.lower() in ["true", "1", "t", "y", "yes"]


def empty_str_to_int_default(v: str, default: int) -> int:
    """Convert empty string to default integer value"""
    if v in [None, ""]:
        return default
    try:
        return int(v)
    except ValueError:
        return default


# pylint: disable=too-many-instance-attributes,too-many-public-methods
class Settings(BaseSettings):
    """
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
    - Sensitive values are stored as pydantic SecretStr types.
    - smarter_settings values are initialized according to the following prioritization sequence:
        1. constructor. This is discouraged. prefer to use .env file or environment variables.
        2. SettingsDefaults
        3. `.env` file
        4. environment variables. If present and not already consumed by SettingsDefaults, these are overridden by .env file values.
        5. default values defined in this class.
    - The dump property returns a dictionary of all configuration values.
    - smarter_settings values should be accessed via the smarter_settings singleton instance when possible.
    """

    # pylint: disable=too-few-public-methods
    class Config:
        """Pydantic configuration"""

        frozen = True

    _dump: dict

    # pylint: disable=too-many-branches,too-many-statements
    def __init__(self, **data: Any):  # noqa: C901
        super().__init__(**data)

        logger.setLevel(SettingsDefaults.LOG_LEVEL)

        # pylint: disable=logging-fstring-interpolation
        logger.debug("Settings initialized")

    shared_resource_identifier: str = Field(
        SettingsDefaults.SHARED_RESOURCE_IDENTIFIER,
        description="Smarter 1-word identifier to be used when naming any shared resource.",
        examples=["smarter", "mycompany", "myproject"],
    )
    """
    A single, lowercase word used as a unique identifier for all shared resources across the Smarter platform.

    This value is used as a prefix or namespace when naming resources that are shared between services, environments, or deployments—such as S3 buckets, Kubernetes namespaces, or other cloud resources. It ensures that resource names are consistent, easily identifiable, and do not conflict with those from other projects or organizations.

    **Typical usage:**
        - As a prefix for cloud resource names (e.g., ``smarter-platform-alpha``)
        - To distinguish resources in multi-tenant or multi-environment deployments
        - For automated naming conventions in infrastructure-as-code and deployment scripts

    **Examples:**
        - ``smarter``
        - ``mycompany``
        - ``myproject``

    :type: str
    :default: Value from ``SettingsDefaults.SHARED_RESOURCE_IDENTIFIER``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    debug_mode: bool = Field(
        SettingsDefaults.DEBUG_MODE,
        description="True if debug mode is enabled. This enables verbose logging and other debug features.",
    )
    """
    True if debug mode is enabled. This enables verbose logging and other debug features.

    When debug mode is enabled, the platform will log additional information useful for
    troubleshooting and development. This may include detailed error messages, stack traces, and
    other diagnostic data that can help identify issues during development or testing.

    :type: bool
    :default: Value from ``SettingsDefaults.DEBUG_MODE``
    :raises SmarterConfigurationError: If the value is not a boolean.
    """
    default_missing_value: str = Field(
        DEFAULT_MISSING_VALUE,
        description="Default missing value placeholder string. Used for consistency across settings.",
        examples=["SET-ME-PLEASE"],
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
        SettingsDefaults.DEVELOPER_MODE,
        description="True if developer mode is enabled. Used as a means to configure a production Docker container to run locally for student use.",
    )
    """
    True if developer mode is enabled. Used as a means to configure a production Docker container to run locally for student use.
    When developer mode is enabled, certain restrictions or configurations that are typical
    of a production environment may be relaxed or altered to facilitate local development
    and testing. This allows developers to work with a production-like setup without the
    constraints that would normally apply in a live environment.

    :type: bool
    :default: Value from ``SettingsDefaults.DEVELOPER_MODE``
    :raises SmarterConfigurationError: If the value is not a boolean.
    """
    django_default_file_storage: str = Field(
        SettingsDefaults.DJANGO_DEFAULT_FILE_STORAGE,
        description="The default Django file storage backend.",
        examples=["storages.backends.s3boto3.S3Boto3Storage", "django.core.files.storage.FileSystemStorage"],
    )
    """
    The default Django file storage backend.
    This setting determines where Django will store uploaded files by default.
    It can be configured to use different storage backends, such as Amazon S3 or the local file system,
    depending on the needs of the application and its deployment environment.

    :type: str
    :default: Value from ``SettingsDefaults.DJANGO_DEFAULT_FILE_STORAGE``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    log_level: int = Field(
        SettingsDefaults.LOG_LEVEL,
        description="The logging level for the platform based on Python logging levels: logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL",
        examples=[logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL],
    )
    dump_defaults: bool = Field(
        SettingsDefaults.DUMP_DEFAULTS, description="True if default values should be dumped for debugging purposes."
    )
    """
    True if default values should be dumped for debugging purposes.
    When enabled, the platform will log or output the default configuration values
    used during initialization. This can help developers and administrators
    understand the effective configuration of the system, especially when
    troubleshooting issues related to settings.

    :type: bool
    :default: Value from ``SettingsDefaults.DUMP_DEFAULTS``
    :raises SmarterConfigurationError: If the value is not a boolean.
    """
    aws_profile: Optional[str] = Field(
        SettingsDefaults.AWS_PROFILE,
        description="The AWS profile to use for authentication. If present, this will take precedence over AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY.",
        examples=["default", "smarter-profile"],
    )
    """
    The AWS profile to use for authentication. If present, this will take precedence over AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY.
    This setting specifies which AWS credentials profile to use when connecting to AWS services.
    Profiles are defined in the AWS credentials file (typically located at ~/.aws/credentials)
    and allow for managing multiple sets of credentials for different environments or accounts.

    :type: Optional[str]
    :default: Value from ``SettingsDefaults.AWS_PROFILE``
    :raises SmarterConfigurationError: If the value is not a string.
    """
    aws_access_key_id: SecretStr = Field(
        SettingsDefaults.AWS_ACCESS_KEY_ID,
        description="The AWS access key ID for authentication. Used if AWS_PROFILE is not set. Masked by pydantic SecretStr.",
        examples=["^AKIA[0-9A-Z]{16}$"],
    )
    """
    The AWS access key ID for authentication. Used if AWS_PROFILE is not set. Masked by pydantic SecretStr.
    This setting provides the access key ID used to authenticate with AWS services.
    It is used in conjunction with the AWS secret access key to sign requests to AWS APIs.

    :type: SecretStr
    :default: Value from ``SettingsDefaults.AWS_ACCESS_KEY_ID``
    :raises SmarterConfigurationError: If the value is not a valid AWS access key ID
    """
    aws_secret_access_key: SecretStr = Field(
        SettingsDefaults.AWS_SECRET_ACCESS_KEY,
        description="The AWS secret access key for authentication. Used if AWS_PROFILE is not set. Masked by pydantic SecretStr.",
        examples=["^[0-9a-zA-Z/+]{40}$"],
    )
    """
    The AWS secret access key for authentication. Used if AWS_PROFILE is not set. Masked by pydantic SecretStr.
    This setting provides the secret access key used to authenticate with AWS services.
    It is used in conjunction with the AWS access key ID to sign requests to AWS APIs.

    :type: SecretStr
    :default: Value from ``SettingsDefaults.AWS_SECRET_ACCESS_KEY``
    :raises SmarterConfigurationError: If the value is not a valid AWS secret access key
    """
    aws_regions: List[str] = Field(
        AWS_REGIONS,
        description="A list of AWS regions considered valid for this platform.",
        examples=["us-east-1", "us-west-2", "eu-west-1"],
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
    aws_region: str = Field(
        SettingsDefaults.AWS_REGION,
        description="The single AWS region in which all AWS service clients will operate.",
        examples=["us-east-1", "us-west-2", "eu-west-1"],
    )
    """
    The single AWS region in which all AWS service clients will operate.
    This setting specifies the default AWS region for the platform.
    All AWS service clients will be configured to use this region unless
    overridden on a per-client basis.

    :type: str
    :default: Value from ``SettingsDefaults.AWS_REGION``
    :raises SmarterConfigurationError: If the value is not a valid AWS region name.
    """
    aws_is_configured: bool = Field(
        SettingsDefaults.AWS_IS_CONFIGURED,
        description="True if AWS is configured. This is determined by the presence of either AWS_PROFILE or both AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY.",
    )
    """
    True if AWS is configured. This is determined by the presence of either AWS_PROFILE or both AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY.
    This setting indicates whether the platform has sufficient AWS credentials
    configured to connect to AWS services. If AWS is not configured, attempts
    to use AWS services will fail.

    :type: bool
    :default: Value from ``SettingsDefaults.AWS_IS_CONFIGURED``
    :raises SmarterConfigurationError: If the value is not a boolean.
    """

    aws_eks_cluster_name: str = Field(
        SettingsDefaults.AWS_EKS_CLUSTER_NAME,
        description="The name of the AWS EKS cluster used for hosting applications.",
        examples=["apps-hosting-service"],
    )
    """
    The name of the AWS EKS cluster used for hosting applications.
    This setting specifies the Amazon EKS cluster that the platform will use
    for deploying and managing containerized applications. The cluster name
    should correspond to an existing EKS cluster in the configured AWS account.

    :type: str
    :default: Value from ``SettingsDefaults.AWS_EKS_CLUSTER_NAME``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    aws_db_instance_identifier: str = Field(
        SettingsDefaults.AWS_RDS_DB_INSTANCE_IDENTIFIER,
        description="The RDS database instance identifier used for the platform's primary database.",
        examples=["apps-hosting-service"],
    )
    """
    The RDS database instance identifier used for the platform's primary database.
    This setting specifies the Amazon RDS database instance that the platform
    will connect to for data storage and retrieval. The instance identifier should
    correspond to an existing RDS instance in the configured AWS account.

    :type: str
    :default: Value from ``SettingsDefaults.AWS_RDS_DB_INSTANCE_IDENTIFIER``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    anthropic_api_key: SecretStr = Field(
        SettingsDefaults.ANTHROPIC_API_KEY,
        description="The API key for Anthropic services. Masked by pydantic SecretStr.",
        examples=["sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"],
    )
    """
    The API key for Anthropic services. Masked by pydantic SecretStr.
    This setting provides the API key used to authenticate with Anthropic services.
    It is required for accessing Anthropic's APIs and services.

    :type: SecretStr
    :default: Value from ``SettingsDefaults.ANTHROPIC_API_KEY``
    :raises SmarterConfigurationError: If the value is not a valid API key.
    """

    environment: str = Field(
        SettingsDefaults.ENVIRONMENT,
        description="The deployment environment for the platform.",
        examples=SmarterEnvironments.all,
    )
    """
    The deployment environment for the platform.
    This setting indicates the environment in which the platform is running,
    such as development, staging, or production. It can be used to adjust
    behavior and configurations based on the environment.

    :type: str
    :default: Value from ``SettingsDefaults.ENVIRONMENT``
    :raises SmarterConfigurationError: If the value is not a valid environment name from SmarterEnvironments.all
    """

    fernet_encryption_key: SecretStr = Field(
        SettingsDefaults.FERNET_ENCRYPTION_KEY,
        description="The Fernet encryption key used for encrypting Smarter Secrets data.",
        examples=["gAAAAABh..."],
    )
    """
    The Fernet encryption key used for encrypting Smarter Secrets data.
    This setting provides the key used for symmetric encryption and decryption
    of sensitive data within the platform. The key should be a URL-safe base64-encoded
    32-byte key.

    :type: str
    :default: Value from ``SettingsDefaults.FERNET_ENCRYPTION_KEY``
    :raises SmarterConfigurationError: If the value is not a valid Fernet key.
    """

    local_hosts: List[str] = Field(
        SettingsDefaults.LOCAL_HOSTS,
        description="A list of hostnames considered local for development and testing purposes.",
        examples=SettingsDefaults.LOCAL_HOSTS,
    )
    """
    A list of hostnames considered local for development and testing purposes.
    This setting defines hostnames that are treated as local addresses by the platform.
    It is useful for distinguishing between local and remote requests, especially
    during development and testing.

    :type: List[str]
    :default: Value from ``SettingsDefaults.LOCAL_HOSTS``
    :raises SmarterConfigurationError: If the value is not a list of strings matching SettingsDefaults.LOCAL_HOSTS
    """

    root_domain: str = Field(
        SettingsDefaults.ROOT_DOMAIN,
        description="The root domain for the platform.",
        examples=["example.com"],
    )
    """
    The root domain for the platform.
    This setting specifies the primary domain name used by the platform.
    It is used for constructing URLs, email addresses, and other domain-related
    configurations.

    :type: str
    :default: Value from ``SettingsDefaults.ROOT_DOMAIN``
    :raises SmarterConfigurationError: If the value is not a valid domain name.
    """

    init_info: Optional[str] = Field(
        None,
    )

    google_maps_api_key: SecretStr = Field(
        SettingsDefaults.GOOGLE_MAPS_API_KEY,
        description="The API key for Google Maps services. Masked by pydantic SecretStr. Used for geocoding, maps, and places APIs, for the OpenAI get_weather() example function.",
        examples=["AIzaSy..."],
    )
    """
    The API key for Google Maps services. Masked by pydantic SecretStr. Used for geocoding, maps, and places APIs, for the OpenAI get_weather() example function.
    This setting provides the API key used to authenticate with Google Maps services.
    It is required for accessing Google Maps APIs such as geocoding, maps rendering,
    and places information.

    :type: SecretStr
    :default: Value from ``SettingsDefaults.GOOGLE_MAPS_API_KEY``
    :raises SmarterConfigurationError: If the value is not a valid API key.
    """

    google_service_account: SecretStr = Field(
        SettingsDefaults.GOOGLE_SERVICE_ACCOUNT,
        description="The Google service account credentials as a dictionary. Used for Google Cloud services integration.",
        examples=[{"type": "service_account", "project_id": "my-project", "...": "..."}],
    )
    """
    The Google service account credentials as a dictionary. Used for Google Cloud services integration.
    This setting contains the credentials for a Google service account in JSON format.
    It is used to authenticate and authorize access to Google Cloud services on behalf
    of the platform.

    :type: dict
    :default: Value from ``SettingsDefaults.GOOGLE_SERVICE_ACCOUNT``
    :raises SmarterConfigurationError: If the value is not a valid service account JSON.
    """

    gemini_api_key: SecretStr = Field(
        SettingsDefaults.GEMINI_API_KEY,
        description="The API key for Google Gemini services. Masked by pydantic SecretStr.",
        examples=["sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"],
    )
    """
    The API key for Google Gemini services. Masked by pydantic SecretStr.
    This setting provides the API key used to authenticate with Google Gemini services.
    It is required for accessing Gemini's APIs and services.

    :type: SecretStr
    :default: Value from ``SettingsDefaults.GEMINI_API_KEY``
    :raises SmarterConfigurationError: If the value is not a valid API key.
    """
    llama_api_key: SecretStr = Field(
        SettingsDefaults.LLAMA_API_KEY,
        description="The API key for LLaMA services. Masked by pydantic SecretStr.",
        examples=["sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"],
    )
    """
    The API key for LLaMA services. Masked by pydantic SecretStr.
    This setting provides the API key used to authenticate with LLaMA services.
    It is required for accessing LLaMA's APIs and services.

    :type: SecretStr
    :default: Value from ``SettingsDefaults.LLAMA_API_KEY``
    :raises SmarterConfigurationError: If the value is not a valid API key.
    """

    smarter_mysql_test_database_secret_name: Optional[str] = Field(
        SettingsDefaults.SMARTER_MYSQL_TEST_DATABASE_SECRET_NAME,
        description="The secret name for the Smarter MySQL test database. Used for example Smarter Plugins that are pre-installed on new installations.",
        examples=["smarter-mysql-test-db-secret"],
    )
    """
    The secret name for the Smarter MySQL test database. Used for example Smarter Plugins that are pre-installed on new installations.
    This setting specifies the name of the secret in AWS Secrets Manager
    that contains the credentials for the Smarter MySQL test database.
    It is used by example Smarter Plugins that require access to a test database.

    :type: Optional[str]
    :default: Value from ``SettingsDefaults.SMARTER_MYSQL_TEST_DATABASE_SECRET_NAME`
    :raises SmarterConfigurationError: If the value is not a string.
    """

    smarter_mysql_test_database_password: Optional[SecretStr] = Field(
        SettingsDefaults.SMARTER_MYSQL_TEST_DATABASE_PASSWORD,
        description="The password for the Smarter MySQL test database. Used for example Smarter Plugins that are pre-installed on new installations.",
        examples=["your_password_here"],
    )
    """
    The password for the Smarter MySQL test database. Used for example Smarter Plugins that are pre-installed on new installations.
    This setting provides the password used to connect to the Smarter MySQL test database.
    It is used by example Smarter Plugins that require access to a test database.

    :type: Optional[str]
    :default: Value from ``SettingsDefaults.SMARTER_MYSQL_TEST_DATABASE_PASSWORD``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    smarter_reactjs_app_loader_path: str = Field(
        SettingsDefaults.SMARTER_REACTJS_APP_LOADER_PATH,
        description="The path to the ReactJS app loader script.",
        examples=["/ui-chat/app-loader.js"],
    )
    """
    The path to the ReactJS app loader script.
    This setting specifies the URL path where the ReactJS application loader script is located.
    It is used to load the ReactJS frontend for the platform.

    :type: str
    :default: Value from ``SettingsDefaults.SMARTER_REACTJS_APP_LOADER_PATH``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    social_auth_google_oauth2_key: SecretStr = Field(
        SettingsDefaults.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY,
        description="The OAuth2 key for Google social authentication. Masked by pydantic SecretStr.",
        examples=["your-google-oauth2-key"],
    )
    """
    The OAuth2 key for Google social authentication. Masked by pydantic SecretStr.
    This setting provides the OAuth2 client ID used for Google social authentication.
    It is required for enabling users to log in using their Google accounts.

    :type: SecretStr
    :default: Value from ``SettingsDefaults.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY
    :raises SmarterConfigurationError: If the value is not a valid OAuth2 client ID.
    """
    social_auth_google_oauth2_secret: SecretStr = Field(
        SettingsDefaults.SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET,
        description="The OAuth2 secret for Google social authentication. Masked by pydantic SecretStr.",
        examples=["your-google-oauth2-secret"],
    )
    """
    The OAuth2 secret for Google social authentication. Masked by pydantic SecretStr.
    This setting provides the OAuth2 client secret used for Google social authentication.
    It is required for enabling users to log in using their Google accounts.

    :type: SecretStr
    :default: Value from ``SettingsDefaults.SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET
    :raises SmarterConfigurationError: If the value is not a valid OAuth2 client secret
    """

    social_auth_github_key: SecretStr = Field(
        SettingsDefaults.SOCIAL_AUTH_GITHUB_KEY,
        description="The OAuth2 key for GitHub social authentication. Masked by pydantic SecretStr.",
        examples=["your-github-oauth2-key"],
    )
    """
    The OAuth2 key for GitHub social authentication. Masked by pydantic SecretStr.
    This setting provides the OAuth2 client ID used for GitHub social authentication.
    It is required for enabling users to log in using their GitHub accounts.

    :type: SecretStr
    :default: Value from ``SettingsDefaults.SOCIAL_AUTH_GITHUB_KEY
    :raises SmarterConfigurationError: If the value is not a valid OAuth2 client ID
    """
    social_auth_github_secret: SecretStr = Field(
        SettingsDefaults.SOCIAL_AUTH_GITHUB_SECRET,
        description="The OAuth2 secret for GitHub social authentication. Masked by pydantic SecretStr.",
        examples=["your-github-oauth2-secret"],
    )
    """
    The OAuth2 secret for GitHub social authentication. Masked by pydantic SecretStr.
    This setting provides the OAuth2 client secret used for GitHub social authentication.
    It is required for enabling users to log in using their GitHub accounts.

    :type: SecretStr
    :default: Value from ``SettingsDefaults.SOCIAL_AUTH_GITHUB_SECRET
    :raises SmarterConfigurationError: If the value is not a valid OAuth2 client secret
    """

    social_auth_linkedin_oauth2_key: SecretStr = Field(
        SettingsDefaults.SOCIAL_AUTH_LINKEDIN_OAUTH2_KEY,
        description="The OAuth2 key for LinkedIn social authentication. Masked by pydantic SecretStr.",
        examples=["your-linkedin-oauth2-key"],
    )
    """
    .. deprecated:: 0.13.35
        This setting is deprecated and will be removed in a future release. LinkedIn social authentication is no longer supported or recommended for new deployments.

    The OAuth2 key for LinkedIn social authentication. Masked by pydantic SecretStr.
    This setting provides the OAuth2 client ID used for LinkedIn social authentication.
    It was required for enabling users to log in using their LinkedIn accounts.

    :type: SecretStr
    :default: Value from ``SettingsDefaults.SOCIAL_AUTH_LINKEDIN_OAUTH2``
    :raises SmarterConfigurationError: If the value is not a valid OAuth2 client ID
    """

    social_auth_linkedin_oauth2_secret: SecretStr = Field(
        SettingsDefaults.SOCIAL_AUTH_LINKEDIN_OAUTH2_SECRET,
        description="The OAuth2 secret for LinkedIn social authentication. Masked by pydantic SecretStr.",
        examples=["your-linkedin-oauth2-secret"],
    )
    """
    .. deprecated:: 0.13.35
        This setting is deprecated and will be removed in a future release. LinkedIn social authentication is no longer supported or recommended for new deployments.

    The OAuth2 secret for LinkedIn social authentication. Masked by pydantic SecretStr.
    This setting provides the OAuth2 client secret used for LinkedIn social authentication.
    It was required for enabling users to log in using their LinkedIn accounts.

    :type: SecretStr
    :default: Value from ``SettingsDefaults.SOCIAL_AUTH_LINKEDIN_OAUTH2
    :raises SmarterConfigurationError: If the value is not a valid OAuth2 client secret
    """

    langchain_memory_key: Optional[str] = Field(SettingsDefaults.LANGCHAIN_MEMORY_KEY)
    """
    The key used for LangChain memory storage.
    This setting specifies the key under which LangChain memory data is stored.
    It is used to manage and retrieve memory data within LangChain applications.

    :type: Optional[str]
    :default: Value from ``SettingsDefaults.LANGCHAIN_MEMORY_KEY``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    logo: Optional[HttpUrl] = Field(SettingsDefaults.LOGO)
    """
    The URL to the platform's logo image.
    This setting specifies the web address of the logo image used in the platform's user interface.
    It should be a valid URL pointing to an external image resource accessible by the frontend.

    :type: Optional[str]
    :default: Value from ``SettingsDefaults.LOGO``
    :raises SmarterConfigurationError: If the value is not a valid URL string.
    """

    mailchimp_api_key: Optional[SecretStr] = Field(SettingsDefaults.MAILCHIMP_API_KEY)
    """
    The API key for Mailchimp services. Masked by pydantic SecretStr.
    This setting provides the API key used to authenticate with Mailchimp services.
    It is required for accessing Mailchimp's APIs and services.

    :type: Optional[SecretStr]
    :default: Value from ``SettingsDefaults.MAILCHIMP_API_KEY``
    :raises SmarterConfigurationError: If the value is not a valid API key.
    """

    mailchimp_list_id: Optional[str] = Field(SettingsDefaults.MAILCHIMP_LIST_ID)
    """
    The Mailchimp list ID for managing email subscribers.
    This setting specifies the unique identifier of the Mailchimp list
    used for managing email subscribers. It is required for adding, removing,
    and managing subscribers within Mailchimp.

    :type: Optional[str]
    :default: Value from ``SettingsDefaults.MAILCHIMP_LIST_ID``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    marketing_site_url: Optional[HttpUrl] = Field(SettingsDefaults.MARKETING_SITE_URL)
    """
    The URL to the platform's marketing site.
    This setting specifies the web address of the marketing site associated
    with the platform. It should be a valid URL pointing to an external website.

    :type: Optional[httpHttpUrl]
    :default: Value from ``SettingsDefaults.MARKETING_SITE_URL``
    :raises SmarterConfigurationError: If the value is not a valid URL string.
    """

    openai_api_organization: Optional[str] = Field(
        SettingsDefaults.OPENAI_API_ORGANIZATION,
        description="The OpenAI API organization ID.",
        examples=["org-xxxxxxxxxxxxxxxx"],
    )
    """
    The OpenAI API organization ID.
    This setting specifies the organization ID used when making requests to the OpenAI API.
    It is used to associate API requests with a specific organization account.

    :type: Optional[str]
    :default: Value from ``SettingsDefaults.OPENAI_API_ORGANIZATION``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    openai_api_key: SecretStr = Field(
        SettingsDefaults.OPENAI_API_KEY,
        description="The API key for OpenAI services. Masked by pydantic SecretStr.",
        examples=["sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"],
    )
    """
    The API key for OpenAI services. Masked by pydantic SecretStr.
    This setting provides the API key used to authenticate with OpenAI services.
    It is required for accessing OpenAI's APIs and services.

    :type: SecretStr
    :default: Value from ``SettingsDefaults.OPENAI_API_KEY``
    :raises SmarterConfigurationError: If the value is not a valid API key.
    """

    openai_endpoint_image_n: Optional[int] = Field(
        SettingsDefaults.OPENAI_ENDPOINT_IMAGE_N,
        description="The number of images to generate per request to the OpenAI image endpoint.",
        examples=[1, 2, 4],
    )
    """
    The number of images to generate per request to the OpenAI image endpoint.
    This setting specifies how many images should be generated in response to
    a single request to the OpenAI image generation API.

    :type: Optional[int]
    :default: Value from ``SettingsDefaults.OPENAI_ENDPOINT_IMAGE_N``
    :raises SmarterConfigurationError: If the value is not a positive integer.
    """

    openai_endpoint_image_size: Optional[str] = Field(
        SettingsDefaults.OPENAI_ENDPOINT_IMAGE_SIZE,
        description="The size of images to generate from the OpenAI image endpoint.",
        examples=["256x256", "512x512", "1024x768"],
    )
    """
    The size of images to generate from the OpenAI image endpoint.
    This setting specifies the dimensions of the images to be generated
    by the OpenAI image generation API.

    :type: Optional[str]
    :default: Value from ``SettingsDefaults.OPENAI_ENDPOINT_IMAGE_SIZE``
    :raises SmarterConfigurationError: If the value is not a valid image size string.
    """

    llm_default_provider: str = Field(
        SettingsDefaults.LLM_DEFAULT_PROVIDER,
        description="The default LLM provider to use for language model interactions.",
        examples=["openai", "anthropic", "gemini", "llama"],
    )
    """
    The default LLM provider to use for language model interactions.
    This setting specifies which language model provider should be used by default
    for processing natural language tasks. It determines the backend service that
    will handle requests for language generation, understanding, and other related functions.

    :type: str
    :default: Value from ``SettingsDefaults.LLM_DEFAULT_PROVIDER``
    :raises SmarterConfigurationError: If the value is not a valid LLM provider name
    """

    llm_default_model: str = Field(
        SettingsDefaults.LLM_DEFAULT_MODEL,
        description="The default LLM model to use for language model interactions.",
        examples=["gpt-4o-mini", "claude-2", "gemini"],
    )
    """
    The default LLM model to use for language model interactions.
    This setting specifies which specific language model should be used by default
    for processing natural language tasks. It determines the model variant that
    will handle requests for language generation, understanding, and other related functions.

    :type: str
    :default: Value from ``SettingsDefaults.LLM_DEFAULT_MODEL``
    :raises SmarterConfigurationError: If the value is not a valid LLM model name
    """

    llm_default_system_role: str = Field(
        SettingsDefaults.LLM_DEFAULT_SYSTEM_ROLE,
        description="The default system role prompt to use for language model interactions.",
        examples=["You are a helpful chatbot..."],
    )
    """
    The default system role prompt to use for language model interactions.
    This setting provides the default system role prompt that guides the behavior
    of the language model during interactions. It helps define the context and
    tone of the responses generated by the model.

    :type: str
    :default: Value from ``SettingsDefaults.LLM_DEFAULT_SYSTEM_ROLE``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    llm_default_temperature: float = Field(
        SettingsDefaults.LLM_DEFAULT_TEMPERATURE,
        description="The default temperature to use for language model interactions.",
        examples=[0.0, 0.5, 1.0],
    )
    """
    The default temperature to use for language model interactions.
    This setting controls the randomness of the language model's output.
    A lower temperature (e.g., 0.0) results in more deterministic and focused
    responses, while a higher temperature (e.g., 1.0) produces more diverse
    and creative outputs.

    :type: float
    :default: Value from ``SettingsDefaults.LLM_DEFAULT_TEMPERATURE``
    :raises SmarterConfigurationError: If the value is not a float between 0.
    """

    llm_default_max_tokens: int = Field(
        SettingsDefaults.LLM_DEFAULT_MAX_TOKENS,
        description="The default maximum number of tokens to generate for language model interactions.",
        examples=[256, 512, 1024, 2048],
    )
    """
    The default maximum number of tokens to generate for language model interactions.
    This setting specifies the upper limit on the number of tokens that the language
    model can generate in response to a single request. It helps control the length
    of the output and manage resource usage.

    :type: int
    :default: Value from ``SettingsDefaults.LLM_DEFAULT_MAX_TOKENS``
    :raises SmarterConfigurationError: If the value is not a positive integer.
    """

    pinecone_api_key: SecretStr = Field(
        SettingsDefaults.PINECONE_API_KEY,
        description="The API key for Pinecone services. Masked by pydantic SecretStr.",
        examples=["xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"],
    )
    """
    The API key for Pinecone services. Masked by pydantic SecretStr.
    This setting provides the API key used to authenticate with Pinecone services.
    It is required for accessing Pinecone's APIs and services.

    :type: SecretStr
    :default: Value from ``SettingsDefaults.PINECONE_API_KEY``
    :raises SmarterConfigurationError: If the value is not a valid API key.
    """

    stripe_live_secret_key: Optional[SecretStr] = Field(
        SettingsDefaults.STRIPE_LIVE_SECRET_KEY,
        description="DEPRECATED: The secret key for Stripe live environment.",
        examples=["sk_live_xxxxxxxxxxxxxxxxxxxxxxxx"],
    )
    """
    .. deprecated:: 0.13.0
        This setting is deprecated and will be removed in a future release. Please use the new payment processing configuration settings.

    The secret key for Stripe live environment.
    This setting provides the secret key used to authenticate with Stripe's live environment.
    It is used for processing real transactions and payments.

    :type: Optional[str]
    :default: Value from ``SettingsDefaults.STRIPE_LIVE_SECRET_KEY``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    stripe_test_secret_key: Optional[SecretStr] = Field(
        SettingsDefaults.STRIPE_TEST_SECRET_KEY,
        description="DEPRECATED: The secret key for Stripe test environment.",
        examples=["sk_test_xxxxxxxxxxxxxxxxxxxxxxxx"],
    )
    """
    .. deprecated:: 0.13.0
        This setting is deprecated and will be removed in a future release. Please use the new payment processing configuration settings.

    The secret key for Stripe test environment.
    This setting provides the secret key used to authenticate with Stripe's test environment.
    It is used for processing test transactions and payments.

    :type: Optional[str]
    :default: Value from ``SettingsDefaults.STRIPE_TEST_SECRET_KEY``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    secret_key: Optional[SecretStr] = Field(
        SettingsDefaults.SECRET_KEY,
        description="The Django secret key for cryptographic signing.",
        examples=["your-django-secret-key"],
    )
    """
    The Django secret key for cryptographic signing.
    This setting provides the secret key used by Django for cryptographic signing.
    It is essential for maintaining the security of sessions, cookies, and other
    cryptographic operations within the Django framework.

    :type: Optional[str]
    :default: Value from ``SettingsDefaults.SECRET_KEY``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    smtp_sender: Optional[EmailStr] = Field(
        SettingsDefaults.SMTP_SENDER,
        description="The sender email address for SMTP emails.",
        examples=["sender@example.com"],
    )
    """
    The sender email address for SMTP emails.
    This setting specifies the email address that will appear as the sender
    in outgoing SMTP emails sent by the platform.

    :type: Optional[EmailStr]
    :default: Value from ``SettingsDefaults.SMTP_SENDER``
    :raises SmarterConfigurationError: If the value is not a valid email address.
    """

    smtp_from_email: Optional[EmailStr] = Field(
        SettingsDefaults.SMTP_FROM_EMAIL,
        description="The from email address for SMTP emails.",
        examples=["from@example.com"],
    )
    """
    The from email address for SMTP emails.
    This setting specifies the email address that will appear in the "From"
    field of outgoing SMTP emails sent by the platform.

    :type: Optional[EmailStr]
    :default: Value from ``SettingsDefaults.SMTP_FROM_EMAIL``
    :raises SmarterConfigurationError: If the value is not a valid email address.
    """

    smtp_host: Optional[str] = Field(
        SettingsDefaults.SMTP_HOST,
        description="The SMTP host address for sending emails.",
        examples=["smtp.example.com"],
    )
    """
    The SMTP host address for sending emails.
    This setting specifies the hostname or IP address of the SMTP server
    used for sending outgoing emails from the platform.

    :type: Optional[str]
    :default: Value from ``SettingsDefaults.SMTP_HOST``
    :raises SmarterConfigurationError: If the value is not a valid hostname or IP address
    """

    smtp_password: Optional[SecretStr] = Field(
        SettingsDefaults.SMTP_PASSWORD,
        description="The SMTP password for authentication.",
        examples=["your-smtp-password"],
    )
    """
    The SMTP password for authentication.
    This setting provides the password used to authenticate with the SMTP server.
    It is required for sending emails through the SMTP server.

    :type: Optional[SecretStr]
    :default: Value from ``SettingsDefaults.SMTP_PASSWORD``
    :raises SmarterConfigurationError: If the value is not a valid password.
    """

    smtp_port: Optional[int] = Field(
        SettingsDefaults.SMTP_PORT,
        description="The SMTP port for sending emails.",
        examples=[25, 465, 587],
    )
    """
    The SMTP port for sending emails.
    This setting specifies the port number used to connect to the SMTP server
    for sending outgoing emails.

    :type: Optional[int]
    :default: Value from ``SettingsDefaults.SMTP_PORT``
    :raises SmarterConfigurationError: If the value is not a valid port number.
    """

    smtp_use_ssl: Optional[bool] = Field(
        SettingsDefaults.SMTP_USE_SSL,
        description="Whether to use SSL for SMTP connections.",
        examples=[True, False],
    )
    """
    Whether to use SSL for SMTP connections.
    This setting indicates whether SSL (Secure Sockets Layer) should be used
    when connecting to the SMTP server for sending emails.

    :type: Optional[bool]
    :default: Value from ``SettingsDefaults.SMTP_USE_SSL``
    :raises SmarterConfigurationError: If the value is not a boolean.
    """

    smtp_use_tls: Optional[bool] = Field(
        SettingsDefaults.SMTP_USE_TLS,
        description="Whether to use TLS for SMTP connections.",
        examples=[True, False],
    )
    """
    Whether to use TLS for SMTP connections.
    This setting indicates whether TLS (Transport Layer Security) should be used
    when connecting to the SMTP server for sending emails.

    :type: Optional[bool]
    :default: Value from ``SettingsDefaults.SMTP_USE_TLS``
    :raises SmarterConfigurationError: If the value is not a boolean.
    """

    smtp_username: Optional[SecretStr] = Field(
        SettingsDefaults.SMTP_USERNAME,
        description="The SMTP username for authentication.",
        examples=["your-smtp-username"],
    )
    """
    The SMTP username for authentication.
    This setting provides the username used to authenticate with the SMTP server.
    It is required for sending emails through the SMTP server.

    :type: Optional[str]
    :default: Value from ``SettingsDefaults.SMTP_USERNAME``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @property
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

    @property
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

    @property
    def environment_cdn_domain(self) -> str:
        """
        Return the CDN domain based on the environment domain.

        Examples:
            >>> print(smarter_settings.environment_cdn_domain)
            'cdn.alpha.platform.example.com'
            >>> print(smarter_settings.environment_cdn_domain)
            'cdn.localhost:8000'

        See Also:
            - smarter_settings.platform_subdomain
            - smarter_settings.environment_platform_domain
            - smarter_settings.environment
            - SmarterEnvironments()
        """
        if self.environment == SmarterEnvironments.LOCAL:
            return f"cdn.{SmarterEnvironments.ALPHA}.{self.platform_subdomain}.{self.root_domain}"
        return f"cdn.{self.environment_platform_domain}"

    @property
    def environment_cdn_url(self) -> str:
        """
        Return the CDN URL for the environment.

        Example:
            >>> print(smarter_settings.environment_cdn_url)
            https://cdn.alpha.platform.example.com
            >>> print(smarter_settings.environment_cdn_url)
            https://cdn.localhost:8000

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
        if self.environment == SmarterEnvironments.LOCAL:
            retval = SmarterValidator.urlify(self.environment_cdn_domain, environment=SmarterEnvironments.ALPHA)
        else:
            retval = SmarterValidator.urlify(self.environment_cdn_domain, environment=self.environment)
        if retval is None:
            raise SmarterConfigurationError(
                f"Invalid environment_cdn_domain: {self.environment_cdn_domain}. "
                "Please check your environment settings."
            )
        return retval

    @property
    def platform_subdomain(self) -> str:
        """
        Return the platform subdomain.

        Example:
            >>> print(smarter_settings.platform_subdomain)
            'platform'

        See Also:
            - SMARTER_PLATFORM_SUBDOMAIN
        """
        return SMARTER_PLATFORM_SUBDOMAIN

    @property
    def root_platform_domain(self) -> str:
        """
        Return the platform domain name for the root domain.

        Example:
            >>> print(smarter_settings.root_platform_domain)
            'platform.example.com'

        See Also:
            - smarter.settings.platform_subdomain
            - smarter_settings.root_domain
        """
        return f"{self.platform_subdomain}.{self.root_domain}"

    @property
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

    @property
    def environment_platform_domain(self) -> str:
        """
        Return the complete domain name, including environment prefix if applicable.

        Examples:
            >>> print(smarter_settings.environment_platform_domain)
            'alpha.platform.example.com'
            >>> print(smarter_settings.environment_platform_domain)
            'localhost:8000'

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
        if self.environment == SmarterEnvironments.LOCAL:
            return "localhost:8000"
        # default domain format
        return f"{self.environment}.{self.root_platform_domain}"

    @property
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
                'api.localhost:8000',
                'api.next.platform.example.com',
                'example.com',
                'platform.example.com',
                'alpha.platform.example.com',
                'beta.platform.example.com',
                'localhost:8000',
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

    @property
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

    @property
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

    @property
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

    @property
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
        return f"{self.platform_name}-{self.platform_subdomain}-{settings.environment}"

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

    @property
    def root_api_domain(self) -> str:
        """
        Return the root API domain name, generated
        from the system constant `SMARTER_API_SUBDOMAIN` and the root platform domain.

        Example:
            >>> print(smarter_settings.root_api_domain)
            'api.example.com'

        See Also:
            - SMARTER_API_SUBDOMAIN
            - smarter_settings.root_domain
            - smarter_settings.api_subdomain
        """
        return f"{self.api_subdomain}.{self.root_domain}"

    @property
    def environment_api_domain(self) -> str:
        """
        Return the API domain name for the current environment.

        Example:
            >>> print(smarter_settings.environment_api_domain)
            'alpha.api.platform.example.com'
            >>> print(smarter_settings.environment_api_domain)
            'api.localhost:8000'

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
        if self.environment == SmarterEnvironments.LOCAL:
            return f"{SMARTER_API_SUBDOMAIN}.localhost:8000"
        # default domain format
        return f"{self.environment}.{self.root_api_domain}"

    @property
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

    @property
    def aws_s3_bucket_name(self) -> str:
        """
        Returns the AWS S3 bucket name for the current environment.
        The bucket name is constructed from the Smarter shared resource identifier
        and the root platform domain.

        Example:
            >>> print(smarter_settings.aws_s3_bucket_name)
            'alpha.platform.smarter.sh'

        Note:
            In local environments, this returns 'alpha.platform.smarter.sh' as a proxy.

        See Also:
            - smarter_settings.shared_resource_identifier
            - smarter_settings.root_platform_domain
            - SmarterEnvironments()
            - smarter_settings.environment_platform_domain
        """
        if self.environment == SmarterEnvironments.LOCAL:
            return f"{SmarterEnvironments.ALPHA}.{self.root_platform_domain}"
        return self.environment_platform_domain

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

    @property
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
                'SMARTER_MYSQL_TEST_DATABASE_SECRET_NAME',
                'SMARTER_MYSQL_TEST_DATABASE_PASSWORD',
                'ENVIRONMENT',
                'PYTHONPATH',
                'NODE_MAJOR',
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
                'SMARTER_MYSQL_DATABASE',
                'SMARTER_MYSQL_PASSWORD',
                'SMARTER_MYSQL_USERNAME',
                'MYSQL_ROOT_USERNAME',
                'MYSQL_ROOT_PASSWORD',
                'SMARTER_LOGIN_URL',
                'SMARTER_ADMIN_PASSWORD',
                'SMARTER_ADMIN_USERNAME',
                'SMARTER_DOCKER_IMAGE'
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

    @property
    def smarter_reactjs_app_loader_url(self) -> str:
        """
        Return the full URL to the ReactJS app loader script.
        This is used for loading the ReactJS Chat
        frontend component into html web pages.

        Example:
            >>> print(smarter_settings.smarter_reactjs_app_loader_url)
            'https://alpha.platform.example.com/ui-chat/app-loader.js'

        See Also:
            - smarter_settings.environment_cdn_url
            - smarter_settings.smarter_reactjs_app_loader_path
        """
        return urljoin(self.environment_cdn_url, self.smarter_reactjs_app_loader_path)

    @property
    def smarter_reactjs_root_div_id(self) -> str:
        """
        Return the HTML div ID used as the root for the ReactJS Chat app.
        Start with a string like: "smarter.sh/v1/ui-chat/root", then
        convert it into an html safe id like: "smarter-sh-v1-ui-chat-root"

        Example:
            >>> print(smarter_settings.smarter_reactjs_root_div_id)
            'smarter-sh-v1-ui-chat-root'
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

    @property
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

    def dump(self) -> dict:
        """
        Dump all settings. Useful for debugging and logging.

        Returns:
            dict: A dictionary containing all settings and their values.

        Example:
            >>> import json
            >>> print(json.dumps(smarter_settings.dump(), indent=2))
            {
              "environment": {
                "is_using_dotenv_file": true,
                "os": "posix",
                ....
                },

        Note:
            Sensitive values are masked by Pydantic SecretStr and will not be displayed in full.
            The dump is cached after the first call for performance.
        """

        def get_installed_packages():
            return [(dist.metadata["Name"], dist.version) for dist in distributions()]

        if self._dump:
            return self._dump

        packages = get_installed_packages()
        packages_dict = [{"name": name, "version": version} for name, version in packages]

        self._dump = {
            "environment": {
                "is_using_dotenv_file": self.is_using_dotenv_file,
                "os": os.name,
                "system": platform.system(),
                "release": platform.release(),
                "shared_resource_identifier": self.shared_resource_identifier,
                "debug_mode": self.debug_mode,
                "dump_defaults": self.dump_defaults,
                "version": self.version,
                "python_version": platform.python_version(),
                "python_implementation": platform.python_implementation(),
                "python_compiler": platform.python_compiler(),
                "python_build": platform.python_build(),
                "python_installed_packages": packages_dict,
            },
            "anthropic": {
                "anthropic_api_key": self.anthropic_api_key,
            },
            "google": {
                "google_maps_api_key": self.google_maps_api_key,
                "gemini_api_key": self.gemini_api_key,
                "google_service_account": self.google_service_account,
            },
            "metaai": {
                "llama_api_key": self.llama_api_key,
            },
            "opeanai": {
                "openai_api_organization": self.openai_api_organization,
                "openai_api_key": self.openai_api_key,
            },
            "openai_passthrough": {
                "aws_s3_bucket_name": self.aws_s3_bucket_name,
                "langchain_memory_key": self.langchain_memory_key,
                "openai_endpoint_image_n": self.openai_endpoint_image_n,
                "openai_endpoint_image_size": self.openai_endpoint_image_size,
            },
        }
        if self.dump_defaults:
            settings_defaults = SettingsDefaults.to_dict()
            self._dump["settings_defaults"] = settings_defaults

        if self.is_using_dotenv_file:
            self._dump["environment"]["dotenv"] = self.environment_variables

        self._dump = recursive_sort_dict(self._dump)
        return self._dump

    @field_validator("shared_resource_identifier")
    def validate_shared_resource_identifier(cls, v: Optional[str]) -> str:
        """Validates the `shared_resource_identifier` field.
        Uses SettingsDefaults if no value is received.

        Args:
            v (Optional[str]): The shared resource identifier to validate.

        Returns:
            str: The validated shared resource identifier.
        """
        if v in [None, ""]:
            return SettingsDefaults.SHARED_RESOURCE_IDENTIFIER

        if not isinstance(v, str):
            raise SmarterConfigurationError("shared_resource_identifier is not a str.")

        return v

    @field_validator("aws_profile")
    def validate_aws_profile(cls, v: Optional[str]) -> Optional[str]:
        """Validates the `aws_profile` field.
        Uses SettingsDefaults if no value is received.

        Args:
            v (Optional[str]): The AWS profile value to validate.

        Returns:
            Optional[str]: The validated AWS profile.
        """
        if v in [None, ""]:
            return SettingsDefaults.AWS_PROFILE
        return v

    @field_validator("aws_access_key_id")
    def validate_aws_access_key_id(cls, v: Optional[SecretStr], values: ValidationInfo) -> SecretStr:
        """Validates the `aws_access_key_id` field.
        Uses SettingsDefaults if no value is received.


        Args:
            v (Optional[SecretStr]): The AWS access key ID value to validate.
            values (ValidationInfo): The validation info containing other field values.

        Returns:
            SecretStr: The validated AWS access key ID.
        """
        if isinstance(v, str):
            v = SecretStr(v)
        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError("could not convert aws_access_key_id value to SecretStr")

        if v.get_secret_value() in [None, ""]:
            return SettingsDefaults.AWS_ACCESS_KEY_ID
        aws_profile = values.data.get("aws_profile", None)
        if aws_profile and len(aws_profile) > 0 and aws_profile != SettingsDefaults.AWS_PROFILE:
            # pylint: disable=logging-fstring-interpolation
            logger.warning(f"aws_access_key_id is being ignored. using aws_profile {aws_profile}.")
            return SettingsDefaults.AWS_ACCESS_KEY_ID
        return v

    @field_validator("aws_secret_access_key")
    def validate_aws_secret_access_key(cls, v: Optional[SecretStr], values: ValidationInfo) -> SecretStr:
        """Validates the `aws_secret_access_key` field.
        Uses SettingsDefaults if no value is received.

        Args:
            v (Optional[SecretStr]): The AWS secret access key value to validate.
            values (ValidationInfo): The validation info containing other field values.

        Returns:
            SecretStr: The validated AWS secret access key.
        """
        if isinstance(v, str):
            v = SecretStr(v)
        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError("could not convert aws_secret_access_key value to SecretStr")
        if v.get_secret_value() in [None, ""]:
            return SettingsDefaults.AWS_SECRET_ACCESS_KEY
        aws_profile = values.data.get("aws_profile", None)
        if aws_profile and len(aws_profile) > 0 and aws_profile != SettingsDefaults.AWS_PROFILE:
            # pylint: disable=logging-fstring-interpolation
            logger.warning(f"aws_secret_access_key is being ignored. using aws_profile {aws_profile}.")
            return SettingsDefaults.AWS_SECRET_ACCESS_KEY
        return v

    @field_validator("aws_region")
    def validate_aws_region(cls, v: Optional[str], values: ValidationInfo, **kwargs) -> Optional[str]:
        """Validates the `aws_region` field.
        Uses SettingsDefaults if no value is received.

        Args:
            v (Optional[str]): The AWS region value to validate.
            values (ValidationInfo): The validation info containing other field values.

        Returns:
            Optional[str]: The validated AWS region.
        """

        valid_regions = values.data.get("aws_regions", ["us-east-1"])
        if v in [None, ""]:
            return SettingsDefaults.AWS_REGION
        if v not in valid_regions:
            raise SmarterValueError(f"aws_region {v} not in aws_regions: {valid_regions}")
        return v

    @field_validator("environment")
    def validate_environment(cls, v: Optional[str]) -> str:
        """Validates the `environment` field.

        Args:
            v (Optional[str]): The environment value to validate.

        Returns:
            Optional[str]: The validated environment.
        """
        if v in [None, ""]:
            return SettingsDefaults.ENVIRONMENT
        if not isinstance(v, str):
            raise SmarterConfigurationError("environment is not a str.")
        return v

    @field_validator("fernet_encryption_key")
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

        if v in [None, ""]:
            return SettingsDefaults.FERNET_ENCRYPTION_KEY

        if v == DEFAULT_MISSING_VALUE:
            return None

        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError("fernet_encryption_key is not a SecretStr.")
        try:
            # Decode the key using URL-safe base64
            decoded_key = base64.urlsafe_b64decode(v.get_secret_value())
            # Ensure the decoded key is exactly 32 bytes
            if len(decoded_key) != 32:
                raise ValueError("Fernet key must be exactly 32 bytes when decoded.")
        except (TypeError, ValueError, base64.binascii.Error) as e:  # type: ignore[catch-base-exception]
            raise SmarterValueError(f"Invalid Fernet encryption key: {v}. Error: {e}") from e

        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError("fernet_encryption_key is not a SecretStr.")
        return v

    @field_validator("local_hosts")
    def validate_local_hosts(cls, v: Optional[List[str]]) -> List[str]:
        """Validates the `local_hosts` field.

        Args:
            v (Optional[List[str]]): The local hosts value to validate.

        Returns:
            List[str]: The validated local hosts.
        """
        if v in [None, ""]:
            return SettingsDefaults.LOCAL_HOSTS

        if not isinstance(v, list):
            raise SmarterConfigurationError("local_hosts is not a list")
        return v

    @field_validator("root_domain")
    def validate_aws_apigateway_root_domain(cls, v: Optional[str]) -> str:
        """
        Validates the `root_domain` field.

        If the value is not set, returns the default root domain.

        Args:
            v (Optional[str]): The root domain value to validate.

        Returns:
            str: The validated root domain.
        """
        if v in [None, ""]:
            return SettingsDefaults.ROOT_DOMAIN

        if not isinstance(v, str):
            raise SmarterConfigurationError("root_domain is not a str.")

        return v

    @field_validator("aws_eks_cluster_name")
    def validate_aws_eks_cluster_name(cls, v: Optional[str]) -> str:
        """Validates the `aws_eks_cluster_name` field.

        Args:
            v (Optional[str]): The AWS EKS cluster name value to validate.

        Returns:
            str: The validated AWS EKS cluster name.
        """
        if v in [None, ""]:
            return SettingsDefaults.AWS_EKS_CLUSTER_NAME

        if not isinstance(v, str):
            raise SmarterConfigurationError("aws_eks_cluster_name is not a str.")

        return v

    @field_validator("aws_db_instance_identifier")
    def validate_aws_db_instance_identifier(cls, v: Optional[str]) -> str:
        """Validates the `aws_db_instance_identifier` field.

        Args:
            v (Optional[str]): The AWS RDS DB instance identifier value to validate.

        Returns:
            str: The validated AWS RDS DB instance identifier.
        """
        if v in [None, ""]:
            return SettingsDefaults.AWS_RDS_DB_INSTANCE_IDENTIFIER

        if not isinstance(v, str):
            raise SmarterConfigurationError("aws_db_instance_identifier is not a str.")

        return v

    @field_validator("anthropic_api_key")
    def validate_anthropic_api_key(cls, v: Optional[SecretStr]) -> SecretStr:
        """Validates the `anthropic_api_key` field.

        Args:
            v (Optional[SecretStr]): The Anthropic API key value to validate.

        Returns:
            SecretStr: The validated Anthropic API key.
        """
        if v in [None, ""]:
            return SettingsDefaults.ANTHROPIC_API_KEY

        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError("anthropic_api_key is not a SecretStr.")

        return v

    @field_validator("debug_mode")
    def parse_debug_mode(cls, v: Optional[Union[bool, str]]) -> bool:
        """Validates the 'debug_mode' field.

        Args:
            v (Union[bool, str]): the debug_mode value to validate

        Returns:
            bool: The validated debug_mode.
        """
        if isinstance(v, bool):
            return v
        if v in [None, ""]:
            return SettingsDefaults.DEBUG_MODE
        if isinstance(v, str):
            return v.lower() in ["true", "1", "t", "y", "yes"]

        raise SmarterConfigurationError("could not validate debug_mode")

    @field_validator("dump_defaults")
    def parse_dump_defaults(cls, v: Optional[Union[bool, str]]) -> bool:
        """Validates the 'dump_defaults' field.

        Args:
            v (Optional[Union[bool, str]]): the dump_defaults value to validate

        Returns:
            bool: The validated dump_defaults.
        """
        if isinstance(v, bool):
            return v
        if v in [None, ""]:
            return SettingsDefaults.DUMP_DEFAULTS
        if isinstance(v, str):
            return v.lower() in ["true", "1", "t", "y", "yes"]

        raise SmarterConfigurationError("could not validate dump_defaults")

    @field_validator("google_maps_api_key")
    def check_google_maps_api_key(cls, v: Optional[SecretStr]) -> SecretStr:
        """Validates the `google_maps_api_key` field.

        Args:
            v (Optional[SecretStr]): The Google Maps API key value to validate.

        Returns:
            SecretStr: The validated Google Maps API key.
        """
        if str(v) in [None, ""]:
            return SettingsDefaults.GOOGLE_MAPS_API_KEY
        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError("google_maps_api_key is not a SecretStr.")
        return v

    @field_validator("google_service_account")
    def check_google_service_account(cls, v: Optional[SecretStr]) -> Optional[SecretStr]:
        """Validates the `google_service_account` field.

        Args:
            v (Optional[SecretStr]): The Google service account value to validate.
        Returns:
            SecretStr: The validated Google service account.
        """
        if v is None:
            return SettingsDefaults.GOOGLE_SERVICE_ACCOUNT

        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError("google_service_account is not a SecretStr.")
        return v

    @field_validator("gemini_api_key")
    def check_gemini_api_key(cls, v: Optional[SecretStr]) -> SecretStr:
        """Validates the `gemini_api_key` field.

        Args:
            v (Optional[SecretStr]): The Gemini API key value to validate.

        Returns:
            SecretStr: The validated Gemini API key.
        """
        if str(v) in [None, ""]:
            return SettingsDefaults.GEMINI_API_KEY
        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError("gemini_api_key is not a SecretStr.")

        return v

    @field_validator("llama_api_key")
    def check_llama_api_key(cls, v: Optional[SecretStr]) -> SecretStr:
        """Validates the `llama_api_key` field.

        Args:
            v (Optional[SecretStr]): The Llama API key value to validate.

        Returns:
            SecretStr: The validated Llama API key.
        """
        if str(v) in [None, ""]:
            return SettingsDefaults.LLAMA_API_KEY

        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError("llama_api_key is not a SecretStr.")
        return v

    @field_validator("social_auth_google_oauth2_key")
    def check_social_auth_google_oauth2_key(cls, v: Optional[SecretStr]) -> SecretStr:
        """Validates the `social_auth_google_oauth2_key` field.

        Args:
            v (Optional[SecretStr]): The Google OAuth2 key value to validate.
        Returns:
            SecretStr: The validated Google OAuth2 key.
        """
        if str(v) in [None, ""] and SettingsDefaults.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY:
            return SettingsDefaults.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY

        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError("social_auth_google_oauth2_key is not a SecretStr.")
        return v

    @field_validator("social_auth_google_oauth2_secret")
    def check_social_auth_google_oauth2_secret(cls, v: Optional[SecretStr]) -> SecretStr:
        """Validates the `social_auth_google_oauth2_secret` field.

        Args:
            v (Optional[SecretStr]): The Google OAuth2 secret value to validate.

        Returns:
            SecretStr: The validated Google OAuth2 secret.
        """
        if str(v) in [None, ""] and SettingsDefaults.SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET is not None:
            return SettingsDefaults.SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET

        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError("social_auth_google_oauth2_secret is not a SecretStr.")
        return v

    @field_validator("social_auth_github_key")
    def check_social_auth_github_key(cls, v: Optional[SecretStr]) -> SecretStr:
        """Validates the `social_auth_github_key` field.

        Args:
            v (Optional[SecretStr]): The GitHub OAuth2 key value to validate.
        Returns:
            SecretStr: The validated GitHub OAuth2 key.
        """
        if str(v) in [None, ""] and SettingsDefaults.SOCIAL_AUTH_GITHUB_KEY is not None:
            return SettingsDefaults.SOCIAL_AUTH_GITHUB_KEY

        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError("social_auth_github_key is not a SecretStr")

        return v

    @field_validator("social_auth_github_secret")
    def check_social_auth_github_secret(cls, v: Optional[SecretStr]) -> SecretStr:
        """Validates the `social_auth_github_secret` field.

        Args:
            v (Optional[SecretStr]): The GitHub OAuth2 secret value to validate.
        Returns:
            SecretStr: The validated GitHub OAuth2 secret.
        """
        if str(v) in [None, ""] and SettingsDefaults.SOCIAL_AUTH_GITHUB_SECRET is not None:
            return SettingsDefaults.SOCIAL_AUTH_GITHUB_SECRET

        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError("social_auth_github_secret is not a SecretStr.")
        return v

    @field_validator("social_auth_linkedin_oauth2_key")
    def check_social_auth_linkedin_oauth2_key(cls, v: Optional[SecretStr]) -> SecretStr:
        """Validates the `social_auth_linkedin_oauth2_key` field.

        Args:
            v (Optional[SecretStr]): The LinkedIn OAuth2 key value to validate.
        Returns:
            SecretStr: The validated LinkedIn OAuth2 key.
        """
        if str(v) in [None, ""] and SettingsDefaults.SOCIAL_AUTH_LINKEDIN_OAUTH2_KEY is not None:
            return SettingsDefaults.SOCIAL_AUTH_LINKEDIN_OAUTH2_KEY
        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError("social_auth_linkedin_oauth2_key is not a SecretStr.")
        return v

    @field_validator("social_auth_linkedin_oauth2_secret")
    def check_social_auth_linkedin_oauth2_secret(cls, v: Optional[SecretStr]) -> SecretStr:
        """Validates the `social_auth_linkedin_oauth2_secret` field.

        Args:
            v (Optional[SecretStr]): The LinkedIn OAuth2 secret value to validate.

        Returns:
            SecretStr: The validated LinkedIn OAuth2 secret.
        """
        if str(v) in [None, ""] and SettingsDefaults.SOCIAL_AUTH_LINKEDIN_OAUTH2_SECRET is not None:
            return SettingsDefaults.SOCIAL_AUTH_LINKEDIN_OAUTH2_SECRET
        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError("social_auth_linkedin_oauth2_secret is not a SecretStr.")
        return v

    @field_validator("langchain_memory_key")
    def check_langchain_memory_key(cls, v: Optional[str]) -> str:
        """Validates the `langchain_memory_key` field.

        Args:
            v (Optional[str]): The Langchain memory key value to validate.
        Returns:
            str: The validated Langchain memory key.
        """
        if str(v) in [None, ""] and SettingsDefaults.LANGCHAIN_MEMORY_KEY is not None:
            return SettingsDefaults.LANGCHAIN_MEMORY_KEY
        return str(v)

    @field_validator("logo")
    def check_logo(cls, v: Optional[str]) -> str:
        """Validates the `logo` field.

        Args:
            v (str): The logo value to validate.

        Returns:
            str: The validated logo.
        """
        if str(v) in [None, ""] and SettingsDefaults.LOGO is not None:
            return SettingsDefaults.LOGO
        return str(v)

    @field_validator("mailchimp_api_key")
    def check_mailchimp_api_key(cls, v: Optional[SecretStr]) -> SecretStr:
        """Validates the `mailchimp_api_key` field.

        Args:
            v (Optional[SecretStr]): The Mailchimp API key value to validate.

        Returns:
            SecretStr: The validated Mailchimp API key.
        """
        if str(v) in [None, ""] and SettingsDefaults.MAILCHIMP_API_KEY is not None:
            return SettingsDefaults.MAILCHIMP_API_KEY

        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError("mailchimp_api_key is not a SecretStr")
        return v

    @field_validator("mailchimp_list_id")
    def check_mailchimp_list_id(cls, v: Optional[str]) -> Optional[str]:
        """Validates the `mailchimp_list_id` field.

        Args:
            v (Optional[str]): The Mailchimp list ID value to validate.

        Returns:
            Optional[str]: The validated Mailchimp list ID.
        """
        if str(v) in [None, ""] and SettingsDefaults.MAILCHIMP_LIST_ID is not None:
            return SettingsDefaults.MAILCHIMP_LIST_ID
        return v

    @field_validator("marketing_site_url")
    def check_marketing_site_url(cls, v: Optional[HttpUrl]) -> HttpUrl:
        """Validates the `marketing_site_url` field.

        Args:
            v (Optional[HttpUrl]): The marketing site URL value to validate.
        Returns:
            HttpUrl: The validated marketing site URL.
        """
        if str(v) in [None, ""] and SettingsDefaults.MARKETING_SITE_URL is not None:
            return SettingsDefaults.MARKETING_SITE_URL
        if not isinstance(v, HttpUrl):
            raise SmarterConfigurationError("marketing_site_url is not a HttpUrl.")
        SmarterValidator.validate_url(str(v))
        return v

    @field_validator("openai_api_organization")
    def check_openai_api_organization(cls, v: Optional[str]) -> Optional[str]:
        """Validates the `openai_api_organization` field.

        Args:
            v (Optional[str]): The OpenAI API organization value to validate.

        Returns:
            Optional[str]: The validated OpenAI API organization.
        """
        if str(v) in [None, ""] and SettingsDefaults.OPENAI_API_ORGANIZATION is not None:
            return SettingsDefaults.OPENAI_API_ORGANIZATION

        if not isinstance(v, str):
            raise SmarterConfigurationError("openai_api_organization is not a str.")
        return v

    @field_validator("openai_api_key")
    def check_openai_api_key(cls, v: Optional[SecretStr]) -> SecretStr:
        """Validates the `openai_api_key` field.

        Args:
            v (Optional[SecretStr]): The OpenAI API key value to validate.
        Returns:
            SecretStr: The validated OpenAI API key.
        """
        if str(v) in [None, ""] and SettingsDefaults.OPENAI_API_KEY is not None:
            return SettingsDefaults.OPENAI_API_KEY

        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError("openai_api_key is not a SecretStr")

        return v

    @field_validator("openai_endpoint_image_n")
    def check_openai_endpoint_image_n(cls, v: Optional[int]) -> int:
        """Validates the `openai_endpoint_image_n` field.

        Args:
            v (Optional[int]): The OpenAI endpoint image number value to validate.
        Returns:
            int: The validated OpenAI endpoint image number.
        """
        if isinstance(v, int):
            return v
        if str(v) in [None, ""] and SettingsDefaults.OPENAI_ENDPOINT_IMAGE_N is not None:
            return SettingsDefaults.OPENAI_ENDPOINT_IMAGE_N
        if not isinstance(v, int):
            raise SmarterConfigurationError("openai_endpoint_image_n is not an int.")

        return int(v)

    @field_validator("openai_endpoint_image_size")
    def check_openai_endpoint_image_size(cls, v: Optional[str]) -> str:
        """Validates the `openai_endpoint_image_size` field.

        Args:
            v (Optional[str]): The OpenAI endpoint image size value to validate.

        Returns:
            str: The validated OpenAI endpoint image size.
        """
        if str(v) in [None, ""] and SettingsDefaults.OPENAI_ENDPOINT_IMAGE_SIZE is not None:
            return SettingsDefaults.OPENAI_ENDPOINT_IMAGE_SIZE

        if not isinstance(v, str):
            raise SmarterConfigurationError("openai_endpoint_image_size is not a str.")

        return v

    @field_validator("llm_default_model")
    def check_openai_default_model(cls, v: Optional[str]) -> Optional[str]:
        """Validates the `llm_default_model` field.

        Args:
            v (Optional[str]): The LLM default model value to validate.

        Returns:
            Optional[str]: The validated LLM default model.
        """
        if str(v) in [None, ""] and SettingsDefaults.LLM_DEFAULT_MODEL is not None:
            return SettingsDefaults.LLM_DEFAULT_MODEL

        if not isinstance(v, str):
            raise SmarterConfigurationError("llm_default_model is not a str.")
        return v

    @field_validator("llm_default_provider")
    def check_openai_default_provider(cls, v: Optional[str]) -> Optional[str]:
        """Validates the `llm_default_provider` field.

        Args:
            v (Optional[str]): The LLM default provider value to validate.

        Returns:
            Optional[str]: The validated LLM default provider.
        """
        if str(v) in [None, ""] and SettingsDefaults.LLM_DEFAULT_PROVIDER is not None:
            return SettingsDefaults.LLM_DEFAULT_PROVIDER

        if not isinstance(v, str):
            raise SmarterConfigurationError("llm_default_provider is not a str.")
        return v

    @field_validator("llm_default_system_role")
    def check_openai_default_system_prompt(cls, v: Optional[str]) -> Optional[str]:
        """Validates the `llm_default_system_role` field.

        Args:
            v (Optional[str]): The LLM default system role value to validate.

        Returns:
            Optional[str]: The validated LLM default system role.
        """
        if str(v) in [None, ""] and SettingsDefaults.LLM_DEFAULT_SYSTEM_ROLE is not None:
            return SettingsDefaults.LLM_DEFAULT_SYSTEM_ROLE

        if not isinstance(v, str):
            raise SmarterConfigurationError("llm_default_system_role is not a str.")
        return v

    @field_validator("llm_default_temperature")
    def check_openai_default_temperature(cls, v: Optional[float]) -> float:
        """Validates the `llm_default_temperature` field.

        Args:
            v (Optional[float]): The LLM default temperature value to validate.
        Returns:
            float: The validated LLM default temperature.
        """
        if isinstance(v, float):
            return v
        if v in [None, ""]:
            return SettingsDefaults.LLM_DEFAULT_TEMPERATURE
        try:
            retval = float(v)  # type: ignore
            return retval
        except (TypeError, ValueError) as e:
            raise SmarterConfigurationError("llm_default_temperature is not a float.") from e

    @field_validator("llm_default_max_tokens")
    def check_openai_default_max_completion_tokens(cls, v: Optional[int]) -> int:
        """Validates the `llm_default_max_tokens` field.

        Args:
            v (Optional[int]): The LLM default max tokens value to validate.

        Returns:
            int: The validated LLM default max tokens.
        """
        if isinstance(v, int):
            return v
        if v in [None, ""]:
            return SettingsDefaults.LLM_DEFAULT_MAX_TOKENS

        try:
            retval = int(v)  # type: ignore
            return retval
        except (TypeError, ValueError) as e:
            raise SmarterConfigurationError("llm_default_max_tokens is not an int.") from e

    @field_validator("pinecone_api_key")
    def check_pinecone_api_key(cls, v: Optional[SecretStr]) -> Optional[SecretStr]:
        """Validates the `pinecone_api_key` field.

        Args:
            v (Optional[SecretStr]): The Pinecone API key value to validate.

        Returns:
            SecretStr: The validated Pinecone API key.
        """
        if str(v) in [None, ""] and SettingsDefaults.PINECONE_API_KEY is not None:
            return SettingsDefaults.PINECONE_API_KEY

        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError("pinecone_api_key is not a SecretStr")

        return v

    @field_validator("stripe_live_secret_key")
    def check_stripe_live_secret_key(cls, v: Optional[SecretStr]) -> SecretStr:
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
            return SettingsDefaults.STRIPE_LIVE_SECRET_KEY

        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError("stripe_live_secret_key is not a SecretStr.")
        return v

    @field_validator("stripe_test_secret_key")
    def check_stripe_test_secret_key(cls, v: Optional[SecretStr]) -> SecretStr:
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
            return SettingsDefaults.STRIPE_TEST_SECRET_KEY

        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError("stripe_test_secret_key is not a SecretStr.")
        return v

    @field_validator("secret_key")
    def check_secret_key(cls, v: Optional[SecretStr]) -> SecretStr:
        """Validates the `secret_key` field.

        Args:
            v (Optional[SecretStr]): The secret key value to validate.
        Returns:
            SecretStr: The validated secret key.
        """
        if v is None:
            return SettingsDefaults.SECRET_KEY

        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError(f"secret_key {type(v)} is not a SecretStr.")
        return v

    @field_validator("smarter_reactjs_app_loader_path")
    def check_smarter_reactjs_app_loader_path(cls, v: Optional[str]) -> str:
        """Validates the `smarter_reactjs_app_loader_path` field. Needs
        to start with a slash (/) and end with '.js'. The final string value
        should be url friendly. example: /ui-chat/app-loader.js

        Args:
            v (Optional[str]): The Smarter ReactJS app loader path value to validate.

        Returns:
            str: The validated Smarter ReactJS app loader path.
        """
        if v in [None, ""]:
            return SettingsDefaults.SMARTER_REACTJS_APP_LOADER_PATH

        if not isinstance(v, str):
            raise SmarterConfigurationError("smarter_reactjs_app_loader_path is not a str.")

        if not v.startswith("/"):
            raise SmarterConfigurationError("smarter_reactjs_app_loader_path must start with '/'")
        if not v.endswith(".js"):
            raise SmarterConfigurationError("smarter_reactjs_app_loader_path must end with '.js'")
        return v

    @field_validator("smtp_sender")
    def check_smtp_sender(cls, v: Optional[str]) -> str:
        """Validates the `smtp_sender` field.

        Args:
            v (Optional[str]): The SMTP sender email address to validate.

        Returns:
            Optional[str]: The validated SMTP sender email address.
        """
        if v in [None, ""]:
            v = SettingsDefaults.SMTP_SENDER
            SmarterValidator.validate_domain(v)

        if not isinstance(v, str):
            raise SmarterConfigurationError("smtp_sender is not a str.")
        return v

    @field_validator("smtp_from_email")
    def check_smtp_from_email(cls, v: Optional[str]) -> Optional[str]:
        """Validates the `smtp_from_email` field.

        Args:
            v (Optional[str]): The SMTP from email address to validate.

        Returns:
            Optional[str]: The validated SMTP from email address.
        """
        if v in [None, ""]:
            return SettingsDefaults.SMTP_FROM_EMAIL

        if isinstance(v, str):
            SmarterValidator.validate_email(v)
            return v

        raise SmarterConfigurationError("could not validate smtp_from_email.")

    @field_validator("smtp_host")
    def check_smtp_host(cls, v: Optional[str]) -> Optional[str]:
        """Validates the `smtp_host` field.

        Args:
            v (Optional[str]): The SMTP host to validate.

        Returns:
            Optional[str]: The validated SMTP host.
        """
        if v in [None, ""]:
            v = SettingsDefaults.SMTP_HOST
            SmarterValidator.validate_domain(v)

        if not isinstance(v, str):
            raise SmarterConfigurationError("smtp_host is not a str.")
        return v

    @field_validator("smtp_password")
    def check_smtp_password(cls, v: Optional[SecretStr]) -> Optional[SecretStr]:
        """Validates the `smtp_password` field.

        Args:
            v (Optional[SecretStr]): The SMTP password to validate.
        Returns:
            Optional[SecretStr]: The validated SMTP password.
        """
        if v in [None, ""]:
            return SettingsDefaults.SMTP_PASSWORD

        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError("smtp_password is not a str.")
        return v

    @field_validator("smtp_port")
    def check_smtp_port(cls, v: Optional[int]) -> Optional[int]:
        """Validates the `smtp_port` field.

        Args:
            v (Optional[int]): The SMTP port to validate.

        Returns:
            int: The validated SMTP port.
        """
        if v in [None, ""]:
            v = SettingsDefaults.SMTP_PORT
        try:
            retval = int(v)  # type: ignore
        except ValueError as e:
            raise SmarterValueError("Could not convert port number to int.") from e

        if not str(retval).isdigit() or not 1 <= int(retval) <= 65535:
            raise SmarterValueError("Invalid port number")

        return retval

    @field_validator("smtp_use_ssl")
    def check_smtp_use_ssl(cls, v: Optional[Union[bool, str]]) -> bool:
        """Validates the `smtp_use_ssl` field.

        Args:
            v (Optional[Union[bool, str]]): The SMTP use SSL flag to validate.

        Returns:
            bool: The validated SMTP use SSL flag.
        """
        if isinstance(v, bool):
            return v
        if v in [None, ""]:
            return SettingsDefaults.SMTP_USE_SSL
        return str(v).lower() in ["true", "1", "yes", "on"]

    @field_validator("smtp_use_tls")
    def check_smtp_use_tls(cls, v: Optional[Union[bool, str]]) -> bool:
        """Validates the `smtp_use_tls` field.

        Args:
            v (Optional[Union[bool, str]]): The SMTP use TLS flag to validate.
        Returns:
            bool: The validated SMTP use TLS flag.
        """
        if isinstance(v, bool):
            return v
        if v in [None, ""]:
            return SettingsDefaults.SMTP_USE_TLS
        return str(v).lower() in ["true", "1", "yes", "on"]

    @field_validator("smtp_username")
    def check_smtp_username(cls, v: Optional[SecretStr]) -> SecretStr:
        """Validates the `smtp_username` field.

        Args:
            v (Optional[str]): The SMTP username to validate.

        Returns:
            Optional[str]: The validated SMTP username.
        """
        if v is None:
            return SettingsDefaults.SMTP_USERNAME
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get the singleton settings instance."""
    try:
        return Settings()
    except ValidationError as e:
        raise SmarterConfigurationError("Invalid configuration: " + str(e)) from e


settings = get_settings()
