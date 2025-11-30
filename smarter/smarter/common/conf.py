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

# 3rd party stuff
import boto3  # AWS SDK for Python https://boto3.amazonaws.com/v1/documentation/api/latest/index.html
from botocore.exceptions import NoCredentialsError, ProfileNotFound
from dotenv import load_dotenv
from pydantic import Field, SecretStr, ValidationError, ValidationInfo, field_validator
from pydantic_settings import BaseSettings

from smarter.lib import json

from ..lib.django.validators import SmarterValidator

# our stuff
from .const import (
    IS_USING_TFVARS,
    SMARTER_API_KEY_MAX_LIFETIME_DAYS,
    SMARTER_API_SUBDOMAIN,
    SMARTER_PLATFORM_SUBDOMAIN,
    TFVARS,
    VERSION,
    SmarterEnvironments,
)
from .exceptions import SmarterConfigurationError, SmarterValueError


logger = logging.getLogger(__name__)
DEFAULT_MISSING_VALUE = "SET-ME-PLEASE"
TFVARS = TFVARS or {}
DOT_ENV_LOADED = load_dotenv()


def recursive_sort_dict(d):
    """Recursively sort a dictionary by key."""
    return {k: recursive_sort_dict(v) if isinstance(v, dict) else v for k, v in sorted(d.items())}


def bool_environment_variable(var_name: str, default: bool) -> bool:
    """Get a boolean environment variable"""
    value = os.environ.get(var_name)
    if value is None:
        return default
    return value.lower() in ["true", "1", "t", "y", "yes"]


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
      2. tfvars
      3. defaults.
    """

    ROOT_DOMAIN = os.environ.get("ROOT_DOMAIN", TFVARS.get("root_domain", "example.com"))

    ANTHROPIC_API_KEY: SecretStr = SecretStr(os.environ.get("ANTHROPIC_API_KEY", DEFAULT_MISSING_VALUE))

    # aws auth
    AWS_PROFILE = os.environ.get("AWS_PROFILE", TFVARS.get("aws_profile", None))
    AWS_ACCESS_KEY_ID: SecretStr = SecretStr(os.environ.get("AWS_ACCESS_KEY_ID", DEFAULT_MISSING_VALUE))
    AWS_SECRET_ACCESS_KEY: SecretStr = SecretStr(os.environ.get("AWS_SECRET_ACCESS_KEY", DEFAULT_MISSING_VALUE))
    AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
    AWS_IS_CONFIGURED = bool(
        AWS_PROFILE
        or (
            AWS_ACCESS_KEY_ID.get_secret_value() != DEFAULT_MISSING_VALUE
            and AWS_SECRET_ACCESS_KEY.get_secret_value() != DEFAULT_MISSING_VALUE
        )
    )

    AWS_EKS_CLUSTER_NAME = os.environ.get(
        "AWS_EKS_CLUSTER_NAME", TFVARS.get("aws_eks_cluster_name", "apps-hosting-service")
    )
    AWS_RDS_DB_INSTANCE_IDENTIFIER = os.environ.get("AWS_RDS_DB_INSTANCE_IDENTIFIER", "apps-hosting-service")
    DEBUG_MODE: bool = bool(os.environ.get("DEBUG_MODE", TFVARS.get("debug_mode", False)))
    DEVELOPER_MODE: bool = bool(os.environ.get("DEVELOPER_MODE", TFVARS.get("developer_mode", False)))

    DJANGO_DEFAULT_FILE_STORAGE = os.environ.get("DJANGO_DEFAULT_FILE_STORAGE", DjangoPermittedStorages.AWS_S3)
    if DJANGO_DEFAULT_FILE_STORAGE == DjangoPermittedStorages.AWS_S3 and not AWS_IS_CONFIGURED:
        DJANGO_DEFAULT_FILE_STORAGE = DjangoPermittedStorages.FILE_SYSTEM
        logger.warning(
            "AWS is not configured properly. Falling back to FileSystemStorage for Django default file storage."
        )

    DUMP_DEFAULTS: bool = bool(os.environ.get("DUMP_DEFAULTS", TFVARS.get("dump_defaults", False)))
    ENVIRONMENT = os.environ.get("ENVIRONMENT", "local")

    FERNET_ENCRYPTION_KEY: str = os.environ.get("FERNET_ENCRYPTION_KEY", DEFAULT_MISSING_VALUE)

    GOOGLE_MAPS_API_KEY: SecretStr = SecretStr(
        os.environ.get("GOOGLE_MAPS_API_KEY", os.environ.get("google_maps_api_key", DEFAULT_MISSING_VALUE))
    )

    try:
        GOOGLE_SERVICE_ACCOUNT_B64 = os.environ.get("GOOGLE_SERVICE_ACCOUNT_B64", "")
        GOOGLE_SERVICE_ACCOUNT = json.loads(base64.b64decode(GOOGLE_SERVICE_ACCOUNT_B64).decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.error("Failed to load Google service account: %s", e)
        logger.error(
            "See https://console.cloud.google.com/projectselector2/iam-admin/serviceaccounts?supportedpurview=project"
        )
        GOOGLE_SERVICE_ACCOUNT = {}

    GEMINI_API_KEY: SecretStr = SecretStr(os.environ.get("GEMINI_API_KEY", DEFAULT_MISSING_VALUE))
    LANGCHAIN_MEMORY_KEY = os.environ.get("LANGCHAIN_MEMORY_KEY", "chat_history")

    LLAMA_API_KEY: SecretStr = SecretStr(os.environ.get("LLAMA_API_KEY", DEFAULT_MISSING_VALUE))

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

    LOGO: str = os.environ.get(
        "OPENAI_API_ORGANIZATION", "https://platform.smarter.sh/static/images/logo/smarter-crop.png"
    )
    MAILCHIMP_API_KEY: SecretStr = SecretStr(os.environ.get("MAILCHIMP_API_KEY", DEFAULT_MISSING_VALUE))
    MAILCHIMP_LIST_ID = os.environ.get("MAILCHIMP_LIST_ID", DEFAULT_MISSING_VALUE)

    MARKETING_SITE_URL: str = os.environ.get("OPENAI_API_ORGANIZATION", f"https://{ROOT_DOMAIN}")

    OPENAI_API_ORGANIZATION = os.environ.get("OPENAI_API_ORGANIZATION", DEFAULT_MISSING_VALUE)
    OPENAI_API_KEY: SecretStr = SecretStr(os.environ.get("OPENAI_API_KEY", DEFAULT_MISSING_VALUE))
    OPENAI_ENDPOINT_IMAGE_N = 4
    OPENAI_ENDPOINT_IMAGE_SIZE = "1024x768"
    PINECONE_API_KEY: SecretStr = SecretStr(os.environ.get("PINECONE_API_KEY", DEFAULT_MISSING_VALUE))

    SHARED_RESOURCE_IDENTIFIER = os.environ.get(
        "SHARED_RESOURCE_IDENTIFIER", TFVARS.get("shared_resource_identifier", "smarter")
    )

    SMARTER_MYSQL_TEST_DATABASE_SECRET_NAME = os.environ.get(
        "SMARTER_MYSQL_TEST_DATABASE_SECRET_NAME",
        "smarter_test_db",
    )
    SMARTER_MYSQL_TEST_DATABASE_PASSWORD = os.environ.get(
        "SMARTER_MYSQL_TEST_DATABASE_PASSWORD",
        DEFAULT_MISSING_VALUE,
    )

    # -------------------------------------------------------------------------
    # see: https://console.cloud.google.com/apis/credentials/oauthclient/231536848926-egabg8jas321iga0nmleac21ccgbg6tq.apps.googleusercontent.com?project=smarter-sh
    # -------------------------------------------------------------------------
    SOCIAL_AUTH_GOOGLE_OAUTH2_KEY: SecretStr = SecretStr(
        os.environ.get("SOCIAL_AUTH_GOOGLE_OAUTH2_KEY", DEFAULT_MISSING_VALUE)
    )
    SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET: SecretStr = SecretStr(
        os.environ.get("SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET", DEFAULT_MISSING_VALUE)
    )
    # -------------------------------------------------------------------------
    # see: https://github.com/settings/applications/2620957
    # -------------------------------------------------------------------------
    SOCIAL_AUTH_GITHUB_KEY: SecretStr = SecretStr(os.environ.get("SOCIAL_AUTH_GITHUB_KEY", DEFAULT_MISSING_VALUE))
    SOCIAL_AUTH_GITHUB_SECRET: SecretStr = SecretStr(os.environ.get("SOCIAL_AUTH_GITHUB_SECRET", DEFAULT_MISSING_VALUE))
    # -------------------------------------------------------------------------
    # see:  https://www.linkedin.com/developers/apps/221422881/settings
    #       https://www.linkedin.com/developers/apps/221422881/products?refreshKey=1734980684455
    # verification url: https://www.linkedin.com/developers/apps/verification/3ac34414-09a4-433b-983a-0d529fa486f1
    # -------------------------------------------------------------------------
    SOCIAL_AUTH_LINKEDIN_OAUTH2_KEY: SecretStr = SecretStr(
        os.environ.get("SOCIAL_AUTH_LINKEDIN_OAUTH2_KEY", DEFAULT_MISSING_VALUE)
    )
    SOCIAL_AUTH_LINKEDIN_OAUTH2_SECRET: SecretStr = SecretStr(
        os.environ.get("SOCIAL_AUTH_LINKEDIN_OAUTH2_SECRET", DEFAULT_MISSING_VALUE)
    )

    SECRET_KEY = os.getenv("SECRET_KEY")

    SMTP_SENDER = os.environ.get("SMTP_SENDER", DEFAULT_MISSING_VALUE)
    SMTP_FROM_EMAIL = os.environ.get("SMTP_FROM_EMAIL", f"no-reply@{ROOT_DOMAIN}")
    SMTP_HOST = os.environ.get("SMTP_HOST", "email-smtp.us-east-2.amazonaws.com")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
    SMTP_USE_SSL = bool(os.environ.get("SMTP_USE_SSL", False))
    SMTP_USE_TLS = bool(os.environ.get("SMTP_USE_TLS", True))
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", DEFAULT_MISSING_VALUE)
    SMTP_USERNAME = os.environ.get("SMTP_USERNAME", DEFAULT_MISSING_VALUE)

    STRIPE_LIVE_SECRET_KEY = os.environ.get("STRIPE_LIVE_SECRET_KEY", DEFAULT_MISSING_VALUE)
    STRIPE_TEST_SECRET_KEY = os.environ.get("STRIPE_TEST_SECRET_KEY", DEFAULT_MISSING_VALUE)

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


# pylint: disable=too-many-public-methods
# pylint: disable=too-many-instance-attributes
class Settings(BaseSettings):
    """
    Smarter derived settings. This is intended to be instantiated as
    an immutable singleton object called `smarter_settings`. smarter_settings
    contains superseding, validated, and derived settings values for the platform.

    This class implements a consistent set of rules for initializing configuration
    values from multiple sources, including environment variables, `.env` file, TFVARS,
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
    debug_mode: bool = Field(
        SettingsDefaults.DEBUG_MODE,
        description="True if debug mode is enabled. This enables verbose logging and other debug features.",
    )
    default_missing_value: str = Field(
        DEFAULT_MISSING_VALUE,
        description="Default missing value placeholder string. Used for consistency across settings.",
        examples=["SET-ME-PLEASE"],
    )

    # new in 0.13.26
    # True if developer mode is enabled. Used as a means to configure a production
    # Docker container to run locally for student use.
    developer_mode: bool = Field(
        SettingsDefaults.DEVELOPER_MODE,
        description="True if developer mode is enabled. Used as a means to configure a production Docker container to run locally for student use.",
    )
    django_default_file_storage: str = Field(
        SettingsDefaults.DJANGO_DEFAULT_FILE_STORAGE,
        description="The default Django file storage backend.",
        examples=["storages.backends.s3boto3.S3Boto3Storage", "django.core.files.storage.FileSystemStorage"],
    )
    log_level: int = Field(
        SettingsDefaults.LOG_LEVEL,
        description="The logging level for the platform based on Python logging levels: logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL",
        examples=[logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL],
    )
    dump_defaults: bool = Field(
        SettingsDefaults.DUMP_DEFAULTS, description="True if default values should be dumped for debugging purposes."
    )
    aws_profile: Optional[str] = Field(
        SettingsDefaults.AWS_PROFILE,
        description="The AWS profile to use for authentication. If present, this will take precedence over AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY.",
        examples=["default", "smarter-profile"],
    )
    aws_access_key_id: SecretStr = Field(
        SettingsDefaults.AWS_ACCESS_KEY_ID,
        description="The AWS access key ID for authentication. Used if AWS_PROFILE is not set. Masked by pydantic SecretStr.",
        examples=["^AKIA[0-9A-Z]{16}$"],
    )
    aws_secret_access_key: SecretStr = Field(
        SettingsDefaults.AWS_SECRET_ACCESS_KEY,
        description="The AWS secret access key for authentication. Used if AWS_PROFILE is not set. Masked by pydantic SecretStr.",
        examples=["^[0-9a-zA-Z/+]{40}$"],
    )
    aws_regions: List[str] = Field(
        AWS_REGIONS,
        description="A list of AWS regions considered valid for this platform.",
        examples=["us-east-1", "us-west-2", "eu-west-1"],
    )
    aws_region: str = Field(
        SettingsDefaults.AWS_REGION,
        description="The single AWS region in which all AWS service clients will operate.",
        examples=["us-east-1", "us-west-2", "eu-west-1"],
    )
    aws_is_configured: bool = Field(
        SettingsDefaults.AWS_IS_CONFIGURED,
        description="True if AWS is configured. This is determined by the presence of either AWS_PROFILE or both AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY.",
    )
    aws_eks_cluster_name: str = Field(
        SettingsDefaults.AWS_EKS_CLUSTER_NAME,
        description="The name of the AWS EKS cluster used for hosting applications.",
        examples=["apps-hosting-service"],
    )
    aws_db_instance_identifier: str = Field(
        SettingsDefaults.AWS_RDS_DB_INSTANCE_IDENTIFIER,
        description="The RDS database instance identifier used for the platform's primary database.",
        examples=["apps-hosting-service"],
    )
    anthropic_api_key: SecretStr = Field(
        SettingsDefaults.ANTHROPIC_API_KEY,
        description="The API key for Anthropic services. Masked by pydantic SecretStr.",
        examples=["sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"],
    )
    environment: str = Field(
        SettingsDefaults.ENVIRONMENT,
        description="The deployment environment for the platform.",
        examples=SmarterEnvironments.all,
    )
    fernet_encryption_key: str = Field(
        SettingsDefaults.FERNET_ENCRYPTION_KEY,
        description="The Fernet encryption key used for encrypting Smarter Secrets data.",
        examples=["gAAAAABh..."],
    )
    local_hosts: List[str] = Field(
        SettingsDefaults.LOCAL_HOSTS,
        description="A list of hostnames considered local for development and testing purposes.",
        examples=SettingsDefaults.LOCAL_HOSTS,
    )
    root_domain: str = Field(
        SettingsDefaults.ROOT_DOMAIN,
        description="The root domain for the platform.",
        examples=["example.com"],
    )
    init_info: Optional[str] = Field(
        None,
    )
    google_maps_api_key: SecretStr = Field(
        SettingsDefaults.GOOGLE_MAPS_API_KEY,
        description="The API key for Google Maps services. Masked by pydantic SecretStr. Used for geocoding, maps, and places APIs, for the OpenAI get_weather() example function.",
        examples=["AIzaSy..."],
    )
    google_service_account: dict = Field(
        SettingsDefaults.GOOGLE_SERVICE_ACCOUNT,
        description="The Google service account credentials as a dictionary. Used for Google Cloud services integration.",
        examples=[{"type": "service_account", "project_id": "my-project", "...": "..."}],
    )
    gemini_api_key: SecretStr = Field(
        SettingsDefaults.GEMINI_API_KEY,
        description="The API key for Google Gemini services. Masked by pydantic SecretStr.",
        examples=["sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"],
    )
    llama_api_key: SecretStr = Field(
        SettingsDefaults.LLAMA_API_KEY,
        description="The API key for LLaMA services. Masked by pydantic SecretStr.",
        examples=["sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"],
    )
    smarter_mysql_test_database_secret_name: Optional[str] = Field(
        SettingsDefaults.SMARTER_MYSQL_TEST_DATABASE_SECRET_NAME,
        description="The secret name for the Smarter MySQL test database. Used for example Smarter Plugins that are pre-installed on new installations.",
        examples=["smarter-mysql-test-db-secret"],
    )
    smarter_mysql_test_database_password: Optional[str] = Field(
        SettingsDefaults.SMARTER_MYSQL_TEST_DATABASE_PASSWORD,
        description="The password for the Smarter MySQL test database. Used for example Smarter Plugins that are pre-installed on new installations.",
        examples=["your_password_here"],
    )
    social_auth_google_oauth2_key: SecretStr = Field(
        SettingsDefaults.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY,
        description="The OAuth2 key for Google social authentication. Masked by pydantic SecretStr.",
        examples=["your-google-oauth2-key"],
    )
    social_auth_google_oauth2_secret: SecretStr = Field(
        SettingsDefaults.SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET,
        description="The OAuth2 secret for Google social authentication. Masked by pydantic SecretStr.",
        examples=["your-google-oauth2-secret"],
    )
    social_auth_github_key: SecretStr = Field(
        SettingsDefaults.SOCIAL_AUTH_GITHUB_KEY,
        description="The OAuth2 key for GitHub social authentication. Masked by pydantic SecretStr.",
        examples=["your-github-oauth2-key"],
    )
    social_auth_github_secret: SecretStr = Field(
        SettingsDefaults.SOCIAL_AUTH_GITHUB_SECRET,
        description="The OAuth2 secret for GitHub social authentication. Masked by pydantic SecretStr.",
        examples=["your-github-oauth2-secret"],
    )
    social_auth_linkedin_oauth2_key: SecretStr = Field(
        SettingsDefaults.SOCIAL_AUTH_LINKEDIN_OAUTH2_KEY,
        description="The OAuth2 key for LinkedIn social authentication. Masked by pydantic SecretStr.",
        examples=["your-linkedin-oauth2-key"],
    )
    social_auth_linkedin_oauth2_secret: SecretStr = Field(
        SettingsDefaults.SOCIAL_AUTH_LINKEDIN_OAUTH2_SECRET,
        description="The OAuth2 secret for LinkedIn social authentication. Masked by pydantic SecretStr.",
        examples=["your-linkedin-oauth2-secret"],
    )
    langchain_memory_key: Optional[str] = Field(SettingsDefaults.LANGCHAIN_MEMORY_KEY)
    logo: Optional[str] = Field(SettingsDefaults.LOGO)
    mailchimp_api_key: Optional[SecretStr] = Field(SettingsDefaults.MAILCHIMP_API_KEY)
    mailchimp_list_id: Optional[str] = Field(SettingsDefaults.MAILCHIMP_LIST_ID)
    marketing_site_url: Optional[str] = Field(SettingsDefaults.MARKETING_SITE_URL)
    openai_api_organization: Optional[str] = Field(
        SettingsDefaults.OPENAI_API_ORGANIZATION,
        description="The OpenAI API organization ID.",
        examples=["org-xxxxxxxxxxxxxxxx"],
    )
    openai_api_key: SecretStr = Field(
        SettingsDefaults.OPENAI_API_KEY,
        description="The API key for OpenAI services. Masked by pydantic SecretStr.",
        examples=["sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"],
    )
    openai_endpoint_image_n: Optional[int] = Field(
        SettingsDefaults.OPENAI_ENDPOINT_IMAGE_N,
        description="The number of images to generate per request to the OpenAI image endpoint.",
        examples=[1, 2, 4],
    )
    openai_endpoint_image_size: Optional[str] = Field(
        SettingsDefaults.OPENAI_ENDPOINT_IMAGE_SIZE,
        description="The size of images to generate from the OpenAI image endpoint.",
        examples=["256x256", "512x512", "1024x768"],
    )
    llm_default_provider: str = Field(
        SettingsDefaults.LLM_DEFAULT_PROVIDER,
        description="The default LLM provider to use for language model interactions.",
        examples=["openai", "anthropic", "gemini", "llama"],
    )
    llm_default_model: str = Field(
        SettingsDefaults.LLM_DEFAULT_MODEL,
        description="The default LLM model to use for language model interactions.",
        examples=["gpt-4o-mini", "claude-2", "gemini"],
    )
    llm_default_system_role: str = Field(
        SettingsDefaults.LLM_DEFAULT_SYSTEM_ROLE,
        description="The default system role prompt to use for language model interactions.",
        examples=["You are a helpful chatbot..."],
    )
    llm_default_temperature: float = Field(
        SettingsDefaults.LLM_DEFAULT_TEMPERATURE,
        description="The default temperature to use for language model interactions.",
        examples=[0.0, 0.5, 1.0],
    )
    llm_default_max_tokens: int = Field(
        SettingsDefaults.LLM_DEFAULT_MAX_TOKENS,
        description="The default maximum number of tokens to generate for language model interactions.",
        examples=[256, 512, 1024, 2048],
    )
    pinecone_api_key: SecretStr = Field(
        SettingsDefaults.PINECONE_API_KEY,
        description="The API key for Pinecone services. Masked by pydantic SecretStr.",
        examples=["xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"],
    )
    stripe_live_secret_key: Optional[str] = Field(
        SettingsDefaults.STRIPE_LIVE_SECRET_KEY,
        description="DEPRECATED: The secret key for Stripe live environment.",
        examples=["sk_live_xxxxxxxxxxxxxxxxxxxxxxxx"],
    )
    stripe_test_secret_key: Optional[str] = Field(
        SettingsDefaults.STRIPE_TEST_SECRET_KEY,
        description="DEPRECATED: The secret key for Stripe test environment.",
        examples=["sk_test_xxxxxxxxxxxxxxxxxxxxxxxx"],
    )

    secret_key: Optional[str] = Field(
        SettingsDefaults.SECRET_KEY,
        description="The Django secret key for cryptographic signing.",
        examples=["your-django-secret-key"],
    )

    smtp_sender: Optional[str] = Field(
        SettingsDefaults.SMTP_SENDER,
        description="The sender email address for SMTP emails.",
        examples=["sender@example.com"],
    )
    smtp_from_email: Optional[str] = Field(
        SettingsDefaults.SMTP_FROM_EMAIL,
        description="The from email address for SMTP emails.",
        examples=["from@example.com"],
    )
    smtp_host: Optional[str] = Field(
        SettingsDefaults.SMTP_HOST,
        description="The SMTP host address for sending emails.",
        examples=["smtp.example.com"],
    )
    smtp_password: Optional[str] = Field(
        SettingsDefaults.SMTP_PASSWORD,
        description="The SMTP password for authentication.",
        examples=["your-smtp-password"],
    )
    smtp_port: Optional[int] = Field(
        SettingsDefaults.SMTP_PORT,
        description="The SMTP port for sending emails.",
        examples=[25, 465, 587],
    )
    smtp_use_ssl: Optional[bool] = Field(
        SettingsDefaults.SMTP_USE_SSL,
        description="Whether to use SSL for SMTP connections.",
        examples=[True, False],
    )
    smtp_use_tls: Optional[bool] = Field(
        SettingsDefaults.SMTP_USE_TLS,
        description="Whether to use TLS for SMTP connections.",
        examples=[True, False],
    )
    smtp_username: Optional[str] = Field(
        SettingsDefaults.SMTP_USERNAME,
        description="The SMTP username for authentication.",
        examples=["your-smtp-username"],
    )

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
            - SMARTER_PLATFORM_SUBDOMAIN
            - smarter_settings.environment_platform_domain
            - smarter_settings.environment
            - SMARTER_PLATFORM_SUBDOMAIN
            - SmarterEnvironments()
        """
        if self.environment == SmarterEnvironments.LOCAL:
            return f"cdn.{SmarterEnvironments.ALPHA}.{SMARTER_PLATFORM_SUBDOMAIN}.{self.root_domain}"
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
    def root_platform_domain(self) -> str:
        """
        Return the platform domain name for the root domain.

        Example:
            >>> print(smarter_settings.root_platform_domain)
            'platform.example.com'

        See Also:
            - SMARTER_PLATFORM_SUBDOMAIN
            - smarter_settings.root_domain
        """
        return f"{SMARTER_PLATFORM_SUBDOMAIN}.{self.root_domain}"

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
            - SMARTER_PLATFORM_SUBDOMAIN
            - SMARTER_API_SUBDOMAIN
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
            SMARTER_PLATFORM_SUBDOMAIN,
            SMARTER_API_SUBDOMAIN,
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
            - SMARTER_PLATFORM_SUBDOMAIN
            - smarter_settings.platform_name
            - smarter_settings.environment
        """
        return f"{self.platform_name}-{SMARTER_PLATFORM_SUBDOMAIN}-{settings.environment}"

    @property
    def root_api_domain(self) -> str:
        """
        Return the root API domain name, generated
        from the system constant `SMARTER_API_SUBDOMAIN` and the root platform domain.

        Example:
            >>> print(smarter_settings.root_api_domain)
            'api.platform.example.com'

        See Also:
            - SMARTER_API_SUBDOMAIN
            - smarter_settings.root_domain
        """
        return f"{SMARTER_API_SUBDOMAIN}.{self.root_domain}"

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
            Changing this value requires a platform redeploy and could invalidate existing API keys.
            Expired API keys still function but will log warnings.

        See Also:
            - SMARTER_API_KEY_MAX_LIFETIME_DAYS
        """
        return SMARTER_API_KEY_MAX_LIFETIME_DAYS

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
    def validate_shared_resource_identifier(cls, v) -> str:
        """Validate shared_resource_identifier"""
        if v in [None, ""]:
            return SettingsDefaults.SHARED_RESOURCE_IDENTIFIER
        return v

    @field_validator("aws_profile")
    def validate_aws_profile(cls, v) -> Optional[str]:
        """Validate aws_profile"""
        if v in [None, ""]:
            return SettingsDefaults.AWS_PROFILE
        return v

    @field_validator("aws_access_key_id")
    def validate_aws_access_key_id(cls, v, values: ValidationInfo) -> SecretStr:
        """Validate aws_access_key_id"""
        if not isinstance(v, SecretStr):
            v = SecretStr(v)
        if v.get_secret_value() in [None, ""]:
            return SettingsDefaults.AWS_ACCESS_KEY_ID
        aws_profile = values.data.get("aws_profile", None)
        if aws_profile and len(aws_profile) > 0 and aws_profile != SettingsDefaults.AWS_PROFILE:
            # pylint: disable=logging-fstring-interpolation
            logger.warning(f"aws_access_key_id is being ignored. using aws_profile {aws_profile}.")
            return SettingsDefaults.AWS_ACCESS_KEY_ID
        return v

    @field_validator("aws_secret_access_key")
    def validate_aws_secret_access_key(cls, v, values: ValidationInfo) -> SecretStr:
        """Validate aws_secret_access_key"""
        if not isinstance(v, SecretStr):
            v = SecretStr(v)
        if v.get_secret_value() in [None, ""]:
            return SettingsDefaults.AWS_SECRET_ACCESS_KEY
        aws_profile = values.data.get("aws_profile", None)
        if aws_profile and len(aws_profile) > 0 and aws_profile != SettingsDefaults.AWS_PROFILE:
            # pylint: disable=logging-fstring-interpolation
            logger.warning(f"aws_secret_access_key is being ignored. using aws_profile {aws_profile}.")
            return SettingsDefaults.AWS_SECRET_ACCESS_KEY
        return v

    @field_validator("aws_region")
    def validate_aws_region(cls, v, values: ValidationInfo, **kwargs) -> Optional[str]:
        """Validate aws_region"""
        valid_regions = values.data.get("aws_regions", ["us-east-1"])
        if v in [None, ""]:
            return SettingsDefaults.AWS_REGION
        if v not in valid_regions:
            raise SmarterValueError(f"aws_region {v} not in aws_regions: {valid_regions}")
        return v

    @field_validator("environment")
    def validate_environment(cls, v) -> Optional[str]:
        """Validate environment"""
        if v in [None, ""]:
            return SettingsDefaults.ENVIRONMENT
        return v

    @field_validator("fernet_encryption_key")
    def validate_fernet_encryption_key(cls, v) -> Optional[str]:
        """Validate fernet_encryption_key"""

        if v in [None, ""]:
            return SettingsDefaults.FERNET_ENCRYPTION_KEY

        if v == DEFAULT_MISSING_VALUE:
            return v

        try:
            # Decode the key using URL-safe base64
            decoded_key = base64.urlsafe_b64decode(v)
            # Ensure the decoded key is exactly 32 bytes
            if len(decoded_key) != 32:
                raise ValueError("Fernet key must be exactly 32 bytes when decoded.")
        except (TypeError, ValueError, base64.binascii.Error) as e:  # type: ignore[catch-base-exception]
            raise SmarterValueError(f"Invalid Fernet encryption key: {v}. Error: {e}") from e

        return v

    @field_validator("local_hosts")
    def validate_local_hosts(cls, v) -> List[str]:
        """Validate local_hosts"""
        if v in [None, ""]:
            return SettingsDefaults.LOCAL_HOSTS
        return v

    @field_validator("root_domain")
    def validate_aws_apigateway_root_domain(cls, v) -> str:
        """Validate root_domain"""
        if v in [None, ""]:
            return SettingsDefaults.ROOT_DOMAIN
        return v

    @field_validator("aws_eks_cluster_name")
    def validate_aws_eks_cluster_name(cls, v) -> str:
        """Validate aws_eks_cluster_name"""
        if v in [None, ""]:
            return SettingsDefaults.AWS_EKS_CLUSTER_NAME
        return v

    @field_validator("aws_db_instance_identifier")
    def validate_aws_db_instance_identifier(cls, v) -> str:
        """Validate aws_db_instance_identifier"""
        if v in [None, ""]:
            return SettingsDefaults.AWS_RDS_DB_INSTANCE_IDENTIFIER
        return v

    @field_validator("anthropic_api_key")
    def validate_anthropic_api_key(cls, v) -> SecretStr:
        """Validate anthropic_api_key"""
        if v in [None, ""]:
            return SettingsDefaults.ANTHROPIC_API_KEY
        return v

    @field_validator("debug_mode")
    def parse_debug_mode(cls, v) -> bool:
        """Parse debug_mode"""
        if isinstance(v, bool):
            return v
        if v in [None, ""]:
            return SettingsDefaults.DEBUG_MODE
        return v.lower() in ["true", "1", "t", "y", "yes"]

    @field_validator("dump_defaults")
    def parse_dump_defaults(cls, v) -> bool:
        """Parse dump_defaults"""
        if isinstance(v, bool):
            return v
        if v in [None, ""]:
            return SettingsDefaults.DUMP_DEFAULTS
        return v.lower() in ["true", "1", "t", "y", "yes"]

    @field_validator("google_maps_api_key")
    def check_google_maps_api_key(cls, v) -> SecretStr:
        """Check google_maps_api_key"""
        if str(v) in [None, ""]:
            return SettingsDefaults.GOOGLE_MAPS_API_KEY
        return v

    @field_validator("google_service_account")
    def check_google_service_account(cls, v) -> dict:
        """Check google_service_account"""
        if v in [None, {}]:
            return SettingsDefaults.GOOGLE_SERVICE_ACCOUNT
        return v

    @field_validator("gemini_api_key")
    def check_gemini_api_key(cls, v) -> SecretStr:
        """Check gemini_api_key"""
        if str(v) in [None, ""]:
            return SettingsDefaults.GEMINI_API_KEY
        return v

    @field_validator("llama_api_key")
    def check_llama_api_key(cls, v) -> SecretStr:
        """Check llama_api_key"""
        if str(v) in [None, ""]:
            return SettingsDefaults.LLAMA_API_KEY
        return v

    @field_validator("social_auth_google_oauth2_key")
    def check_social_auth_google_oauth2_key(cls, v) -> SecretStr:
        """Check social_auth_google_oauth2_key"""
        if v in [None, ""] and SettingsDefaults.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY:
            return SettingsDefaults.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY
        return v

    @field_validator("social_auth_google_oauth2_secret")
    def check_social_auth_google_oauth2_secret(cls, v) -> SecretStr:
        """Check social_auth_google_oauth2_secret"""
        if v in [None, ""] and SettingsDefaults.SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET is not None:
            return SettingsDefaults.SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET
        return v

    @field_validator("social_auth_github_key")
    def check_social_auth_github_key(cls, v) -> SecretStr:
        """Check social_auth_github_key"""
        if v in [None, ""] and SettingsDefaults.SOCIAL_AUTH_GITHUB_KEY is not None:
            return SettingsDefaults.SOCIAL_AUTH_GITHUB_KEY
        return v

    @field_validator("social_auth_github_secret")
    def check_social_auth_github_secret(cls, v) -> SecretStr:
        """Check social_auth_github_secret"""
        if v in [None, ""]:
            return SettingsDefaults.SOCIAL_AUTH_GITHUB_SECRET
        return v

    @field_validator("social_auth_linkedin_oauth2_key")
    def check_social_auth_linkedin_oauth2_key(cls, v) -> SecretStr:
        """Check social_auth_linkedin_oauth2_key"""
        if v in [None, ""]:
            return SettingsDefaults.SOCIAL_AUTH_LINKEDIN_OAUTH2_KEY
        return v

    @field_validator("social_auth_linkedin_oauth2_secret")
    def check_social_auth_linkedin_oauth2_secret(cls, v) -> SecretStr:
        """Check social_auth_linkedin_oauth2_secret"""
        if v in [None, ""]:
            return SettingsDefaults.SOCIAL_AUTH_LINKEDIN_OAUTH2_SECRET
        return v

    @field_validator("langchain_memory_key")
    def check_langchain_memory_key(cls, v) -> str:
        """Check langchain_memory_key"""
        if v in [None, ""] and SettingsDefaults.LANGCHAIN_MEMORY_KEY:
            return SettingsDefaults.LANGCHAIN_MEMORY_KEY
        return str(v)

    @field_validator("logo")
    def check_logo(cls, v) -> str:
        """Check logo"""
        if v in [None, ""]:
            return SettingsDefaults.LOGO
        return v

    @field_validator("mailchimp_api_key")
    def check_mailchimp_api_key(cls, v) -> SecretStr:
        """Check mailchimp_api_key"""
        if v in [None, ""] and SettingsDefaults.MAILCHIMP_API_KEY is not None:
            return SettingsDefaults.MAILCHIMP_API_KEY
        return v

    @field_validator("mailchimp_list_id")
    def check_mailchimp_list_id(cls, v) -> Optional[str]:
        """Check mailchimp_list_id"""
        if v in [None, ""]:
            return SettingsDefaults.MAILCHIMP_LIST_ID
        return v

    @field_validator("marketing_site_url")
    def check_marketing_site_url(cls, v) -> str:
        """Check marketing_site_url. example: https://example.com"""
        if v in [None, ""]:
            return SettingsDefaults.MARKETING_SITE_URL
        SmarterValidator.validate_url(v)
        return v

    @field_validator("openai_api_organization")
    def check_openai_api_organization(cls, v) -> Optional[str]:
        """Check openai_api_organization"""
        if v in [None, ""]:
            return SettingsDefaults.OPENAI_API_ORGANIZATION
        return v

    @field_validator("openai_api_key")
    def check_openai_api_key(cls, v) -> SecretStr:
        """Check openai_api_key"""
        if v in [None, ""]:
            return SettingsDefaults.OPENAI_API_KEY
        return v

    @field_validator("openai_endpoint_image_n")
    def check_openai_endpoint_image_n(cls, v) -> int:
        """Check openai_endpoint_image_n"""
        if isinstance(v, int):
            return v
        if v in [None, ""]:
            return SettingsDefaults.OPENAI_ENDPOINT_IMAGE_N
        return int(v)

    @field_validator("openai_endpoint_image_size")
    def check_openai_endpoint_image_size(cls, v) -> str:
        """Check openai_endpoint_image_size"""
        if v in [None, ""]:
            return SettingsDefaults.OPENAI_ENDPOINT_IMAGE_SIZE
        return v

    @field_validator("llm_default_model")
    def check_openai_default_model(cls, v) -> str:
        """Check llm_default_model"""
        if v in [None, ""]:
            return SettingsDefaults.LLM_DEFAULT_MODEL
        return v

    @field_validator("llm_default_provider")
    def check_openai_default_provider(cls, v) -> str:
        """Check llm_default_provider"""
        if v in [None, ""]:
            return SettingsDefaults.LLM_DEFAULT_PROVIDER
        return v

    @field_validator("llm_default_system_role")
    def check_openai_default_system_prompt(cls, v) -> str:
        """Check llm_default_system_role"""
        if v in [None, ""]:
            return SettingsDefaults.LLM_DEFAULT_SYSTEM_ROLE
        return v

    @field_validator("llm_default_temperature")
    def check_openai_default_temperature(cls, v) -> float:
        """Check llm_default_temperature"""
        if isinstance(v, float):
            return v
        if v in [None, ""]:
            return SettingsDefaults.LLM_DEFAULT_TEMPERATURE
        return float(v)

    @field_validator("llm_default_max_tokens")
    def check_openai_default_max_completion_tokens(cls, v) -> int:
        """Check llm_default_max_tokens"""
        if isinstance(v, int):
            return v
        if v in [None, ""]:
            return SettingsDefaults.LLM_DEFAULT_MAX_TOKENS
        return int(v)

    @field_validator("pinecone_api_key")
    def check_pinecone_api_key(cls, v) -> SecretStr:
        """Check pinecone_api_key"""
        if v in [None, ""]:
            return SettingsDefaults.PINECONE_API_KEY
        return v

    @field_validator("stripe_live_secret_key")
    def check_stripe_live_secret_key(cls, v) -> str:
        """Check stripe_live_secret_key"""
        if v in [None, ""]:
            warnings.warn(
                "The 'stripe_live_secret_key' field is deprecated and will be removed in a future release.",
                DeprecationWarning,
                stacklevel=2,
            )
            return SettingsDefaults.STRIPE_LIVE_SECRET_KEY
        return v

    @field_validator("stripe_test_secret_key")
    def check_stripe_test_secret_key(cls, v) -> str:
        """Check stripe_test_secret_key"""
        if v in [None, ""]:
            warnings.warn(
                "The 'stripe_live_secret_key' field is deprecated and will be removed in a future release.",
                DeprecationWarning,
                stacklevel=2,
            )
            return SettingsDefaults.STRIPE_TEST_SECRET_KEY
        return v

    @field_validator("secret_key")
    def check_secret_key(cls, v) -> str:
        """Check secret_key"""
        if v in [None, ""] and SettingsDefaults.SECRET_KEY is not None:
            return SettingsDefaults.SECRET_KEY
        return v

    @field_validator("smtp_sender")
    def check_smtp_sender(cls, v) -> Optional[str]:
        """Check smtp_sender"""
        if v in [None, ""]:
            v = SettingsDefaults.SMTP_SENDER
            SmarterValidator.validate_domain(v)
        return v

    @field_validator("smtp_from_email")
    def check_smtp_from_email(cls, v) -> str:
        """Check smtp_from_email"""
        if v in [None, ""]:
            v = SettingsDefaults.SMTP_FROM_EMAIL
        if v not in [None, ""]:
            SmarterValidator.validate_email(v)
        return v

    @field_validator("smtp_host")
    def check_smtp_host(cls, v) -> str:
        """Check smtp_host"""
        if v in [None, ""]:
            v = SettingsDefaults.SMTP_HOST
            SmarterValidator.validate_domain(v)
        return v

    @field_validator("smtp_password")
    def check_smtp_password(cls, v) -> str:
        """Check smtp_password"""
        if v in [None, ""]:
            return SettingsDefaults.SMTP_PASSWORD
        return v

    @field_validator("smtp_port")
    def check_smtp_port(cls, v) -> int:
        """Check smtp_port"""
        if v in [None, ""]:
            v = SettingsDefaults.SMTP_PORT
        if not str(v).isdigit() or not 1 <= int(v) <= 65535:
            raise SmarterValueError("Invalid port number")
        return int(v)

    @field_validator("smtp_use_ssl")
    def check_smtp_use_ssl(cls, v) -> bool:
        """Check smtp_use_ssl"""
        if v in [None, ""]:
            return SettingsDefaults.SMTP_USE_SSL
        return v

    @field_validator("smtp_use_tls")
    def check_smtp_use_tls(cls, v) -> bool:
        """Check smtp_use_tls"""
        if v in [None, ""]:
            return SettingsDefaults.SMTP_USE_TLS
        return v

    @field_validator("smtp_username")
    def check_smtp_username(cls, v) -> str:
        """Check smtp_username"""
        if v in [None, ""]:
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
