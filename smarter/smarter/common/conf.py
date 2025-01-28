# pylint: disable=no-member,no-self-argument,unused-argument,R0801,too-many-lines
"""
Configuration for Lambda functions.

This module is used to configure the Lambda functions. It uses the pydantic_settings
library to validate the configuration values. The configuration values are initialized
according to the following prioritization sequence:
    1. constructor
    2. environment variables
    3. `.env` file
    4. tfvars file
    5. defaults

The Settings class also provides a dump property that returns a dictionary of all
configuration values. This is useful for debugging and logging.
"""

# -------------------- WARNING --------------------
# DO NOT IMPORT DJANGO OR ANY DJANGO MODULES. THIS
# ENTIRE MODULE SITS UPSTREAM OF DJANGO AND IS
# INTENDED TO BE USED INDEPENDENTLY OF DJANGO.
# ------------------------------------------------

# python stuff
import logging
import os  # library for interacting with the operating system
import platform  # library to view information about the server host this module runs on
import re
from typing import Any, List, Optional, Tuple, Union

# 3rd party stuff
import boto3  # AWS SDK for Python https://boto3.amazonaws.com/v1/documentation/api/latest/index.html
import pkg_resources
from botocore.exceptions import NoCredentialsError, ProfileNotFound
from dotenv import load_dotenv
from pydantic import Field, SecretStr, ValidationError, ValidationInfo, field_validator
from pydantic_settings import BaseSettings

from ..lib.django.validators import SmarterValidator

# our stuff
from .const import (
    IS_USING_TFVARS,
    SMARTER_CUSTOMER_API_SUBDOMAIN,
    SMARTER_CUSTOMER_PLATFORM_SUBDOMAIN,
    TFVARS,
    VERSION,
    SmarterEnvironments,
)
from .exceptions import SmarterConfigurationError, SmarterValueError
from .utils import recursive_sort_dict


logger = logging.getLogger(__name__)
TFVARS = TFVARS or {}
DOT_ENV_LOADED = load_dotenv()


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
            raise SmarterConfigurationError(f"{service} is not enabled. See conf.Services")

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


# pylint: disable=too-few-public-methods
class SettingsDefaults:
    """
    Default values for Settings. This takes care of most of what we're interested in.
    It initializes from the following prioritization sequence:
      1. environment variables
      2. tfvars
      3. defaults.
    """

    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", None)

    LLM_DEFAULT_PROVIDER = "openai"
    LLM_DEFAULT_MODEL = "gpt-4-turbo"
    LLM_DEFAULT_SYSTEM_ROLE = (
        "You are a helpful chatbot. When given the opportunity to utilize "
        "function calling, you should always do so. This will allow you to "
        "provide the best possible responses to the user. If you are unable to "
        "provide a response, you should prompt the user for more information. If "
        "you are still unable to provide a response, you should inform the user "
        "that you are unable to help them at this time."
    )
    LLM_DEFAULT_TEMPERATURE = 0.5
    LLM_DEFAULT_MAX_TOKENS = 256

    # defaults for this Python package
    ENVIRONMENT = os.environ.get("ENVIRONMENT", TFVARS.get("environment", SmarterEnvironments.LOCAL))
    ROOT_DOMAIN = os.environ.get("ROOT_DOMAIN", TFVARS.get("root_domain", "example.com"))
    SHARED_RESOURCE_IDENTIFIER = os.environ.get(
        "SHARED_RESOURCE_IDENTIFIER", TFVARS.get("shared_resource_identifier", "smarter")
    )
    DEBUG_MODE: bool = os.environ.get("DEBUG_MODE", bool(TFVARS.get("debug_mode", True)))
    DUMP_DEFAULTS: bool = os.environ.get("DUMP_DEFAULTS", bool(TFVARS.get("dump_defaults", True)))

    # aws auth
    AWS_PROFILE = os.environ.get("AWS_PROFILE", TFVARS.get("aws_profile", None))
    AWS_ACCESS_KEY_ID = SecretStr(os.environ.get("AWS_ACCESS_KEY_ID", TFVARS.get("aws_access_key_id", None)))
    AWS_SECRET_ACCESS_KEY = SecretStr(
        os.environ.get("AWS_SECRET_ACCESS_KEY", TFVARS.get("aws_secret_access_key", None))
    )
    AWS_REGION = os.environ.get("AWS_REGION", TFVARS.get("aws_region", "us-east-1"))

    # aws api gateway defaults
    AWS_APIGATEWAY_CREATE_CUSTOM_DOMAIN = TFVARS.get("create_custom_domain", False)
    AWS_APIGATEWAY_READ_TIMEOUT: int = TFVARS.get("aws_apigateway_read_timeout", 70)
    AWS_APIGATEWAY_CONNECT_TIMEOUT: int = TFVARS.get("aws_apigateway_connect_timeout", 70)
    AWS_APIGATEWAY_MAX_ATTEMPTS: int = TFVARS.get("aws_apigateway_max_attempts", 10)

    AWS_EKS_CLUSTER_NAME = os.environ.get(
        "AWS_EKS_CLUSTER_NAME", TFVARS.get("aws_eks_cluster_name", "apps-hosting-service")
    )
    AWS_RDS_DB_INSTANCE_IDENTIFIER = os.environ.get("AWS_RDS_DB_INSTANCE_IDENTIFIER", "apps-hosting-service")

    GOOGLE_MAPS_API_KEY: str = os.environ.get(
        "GOOGLE_MAPS_API_KEY",
        TFVARS.get("google_maps_api_key", None) or os.environ.get("TF_VAR_GOOGLE_MAPS_API_KEY", None),
    )
    GEMINI_API_KEY: str = os.environ.get("GEMINI_API_KEY", None)
    LLAMA_API_KEY: str = os.environ.get("LLAMA_API_KEY", None)

    # -------------------------------------------------------------------------
    # see: https://console.cloud.google.com/apis/credentials/oauthclient/231536848926-egabg8jas321iga0nmleac21ccgbg6tq.apps.googleusercontent.com?project=smarter-sh
    # -------------------------------------------------------------------------
    SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.environ.get(
        "SOCIAL_AUTH_GOOGLE_OAUTH2_KEY",
        TFVARS.get("social_auth_google_oauth2_key", None) or os.environ.get("SOCIAL_AUTH_GOOGLE_OAUTH2_KEY", None),
    )
    SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.environ.get(
        "SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET",
        TFVARS.get("social_auth_google_oauth2_secret", None)
        or os.environ.get("SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET", None),
    )
    # -------------------------------------------------------------------------
    # see: https://github.com/settings/applications/2620957
    # -------------------------------------------------------------------------
    SOCIAL_AUTH_GITHUB_KEY = os.environ.get(
        "SOCIAL_AUTH_GITHUB_KEY",
        TFVARS.get("social_auth_github_key", None) or os.environ.get("SOCIAL_AUTH_GITHUB_KEY", None),
    )
    SOCIAL_AUTH_GITHUB_SECRET = os.environ.get(
        "SOCIAL_AUTH_GITHUB_SECRET",
        TFVARS.get("social_auth_github_secret", None) or os.environ.get("SOCIAL_AUTH_GITHUB_SECRET", None),
    )
    # -------------------------------------------------------------------------
    # see:  https://www.linkedin.com/developers/apps/221422881/settings
    #       https://www.linkedin.com/developers/apps/221422881/products?refreshKey=1734980684455
    # verification url: https://www.linkedin.com/developers/apps/verification/3ac34414-09a4-433b-983a-0d529fa486f1
    # -------------------------------------------------------------------------
    SOCIAL_AUTH_LINKEDIN_OAUTH2_KEY = os.environ.get(
        "SOCIAL_AUTH_LINKEDIN_OAUTH2_KEY",
        TFVARS.get("social_auth_linkedin_oauth2_key", None) or os.environ.get("SOCIAL_AUTH_LINKEDIN_OAUTH2_KEY", None),
    )
    SOCIAL_AUTH_LINKEDIN_OAUTH2_SECRET = os.environ.get(
        "SOCIAL_AUTH_LINKEDIN_OAUTH2_SECRET",
        TFVARS.get("social_auth_linkedin_oauth2_secret", None)
        or os.environ.get("SOCIAL_AUTH_LINKEDIN_OAUTH2_SECRET", None),
    )

    LANGCHAIN_MEMORY_KEY = os.environ.get("LANGCHAIN_MEMORY_KEY", "chat_history")

    MAILCHIMP_API_KEY = os.environ.get("MAILCHIMP_API_KEY", None)
    MAILCHIMP_LIST_ID = os.environ.get("MAILCHIMP_LIST_ID", None)

    MARKETING_SITE_URL: str = os.environ.get("OPENAI_API_ORGANIZATION", "https://smarter.sh")
    LOGO: str = os.environ.get(
        "OPENAI_API_ORGANIZATION", "https://smarter.sh/wp-content/uploads/2024/04/Smarter_crop.png"
    )

    OPENAI_API_ORGANIZATION: str = os.environ.get("OPENAI_API_ORGANIZATION", None)
    OPENAI_API_KEY = SecretStr(os.environ.get("TF_VAR_OPENAI_API_KEY", None))
    OPENAI_ENDPOINT_IMAGE_N = 4
    OPENAI_ENDPOINT_IMAGE_SIZE = "1024x768"
    PINECONE_API_KEY = SecretStr(None)

    SECRET_KEY = os.getenv("SECRET_KEY")

    SMTP_SENDER = os.environ.get("SMTP_SENDER", None)
    SMTP_FROM_EMAIL = os.environ.get("SMTP_FROM_EMAIL", None)
    SMTP_HOST = os.environ.get("SMTP_HOST", "email-smtp.us-east-2.amazonaws.com")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
    SMTP_USE_SSL = bool(os.environ.get("SMTP_USE_SSL", False))
    SMTP_USE_TLS = bool(os.environ.get("SMTP_USE_TLS", True))
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "SET-ME-PLEASE")
    SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "SET-ME-PLEASE")

    STRIPE_LIVE_SECRET_KEY = os.environ.get("STRIPE_LIVE_SECRET_KEY", "SET-ME-PLEASE")
    STRIPE_TEST_SECRET_KEY = os.environ.get("STRIPE_TEST_SECRET_KEY", "SET-ME-PLEASE")

    LOCAL_HOSTS = ["localhost", "127.0.0.1"]
    LOCAL_HOSTS += [host + ":8000" for host in LOCAL_HOSTS]
    LOCAL_HOSTS.append("testserver")

    @classmethod
    def to_dict(cls):
        """Convert SettingsDefaults to dict"""
        return {
            key: "***MASKED***" if key in ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"] else value
            for key, value in SettingsDefaults.__dict__.items()
            if not key.startswith("__") and not callable(key) and key != "to_dict"
        }


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
    """Settings for Lambda functions"""

    # pylint: disable=too-few-public-methods
    class Config:
        """Pydantic configuration"""

        frozen = True

    _aws_access_key_id_source: str = "unset"
    _aws_secret_access_key_source: str = "unset"
    _dump: dict = None

    # pylint: disable=too-many-branches,too-many-statements
    def __init__(self, **data: Any):  # noqa: C901
        super().__init__(**data)

        if self.debug_mode:
            logger.setLevel(logging.DEBUG)

        # pylint: disable=logging-fstring-interpolation
        logger.debug("Settings initialized")

    shared_resource_identifier: Optional[str] = Field(
        SettingsDefaults.SHARED_RESOURCE_IDENTIFIER, env="SHARED_RESOURCE_IDENTIFIER"
    )
    debug_mode: Optional[bool] = Field(
        SettingsDefaults.DEBUG_MODE,
        env="DEBUG_MODE",
        pre=True,
        getter=lambda v: empty_str_to_bool_default(v, SettingsDefaults.DEBUG_MODE),
    )
    dump_defaults: Optional[bool] = Field(
        SettingsDefaults.DUMP_DEFAULTS,
        env="DUMP_DEFAULTS",
        pre=True,
        getter=lambda v: empty_str_to_bool_default(v, SettingsDefaults.DUMP_DEFAULTS),
    )
    aws_profile: Optional[str] = Field(
        SettingsDefaults.AWS_PROFILE,
        env="AWS_PROFILE",
    )
    aws_access_key_id: Optional[SecretStr] = Field(
        SettingsDefaults.AWS_ACCESS_KEY_ID,
        env="AWS_ACCESS_KEY_ID",
    )
    aws_secret_access_key: Optional[SecretStr] = Field(
        SettingsDefaults.AWS_SECRET_ACCESS_KEY,
        env="AWS_SECRET_ACCESS_KEY",
    )
    aws_regions: Optional[List[str]] = Field(AWS_REGIONS, description="The list of AWS regions")
    aws_region: Optional[str] = Field(
        SettingsDefaults.AWS_REGION,
        env="AWS_REGION",
    )
    aws_apigateway_create_custom_domaim: Optional[bool] = Field(
        SettingsDefaults.AWS_APIGATEWAY_CREATE_CUSTOM_DOMAIN,
        env="AWS_APIGATEWAY_CREATE_CUSTOM_DOMAIN",
        pre=True,
        getter=lambda v: empty_str_to_bool_default(v, SettingsDefaults.AWS_APIGATEWAY_CREATE_CUSTOM_DOMAIN),
    )
    aws_eks_cluster_name: Optional[str] = Field(
        SettingsDefaults.AWS_EKS_CLUSTER_NAME,
        env="AWS_EKS_CLUSTER_NAME",
    )
    aws_db_instance_identifier: Optional[str] = Field(
        SettingsDefaults.AWS_RDS_DB_INSTANCE_IDENTIFIER,
        env="AWS_RDS_DB_INSTANCE_IDENTIFIER",
    )
    anthropic_api_key: Optional[str] = Field(
        SettingsDefaults.ANTHROPIC_API_KEY,
        env="ANTHROPIC_API_KEY",
    )
    environment: Optional[str] = Field(
        SettingsDefaults.ENVIRONMENT,
        env="ENVIRONMENT",
    )
    local_hosts: Optional[List[str]] = Field(
        SettingsDefaults.LOCAL_HOSTS,
        env="LOCAL_HOSTS",
    )
    root_domain: Optional[str] = Field(
        SettingsDefaults.ROOT_DOMAIN,
        env="ROOT_DOMAIN",
    )
    init_info: Optional[str] = Field(
        None,
        env="INIT_INFO",
    )
    google_maps_api_key: Optional[SecretStr] = Field(
        SettingsDefaults.GOOGLE_MAPS_API_KEY,
        env=["GOOGLE_MAPS_API_KEY", "TF_VAR_GOOGLE_MAPS_API_KEY"],
    )
    gemini_api_key: Optional[SecretStr] = Field(
        SettingsDefaults.GEMINI_API_KEY,
        env="GEMINI_API_KEY",
    )
    llama_api_key: Optional[SecretStr] = Field(
        SettingsDefaults.LLAMA_API_KEY,
        env="LLAMA_API_KEY",
    )
    social_auth_google_oauth2_key: Optional[str] = Field(
        SettingsDefaults.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY,
        env=["SOCIAL_AUTH_GOOGLE_OAUTH2_KEY", "TF_VAR_SOCIAL_AUTH_GOOGLE_OAUTH2_KEY"],
    )
    social_auth_google_oauth2_secret: Optional[str] = Field(
        SettingsDefaults.SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET,
        env=["SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET", "TF_VAR_SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET"],
    )
    social_auth_github_key: Optional[str] = Field(
        SettingsDefaults.SOCIAL_AUTH_GITHUB_KEY,
        env=["SOCIAL_AUTH_GITHUB_KEY", "TF_VAR_SOCIAL_AUTH_GITHUB_KEY"],
    )
    social_auth_github_secret: Optional[str] = Field(
        SettingsDefaults.SOCIAL_AUTH_GITHUB_SECRET,
        env=["SOCIAL_AUTH_GITHUB_SECRET", "TF_VAR_SOCIAL_AUTH_GITHUB_SECRET"],
    )
    social_auth_linkedin_oauth2_key: Optional[str] = Field(
        SettingsDefaults.SOCIAL_AUTH_LINKEDIN_OAUTH2_KEY,
        env=["SOCIAL_AUTH_LINKEDIN_OAUTH2_KEY", "TF_VAR_SOCIAL_AUTH_LINKEDIN_OAUTH2_KEY"],
    )
    social_auth_linkedin_oauth2_secret: Optional[str] = Field(
        SettingsDefaults.SOCIAL_AUTH_LINKEDIN_OAUTH2_SECRET,
        env=["SOCIAL_AUTH_LINKEDIN_OAUTH2_SECRET", "TF_VAR_SOCIAL_AUTH_LINKEDIN_OAUTH2_SECRET"],
    )
    langchain_memory_key: Optional[str] = Field(SettingsDefaults.LANGCHAIN_MEMORY_KEY, env="LANGCHAIN_MEMORY_KEY")
    logo: Optional[str] = Field(SettingsDefaults.LOGO, env="LOGO")
    mailchimp_api_key: Optional[SecretStr] = Field(SettingsDefaults.MAILCHIMP_API_KEY, env="MAILCHIMP_API_KEY")
    mailchimp_list_id: Optional[str] = Field(SettingsDefaults.MAILCHIMP_LIST_ID, env="MAILCHIMP_LIST_ID")
    marketing_site_url: Optional[str] = Field(SettingsDefaults.MARKETING_SITE_URL, env="MARKETING_SITE_URL")
    openai_api_organization: Optional[str] = Field(
        SettingsDefaults.OPENAI_API_ORGANIZATION, env="OPENAI_API_ORGANIZATION"
    )
    openai_api_key: Optional[SecretStr] = Field(SettingsDefaults.OPENAI_API_KEY, env="OPENAI_API_KEY")
    openai_endpoint_image_n: Optional[int] = Field(
        SettingsDefaults.OPENAI_ENDPOINT_IMAGE_N, env="OPENAI_ENDPOINT_IMAGE_N"
    )
    openai_endpoint_image_size: Optional[str] = Field(
        SettingsDefaults.OPENAI_ENDPOINT_IMAGE_SIZE, env="OPENAI_ENDPOINT_IMAGE_SIZE"
    )
    llm_default_provider: Optional[str] = Field(SettingsDefaults.LLM_DEFAULT_PROVIDER, env="LLM_DEFAULT_PROVIDER")
    llm_default_model: Optional[str] = Field(SettingsDefaults.LLM_DEFAULT_MODEL, env="LLM_DEFAULT_MODEL")
    llm_default_system_role: Optional[str] = Field(
        SettingsDefaults.LLM_DEFAULT_SYSTEM_ROLE, env="LLM_DEFAULT_SYSTEM_ROLE"
    )
    llm_default_temperature: Optional[float] = Field(
        SettingsDefaults.LLM_DEFAULT_TEMPERATURE, env="LLM_DEFAULT_TEMPERATURE"
    )
    llm_default_max_tokens: Optional[int] = Field(SettingsDefaults.LLM_DEFAULT_MAX_TOKENS, env="LLM_DEFAULT_MAX_TOKENS")
    pinecone_api_key: Optional[SecretStr] = Field(SettingsDefaults.PINECONE_API_KEY, env="PINECONE_API_KEY")
    stripe_live_secret_key: Optional[str] = Field(SettingsDefaults.STRIPE_LIVE_SECRET_KEY, env="STRIPE_LIVE_SECRET_KEY")
    stripe_test_secret_key: Optional[str] = Field(SettingsDefaults.STRIPE_TEST_SECRET_KEY, env="STRIPE_TEST_SECRET_KEY")

    secret_key: Optional[str] = Field(SettingsDefaults.SECRET_KEY, env="SECRET_KEY")

    smtp_sender: Optional[str] = Field(SettingsDefaults.SMTP_SENDER, env="SMTP_SENDER")
    smtp_from_email: Optional[str] = Field(SettingsDefaults.SMTP_FROM_EMAIL, env="SMTP_FROM_EMAIL")
    smtp_host: Optional[str] = Field(SettingsDefaults.SMTP_HOST, env="SMTP_HOST")
    smtp_password: Optional[str] = Field(SettingsDefaults.SMTP_PASSWORD, env="SMTP_PASSWORD")
    smtp_port: Optional[int] = Field(SettingsDefaults.SMTP_PORT, env="SMTP_PORT")
    smtp_use_ssl: Optional[bool] = Field(SettingsDefaults.SMTP_USE_SSL, env="SMTP_USE_SSL")
    smtp_use_tls: Optional[bool] = Field(SettingsDefaults.SMTP_USE_TLS, env="SMTP_USE_TLS")
    smtp_username: Optional[str] = Field(SettingsDefaults.SMTP_USERNAME, env="SMTP_USERNAME")

    stripe_live_secret_key: Optional[str] = Field(SettingsDefaults.STRIPE_LIVE_SECRET_KEY, env="STRIPE_LIVE_SECRET_KEY")
    stripe_test_secret_key: Optional[str] = Field(SettingsDefaults.STRIPE_TEST_SECRET_KEY, env="STRIPE_TEST_SECRET_KEY")

    @property
    def data_directory(self) -> str:
        """Data directory"""
        return "/data"

    @property
    def aws_apigateway_name(self) -> str:
        """Return the API name."""
        return self.shared_resource_identifier + "-api"

    @property
    def aws_apigateway_domain_name(self) -> str:
        """Return the API domain."""
        if self.aws_apigateway_create_custom_domaim:
            return "api." + self.shared_resource_identifier + "." + self.root_domain

        response = self.aws_apigateway_client.get_rest_apis()
        for item in response["items"]:
            if item["name"] == self.aws_apigateway_name:
                api_id = item["id"]
                return f"{api_id}.execute-api.{settings.aws_region}.amazonaws.com"
        return None

    @property
    def environment_cdn_domain(self) -> str:
        """Return the CDN domain."""
        return f"cdn.{self.environment_domain}"

    @property
    def environment_domain(self) -> str:
        """Return the complete domain name."""
        if self.environment == SmarterEnvironments.PROD:
            return SMARTER_CUSTOMER_PLATFORM_SUBDOMAIN + "." + self.root_domain
        if self.environment in SmarterEnvironments.aws_environments:
            return self.environment + "." + SMARTER_CUSTOMER_PLATFORM_SUBDOMAIN + "." + self.root_domain
        if self.environment == SmarterEnvironments.LOCAL:
            return "localhost:8000"
        # default domain format
        return self.environment + "." + SMARTER_CUSTOMER_PLATFORM_SUBDOMAIN + "." + self.root_domain

    @property
    def environment_url(self) -> str:
        if self.environment == SmarterEnvironments.LOCAL:
            return SmarterValidator.urlify(self.environment_domain, environment=self.environment)
        return SmarterValidator.urlify(self.environment_domain, environment=self.environment)

    @property
    def platform_name(self) -> str:
        """Return the platform name."""
        return self.root_domain.split(".")[0]

    @property
    def environment_namespace(self) -> str:
        """Return the Kubernetes namespace for the environment."""
        return f"{self.platform_name}-{SMARTER_CUSTOMER_PLATFORM_SUBDOMAIN}-{settings.environment}"

    @property
    def platform_domain(self) -> str:
        """Return the platform domain name. ie platform.smarter.sh"""
        return f"{SMARTER_CUSTOMER_PLATFORM_SUBDOMAIN}.{self.root_domain}"

    @property
    def api_domain(self) -> str:
        """Return the API domain name. ie alpha.api.smarter.sh"""
        return f"{SMARTER_CUSTOMER_API_SUBDOMAIN}.{self.environment_domain}"

    @property
    def customer_api_domain(self) -> str:
        """Return the customer API domain name."""
        if self.environment == SmarterEnvironments.PROD:
            # api.smarter.sh
            return f"{SMARTER_CUSTOMER_API_SUBDOMAIN}.{self.root_domain}"
        if self.environment in SmarterEnvironments.aws_environments:
            # alpha.api.smarter.sh, beta.api.smarter.sh, next.api.smarter.sh
            return f"{self.environment}.{SMARTER_CUSTOMER_API_SUBDOMAIN}.{self.root_domain}"
        if self.environment == SmarterEnvironments.LOCAL:
            return f"{SMARTER_CUSTOMER_API_SUBDOMAIN}.localhost:8000"
        # default domain format
        return f"{self.environment}.{SMARTER_CUSTOMER_API_SUBDOMAIN}.{self.root_domain}"

    @property
    def customer_api_url(self) -> str:
        if self.environment == SmarterEnvironments.LOCAL:
            return SmarterValidator.urlify(self.customer_api_domain, environment=self.environment)
        return SmarterValidator.urlify(self.customer_api_domain, environment=self.environment)

    @property
    def aws_s3_bucket_name(self) -> str:
        """Return the S3 bucket name."""
        return self.environment_domain

    @property
    def is_using_dotenv_file(self) -> bool:
        """Is the dotenv file being used?"""
        return DOT_ENV_LOADED

    @property
    def environment_variables(self) -> List[str]:
        """Environment variables"""
        return list(os.environ.keys())

    @property
    def is_using_tfvars_file(self) -> bool:
        """Is the tfvars file being used?"""
        return IS_USING_TFVARS

    @property
    def tfvars_variables(self) -> dict:
        """Terraform variables"""
        masked_tfvars = TFVARS.copy()
        if "aws_account_id" in masked_tfvars:
            masked_tfvars["aws_account_id"] = "****"
        return masked_tfvars

    @property
    def version(self) -> str:
        """OpenAI API version"""
        return get_semantic_version()

    @property
    def dump(self) -> dict:
        """Dump all settings."""

        def get_installed_packages():
            installed_packages = pkg_resources.working_set
            # pylint: disable=not-an-iterable
            package_list = [(d.project_name, d.version) for d in installed_packages]
            return package_list

        if self._dump:
            return self._dump

        packages = get_installed_packages()
        packages_dict = [{"name": name, "version": version} for name, version in packages]

        self._dump = {
            "environment": {
                "is_using_tfvars_file": self.is_using_tfvars_file,
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

        if self.is_using_tfvars_file:
            self._dump["environment"]["tfvars"] = self.tfvars_variables

        self._dump = recursive_sort_dict(self._dump)
        return self._dump

    @field_validator("shared_resource_identifier")
    def validate_shared_resource_identifier(cls, v) -> str:
        """Validate shared_resource_identifier"""
        if v in [None, ""]:
            return SettingsDefaults.SHARED_RESOURCE_IDENTIFIER
        return v

    @field_validator("aws_profile")
    def validate_aws_profile(cls, v) -> str:
        """Validate aws_profile"""
        if v in [None, ""]:
            return SettingsDefaults.AWS_PROFILE
        return v

    @field_validator("aws_access_key_id")
    def validate_aws_access_key_id(cls, v, values: ValidationInfo) -> str:
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
    def validate_aws_secret_access_key(cls, v, values: ValidationInfo) -> str:
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
    def validate_aws_region(cls, v, values: ValidationInfo, **kwargs) -> str:
        """Validate aws_region"""
        valid_regions = values.data.get("aws_regions", ["us-east-1"])
        if v in [None, ""]:
            return SettingsDefaults.AWS_REGION
        if v not in valid_regions:
            raise SmarterValueError(f"aws_region {v} not in aws_regions: {valid_regions}")
        return v

    @field_validator("environment")
    def validate_environment(cls, v) -> str:
        """Validate environment"""
        if v in [None, ""]:
            return SettingsDefaults.ENVIRONMENT
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

    @field_validator("aws_apigateway_create_custom_domaim")
    def validate_aws_apigateway_create_custom_domaim(cls, v) -> bool:
        """Validate aws_apigateway_create_custom_domaim"""
        if v in [None, ""]:
            return SettingsDefaults.AWS_APIGATEWAY_CREATE_CUSTOM_DOMAIN
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
    def validate_anthropic_api_key(cls, v) -> str:
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
    def check_google_maps_api_key(cls, v) -> str:
        """Check google_maps_api_key"""
        if v in [None, ""]:
            return SettingsDefaults.GOOGLE_MAPS_API_KEY
        return v

    @field_validator("gemini_api_key")
    def check_gemini_api_key(cls, v) -> str:
        """Check gemini_api_key"""
        if v in [None, ""]:
            return SettingsDefaults.GEMINI_API_KEY
        return v

    @field_validator("llama_api_key")
    def check_llama_api_key(cls, v) -> str:
        """Check llama_api_key"""
        if v in [None, ""]:
            return SettingsDefaults.LLAMA_API_KEY
        return v

    @field_validator("social_auth_google_oauth2_key")
    def check_social_auth_google_oauth2_key(cls, v) -> str:
        """Check social_auth_google_oauth2_key"""
        if v in [None, ""]:
            return SettingsDefaults.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY
        return v

    @field_validator("social_auth_google_oauth2_secret")
    def check_social_auth_google_oauth2_secret(cls, v) -> str:
        """Check social_auth_google_oauth2_secret"""
        if v in [None, ""]:
            return SettingsDefaults.SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET
        return v

    @field_validator("social_auth_github_key")
    def check_social_auth_github_key(cls, v) -> str:
        """Check social_auth_github_key"""
        if v in [None, ""]:
            return SettingsDefaults.SOCIAL_AUTH_GITHUB_KEY
        return v

    @field_validator("social_auth_github_secret")
    def check_social_auth_github_secret(cls, v) -> str:
        """Check social_auth_github_secret"""
        if v in [None, ""]:
            return SettingsDefaults.SOCIAL_AUTH_GITHUB_SECRET
        return v

    @field_validator("social_auth_linkedin_oauth2_key")
    def check_social_auth_linkedin_oauth2_key(cls, v) -> str:
        """Check social_auth_linkedin_oauth2_key"""
        if v in [None, ""]:
            return SettingsDefaults.SOCIAL_AUTH_LINKEDIN_OAUTH2_KEY
        return v

    @field_validator("social_auth_linkedin_oauth2_secret")
    def check_social_auth_linkedin_oauth2_secret(cls, v) -> str:
        """Check social_auth_linkedin_oauth2_secret"""
        if v in [None, ""]:
            return SettingsDefaults.SOCIAL_AUTH_LINKEDIN_OAUTH2_SECRET
        return v

    @field_validator("langchain_memory_key")
    def check_langchain_memory_key(cls, v) -> str:
        """Check langchain_memory_key"""
        if isinstance(v, int):
            return v
        if v in [None, ""]:
            return SettingsDefaults.LANGCHAIN_MEMORY_KEY
        return v

    @field_validator("logo")
    def check_logo(cls, v) -> str:
        """Check logo"""
        if v in [None, ""]:
            return SettingsDefaults.LOGO
        return v

    @field_validator("mailchimp_api_key")
    def check_mailchimp_api_key(cls, v) -> str:
        """Check mailchimp_api_key"""
        if v in [None, ""]:
            return SettingsDefaults.MAILCHIMP_API_KEY
        return v

    @field_validator("mailchimp_list_id")
    def check_mailchimp_list_id(cls, v) -> str:
        """Check mailchimp_list_id"""
        if v in [None, ""]:
            return SettingsDefaults.MAILCHIMP_LIST_ID
        return v

    @field_validator("marketing_site_url")
    def check_marketing_site_url(cls, v) -> str:
        """Check marketing_site_url"""
        if v in [None, ""]:
            return SettingsDefaults.MARKETING_SITE_URL
        SmarterValidator.validate_url(v)
        return v

    @field_validator("openai_api_organization")
    def check_openai_api_organization(cls, v) -> str:
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
    def check_openai_default_max_tokens(cls, v) -> int:
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
            return SettingsDefaults.STRIPE_LIVE_SECRET_KEY
        return v

    @field_validator("stripe_test_secret_key")
    def check_stripe_test_secret_key(cls, v) -> str:
        """Check stripe_test_secret_key"""
        if v in [None, ""]:
            return SettingsDefaults.STRIPE_TEST_SECRET_KEY
        return v

    @field_validator("secret_key")
    def check_secret_key(cls, v) -> str:
        """Check secret_key"""
        if v in [None, ""]:
            return SettingsDefaults.SECRET_KEY
        return v

    @field_validator("smtp_sender")
    def check_smtp_sender(cls, v) -> str:
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


class SingletonSettings:
    """
    Alternative Singleton pattern to resolve metaclass inheritance conflict
    from Pydantic BaseSettings.

    Traceback (most recent call last):
    File "/smarter/manage.py", line 8, in <module>
        from smarter.common.conf import settings as smarter_settings
    File "/smarter/smarter/common/conf.py", line 262, in <module>
        class Settings(BaseSettings, metaclass=Singleton):
    TypeError: metaclass conflict: the metaclass of a derived class must be a (non-strict) subclass of the metaclasses of all its bases
    """

    _instance = None

    def __new__(cls):
        """Create a new instance of Settings"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            try:
                cls._instance._settings = Settings()
            except ValidationError as e:
                raise SmarterConfigurationError("Invalid configuration: " + str(e)) from e
        return cls._instance

    @property
    def settings(self) -> Settings:
        """Return the settings"""
        return self._settings


settings = SingletonSettings().settings
