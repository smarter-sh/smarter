"""
Default configuration values for Smarter platform settings.
"""

import base64  # library for base64 encoding and decoding
import logging  # library for logging messages
import os  # library for interacting with the operating system
import re  # library for regular expressions

# python stuff
import warnings  # library for issuing warning messages
from functools import lru_cache  # utility for caching function/method results
from typing import List, Optional, Pattern  # type hint utilities
from urllib.parse import urljoin  # library for URL manipulation

# 3rd party stuff
from pydantic import (
    EmailStr,
    HttpUrl,
    SecretStr,
)

from smarter.common.const import (
    SMARTER_DEFAULT_APP_LOADER_PATH,
    SMARTER_LOCAL_PORT,
    SMARTER_ORGANIZATION_NAME,
    SMARTER_PLATFORM_DEFAULT_SUBDOMAIN,
    SMARTER_PROJECT_CDN_URL,
    SmarterEnvironments,
)

# our stuff
from smarter.common.exceptions import SmarterConfigurationError
from smarter.common.helpers.console_helpers import formatted_text
from smarter.common.utils import (
    bool_environment_variable,
    generate_fernet_encryption_key,
)
from smarter.lib import json

from .const import DEFAULT_ROOT_DOMAIN
from .env import get_env
from .services import Services

logger = logging.getLogger(__name__)
logger_prefix = formatted_text(__name__ + ".SettingsDefaults()")


class DjangoPermittedStorages:
    """Django permitted storage backends"""

    AWS_S3 = "storages.backends.s3boto3.S3Boto3Storage"
    FILE_SYSTEM = "django.core.files.storage.FileSystemStorage"


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
    ALLOWED_HOSTS: List[str] = get_env("ALLOWED_HOSTS", ["localhost", "testserver"])
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

    BRANDING_CORPORATE_NAME: str = get_env("BRANDING_CORPORATE_NAME", SMARTER_ORGANIZATION_NAME)
    BRANDING_SUPPORT_PHONE_NUMBER: str = get_env("BRANDING_SUPPORT_PHONE_NUMBER", "(###) 555-1212")
    BRANDING_SUPPORT_EMAIL: EmailStr = get_env("BRANDING_SUPPORT_EMAIL", "lpm0073@gmail.com")
    BRANDING_ADDRESS1: str = get_env("BRANDING_ADDRESS1", "123 Main St, Anytown, USA")
    BRANDING_ADDRESS2: str = get_env("BRANDING_ADDRESS2", "Suite 100")
    BRANDING_CITY: str = get_env("BRANDING_CITY", "Anytown")
    BRANDING_STATE: str = get_env("BRANDING_STATE", "CA")
    BRANDING_POSTAL_CODE: str = get_env("BRANDING_POSTAL_CODE", "12345")
    BRANDING_COUNTRY: str = get_env("BRANDING_COUNTRY", "USA")
    BRANDING_CURRENCY: str = get_env("BRANDING_CURRENCY", "USD")
    BRANDING_TIMEZONE: str = get_env("BRANDING_TIMEZONE", "America/Denver")
    BRANDING_CONTACT_URL: Optional[HttpUrl] = get_env("BRANDING_CONTACT_URL", "https://lawrencemcdaniel.com/")
    BRANDING_SUPPORT_HOURS: str = get_env("BRANDING_SUPPORT_HOURS", "MON-FRI 9:00 AM - 5:00 PM GMT-6 (CST)")
    BRANDING_URL_FACEBOOK: Optional[HttpUrl] = get_env("BRANDING_URL_FACEBOOK", "https://facebook.com")
    BRANDING_URL_TWITTER: Optional[HttpUrl] = get_env("BRANDING_URL_TWITTER", "https://x.com/fullstackwlarry")
    BRANDING_URL_LINKEDIN: Optional[HttpUrl] = get_env(
        "BRANDING_URL_LINKEDIN", "https://www.linkedin.com/in/lawrencemcdaniel/"
    )

    CACHE_EXPIRATION: int = int(get_env("CACHE_EXPIRATION", 60 * 1))  # 1 minute
    CHAT_CACHE_EXPIRATION: int = int(get_env("CHAT_CACHE_EXPIRATION", 60 * 5))  # 5 minutes
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

    SENSITIVE_FILES_AMNESTY_PATTERNS: List[Pattern] = [
        re.compile(r"^/$"),
        re.compile(r"^/static(/.*)?$"),
        re.compile(r"^/api/v\d+(\.\d+)?/.+"),
        re.compile(r"^/dashboard(/.*)?$"),
        re.compile(r"^/docs/manifest(/.*)?$"),
        re.compile(r"^/docs/json-schema(/.*)?$"),
        re.compile(r"^/config/?$"),
        re.compile(r"^/login/?$"),
        re.compile(r"^/logout/?$"),
        re.compile(r"^/admin/?$"),
    ]

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

    ENABLE_FILE_DROP_ZONE: bool = bool_environment_variable("ENABLE_FILE_DROP_ZONE", True)
    ENABLE_VECTORSTORE: bool = bool_environment_variable("ENABLE_VECTORSTORE", True)
    ENABLE_TERMINAL_APP: bool = bool_environment_variable("ENABLE_TERMINAL_APP", True)

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

    FILE_DROP_ZONE_ENABLED = bool_environment_variable("FILE_DROP_ZONE_ENABLED", True)

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
    LOCAL_HOSTS += [host + f":{SMARTER_LOCAL_PORT}" for host in LOCAL_HOSTS]
    LOCAL_HOSTS.append("testserver")

    LOG_LEVEL: int = logging.DEBUG if get_env("DEBUG_MODE", False) else logging.INFO

    LOGO: HttpUrl = get_env("LOGO", urljoin(SMARTER_PROJECT_CDN_URL, "/images/logo/smarter-crop.png"))
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
    PLATFORM_SUBDOMAIN = get_env("PLATFORM_SUBDOMAIN", SMARTER_PLATFORM_DEFAULT_SUBDOMAIN)
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
    SMTP_FROM_EMAIL = get_env("SMTP_FROM_EMAIL", f"no-reply@{PLATFORM_SUBDOMAIN}.{ROOT_DOMAIN}", is_required=True)
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

    VERBOSE_LOGGING: bool = bool_environment_variable("VERBOSE_LOGGING", False)

    @classmethod
    def to_dict(cls):
        """Convert SettingsDefaults to dict"""
        return {
            key: value
            for key, value in SettingsDefaults.__dict__.items()
            if not key.startswith("__") and not callable(key) and key != "to_dict"
        }


@lru_cache(maxsize=1)
def get_settings_defaults() -> SettingsDefaults:
    """Get the singleton instance."""
    try:
        return SettingsDefaults()
    except Exception as e:
        raise SmarterConfigurationError("Invalid configuration: " + str(e)) from e


settings_defaults = get_settings_defaults()

__all__ = ["settings_defaults", "SettingsDefaults"]
