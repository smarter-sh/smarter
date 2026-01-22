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
    4. default values defined in SettingsDefaults.

.. note::

    You can also set any Django settings value from environment variables
    and/or `.env` file variables. For example, to set the Django
    ``SECRET_KEY`` setting, you can set the environment variable ``SECRET_KEY=MYSECRET``.

.. warning::

    DO NOT import Django or any Django modules in this module. This module
    sits upstream of Django and is intended to be used independently of Django.

"""

# -------------------- WARNING --------------------
# DO NOT IMPORT DJANGO OR ANY DJANGO MODULES. THIS
# ENTIRE MODULE SITS UPSTREAM OF DJANGO AND IS
# INTENDED TO BE USED INDEPENDENTLY OF DJANGO.
# ------------------------------------------------

# python stuff
import base64  # library for base64 encoding and decoding
import logging  # library for logging messages
import os  # library for interacting with the operating system
import platform  # library to view information about the server host this module runs on
import re  # library for regular expressions
import warnings  # library for issuing warning messages
from functools import (  # utilities for caching function/method results
    cache,
    cached_property,
    lru_cache,
)
from importlib.metadata import distributions  # library for accessing package metadata
from typing import Any, List, Optional, Pattern, Tuple, Union  # type hint utilities
from urllib.parse import urljoin, urlparse  # library for URL manipulation

# 3rd party stuff
import boto3  # AWS SDK for Python https://boto3.amazonaws.com/v1/documentation/api/latest/index.html
import requests
from botocore.exceptions import NoCredentialsError, ProfileNotFound
from dotenv import load_dotenv
from pydantic import (
    EmailStr,
    Field,
    HttpUrl,
    SecretStr,
    ValidationError,
    ValidationInfo,
)
from pydantic import __version__ as pydantic_version
from pydantic import (
    field_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

from smarter.common.api import SmarterApiVersions
from smarter.common.helpers.console_helpers import (
    formatted_text,
    formatted_text_green,
    formatted_text_red,
)
from smarter.common.utils import generate_fernet_encryption_key
from smarter.lib import json
from smarter.lib.django.validators import SmarterValidator

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
from .utils import bool_environment_variable

logger = logging.getLogger(__name__)
logger_prefix = formatted_text(__name__ + "Settings()")
DEFAULT_MISSING_VALUE = "SET-ME-PLEASE"
DEFAULT_ROOT_DOMAIN = "example.com"
DOT_ENV_LOADED = load_dotenv()
"""
True if .env file was loaded successfully.
"""

SERVICE_TYPE = str(os.environ.get("SERVICE_TYPE")).lower() if os.environ.get("SERVICE_TYPE") else None
"""
Describes the type of service this instance is running as. valid values are: app, worker, beat.
This value can be set in .env or docker-compose.yml or set as an environment variable.
"""

VERBOSE_CONSOLE_OUTPUT = bool_environment_variable("SMARTER_SETTINGS_OUTPUT", False)


def before_field_validator(*args, **kwargs):
    """
    Wrapper for pydantic field_validator with mode='before'.
    """
    kwargs["mode"] = "before"
    return field_validator(*args, **kwargs)


def get_env(var_name, default: Any = DEFAULT_MISSING_VALUE, is_secret: bool = False, is_required: bool = False) -> Any:
    """
    Retrieve a configuration value from the environment, with  prefix fallback and type conversion.

    This function attempts to obtain a configuration value from the environment using the key ``<var_name>``.
    If the environment variable is not set, it returns the provided ``default`` value. The function also performs
    type conversion and validation based on the type of the default value, supporting strings,
    booleans, integers, floats, lists (comma-separated), and dictionaries (JSON-encoded).

    **Behavior:**

    - Checks for the presence of the environment variable ``<var_name>``.
    - If found, attempts to convert the value to the type of ``default``.
    - If not found, returns the ``default`` value.
    - Logs a message if the environment variable is missing or if type conversion fails.

    This utility is used throughout the Smarter platform to provide a consistent and robust
    mechanism for loading configuration values from the environment, with sensible type handling and error reporting.

    :param var_name: The base name of the environment variable (without the  prefix).
    :type var_name: str
    :param default: The default value to return if the environment variable is not set. The type of this value determines the expected type and conversion logic.
    :type default: Any
    :return: The value from the environment (converted to the appropriate type), or the default if not set or conversion fails.
    :rtype: Any
    """

    def cast_value(val: Optional[str], default: Any) -> Any:
        """
        Cast the environment variable value to the type of the default value.

        :param val: The environment variable value as a string.
        :param default: The default value to determine the target type.
        :return: The casted value.
        """
        if isinstance(default, str):
            return val.strip() if val is not None else default
        if isinstance(default, bool):
            return str(val).lower() in ["true", "1", "t", "y", "yes"] if val is not None else default
        if isinstance(default, int):
            try:
                return int(val) if val is not None else default
            except (ValueError, TypeError):
                logger.error(
                    "Environment variable %s value '%s' cannot be converted to int. Using default %s.",
                    var_name,
                    val,
                    default,
                )
                return default
        if isinstance(default, float):
            try:
                return float(val) if val is not None else default
            except (ValueError, TypeError):
                logger.error(
                    "Environment variable %s value '%s' cannot be converted to float. Using default %s.",
                    var_name,
                    val,
                    default,
                )
                return default
        if isinstance(default, list):
            if isinstance(val, str):
                return [item.strip() for item in val.split(",") if item.strip()] if val is not None else default
            elif isinstance(val, list):
                return val if val is not None else default
            else:
                logger.error(
                    "Environment variable %s value '%s' cannot be converted to list. Using default %s.",
                    var_name,
                    val,
                    default,
                )
                return default
        if isinstance(default, dict):
            try:
                if isinstance(val, str):
                    return json.loads(val) if val is not None else default
                elif isinstance(val, dict):
                    return val if val is not None else default
                else:
                    logger.error(
                        "Environment variable %s value '%s' cannot be converted to dict. Using default %s.",
                        var_name,
                        val,
                        default,
                    )
                    return default
            except json.JSONDecodeError:
                logger.error(
                    "Environment variable %s value '%s' is not valid JSON. Using default %s.", var_name, val, default
                )
                return default
        return val

    retval = os.environ.get(var_name) or os.environ.get(f"SMARTER_{var_name}")
    # Strip surrounding quotes if present
    retval = str(retval).strip() if retval is not None else None
    # Strip surrounding quotes if present
    retval = str(retval).strip('"').strip("'") if retval is not None else None
    if retval is None and is_required:
        msg = (
            f"{formatted_text(__name__ + ".get_env()")} [WARNING] Required environment variable {var_name} is missing."
        )
        logger.warning(msg)
        print(msg)
        return default
    else:
        cast_val = cast_value(retval, default)  # type: ignore
        log_value = cast_val if not is_secret else "****"
        if VERBOSE_CONSOLE_OUTPUT:
            msg = f"{formatted_text(__name__ + ".get_env()")} Environment variable {var_name} found. Overriding Smarter setting from environment variable: {var_name}={repr(log_value)}"
            logger.info(msg)
            print(msg)
        return cast_val


def recursive_sort_dict(d):
    """Recursively sort a dictionary by key."""
    return {k: recursive_sort_dict(v) if isinstance(v, dict) else v for k, v in sorted(d.items())}


@cache
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
        retval = bool(boto3.Session().get_credentials())
        if not retval:
            logger.warning("AWS is not configured properly. Credentials are invalid, or no credentials were found.")
        return retval

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
            if Services.is_connected_to_aws():
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


DOT_ENV_LOADED = DOT_ENV_LOADED or get_env("ENV_LOADED", False)
if not DOT_ENV_LOADED and get_env("ENVIRONMENT", SmarterEnvironments.LOCAL) == SmarterEnvironments.LOCAL:
    print(
        formatted_text_red(
            "\n"
            + "=" * 80
            + "\n[WARNING] .env file was NOT loaded! Environment variables may be missing.\n"
            + "Look for .env.example in the project root and follow the instructions that begin at the top of the file.\n"
            + "Settings values that are required (there are many) will be noted in this file.\n"
            + "=" * 80
            + "\n"
        )
    )


# pylint: disable=too-few-public-methods
class SettingsDefaults:
    """
    .. deprecated:: 2025.12

        This class is deprecated and will be removed in a future release. Use the Settings class
        built-in default value handling instead.

    Default values for Smarter platform settings.

    This class provides the baseline configuration for all Smarter platform settings, supplying sensible defaults for every supported option. These defaults are used unless overridden by environment variables prefixed with ````. The class is designed to ensure that all configuration values are available and type-consistent, supporting robust initialization and validation of platform settings.

    **How defaults are determined:**

    - If a corresponding environment variable with the ```` prefix exists, its value is used (with type conversion and validation as appropriate).
    - If no such environment variable is set, the value defined in this class is used as the default.

    This approach allows for flexible configuration via environment variables, while maintaining a clear and centralized set of fallback values for all settings. The defaults defined here are intended to be safe and reasonable for most development and production scenarios, but can be customized as needed for specific deployments.

    .. note::
        This class is not intended to be instantiated directly. Instead, it serves as a source of default values for the main ``Settings`` class, which handles validation, environment variable loading, and integration with the rest of the platform.

    .. warning::
        Do not add application logic or side effects to this class. It should only define static default values and simple logic for fallback selection.
    """

    ROOT_DOMAIN: str = get_env("ROOT_DOMAIN", DEFAULT_ROOT_DOMAIN, is_required=True)

    # for liveness and readiness probes from kubernetes.
    # see https://stackoverflow.com/questions/40582423/how-to-fix-django-error-disallowedhost-at-invalid-http-host-header-you-m
    ALLOWED_HOSTS: List[str] = get_env("ALLOWED_HOSTS", ["localhost"])
    ANTHROPIC_API_KEY: SecretStr = SecretStr(get_env("ANTHROPIC_API_KEY", is_secret=True, is_required=True))

    API_DESCRIPTION: str = get_env(
        "API_DESCRIPTION", "A declarative AI resource management platform and developer framework"
    )
    API_NAME: str = get_env("API_NAME", "Smarter API")
    API_SCHEMA: str = get_env("API_SCHEMA", "http")

    # aws auth
    AWS_PROFILE = get_env("AWS_PROFILE", default=None)
    AWS_ACCESS_KEY_ID: SecretStr = SecretStr(get_env("AWS_ACCESS_KEY_ID", default=None, is_secret=True))
    AWS_SECRET_ACCESS_KEY: SecretStr = SecretStr(get_env("AWS_SECRET_ACCESS_KEY", default=None, is_secret=True))
    AWS_REGION = get_env("AWS_REGION", default=None)

    AWS_EKS_CLUSTER_NAME = get_env("AWS_EKS_CLUSTER_NAME")
    AWS_RDS_DB_INSTANCE_IDENTIFIER = get_env("AWS_RDS_DB_INSTANCE_IDENTIFIER")

    BRANDING_CORPORATE_NAME: str = get_env("BRANDING_CORPORATE_NAME", "The Smarter Project")
    BRANDING_SUPPORT_PHONE_NUMBER: str = get_env("BRANDING_SUPPORT_PHONE_NUMBER", "(###) 555-1212")
    BRANDING_SUPPORT_EMAIL: EmailStr = get_env("BRANDING_SUPPORT_EMAIL", "support@example.com")
    BRANDING_ADDRESS: str = get_env("BRANDING_ADDRESS", "123 Main St, Anytown, USA")
    BRANDING_CONTACT_URL: Optional[HttpUrl] = get_env("BRANDING_CONTACT_URL", "https://example.com/contact/")
    BRANDING_SUPPORT_HOURS: str = get_env("BRANDING_SUPPORT_HOURS", "MON-FRI 9:00 AM - 5:00 PM GMT-6 (CST)")
    BRANDING_URL_FACEBOOK: Optional[HttpUrl] = get_env("BRANDING_URL_FACEBOOK", "https://facebook.com/example")
    BRANDING_URL_TWITTER: Optional[HttpUrl] = get_env("BRANDING_URL_TWITTER", "https://twitter.com/example")
    BRANDING_URL_LINKEDIN: Optional[HttpUrl] = get_env("BRANDING_URL_LINKEDIN", "https://linkedin.com/company/example")

    CACHE_EXPIRATION: int = int(get_env("CACHE_EXPIRATION", 60 * 1))  # 1 minute
    CHAT_CACHE_EXPIRATION: int = int(get_env("CHAT_CACHE_EXPIRATION", 60 * 5))  # 5 minutes
    CONFIGURE_BETA_ACCOUNT: bool = bool_environment_variable("CONFIGURE_BETA_ACCOUNT", False)
    CONFIGURE_UBC_ACCOUNT: bool = bool_environment_variable("CONFIGURE_UBC_ACCOUNT", False)
    CHATBOT_CACHE_EXPIRATION: int = int(get_env("CHATBOT_CACHE_EXPIRATION", 60 * 5))  # 5 minutes
    CHATBOT_MAX_RETURNED_HISTORY: int = int(get_env("CHATBOT_MAX_RETURNED_HISTORY", 25))
    CHATBOT_TASKS_CREATE_DNS_RECORD: bool = bool_environment_variable("CHATBOT_TASKS_CREATE_DNS_RECORD", True)
    CHATBOT_TASKS_CREATE_INGRESS_MANIFEST: bool = bool_environment_variable(
        "CHATBOT_TASKS_CREATE_INGRESS_MANIFEST", True
    )
    CHATBOT_TASKS_DEFAULT_TTL: int = get_env("CHATBOT_TASKS_DEFAULT_TTL", 600)

    CHATBOT_TASKS_CELERY_MAX_RETRIES: int = int(get_env("CHATBOT_TASKS_CELERY_MAX_RETRIES", 3))
    CHATBOT_TASKS_CELERY_RETRY_BACKOFF: bool = bool_environment_variable("CHATBOT_TASKS_CELERY_RETRY_BACKOFF", True)
    CHATBOT_TASKS_CELERY_TASK_QUEUE: str = get_env("CHATBOT_TASKS_CELERY_TASK_QUEUE", "default_celery_task_queue")
    PLUGIN_MAX_DATA_RESULTS: int = int(get_env("PLUGIN_MAX_DATA_RESULTS", 50))

    SENSITIVE_FILES_AMNESTY_PATTERNS: List[Pattern] = get_env(
        "SENSITIVE_FILES_AMNESTY_PATTERNS",
        [
            re.compile(r"^/dashboard/account/password-reset-link/[^/]+/[^/]+/$"),
            re.compile(r"^/api(/.*)?$"),
            re.compile(r"^/admin(/.*)?$"),
            re.compile(r"^/plugin(/.*)?$"),
            re.compile(r"^/docs/manifest(/.*)?$"),
            re.compile(r"^/docs/json-schema(/.*)?$"),
            re.compile(r".*stackademy.*"),
            re.compile(r"^/\.well-known/acme-challenge(/.*)?$"),
        ],
    )

    DEBUG_MODE: bool = bool_environment_variable("DEBUG_MODE", False)
    DEVELOPER_MODE: bool = bool_environment_variable("DEVELOPER_MODE", False)

    DJANGO_DEFAULT_FILE_STORAGE = get_env("DJANGO_DEFAULT_FILE_STORAGE", DjangoPermittedStorages.AWS_S3)
    if DJANGO_DEFAULT_FILE_STORAGE == DjangoPermittedStorages.AWS_S3 and not Services.is_connected_to_aws():
        DJANGO_DEFAULT_FILE_STORAGE = DjangoPermittedStorages.FILE_SYSTEM
        logger.warning(
            "AWS is not configured properly. Falling back to FileSystemStorage for Django default file storage."
        )

    DUMP_DEFAULTS: bool = bool(get_env("DUMP_DEFAULTS", False))
    EMAIL_ADMIN: EmailStr = get_env("EMAIL_ADMIN", "admin@example.com", is_required=True)
    ENVIRONMENT = get_env("ENVIRONMENT", SmarterEnvironments.LOCAL)

    fernet = get_env("FERNET_ENCRYPTION_KEY", default=None, is_secret=True)
    if fernet is None:
        warnings.warn(
            "FERNET_ENCRYPTION_KEY is not set. "
            "A new encryption key will be generated. This may cause existing encrypted data to become inaccessible. "
            "You can safely disregard this warning if this is a new installation or test environment.",
            UserWarning,
        )
        fernet = generate_fernet_encryption_key()
    FERNET_ENCRYPTION_KEY = SecretStr(fernet)

    GOOGLE_MAPS_API_KEY: SecretStr = SecretStr(get_env("GOOGLE_MAPS_API_KEY", is_secret=True, is_required=True))

    try:
        GOOGLE_SERVICE_ACCOUNT_B64 = get_env("GOOGLE_SERVICE_ACCOUNT_B64", "", is_secret=True, is_required=True)
        GOOGLE_SERVICE_ACCOUNT: SecretStr = SecretStr(
            json.loads(base64.b64decode(GOOGLE_SERVICE_ACCOUNT_B64).decode("utf-8"))
        )
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.error("Failed to load Google service account: %s", e)
        logger.error(
            "See https://console.cloud.google.com/projectselector2/iam-admin/serviceaccounts?supportedpurview=project"
        )
        GOOGLE_SERVICE_ACCOUNT = SecretStr(json.dumps({}))
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("Unexpected error loading Google service account: %s", e)
        GOOGLE_SERVICE_ACCOUNT = SecretStr(json.dumps({}))

    GEMINI_API_KEY: SecretStr = SecretStr(get_env("GEMINI_API_KEY", is_secret=True, is_required=True))
    INTERNAL_IP_PREFIXES: List[str] = get_env("INTERNAL_IP_PREFIXES", ["192.168."])
    LANGCHAIN_MEMORY_KEY = get_env("LANGCHAIN_MEMORY_KEY", "chat_history")

    LLAMA_API_KEY: SecretStr = SecretStr(get_env("LLAMA_API_KEY", is_secret=True, is_required=True))
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
    LOCAL_HOSTS += [host + ":9357" for host in LOCAL_HOSTS]
    LOCAL_HOSTS.append("testserver")

    LOG_LEVEL: int = logging.DEBUG if get_env("DEBUG_MODE", False) else logging.INFO

    LOGO: HttpUrl = get_env("LOGO", "https://cdn.example.com/images/logo/logo.png", is_required=True)
    MAILCHIMP_API_KEY: SecretStr = SecretStr(get_env("MAILCHIMP_API_KEY", is_secret=True))
    MAILCHIMP_LIST_ID = get_env("MAILCHIMP_LIST_ID")

    MARKETING_SITE_URL: HttpUrl = get_env("MARKETING_SITE_URL", f"https://{ROOT_DOMAIN}", is_required=True)

    MYSQL_TEST_DATABASE_SECRET_NAME = get_env(
        "MYSQL_TEST_DATABASE_SECRET_NAME",
        "smarter_test_db",
        is_required=True,
    )
    MYSQL_TEST_DATABASE_PASSWORD: SecretStr = SecretStr(
        get_env("MYSQL_TEST_DATABASE_PASSWORD", is_secret=True, is_required=True)
    )

    OPENAI_API_ORGANIZATION = get_env("OPENAI_API_ORGANIZATION")
    OPENAI_API_KEY: SecretStr = SecretStr(get_env("OPENAI_API_KEY", is_secret=True, is_required=True))
    OPENAI_ENDPOINT_IMAGE_N = get_env("OPENAI_ENDPOINT_IMAGE_N", 4)
    OPENAI_ENDPOINT_IMAGE_SIZE = get_env("OPENAI_ENDPOINT_IMAGE_SIZE", "1024x768")
    PINECONE_API_KEY: SecretStr = SecretStr(get_env("PINECONE_API_KEY", is_secret=True))

    REACTJS_APP_LOADER_PATH = get_env("REACTJS_APP_LOADER_PATH", SMARTER_DEFAULT_APP_LOADER_PATH)

    secret = get_env("SECRET_KEY", default=None, is_secret=True)
    if secret is None:
        warnings.warn(
            "SECRET_KEY is not set. A new secret key will be generated. "
            "This may cause existing sessions and other cryptographic operations to become invalid. "
            "You can safely disregard this warning if this is a new installation or test environment.",
            UserWarning,
        )
        secret = base64.urlsafe_b64encode(os.urandom(32)).decode()
    SECRET_KEY: SecretStr = SecretStr(secret)
    SETTINGS_OUTPUT: bool = bool_environment_variable("SETTINGS_OUTPUT", False)

    SHARED_RESOURCE_IDENTIFIER = get_env("SHARED_RESOURCE_IDENTIFIER", "smarter")

    SMARTER_MYSQL_TEST_DATABASE_SECRET_NAME = get_env(
        "SMARTER_MYSQL_TEST_DATABASE_SECRET_NAME", "smarter_test_db", is_required=True
    )
    SMARTER_MYSQL_TEST_DATABASE_PASSWORD: SecretStr = SecretStr(
        get_env("SMARTER_MYSQL_TEST_DATABASE_PASSWORD", is_secret=True, is_required=True)
    )

    SMTP_SENDER = get_env("SMTP_SENDER", f"admin@{ROOT_DOMAIN}", is_required=True)
    SMTP_FROM_EMAIL = get_env("SMTP_FROM_EMAIL", f"no-reply@{ROOT_DOMAIN}", is_required=True)
    SMTP_HOST = get_env("SMTP_HOST", "email-smtp.us-east-2.amazonaws.com")
    SMTP_PORT = int(get_env("SMTP_PORT", "587"))
    SMTP_USE_SSL = bool(get_env("SMTP_USE_SSL", False))
    SMTP_USE_TLS = bool(get_env("SMTP_USE_TLS", True))
    SMTP_PASSWORD: SecretStr = SecretStr(get_env("SMTP_PASSWORD", is_secret=True, is_required=True))
    SMTP_USERNAME: SecretStr = SecretStr(get_env("SMTP_USERNAME", is_secret=True))

    # -------------------------------------------------------------------------
    # see: https://console.cloud.google.com/apis/credentials/oauthclient/231536848926-egabg8jas321iga0nmleac21ccgbg6tq.apps.googleusercontent.com?project=smarter-sh
    # -------------------------------------------------------------------------
    SOCIAL_AUTH_GOOGLE_OAUTH2_KEY: SecretStr = SecretStr(get_env("SOCIAL_AUTH_GOOGLE_OAUTH2_KEY", is_secret=True))
    SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET: SecretStr = SecretStr(get_env("SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET", is_secret=True))
    # -------------------------------------------------------------------------
    # see: https://github.com/settings/applications/2620957
    # -------------------------------------------------------------------------
    SOCIAL_AUTH_GITHUB_KEY: SecretStr = SecretStr(get_env("SOCIAL_AUTH_GITHUB_KEY", is_secret=True))
    SOCIAL_AUTH_GITHUB_SECRET: SecretStr = SecretStr(get_env("SOCIAL_AUTH_GITHUB_SECRET", is_secret=True))
    # -------------------------------------------------------------------------
    # see:  https://www.linkedin.com/developers/apps/221422881/settings
    #       https://www.linkedin.com/developers/apps/221422881/products?refreshKey=1734980684455
    # verification url: https://www.linkedin.com/developers/apps/verification/3ac34414-09a4-433b-983a-0d529fa486f1
    # -------------------------------------------------------------------------
    SOCIAL_AUTH_LINKEDIN_OAUTH2_KEY: SecretStr = SecretStr(get_env("SOCIAL_AUTH_LINKEDIN_OAUTH2_KEY", is_secret=True))
    SOCIAL_AUTH_LINKEDIN_OAUTH2_SECRET: SecretStr = SecretStr(
        get_env("SOCIAL_AUTH_LINKEDIN_OAUTH2_SECRET", is_secret=True)
    )

    STRIPE_LIVE_SECRET_KEY: SecretStr = SecretStr(get_env("STRIPE_LIVE_SECRET_KEY", is_secret=True))
    STRIPE_TEST_SECRET_KEY: SecretStr = SecretStr(get_env("STRIPE_TEST_SECRET_KEY", is_secret=True))

    @classmethod
    def to_dict(cls):
        """Convert SettingsDefaults to dict"""
        return {
            key: value
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
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("unexpected error initializing aws ec2 client: %s", e)


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
        4. SettingsDefaults
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
        handling that in SettingsDefaults for backward compatibility. There
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

    _dump: dict
    _ready: bool = False

    def __init__(self, **data: Any):
        super().__init__(**data)
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
        :default: Value from ``SettingsDefaults.ALLOWED_HOSTS``
        :raises SmarterConfigurationError: If the value is not a list of strings.
        :examples: ["example.com", "www.example.com"]
        """
        default_allowed_hosts = SettingsDefaults.ALLOWED_HOSTS.copy() or []
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
        SettingsDefaults.ANTHROPIC_API_KEY,
        description="The API key for Anthropic services. Masked by pydantic SecretStr.",
        examples=["sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"],
        title="Anthropic API Key",
    )
    """
    The API key for Anthropic services. Masked by pydantic SecretStr.
    This setting provides the API key used to authenticate with Anthropic services.
    It is required for accessing Anthropic's APIs and services.

    :type: SecretStr
    :default: Value from ``SettingsDefaults.ANTHROPIC_API_KEY``
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
            return SettingsDefaults.ANTHROPIC_API_KEY

        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError(f"anthropic_api_key of type {type(v)} is not a SecretStr.")

        return v

    api_description: str = Field(
        SettingsDefaults.API_DESCRIPTION,
        description="The description of the API.",
        examples=["A declarative AI resource management platform and developer framework"],
        title="API Description",
    )
    """
    The description of the API.
    This setting provides a brief description of the API's purpose and functionality.
    It is used in various contexts, such as Swagger Api documentation site, logging, and user interfaces.
    :type: str
    :default: Value from ``SettingsDefaults.API_DESCRIPTION``
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
        SettingsDefaults.API_NAME,
        description="The name of the API.",
        examples=["Smarter API", "My Custom API"],
        title="API Name",
    )
    """
    The name of the API.
    This setting specifies the name of the API used in various contexts,
    such as Swagger Api documentation site, logging, and user interfaces.

    :type: str
    :default: Value from ``SettingsDefaults.API_NAME``
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
        :default: Value from ``SettingsDefaults.API_SCHEMA``
        :raises SmarterConfigurationError: If the value is not 'http' or 'https'.
        :examples: ["http", "https"],
        """
        if self.environment == SmarterEnvironments.LOCAL:
            return "http"
        else:
            return SettingsDefaults.API_SCHEMA

    aws_profile: Optional[str] = Field(
        SettingsDefaults.AWS_PROFILE,
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
    :default: Value from ``SettingsDefaults.AWS_PROFILE``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("aws_profile")
    def validate_aws_profile(cls, v: Optional[str]) -> Optional[str]:
        """Validates the `aws_profile` field.
        Uses SettingsDefaults if no value is received.

        Args:
            v (Optional[str]): The AWS profile value to validate.

        Returns:
            Optional[str]: The validated AWS profile.
        """
        if v in [None, ""]:
            if SettingsDefaults.AWS_PROFILE == DEFAULT_MISSING_VALUE:
                return None
            return SettingsDefaults.AWS_PROFILE
        return v

    aws_access_key_id: Optional[SecretStr] = Field(
        SettingsDefaults.AWS_ACCESS_KEY_ID,
        description="The AWS access key ID for authentication. Used if AWS_PROFILE is not set. Masked by pydantic SecretStr.",
        examples=["^AKIA[0-9A-Z]{16}$"],
        title="AWS Access Key ID",
    )
    """
    The AWS access key ID for authentication. Used if AWS_PROFILE is not set. Masked by pydantic SecretStr.
    This setting provides the access key ID used to authenticate with AWS services.
    It is used in conjunction with the AWS secret access key to sign requests to AWS APIs.

    :type: SecretStr
    :default: Value from ``SettingsDefaults.AWS_ACCESS_KEY_ID``
    :raises SmarterConfigurationError: If the value is not a valid AWS access key ID
    """

    @before_field_validator("aws_access_key_id")
    def validate_aws_access_key_id(cls, v: Optional[SecretStr], values: ValidationInfo) -> Optional[SecretStr]:
        """Validates the `aws_access_key_id` field.
        Uses SettingsDefaults if no value is received.


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
        SettingsDefaults.AWS_SECRET_ACCESS_KEY,
        description="The AWS secret access key for authentication. Used if AWS_PROFILE is not set. Masked by pydantic SecretStr.",
        examples=["^[0-9a-zA-Z/+]{40}$"],
        title="AWS Secret Access Key",
    )
    """
    The AWS secret access key for authentication. Used if AWS_PROFILE is not set. Masked by pydantic SecretStr.
    This setting provides the secret access key used to authenticate with AWS services.
    It is used in conjunction with the AWS access key ID to sign requests to AWS APIs.

    :type: SecretStr
    :default: Value from ``SettingsDefaults.AWS_SECRET_ACCESS_KEY``
    :raises SmarterConfigurationError: If the value is not a valid AWS secret access key
    """

    @before_field_validator("aws_secret_access_key")
    def validate_aws_secret_access_key(cls, v: Optional[SecretStr], values: ValidationInfo) -> Optional[SecretStr]:
        """Validates the `aws_secret_access_key` field.
        Uses SettingsDefaults if no value is received.

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
        SettingsDefaults.AWS_REGION,
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
    :default: Value from ``SettingsDefaults.AWS_REGION``
    :raises SmarterConfigurationError: If the value is not a valid AWS region name.
    """

    @before_field_validator("aws_region")
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
            if SettingsDefaults.AWS_REGION == DEFAULT_MISSING_VALUE:
                return None
            return SettingsDefaults.AWS_REGION
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
        return Services.is_connected_to_aws()

    aws_eks_cluster_name: str = Field(
        SettingsDefaults.AWS_EKS_CLUSTER_NAME,
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
    :default: Value from ``SettingsDefaults.AWS_EKS_CLUSTER_NAME``
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
        if v in [None, ""]:
            return SettingsDefaults.AWS_EKS_CLUSTER_NAME

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"aws_eks_cluster_name of type {type(v)} is not a str.")

        return v

    aws_db_instance_identifier: str = Field(
        SettingsDefaults.AWS_RDS_DB_INSTANCE_IDENTIFIER,
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
    :default: Value from ``SettingsDefaults.AWS_RDS_DB_INSTANCE_IDENTIFIER``
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
        if v in [None, ""]:
            return SettingsDefaults.AWS_RDS_DB_INSTANCE_IDENTIFIER

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"aws_db_instance_identifier of type {type(v)} is not a str.")

        return v

    branding_corporate_name: str = Field(
        SettingsDefaults.BRANDING_CORPORATE_NAME,
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
    :default: Value from ``SettingsDefaults.BRANDING_CORPORATE_NAME``
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
        if v in [None, ""]:
            return SettingsDefaults.BRANDING_CORPORATE_NAME

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"branding_corporate_name of type {type(v)} is not a str.")

        return v

    branding_support_phone_number: str = Field(
        SettingsDefaults.BRANDING_SUPPORT_PHONE_NUMBER,
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
    :default: Value from ``SettingsDefaults.BRANDING_SUPPORT_PHONE_NUMBER``
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
        if v in [None, ""]:
            return SettingsDefaults.BRANDING_SUPPORT_PHONE_NUMBER

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"branding_support_phone_number of type {type(v)} is not a str.")

        return v

    branding_support_email: EmailStr = Field(
        SettingsDefaults.BRANDING_SUPPORT_EMAIL,
        description="The support email address used for branding purposes throughout the platform.",
        title="Branding Support Email",
    )
    """
    The support email address used for branding purposes throughout the platform.
    This setting specifies the email address that users can contact for support
    or assistance related to the platform. It is used in various branding contexts,
    such as email templates, user interfaces, and documentation.
    :type: EmailStr
    :default: Value from ``SettingsDefaults.BRANDING_SUPPORT_EMAIL``
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
        if v in [None, ""]:
            return SettingsDefaults.BRANDING_SUPPORT_EMAIL

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"branding_support_email of type {type(v)} is not a EmailStr.")
        SmarterValidator.validate_email(v)

        return v

    branding_address: str = Field(
        SettingsDefaults.BRANDING_ADDRESS,
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
    :default: Value from ``SettingsDefaults.BRANDING_ADDRESS``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("branding_address")
    def validate_branding_address(cls, v: Optional[str]) -> str:
        """Validates the `branding_address` field.

        Args:
            v (Optional[str]): The branding address value to validate.

        Returns:
            str: The validated branding address.
        """
        if v in [None, ""]:
            return SettingsDefaults.BRANDING_ADDRESS

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"branding_address of type {type(v)} is not a str.")

        return v

    branding_contact_url: Optional[HttpUrl] = Field(
        SettingsDefaults.BRANDING_CONTACT_URL,
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
    :default: Value from ``SettingsDefaults.BRANDING_CONTACT_URL``
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
            return SettingsDefaults.BRANDING_CONTACT_URL
        return v

    branding_support_hours: str = Field(
        SettingsDefaults.BRANDING_SUPPORT_HOURS,
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
    :default: Value from ``SettingsDefaults.BRANDING_SUPPORT_HOURS``
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
        if v in [None, ""]:
            return SettingsDefaults.BRANDING_SUPPORT_HOURS

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"branding_support_hours of type {type(v)} is not a str.")

        return v

    branding_url_facebook: Optional[HttpUrl] = Field(
        SettingsDefaults.BRANDING_URL_FACEBOOK,
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
    :default: Value from ``SettingsDefaults.BRANDING_URL_FACEBOOK``
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
            return SettingsDefaults.BRANDING_URL_FACEBOOK
        return v

    branding_url_twitter: Optional[HttpUrl] = Field(
        SettingsDefaults.BRANDING_URL_TWITTER,
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
    :default: Value from ``SettingsDefaults.BRANDING_URL_TWITTER``
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
            return SettingsDefaults.BRANDING_URL_TWITTER
        return v

    branding_url_linkedin: Optional[HttpUrl] = Field(
        SettingsDefaults.BRANDING_URL_LINKEDIN,
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
    :default: Value from ``SettingsDefaults.BRANDING_URL_LINKEDIN``
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
            return SettingsDefaults.BRANDING_URL_LINKEDIN
        return v

    cache_expiration: int = Field(
        SettingsDefaults.CACHE_EXPIRATION,
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
    :default: Value from ``SettingsDefaults.CACHE_EXPIRATION``
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
        if v in [None, ""]:
            return SettingsDefaults.CACHE_EXPIRATION
        try:
            int_value = int(v)  # type: ignore[reportArgumentType]
            if int_value < 0:
                raise SmarterConfigurationError(f"cache_expiration {int_value} must be a positive integer.")
            return int_value
        except ValueError as e:
            raise SmarterConfigurationError("could not validate cache_expiration") from e

    chat_cache_expiration: int = Field(
        SettingsDefaults.CHAT_CACHE_EXPIRATION,
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
    :default: Value from ``SettingsDefaults.CHAT_CACHE_EXPIRATION``
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
        if v in [None, ""]:
            return SettingsDefaults.CHAT_CACHE_EXPIRATION
        try:
            int_value = int(v)  # type: ignore[reportArgumentType]
            if int_value < 0:
                raise SmarterConfigurationError(f"chat_cache_expiration {int_value} must be a positive integer.")
            return int_value
        except ValueError as e:
            raise SmarterConfigurationError("could not validate chat_cache_expiration") from e

    configure_beta_account: bool = Field(
        SettingsDefaults.CONFIGURE_BETA_ACCOUNT,
        description="True if beta account should be added to CD-CD processes.",
        title="Configure Beta Account",
    )
    """
    True if beta account should be added to CD-CD processes.
    This setting indicates whether a beta account should be included
    in continuous deployment and continuous delivery processes.
    Enabling this setting gives you a way to provide early access
    to new features, in production but with controlled access to a
    select set of users.

    When enabled, the platform will automatically create and manage
    a beta account during deployment processes. Namely, it will
    maintain the built-in example AI resources, which are a common
    means of demonstrating new features.

    :raises SmarterConfigurationError: If the value is not a boolean.

    :type: bool
    :default: False
    """

    @before_field_validator("configure_beta_account")
    def parse_configure_beta_account(cls, v: Optional[Union[bool, str]]) -> bool:
        """Validates the 'configure_beta_account' field.
        Args:
            v (Optional[Union[bool, str]]): the configure_beta_account value to validate
        Returns:
            bool: The validated configure_beta_account.
        """
        if isinstance(v, bool):
            return v
        if v in [None, ""]:
            return SettingsDefaults.CONFIGURE_BETA_ACCOUNT
        if isinstance(v, str):
            return v.lower() in ["true", "1", "t", "y", "yes"]

        raise SmarterConfigurationError(f"could not validate configure_beta_account: {v}")

    configure_ubc_account: bool = Field(
        SettingsDefaults.CONFIGURE_UBC_ACCOUNT,
        description="True if UBC account should be added to CD-CD processes.",
        title="Configure UBC Account",
    )
    """
    True if UBC account should be added to CD-CD processes.
    This setting indicates whether a UBC account should be included
    in continuous deployment and continuous delivery processes.
    Enabling this setting allows for testing and validation of new features
    in a UBC environment before they are released to production.

    :type: bool
    :default: Value from ``SettingsDefaults.CONFIGURE_UBC_ACCOUNT``
    :raises SmarterConfigurationError: If the value is not a boolean.
    """

    @before_field_validator("configure_ubc_account")
    def parse_configure_ubc_account(cls, v: Optional[Union[bool, str]]) -> bool:
        """
        Validates the 'configure_ubc_account' field.
        Args: v (Optional[Union[bool, str]]): the configure_ubc_account value to validate
        Returns: bool: The validated configure_ubc_account.
        """
        if isinstance(v, bool):
            return v
        if v in [None, ""]:
            return SettingsDefaults.CONFIGURE_UBC_ACCOUNT
        if isinstance(v, str):
            return v.lower() in ["true", "1", "t", "y", "yes"]

        raise SmarterConfigurationError(f"could not validate configure_ubc_account: {v}")

    chatbot_cache_expiration: int = Field(
        SettingsDefaults.CHATBOT_CACHE_EXPIRATION,
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
    :default: Value from ``SettingsDefaults.CHATBOT_CACHE_EXPIRATION``
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
        if v in [None, ""]:
            return SettingsDefaults.CHATBOT_CACHE_EXPIRATION
        try:
            int_value = int(v)  # type: ignore[reportArgumentType]
            if int_value < 0:
                raise SmarterConfigurationError(f"chatbot_cache_expiration {int_value} must be a positive integer.")
            return int_value
        except ValueError as e:
            raise SmarterConfigurationError("could not validate chatbot_cache_expiration") from e

    chatbot_max_returned_history: int = Field(
        SettingsDefaults.CHATBOT_MAX_RETURNED_HISTORY,
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
    :default: Value from ``SettingsDefaults.CHATBOT_MAX_RETURNED_HISTORY``
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
        if v in [None, ""]:
            return SettingsDefaults.CHATBOT_MAX_RETURNED_HISTORY
        try:
            int_value = int(v)  # type: ignore[reportArgumentType]
            if int_value < 0:
                raise SmarterConfigurationError(f"chatbot_max_returned_history {int_value} must be a positive integer.")
            return int_value
        except ValueError as e:
            raise SmarterConfigurationError("could not validate chatbot_max_returned_history") from e

    chatbot_tasks_create_dns_record: bool = Field(
        SettingsDefaults.CHATBOT_TASKS_CREATE_DNS_RECORD,
        description="True if DNS records should be created for chatbot tasks.",
        title="Chatbot Tasks Create DNS Record",
    )
    """
    Set these to true if we *DO NOT* place a wildcard A record in the customer API domain
    requiring that every chatbot have its own A record. This is the default behavior.
    For programmatically creating DNS records in AWS Route53 during ChatBot deployment.

    :type: bool
    :default: Value from ``SettingsDefaults.CHATBOT_TASKS_CREATE_DNS_RECORD``
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
        if v in [None, ""]:
            return SettingsDefaults.CHATBOT_TASKS_CREATE_DNS_RECORD
        if isinstance(v, str):
            return v.lower() in ["true", "1", "t", "y", "yes"]

        raise SmarterConfigurationError(f"could not validate chatbot_tasks_create_dns_record: {v}")

    chatbot_tasks_create_ingress_manifest: bool = Field(
        SettingsDefaults.CHATBOT_TASKS_CREATE_INGRESS_MANIFEST,
        description="True if ingress manifests should be created for chatbot tasks.",
        title="Chatbot Tasks Create Ingress Manifest",
    )
    """
    True if ingress manifests should be created for chatbot tasks.
    For programmatically creating ingress manifests during ChatBot deployment.
    :type: bool
    :default: Value from ``SettingsDefaults.CHATBOT_TASKS_CREATE_INGRESS_MANIFEST``
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
        if v in [None, ""]:
            return SettingsDefaults.CHATBOT_TASKS_CREATE_INGRESS_MANIFEST
        if isinstance(v, str):
            return v.lower() in ["true", "1", "t", "y", "yes"]

        raise SmarterConfigurationError(f"could not validate chatbot_tasks_create_ingress_manifest: {v}")

    chatbot_tasks_default_ttl: int = Field(
        SettingsDefaults.CHATBOT_TASKS_DEFAULT_TTL,
        description="Default TTL (time to live) for DNS records created in AWS Route53 during ChatBot deployment.",
        title="Chatbot Tasks Default TTL",
        ge=0,
    )
    """
    Default TTL (time to live) for DNS records created in AWS Route53 during ChatBot deployment.
    :type: int
    :default: Value from ``SettingsDefaults.CHATBOT_TASKS_DEFAULT_TTL``
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
        if v in [None, ""]:
            return SettingsDefaults.CHATBOT_TASKS_DEFAULT_TTL
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
        SettingsDefaults.CHATBOT_TASKS_CELERY_MAX_RETRIES,
        gt=0,
        description="Maximum number of retries for chatbot tasks in Celery.",
        title="Chatbot Tasks Celery Max Retries",
    )
    """
    Maximum number of retries for chatbot tasks in Celery.
    :type: int
    :default: Value from ``SettingsDefaults.CHATBOT_TASKS_CELERY_MAX_RETRIES``
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
        if v in [None, ""]:
            return SettingsDefaults.CHATBOT_TASKS_CELERY_MAX_RETRIES
        try:
            int_value = int(v)  # type: ignore[reportArgumentType]
            return int_value
        except ValueError as e:
            raise SmarterConfigurationError(f"could not validate chatbot_tasks_celery_max_retries: {v}") from e

    chatbot_tasks_celery_retry_backoff: bool = Field(
        SettingsDefaults.CHATBOT_TASKS_CELERY_RETRY_BACKOFF,
        description="If True, enables exponential backoff for Celery task retries related to ChatBot deployment and management",
        title="Chatbot Tasks Celery Retry Backoff",
    )
    """
    If True, enables exponential backoff for Celery task retries related to ChatBot deployment and management.
    :type: bool
    :default: Value from ``SettingsDefaults.CHATBOT_TASKS_CELERY_RETRY_BACKOFF``
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
        if v in [None, ""]:
            return SettingsDefaults.CHATBOT_TASKS_CELERY_RETRY_BACKOFF
        if isinstance(v, str):
            return v.lower() in ["true", "1", "t", "y", "yes"]

        raise SmarterConfigurationError(f"could not validate chatbot_tasks_celery_retry_backoff: {v}")

    chatbot_tasks_celery_task_queue: str = Field(
        SettingsDefaults.CHATBOT_TASKS_CELERY_TASK_QUEUE,
        description="The Celery task queue name for chatbot tasks.",
        title="Chatbot Tasks Celery Task Queue",
    )
    """
    The Celery task queue name for chatbot tasks.
    :type: str
    :default: Value from ``SettingsDefaults.CHATBOT_TASKS_CELERY_TASK_QUEUE``
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
        if v in [None, ""]:
            return SettingsDefaults.CHATBOT_TASKS_CELERY_TASK_QUEUE

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"chatbot_tasks_celery_task_queue of type {type(v)} is not a str: {v}")

        return v

    plugin_max_data_results: int = Field(
        SettingsDefaults.PLUGIN_MAX_DATA_RESULTS,
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
    :default: Value from ``SettingsDefaults.PLUGIN_MAX_DATA_RESULTS``
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
        if v in [None, ""]:
            return SettingsDefaults.PLUGIN_MAX_DATA_RESULTS
        try:
            int_value = int(v)  # type: ignore[reportArgumentType]
            if int_value < 0:
                raise SmarterConfigurationError(f"plugin_max_data_results {int_value} must be a positive integer.")
            return int_value
        except ValueError as e:
            raise SmarterConfigurationError(f"could not validate plugin_max_data_results: {v}") from e

    sensitive_files_amnesty_patterns: List[Pattern] = Field(
        SettingsDefaults.SENSITIVE_FILES_AMNESTY_PATTERNS,
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
    :default: Value from ``SettingsDefaults.SENSITIVE_FILES_AMNESTY_PATTERNS``
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
        if v in [None, ""]:
            return SettingsDefaults.SENSITIVE_FILES_AMNESTY_PATTERNS
        if isinstance(v, str):
            try:
                return [re.compile(v)]
            except re.error as e:
                raise SmarterConfigurationError(f"Invalid regex pattern: {v}") from e

        raise SmarterConfigurationError(f"could not validate sensitive_files_amnesty_patterns: {v}")

    debug_mode: bool = Field(
        SettingsDefaults.DEBUG_MODE,
        description="True if debug mode is enabled. This enables verbose logging and other debug features.",
        title="Debug Mode",
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
        if v in [None, ""]:
            return SettingsDefaults.DEBUG_MODE
        if isinstance(v, str):
            return v.lower() in ["true", "1", "t", "y", "yes"]

        raise SmarterConfigurationError(f"could not validate debug_mode: {v}")

    dump_defaults: bool = Field(
        SettingsDefaults.DUMP_DEFAULTS,
        description="True if default values should be dumped for debugging purposes.",
        title="Dump Defaults",
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
        if v in [None, ""]:
            return SettingsDefaults.DUMP_DEFAULTS
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
        SettingsDefaults.DEVELOPER_MODE,
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
    :default: Value from ``SettingsDefaults.DEVELOPER_MODE``
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
        if v in [None, ""]:
            return SettingsDefaults.DEVELOPER_MODE
        if isinstance(v, str):
            return v.lower() in ["true", "1", "t", "y", "yes"]

        raise SmarterConfigurationError(f"could not validate developer_mode: {v}")

    django_default_file_storage: str = Field(
        SettingsDefaults.DJANGO_DEFAULT_FILE_STORAGE,
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
    :default: Value from ``SettingsDefaults.DJANGO_DEFAULT_FILE_STORAGE``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    email_admin: EmailStr = Field(
        SettingsDefaults.EMAIL_ADMIN,
        description="The administrator email address used for system notifications and alerts.",
        examples=["admin@example.com"],
        title="Administrator Email Address",
    )
    """
    The administrator email address used for system notifications and alerts.
    This email address is used as the primary contact for system notifications,
    alerts, and other administrative communications related to the platform.

    :type: str
    :default: Value from ``SettingsDefaults.EMAIL_ADMIN``
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
        if v in [None, ""]:
            return SettingsDefaults.EMAIL_ADMIN
        if not isinstance(v, str):
            raise SmarterConfigurationError(f"email_admin is not a valid EmailStr: {v}")
        return v

    environment: str = Field(
        SettingsDefaults.ENVIRONMENT,
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
    :default: Value from ``SettingsDefaults.ENVIRONMENT``
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
        if v in [None, ""]:
            return SettingsDefaults.ENVIRONMENT
        if not isinstance(v, str):
            raise SmarterConfigurationError(f"environment of type {type(v)} is not a str: {v}")
        return v

    fernet_encryption_key: SecretStr = Field(
        SettingsDefaults.FERNET_ENCRYPTION_KEY,
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
    :default: Value from ``SettingsDefaults.FERNET_ENCRYPTION_KEY``
    :raises SmarterConfigurationError: If the value is not a valid Fernet key.
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
            return SettingsDefaults.FERNET_ENCRYPTION_KEY

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
        SettingsDefaults.GEMINI_API_KEY,
        description="The API key for Google Gemini services. Masked by pydantic SecretStr.",
        examples=["sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"],
        title="Google Gemini API Key",
    )
    """
    The API key for Google Gemini services. Masked by pydantic SecretStr.
    This setting provides the API key used to authenticate with Google Gemini services.
    It is required for accessing Gemini's APIs and services.

    :type: SecretStr
    :default: Value from ``SettingsDefaults.GEMINI_API_KEY``
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
        if str(v) in [None, ""]:
            return SettingsDefaults.GEMINI_API_KEY
        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError(f"gemini_api_key of type {type(v)} is not a SecretStr.")

        return v

    google_maps_api_key: SecretStr = Field(
        SettingsDefaults.GOOGLE_MAPS_API_KEY,
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
    :default: Value from ``SettingsDefaults.GOOGLE_MAPS_API_KEY``
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
        if str(v) in [None, ""]:
            return SettingsDefaults.GOOGLE_MAPS_API_KEY
        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError(f"google_maps_api_key of type {type(v)} is not a SecretStr.")
        return v

    google_service_account: SecretStr = Field(
        SettingsDefaults.GOOGLE_SERVICE_ACCOUNT,
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
    :default: Value from ``SettingsDefaults.GOOGLE_SERVICE_ACCOUNT``
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
            return SettingsDefaults.GOOGLE_SERVICE_ACCOUNT

        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError(f"google_service_account of type {type(v)} is not a SecretStr.")
        return v

    internal_ip_prefixes: List[str] = Field(
        SettingsDefaults.INTERNAL_IP_PREFIXES,
        description="A list of internal IP prefixes used for security and middleware features.",
        examples=SettingsDefaults.INTERNAL_IP_PREFIXES,
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
    :default: Value from ``SettingsDefaults.INTERNAL_IP_PREFIXES``
    :raises SmarterConfigurationError: If the value is not a list of strings matching SettingsDefaults.INTERNAL_IP_PREFIXES
    """

    @before_field_validator("internal_ip_prefixes")
    def validate_internal_ip_prefixes(cls, v: Optional[List[str]]) -> List[str]:
        """Validates the `internal_ip_prefixes` field.

        Args:
            v (Optional[List[str]]): The internal IP prefixes value to validate.

        Returns:
            List[str]: The validated internal IP prefixes.
        """
        if v in [None, ""]:
            return SettingsDefaults.INTERNAL_IP_PREFIXES

        if not isinstance(v, list):
            raise SmarterConfigurationError(f"internal_ip_prefixes of type {type(v)} is not a list: {v}")
        return v

    log_level: int = Field(
        SettingsDefaults.LOG_LEVEL,
        ge=0,
        le=50,
        description="The logging level for the platform based on Python logging levels: logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL",
        examples=[logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL],
        title="Logging Level",
    )

    llama_api_key: SecretStr = Field(
        SettingsDefaults.LLAMA_API_KEY,
        description="The API key for LLaMA services. Masked by pydantic SecretStr.",
        examples=["sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"],
        title="LLaMA API Key",
    )
    """
    The API key for LLaMA services. Masked by pydantic SecretStr.
    This setting provides the API key used to authenticate with LLaMA services.
    It is required for accessing LLaMA's APIs and services.

    :type: SecretStr
    :default: Value from ``SettingsDefaults.LLAMA_API_KEY``
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
        if str(v) in [None, ""]:
            return SettingsDefaults.LLAMA_API_KEY

        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError(f"llama_api_key of type {type(v)} is not a SecretStr")
        return v

    local_hosts: List[str] = Field(
        SettingsDefaults.LOCAL_HOSTS,
        description="A list of hostnames considered local for development and testing purposes.",
        examples=SettingsDefaults.LOCAL_HOSTS,
        title="Local Hosts",
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

    @before_field_validator("local_hosts")
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
            raise SmarterConfigurationError(f"local_hosts of type {type(v)} is not a list: {v}")
        return v

    langchain_memory_key: Optional[str] = Field(
        SettingsDefaults.LANGCHAIN_MEMORY_KEY,
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
    :default: Value from ``SettingsDefaults.LANGCHAIN_MEMORY_KEY``
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
        if str(v) in [None, ""] and SettingsDefaults.LANGCHAIN_MEMORY_KEY is not None:
            return SettingsDefaults.LANGCHAIN_MEMORY_KEY
        return str(v)

    llm_default_provider: str = Field(
        SettingsDefaults.LLM_DEFAULT_PROVIDER,
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
    :default: Value from ``SettingsDefaults.LLM_DEFAULT_PROVIDER``
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
        if str(v) in [None, ""] and SettingsDefaults.LLM_DEFAULT_PROVIDER is not None:
            return SettingsDefaults.LLM_DEFAULT_PROVIDER

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"llm_default_provider of type {type(v)} is not a str: {v}")
        return v

    llm_default_model: str = Field(
        SettingsDefaults.LLM_DEFAULT_MODEL,
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
    :default: Value from ``SettingsDefaults.LLM_DEFAULT_MODEL``
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
        if str(v) in [None, ""] and SettingsDefaults.LLM_DEFAULT_MODEL is not None:
            return SettingsDefaults.LLM_DEFAULT_MODEL

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"llm_default_model of type {type(v)} is not a str: {v}")
        return v

    llm_default_system_role: str = Field(
        SettingsDefaults.LLM_DEFAULT_SYSTEM_ROLE,
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
    :default: Value from ``SettingsDefaults.LLM_DEFAULT_SYSTEM_ROLE``
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
        if str(v) in [None, ""] and SettingsDefaults.LLM_DEFAULT_SYSTEM_ROLE is not None:
            return SettingsDefaults.LLM_DEFAULT_SYSTEM_ROLE

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"llm_default_system_role of type {type(v)} is not a str: {v}")
        return v

    llm_default_temperature: float = Field(
        SettingsDefaults.LLM_DEFAULT_TEMPERATURE,
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
    :default: Value from ``SettingsDefaults.LLM_DEFAULT_TEMPERATURE``
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
        if v in [None, ""]:
            return SettingsDefaults.LLM_DEFAULT_TEMPERATURE
        try:
            retval = float(v)  # type: ignore
            return retval
        except (TypeError, ValueError) as e:
            raise SmarterConfigurationError(f"llm_default_temperature of type {type(v)} is not a float: {v}") from e

    llm_default_max_tokens: int = Field(
        SettingsDefaults.LLM_DEFAULT_MAX_TOKENS,
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
    :default: Value from ``SettingsDefaults.LLM_DEFAULT_MAX_TOKENS``
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
        if v in [None, ""]:
            return SettingsDefaults.LLM_DEFAULT_MAX_TOKENS

        try:
            retval = int(v)  # type: ignore
            return retval
        except (TypeError, ValueError) as e:
            raise SmarterConfigurationError(f"llm_default_max_tokens of type {type(v)} is not an int: {v}") from e

    logo: Optional[HttpUrl] = Field(
        SettingsDefaults.LOGO,
        description="The URL to the platform's logo image.",
        examples=["https://cdn.example.com/logo.png"],
        title="Platform Logo URL",
    )
    """
    The URL to the platform's logo image.
    This setting specifies the web address of the logo image used in the platform's user interface.
    It should be a valid URL pointing to an external image resource accessible by the frontend.

    :type: Optional[str]
    :default: Value from ``SettingsDefaults.LOGO``
    :raises SmarterConfigurationError: If the value is not a valid URL string.
    """

    @before_field_validator("logo")
    def validate_logo(cls, v: Optional[HttpUrl]) -> HttpUrl:
        """Validates the `logo` field.

        Args:
            v (Optional[HttpUrl]): The logo value to validate.

        Returns:
            HttpUrl: The validated logo.
        """
        if v is None:
            return SettingsDefaults.LOGO
        return v

    mailchimp_api_key: Optional[SecretStr] = Field(
        SettingsDefaults.MAILCHIMP_API_KEY,
        description="The API key for Mailchimp services. Masked by pydantic SecretStr.",
        examples=["sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"],
        title="Mailchimp API Key",
    )
    """
    The API key for Mailchimp services. Masked by pydantic SecretStr.
    This setting provides the API key used to authenticate with Mailchimp services.
    It is required for accessing Mailchimp's APIs and services.

    :type: Optional[SecretStr]
    :default: Value from ``SettingsDefaults.MAILCHIMP_API_KEY``
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
        if str(v) in [None, ""] and SettingsDefaults.MAILCHIMP_API_KEY is not None:
            return SettingsDefaults.MAILCHIMP_API_KEY

        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError(f"mailchimp_api_key of type {type(v)} is not a SecretStr")
        return v

    mailchimp_list_id: Optional[str] = Field(
        SettingsDefaults.MAILCHIMP_LIST_ID,
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
    :default: Value from ``SettingsDefaults.MAILCHIMP_LIST_ID``
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
        if str(v) in [None, ""] and SettingsDefaults.MAILCHIMP_LIST_ID is not None:
            return SettingsDefaults.MAILCHIMP_LIST_ID
        return v

    marketing_site_url: Optional[HttpUrl] = Field(
        SettingsDefaults.MARKETING_SITE_URL,
        description="The URL to the platform's marketing site.",
        examples=["https://www.example.com"],
        title="Marketing Site URL",
    )
    """
    The URL to the platform's marketing site.
    This setting specifies the web address of the marketing site associated
    with the platform. It should be a valid URL pointing to an external website.

    :type: Optional[httpHttpUrl]
    :default: Value from ``SettingsDefaults.MARKETING_SITE_URL``
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
        if str(v) in [None, ""] and SettingsDefaults.MARKETING_SITE_URL is not None:
            return SettingsDefaults.MARKETING_SITE_URL
        return v

    openai_api_organization: Optional[str] = Field(
        SettingsDefaults.OPENAI_API_ORGANIZATION,
        description="The OpenAI API organization ID.",
        examples=["org-xxxxxxxxxxxxxxxx"],
        title="OpenAI API Organization ID",
    )
    """
    The OpenAI API organization ID.
    This setting specifies the organization ID used when making requests to the OpenAI API.
    It is used to associate API requests with a specific organization account.

    :type: Optional[str]
    :default: Value from ``SettingsDefaults.OPENAI_API_ORGANIZATION``
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
        if str(v) in [None, ""] and SettingsDefaults.OPENAI_API_ORGANIZATION is not None:
            return SettingsDefaults.OPENAI_API_ORGANIZATION

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"openai_api_organization of type {type(v)} is not a str: {v}")
        return v

    openai_api_key: SecretStr = Field(
        SettingsDefaults.OPENAI_API_KEY,
        description="The API key for OpenAI services. Masked by pydantic SecretStr.",
        examples=["sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"],
        title="OpenAI API Key",
    )
    """
    The API key for OpenAI services. Masked by pydantic SecretStr.
    This setting provides the API key used to authenticate with OpenAI services.
    It is required for accessing OpenAI's APIs and services.

    :type: SecretStr
    :default: Value from ``SettingsDefaults.OPENAI_API_KEY``
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
        if str(v) in [None, ""] and SettingsDefaults.OPENAI_API_KEY is not None:
            return SettingsDefaults.OPENAI_API_KEY

        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError(f"openai_api_key of type {type(v)} is not a SecretStr")

        return v

    openai_endpoint_image_n: Optional[int] = Field(
        SettingsDefaults.OPENAI_ENDPOINT_IMAGE_N,
        description="The number of images to generate per request to the OpenAI image endpoint.",
        examples=[1, 2, 4],
        title="OpenAI Endpoint Image Number",
    )
    """
    The number of images to generate per request to the OpenAI image endpoint.
    This setting specifies how many images should be generated in response to
    a single request to the OpenAI image generation API.

    :type: Optional[int]
    :default: Value from ``SettingsDefaults.OPENAI_ENDPOINT_IMAGE_N``
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
        if str(v) in [None, ""] and SettingsDefaults.OPENAI_ENDPOINT_IMAGE_N is not None:
            return SettingsDefaults.OPENAI_ENDPOINT_IMAGE_N
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
        SettingsDefaults.OPENAI_ENDPOINT_IMAGE_SIZE,
        description="The size of images to generate from the OpenAI image endpoint.",
        examples=["256x256", "512x512", "1024x768"],
        title="OpenAI Endpoint Image Size",
    )
    """
    The size of images to generate from the OpenAI image endpoint.
    This setting specifies the dimensions of the images to be generated
    by the OpenAI image generation API.

    :type: Optional[str]
    :default: Value from ``SettingsDefaults.OPENAI_ENDPOINT_IMAGE_SIZE``
    :raises SmarterConfigurationError: If the value is not a valid image size string.
    """

    @before_field_validator("openai_endpoint_image_size")
    def validate_openai_endpoint_image_size(cls, v: Optional[str]) -> str:
        """Validates the `openai_endpoint_image_size` field.

        Args:
            v (Optional[str]): The OpenAI endpoint image size value to validate.

        Returns:
            str: The validated OpenAI endpoint image size.
        """
        if str(v) in [None, ""] and SettingsDefaults.OPENAI_ENDPOINT_IMAGE_SIZE is not None:
            return SettingsDefaults.OPENAI_ENDPOINT_IMAGE_SIZE

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"openai_endpoint_image_size of type {type(v)} is not a str: {v}")

        return v

    pinecone_api_key: SecretStr = Field(
        SettingsDefaults.PINECONE_API_KEY,
        description="The API key for Pinecone services. Masked by pydantic SecretStr.",
        examples=["xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"],
        title="Pinecone API Key",
    )
    """
    The API key for Pinecone services. Masked by pydantic SecretStr.
    This setting provides the API key used to authenticate with Pinecone services.
    It is required for accessing Pinecone's APIs and services.

    :type: SecretStr
    :default: Value from ``SettingsDefaults.PINECONE_API_KEY``
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
        if str(v) in [None, ""] and SettingsDefaults.PINECONE_API_KEY is not None:
            return SettingsDefaults.PINECONE_API_KEY

        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError(f"pinecone_api_key of type {type(v)} is not a SecretStr")

        return v

    root_domain: str = Field(
        SettingsDefaults.ROOT_DOMAIN,
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
    :default: Value from ``SettingsDefaults.ROOT_DOMAIN``
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
        if v in [None, ""]:
            return SettingsDefaults.ROOT_DOMAIN

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"root_domain of type {type(v)} is not a str: {v}")

        return v

    secret_key: Optional[SecretStr] = Field(
        SettingsDefaults.SECRET_KEY,
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
    :default: Value from ``SettingsDefaults.SECRET_KEY``
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
            return SettingsDefaults.SECRET_KEY

        if isinstance(v, str):
            try:
                v = SecretStr(v)
            except ValidationError as e:
                raise SmarterConfigurationError(f"secret_key {v} is not a valid SecretStr.") from e

        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError(f"secret_key {type(v)} is not a SecretStr.")
        return v

    settings_output: bool = Field(
        SettingsDefaults.SETTINGS_OUTPUT,
        description="Flag to enable or disable output of settings for debugging purposes.",
        examples=[True, False],
        title="Settings Output",
    )
    """
    If True, enables verbose output of Smarter run-time settings during Django startup.
    This will generate a multi-line header in new terminal windows launched from
    Kubernetes pods running Smarter services.

    :type: bool
    :default: Value from ``SettingsDefaults.SETTINGS_OUTPUT``
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
            return SettingsDefaults.SETTINGS_OUTPUT

        if not isinstance(v, bool):
            raise SmarterConfigurationError(f"settings_output of type {type(v)} is not a bool: {v}")
        return v

    shared_resource_identifier: str = Field(
        SettingsDefaults.SHARED_RESOURCE_IDENTIFIER,
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
    :default: Value from ``SettingsDefaults.SHARED_RESOURCE_IDENTIFIER``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("shared_resource_identifier")
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
            raise SmarterConfigurationError(f"shared_resource_identifier of type {type(v)} is not a str: {v}")

        return v

    smarter_mysql_test_database_secret_name: Optional[str] = Field(
        SettingsDefaults.MYSQL_TEST_DATABASE_SECRET_NAME,
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
    :default: Value from ``SettingsDefaults.MYSQL_TEST_DATABASE_SECRET_NAME`
    :raises SmarterConfigurationError: If the value is not a string.
    """

    smarter_mysql_test_database_password: Optional[SecretStr] = Field(
        SettingsDefaults.MYSQL_TEST_DATABASE_PASSWORD,
        description="The password for the Smarter MySQL test database. Used for example Smarter Plugins that are pre-installed on new installations.",
        examples=["your_password_here"],
        title="Smarter MySQL Test Database Password",
    )
    """
    The password for the Smarter MySQL test database. Used for example Smarter Plugins that are pre-installed on new installations.
    This setting provides the password used to connect to the Smarter MySQL test database.
    It is used by example Smarter Plugins that require access to a test database.

    :type: Optional[str]
    :default: Value from ``SettingsDefaults.MYSQL_TEST_DATABASE_PASSWORD``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    smarter_reactjs_app_loader_path: str = Field(
        SettingsDefaults.REACTJS_APP_LOADER_PATH,
        description="The path to the ReactJS app loader script.",
        examples=["/ui-chat/app-loader.js"],
        title="Smarter ReactJS App Loader Path",
    )
    """
    The path to the ReactJS app loader script.
    This setting specifies the URL path where the ReactJS application loader script is located.
    It is used to load the ReactJS frontend for the platform.

    :type: str
    :default: Value from ``SettingsDefaults.REACTJS_APP_LOADER_PATH``
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
        if v in [None, ""]:
            return SettingsDefaults.REACTJS_APP_LOADER_PATH

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"smarter_reactjs_app_loader_path of type {type(v)} is not a str: {v}")

        if not v.startswith("/"):
            raise SmarterConfigurationError(f"smarter_reactjs_app_loader_path must start with '/': {v}")
        if not v.endswith(".js"):
            raise SmarterConfigurationError(f"smarter_reactjs_app_loader_path must end with '.js': {v}")
        return v

    social_auth_google_oauth2_key: SecretStr = Field(
        SettingsDefaults.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY,
        description="The OAuth2 key for Google social authentication. Masked by pydantic SecretStr.",
        examples=["your-google-oauth2-key"],
        title="Google OAuth2 Key",
    )
    """
    The OAuth2 key for Google social authentication. Masked by pydantic SecretStr.
    This setting provides the OAuth2 client ID used for Google social authentication.
    It is required for enabling users to log in using their Google accounts.

    :type: SecretStr
    :default: Value from ``SettingsDefaults.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY
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
        if str(v) in [None, ""] and SettingsDefaults.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY:
            return SettingsDefaults.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY

        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError(f"social_auth_google_oauth2_key of type {type(v)} is not a SecretStr")
        return v

    social_auth_google_oauth2_secret: SecretStr = Field(
        SettingsDefaults.SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET,
        description="The OAuth2 secret for Google social authentication. Masked by pydantic SecretStr.",
        examples=["your-google-oauth2-secret"],
        title="Google OAuth2 Secret",
    )
    """
    The OAuth2 secret for Google social authentication. Masked by pydantic SecretStr.
    This setting provides the OAuth2 client secret used for Google social authentication.
    It is required for enabling users to log in using their Google accounts.

    :type: SecretStr
    :default: Value from ``SettingsDefaults.SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET
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
        if str(v) in [None, ""] and SettingsDefaults.SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET is not None:
            return SettingsDefaults.SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET

        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError(f"social_auth_google_oauth2_secret of type {type(v)} is not a SecretStr.")
        return v

    social_auth_github_key: SecretStr = Field(
        SettingsDefaults.SOCIAL_AUTH_GITHUB_KEY,
        description="The OAuth2 key for GitHub social authentication. Masked by pydantic SecretStr.",
        examples=["your-github-oauth2-key"],
        title="GitHub OAuth2 Key",
    )
    """
    The OAuth2 key for GitHub social authentication. Masked by pydantic SecretStr.
    This setting provides the OAuth2 client ID used for GitHub social authentication.
    It is required for enabling users to log in using their GitHub accounts.

    :type: SecretStr
    :default: Value from ``SettingsDefaults.SOCIAL_AUTH_GITHUB_KEY
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
        if str(v) in [None, ""] and SettingsDefaults.SOCIAL_AUTH_GITHUB_KEY is not None:
            return SettingsDefaults.SOCIAL_AUTH_GITHUB_KEY

        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError(f"social_auth_github_key of type {type(v)} is not a SecretStr")

        return v

    social_auth_github_secret: SecretStr = Field(
        SettingsDefaults.SOCIAL_AUTH_GITHUB_SECRET,
        description="The OAuth2 secret for GitHub social authentication. Masked by pydantic SecretStr.",
        examples=["your-github-oauth2-secret"],
        title="GitHub OAuth2 Secret",
    )
    """
    The OAuth2 secret for GitHub social authentication. Masked by pydantic SecretStr.
    This setting provides the OAuth2 client secret used for GitHub social authentication.
    It is required for enabling users to log in using their GitHub accounts.

    :type: SecretStr
    :default: Value from ``SettingsDefaults.SOCIAL_AUTH_GITHUB_SECRET
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
        if str(v) in [None, ""] and SettingsDefaults.SOCIAL_AUTH_GITHUB_SECRET is not None:
            return SettingsDefaults.SOCIAL_AUTH_GITHUB_SECRET

        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError(f"social_auth_github_secret of type {type(v)} is not a SecretStr.")
        return v

    social_auth_linkedin_oauth2_key: SecretStr = Field(
        SettingsDefaults.SOCIAL_AUTH_LINKEDIN_OAUTH2_KEY,
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
    :default: Value from ``SettingsDefaults.SOCIAL_AUTH_LINKEDIN_OAUTH2``
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
        if str(v) in [None, ""] and SettingsDefaults.SOCIAL_AUTH_LINKEDIN_OAUTH2_KEY is not None:
            return SettingsDefaults.SOCIAL_AUTH_LINKEDIN_OAUTH2_KEY
        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError(f"social_auth_linkedin_oauth2_key of type {type(v)} is not a SecretStr.")
        return v

    social_auth_linkedin_oauth2_secret: SecretStr = Field(
        SettingsDefaults.SOCIAL_AUTH_LINKEDIN_OAUTH2_SECRET,
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
    :default: Value from ``SettingsDefaults.SOCIAL_AUTH_LINKEDIN_OAUTH2
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
        if str(v) in [None, ""] and SettingsDefaults.SOCIAL_AUTH_LINKEDIN_OAUTH2_SECRET is not None:
            return SettingsDefaults.SOCIAL_AUTH_LINKEDIN_OAUTH2_SECRET
        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError(f"social_auth_linkedin_oauth2_secret of type {type(v)} is not a SecretStr.")
        return v

    smtp_sender: Optional[EmailStr] = Field(
        SettingsDefaults.SMTP_SENDER,
        description="The sender email address for SMTP emails.",
        examples=["sender@example.com"],
        title="SMTP Sender Email Address",
    )
    """
    The sender email address for SMTP emails.
    This setting specifies the email address that will appear as the sender
    in outgoing SMTP emails sent by the platform.

    :type: Optional[EmailStr]
    :default: Value from ``SettingsDefaults.SMTP_SENDER``
    :raises SmarterConfigurationError: If the value is not a valid email address.
    """

    smarter_mysql_test_database_secret_name: Optional[str] = Field(
        SettingsDefaults.MYSQL_TEST_DATABASE_SECRET_NAME,
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
    :default: Value from ``SettingsDefaults.MYSQL_TEST_DATABASE_SECRET_NAME``
    :raises SmarterConfigurationError: If the value is not a string. SMARTER_MYSQL_TEST_DATABASE_PASSWORD
    """

    smarter_mysql_test_database_password: Optional[SecretStr] = Field(
        SettingsDefaults.MYSQL_TEST_DATABASE_PASSWORD,
        description="The password for the Smarter MySQL test database. Used for example Smarter Plugins that are pre-installed on new installations.",
        examples=["smarter_test_user"],
        title="Smarter MySQL Test Database Password",
    )
    """
    The password for the Smarter MySQL test database. Used for example Smarter Plugins that are pre-installed on new installations.
    This setting provides the password used to connect to the Smarter MySQL test database.
    It is used by example Smarter Plugins that require access to a test database.
    :type: Optional[SecretStr]
    :default: Value from ``SettingsDefaults.MYSQL_TEST_DATABASE_PASSWORD``
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
        if v in [None, ""]:
            v = SettingsDefaults.SMTP_SENDER
            SmarterValidator.validate_domain(v)

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"smtp_sender of type {type(v)} is not a str: {v}")
        return v

    smtp_from_email: Optional[EmailStr] = Field(
        SettingsDefaults.SMTP_FROM_EMAIL,
        description="The from email address for SMTP emails.",
        examples=["from@example.com"],
        title="SMTP From Email Address",
    )
    """
    The from email address for SMTP emails.
    This setting specifies the email address that will appear in the "From"
    field of outgoing SMTP emails sent by the platform.

    :type: Optional[EmailStr]
    :default: Value from ``SettingsDefaults.SMTP_FROM_EMAIL``
    :raises SmarterConfigurationError: If the value is not a valid email address.
    """

    @before_field_validator("smtp_from_email")
    def validate_smtp_from_email(cls, v: Optional[EmailStr]) -> Optional[EmailStr]:
        """Validates the `smtp_from_email` field.

        Args:
            v (Optional[EmailStr]): The SMTP from email address to validate.

        Returns:
            Optional[EmailStr]: The validated SMTP from email address.
        """
        if v in [None, ""]:
            return SettingsDefaults.SMTP_FROM_EMAIL

        if isinstance(v, str):
            SmarterValidator.validate_email(v)
            return v

        raise SmarterConfigurationError(f"could not validate smtp_from_email: {v}")

    smtp_host: Optional[str] = Field(
        SettingsDefaults.SMTP_HOST,
        description="The SMTP host address for sending emails.",
        examples=["smtp.example.com"],
        title="SMTP Host Address",
    )
    """
    The SMTP host address for sending emails.
    This setting specifies the hostname or IP address of the SMTP server
    used for sending outgoing emails from the platform.

    :type: Optional[str]
    :default: Value from ``SettingsDefaults.SMTP_HOST``
    :raises SmarterConfigurationError: If the value is not a valid hostname or IP address
    """

    @before_field_validator("smtp_host")
    def validate_smtp_host(cls, v: Optional[str]) -> Optional[str]:
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
            raise SmarterConfigurationError(f"smtp_host of type {type(v)} is not a str: {v}")
        return v

    smtp_password: Optional[SecretStr] = Field(
        SettingsDefaults.SMTP_PASSWORD,
        description="The SMTP password for authentication. Assumed to be an AWS SES-generated IAM keypair secret.",
        examples=["your-smtp-password"],
        title="SMTP Password",
    )
    """
    The SMTP password for authentication.
    This setting provides the password used to authenticate with the SMTP server.
    It is required for sending emails through the SMTP server.

    :type: Optional[SecretStr]
    :default: Value from ``SettingsDefaults.SMTP_PASSWORD``
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
        if v in [None, ""]:
            return SettingsDefaults.SMTP_PASSWORD

        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError(f"smtp_password of type {type(v)} is not a SecretStr")
        return v

    smtp_port: Optional[int] = Field(
        SettingsDefaults.SMTP_PORT,
        description="The SMTP port for sending emails.",
        examples=[25, 465, 587],
        title="SMTP Port Number",
    )
    """
    The SMTP port for sending emails.
    This setting specifies the port number used to connect to the SMTP server
    for sending outgoing emails.

    :type: Optional[int]
    :default: Value from ``SettingsDefaults.SMTP_PORT``
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
        if v in [None, ""]:
            v = SettingsDefaults.SMTP_PORT
        try:
            retval = int(v)  # type: ignore
        except ValueError as e:
            raise SmarterValueError("Could not convert port number to int.") from e

        if not str(retval).isdigit() or not 1 <= int(retval) <= 65535:
            raise SmarterValueError("Invalid port number")

        return retval

    smtp_use_ssl: Optional[bool] = Field(
        SettingsDefaults.SMTP_USE_SSL,
        description="Whether to use SSL for SMTP connections.",
        examples=[True, False],
        title="SMTP Use SSL",
    )
    """
    Whether to use SSL for SMTP connections.
    This setting indicates whether SSL (Secure Sockets Layer) should be used
    when connecting to the SMTP server for sending emails.

    :type: Optional[bool]
    :default: Value from ``SettingsDefaults.SMTP_USE_SSL``
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
        if v in [None, ""]:
            return SettingsDefaults.SMTP_USE_SSL
        return str(v).lower() in ["true", "1", "yes", "on"]

    smtp_use_tls: Optional[bool] = Field(
        SettingsDefaults.SMTP_USE_TLS,
        description="Whether to use TLS for SMTP connections.",
        examples=[True, False],
        title="SMTP Use TLS",
    )
    """
    Whether to use TLS for SMTP connections.
    This setting indicates whether TLS (Transport Layer Security) should be used
    when connecting to the SMTP server for sending emails.

    :type: Optional[bool]
    :default: Value from ``SettingsDefaults.SMTP_USE_TLS``
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
        if v in [None, ""]:
            return SettingsDefaults.SMTP_USE_TLS
        return str(v).lower() in ["true", "1", "yes", "on"]

    smtp_username: Optional[SecretStr] = Field(
        SettingsDefaults.SMTP_USERNAME,
        description="The SMTP username for authentication. Assumed to be an AWS SES-generatred IAM keypair username.",
        examples=["your-smtp-username"],
        title="SMTP Username",
    )
    """
    The SMTP username for authentication.
    This setting provides the username used to authenticate with the SMTP server.
    It is required for sending emails through the SMTP server.

    :type: Optional[str]
    :default: Value from ``SettingsDefaults.SMTP_USERNAME``
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
            return SettingsDefaults.SMTP_USERNAME
        return v

    stripe_live_secret_key: Optional[SecretStr] = Field(
        SettingsDefaults.STRIPE_LIVE_SECRET_KEY,
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
    :default: Value from ``SettingsDefaults.STRIPE_LIVE_SECRET_KEY``
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
            return SettingsDefaults.STRIPE_LIVE_SECRET_KEY

        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError(f"stripe_live_secret_key of type {type(v)} is not a SecretStr.")
        return v

    stripe_test_secret_key: Optional[SecretStr] = Field(
        SettingsDefaults.STRIPE_TEST_SECRET_KEY,
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
    :default: Value from ``SettingsDefaults.STRIPE_TEST_SECRET_KEY``
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
            return SettingsDefaults.STRIPE_TEST_SECRET_KEY

        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError(f"stripe_test_secret_key of type {type(v)} is not a SecretStr.")
        return v

    ###########################################################################
    # Properties
    ###########################################################################

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
        if self.environment == SmarterEnvironments.LOCAL:
            return f"cdn.{SmarterEnvironments.ALPHA}.{self.platform_subdomain}.{self.root_domain}"
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
        if self.environment == SmarterEnvironments.LOCAL:
            return "localhost:9357"
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
        return f"{self.platform_name}-{self.platform_subdomain}-{self.environment}"

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
            'api.example.com'

        See Also:
            - SMARTER_API_SUBDOMAIN
            - smarter_settings.root_domain
            - smarter_settings.api_subdomain
        """
        return f"{self.api_subdomain}.{self.root_domain}"

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
        if self.environment == SmarterEnvironments.LOCAL:
            return f"{SMARTER_API_SUBDOMAIN}.localhost:9357"
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
        fallback_url = "https://cdn.platform.smarter.sh/ui-chat/app-loader.js"
        if check_smarter_reactjs_app_loader_url(intended_url):
            logger.error(
                "%s Could not retrieve the ReactJS app loader from %s. Falling back to %s. See https://github.com/smarter-sh/web-integration-example for details on configuring Smarter Chat.",
                logger_prefix,
                intended_url,
                fallback_url,
            )
            return intended_url
        elif check_smarter_reactjs_app_loader_url(fallback_url):
            logger.error(
                "%s Could not retrieve the ReactJS app loader from the fallback url %s.", logger_prefix, fallback_url
            )
            return fallback_url
        else:
            raise SmarterConfigurationError(
                f"Could not retrieve the ReactJS app loader from either {intended_url} or {fallback_url}. "
                "Please check your CDN configuration and internet connectivity."
            )

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

    def dump(self) -> dict:
        """
        Dump all settings. Useful for debugging and logging.

        Returns:
            dict: A dictionary containing all settings and their values.

        Example:
            >>> from smarter.lib import json
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


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get the singleton settings instance."""
    try:
        return Settings()
    except ValidationError as e:
        raise SmarterConfigurationError("Invalid configuration: " + str(e)) from e


smarter_settings = get_settings()

__all__ = ["smarter_settings"]
