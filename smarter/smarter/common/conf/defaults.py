"""Default configuration values for Smarter platform settings."""

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
    AnyUrl,
    EmailStr,
    HttpUrl,
    SecretStr,
)

from smarter.common.const import (
    SMARTER_LOCAL_PORT,
    SmarterEnvironments,
)

# our stuff
from smarter.common.exceptions import SmarterConfigurationError
from smarter.common.utils.utils import (
    bool_environment_variable,
    generate_fernet_encryption_key,
)

from .const import DEFAULT_ROOT_DOMAIN
from .env import get_env, is_missing_value

logger = logging.getLogger(__name__)


def optional_secret_env(var_name: str) -> Optional[SecretStr]:
    """
    Return an optional secret from the environment, or None if it is missing or a placeholder.

    :param var_name: The environment variable, without the optional ``SMARTER_`` prefix.
    :returns: The secret, or None.
    """
    value = get_env(var_name, default=None, is_secret=True)
    return None if value is None or is_missing_value(value) else SecretStr(value)


GITHUB_TOKEN_NAMES = ("GITHUB_TOKEN", "GH_TOKEN", "GITHUB_API_TOKEN")
"""
The environment variables that hold the platform's GitHub token, in the order they are read.

``GITHUB_TOKEN`` is the name that GitHub Actions and most tools use, and ``GH_TOKEN`` is the GitHub
CLI's. ``GITHUB_API_TOKEN`` is the name that Smarter used before, still read so that an existing
deployment keeps working. Each may also have the ``SMARTER_`` prefix.
"""


def github_token_env() -> Optional[SecretStr]:
    """
    Return the platform's GitHub token, from the first of :data:`GITHUB_TOKEN_NAMES` that is set.

    :returns: The token, or None if none of them is set, or each holds a placeholder.
    """
    for name in GITHUB_TOKEN_NAMES:
        token = optional_secret_env(name)
        if token is not None:
            return token
    return None


# pylint: disable=too-few-public-methods
class SettingsDefaults:
    """
    .. deprecated:: 2025.12.

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

    PLATFORM_ROOT_DOMAIN: str = get_env("PLATFORM_ROOT_DOMAIN", DEFAULT_ROOT_DOMAIN)

    # for liveness and readiness probes from kubernetes.
    # see https://stackoverflow.com/questions/40582423/how-to-fix-django-error-disallowedhost-at-invalid-http-host-header-you-m
    ALLOWED_HOSTS: List[str] = get_env("ALLOWED_HOSTS", ["localhost", "testserver"])

    # Account Manager's platform key, for its subscription status api. Optional: without it, a
    # multitenant platform asks without a key, which Account Manager answers only until it requires keys.
    ACCOUNT_MANAGER_API_KEY: Optional[SecretStr] = optional_secret_env("ACCOUNT_MANAGER_API_KEY")

    # the platform's superuser, which manage.py initialize_platform creates.
    PLATFORM_ADMIN_USERNAME: str = get_env("PLATFORM_ADMIN_USERNAME", "admin")
    PLATFORM_ADMIN_PASSWORD: Optional[SecretStr] = optional_secret_env("PLATFORM_ADMIN_PASSWORD")

    API_SCHEMA: str = get_env("API_SCHEMA", "http")

    # aws auth
    AWS_PROFILE = get_env("AWS_PROFILE", default=None)
    AWS_ACCESS_KEY_ID: Optional[SecretStr] = optional_secret_env("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: Optional[SecretStr] = optional_secret_env("AWS_SECRET_ACCESS_KEY")
    AWS_REGION = get_env("AWS_REGION", default=None)

    PLATFORM_CLOUD_PROVIDER: str = get_env("PLATFORM_CLOUD_PROVIDER", "aws")
    SUBSYSTEM_K8S_CLUSTER_NAME: Optional[str] = get_env("SUBSYSTEM_K8S_CLUSTER_NAME", default=None)
    APP_LLMHOST_NODE_ROLE_ARN = get_env("APP_LLMHOST_NODE_ROLE_ARN", default=None)
    APP_LLMHOST_NODE_SUBNET_IDS = get_env("APP_LLMHOST_NODE_SUBNET_IDS", default=[])

    # the apps' api keys: each app's manage.py initialize_* command stores them as Secrets.
    APP_PROVIDER_ANTHROPIC_API_KEY: Optional[SecretStr] = optional_secret_env("APP_PROVIDER_ANTHROPIC_API_KEY")
    APP_PROVIDER_COHERE_API_KEY: Optional[SecretStr] = optional_secret_env("APP_PROVIDER_COHERE_API_KEY")
    APP_PROVIDER_FIREWORKS_API_KEY: Optional[SecretStr] = optional_secret_env("APP_PROVIDER_FIREWORKS_API_KEY")
    APP_PROVIDER_GEMINI_API_KEY: Optional[SecretStr] = optional_secret_env("APP_PROVIDER_GEMINI_API_KEY")
    APP_PROVIDER_GOOGLE_MAPS_API_KEY: Optional[SecretStr] = optional_secret_env("APP_PROVIDER_GOOGLE_MAPS_API_KEY")
    APP_PROVIDER_GOOGLE_SERVICE_ACCOUNT_B64: Optional[SecretStr] = optional_secret_env(
        "APP_PROVIDER_GOOGLE_SERVICE_ACCOUNT_B64"
    )
    APP_PROVIDER_LLAMA_API_KEY: Optional[SecretStr] = optional_secret_env("APP_PROVIDER_LLAMA_API_KEY")
    APP_PROVIDER_MISTRAL_API_KEY: Optional[SecretStr] = optional_secret_env("APP_PROVIDER_MISTRAL_API_KEY")
    APP_PROVIDER_OPENAI_API_KEY: Optional[SecretStr] = optional_secret_env("APP_PROVIDER_OPENAI_API_KEY")
    APP_PROVIDER_TOGETHERAI_API_KEY: Optional[SecretStr] = optional_secret_env("APP_PROVIDER_TOGETHERAI_API_KEY")
    APP_LLMTOOL_BRAVE_SEARCH_API_KEY: Optional[SecretStr] = optional_secret_env("APP_LLMTOOL_BRAVE_SEARCH_API_KEY")
    APP_LLMTOOL_TAVILY_API_KEY: Optional[SecretStr] = optional_secret_env("APP_LLMTOOL_TAVILY_API_KEY")
    APP_VECTORSTORE_PINECONE_API_KEY: Optional[SecretStr] = optional_secret_env("APP_VECTORSTORE_PINECONE_API_KEY")
    APP_VECTORSTORE_QDRANT_CLOUD_API_KEY: Optional[SecretStr] = optional_secret_env(
        "APP_VECTORSTORE_QDRANT_CLOUD_API_KEY"
    )

    PLATFORM_BRANDING_APP_NAME: str = get_env("PLATFORM_BRANDING_APP_NAME", "Smarter")
    PLATFORM_BRANDING_PRODUCT_NAME: str = get_env("PLATFORM_BRANDING_PRODUCT_NAME", "The Smarter Project")
    PLATFORM_BRANDING_PRODUCT_DESCRIPTION: str = get_env(
        "PLATFORM_BRANDING_PRODUCT_DESCRIPTION",
        "An open source, no-code AI authoring platform designed for instructional use.",
    )
    PLATFORM_BRANDING_CDN_URL: HttpUrl = HttpUrl(get_env("PLATFORM_BRANDING_CDN_URL", "https://cdn.smarter.sh"))
    PLATFORM_BRANDING_DOCS_URL: HttpUrl = HttpUrl(get_env("PLATFORM_BRANDING_DOCS_URL", "https://docs.smarter.sh"))
    PLATFORM_BRANDING_BLOG_URL: HttpUrl = HttpUrl(get_env("PLATFORM_BRANDING_BLOG_URL", "https://blog.smarter.sh"))
    PLATFORM_BRANDING_CORPORATE_NAME: str = get_env("PLATFORM_BRANDING_CORPORATE_NAME", "Lawrence P. McDaniel")
    PLATFORM_BRANDING_SUPPORT_PHONE_NUMBER: str = get_env("PLATFORM_BRANDING_SUPPORT_PHONE_NUMBER", "(###) 555-1212")
    PLATFORM_BRANDING_SUPPORT_EMAIL: EmailStr = get_env("PLATFORM_BRANDING_SUPPORT_EMAIL", "lpm0073@gmail.com")
    PLATFORM_BRANDING_ADDRESS1: str = get_env("PLATFORM_BRANDING_ADDRESS1", "123 Main St, Anytown, USA")
    PLATFORM_BRANDING_ADDRESS2: str = get_env("PLATFORM_BRANDING_ADDRESS2", "Suite 100")
    PLATFORM_BRANDING_CITY: str = get_env("PLATFORM_BRANDING_CITY", "Anytown")
    PLATFORM_BRANDING_STATE: str = get_env("PLATFORM_BRANDING_STATE", "CA")
    PLATFORM_BRANDING_POSTAL_CODE: str = get_env("PLATFORM_BRANDING_POSTAL_CODE", "12345")
    PLATFORM_BRANDING_COUNTRY: str = get_env("PLATFORM_BRANDING_COUNTRY", "USA")
    PLATFORM_BRANDING_CURRENCY: str = get_env("PLATFORM_BRANDING_CURRENCY", "USD")
    PLATFORM_BRANDING_TIMEZONE: str = get_env("PLATFORM_BRANDING_TIMEZONE", "America/Denver")
    PLATFORM_BRANDING_CONTACT_URL: HttpUrl = HttpUrl(
        get_env("PLATFORM_BRANDING_CONTACT_URL", "https://lawrencemcdaniel.com/")
    )
    PLATFORM_BRANDING_PRIMARY_CONTACT: str = get_env("PLATFORM_BRANDING_PRIMARY_CONTACT", "Lawrence McDaniel")
    PLATFORM_BRANDING_SUPPORT_HOURS: str = get_env(
        "PLATFORM_BRANDING_SUPPORT_HOURS", "MON-FRI 9:00 AM - 5:00 PM GMT-6 (CST)"
    )
    PLATFORM_BRANDING_URL_FACEBOOK: HttpUrl = HttpUrl(get_env("PLATFORM_BRANDING_URL_FACEBOOK", "https://facebook.com"))
    PLATFORM_BRANDING_URL_TWITTER: HttpUrl = HttpUrl(
        get_env("PLATFORM_BRANDING_URL_TWITTER", "https://x.com/fullstackwlarry")
    )
    PLATFORM_BRANDING_URL_LINKEDIN: HttpUrl = HttpUrl(
        get_env("PLATFORM_BRANDING_URL_LINKEDIN", "https://www.linkedin.com/in/lawrencemcdaniel/")
    )
    PLATFORM_BRANDING_URL_SLACK: HttpUrl = HttpUrl(
        get_env(
            "PLATFORM_BRANDING_URL_SLACK",
            "https://join.slack.com/t/thesmarterproject/shared_invite/zt-4f0t6v46q-e2c5Of4hS4fBr_XwfQARCw",
        )
    )

    SUBSYSTEM_CACHE_EXPIRATION: int = int(get_env("SUBSYSTEM_CACHE_EXPIRATION", 60 * 1))  # 1 minute
    SUBSYSTEM_CACHE_CHAT_EXPIRATION: int = int(get_env("SUBSYSTEM_CACHE_CHAT_EXPIRATION", 60 * 5))  # 5 minutes
    CONFIGURE_UBC_ACCOUNT: bool = bool_environment_variable("CONFIGURE_UBC_ACCOUNT", False)
    SUBSYSTEM_CACHE_LISTVIEW_EXPIRATION: int = int(get_env("SUBSYSTEM_CACHE_LISTVIEW_EXPIRATION", 60 * 60))  # 1 hour
    SUBSYSTEM_CACHE_LLM_CLIENT_EXPIRATION: int = int(
        get_env("SUBSYSTEM_CACHE_LLM_CLIENT_EXPIRATION", 60 * 5)
    )  # 5 minutes
    MAX_TOOL_ROUNDS: int = int(get_env("MAX_TOOL_ROUNDS", 5))
    PROMPT_HISTORY_MAX_AGE: int = int(get_env("PROMPT_HISTORY_MAX_AGE", 90))  # days
    SUBSYSTEM_CACHE_PROMPT_RESPONSE_EXPIRATION: int = int(
        get_env("SUBSYSTEM_CACHE_PROMPT_RESPONSE_EXPIRATION", 60 * 60)
    )  # 1 hour
    APP_LLMCLIENT_TASKS_CREATE_DNS_RECORD: bool = bool_environment_variable(
        "APP_LLMCLIENT_TASKS_CREATE_DNS_RECORD", True
    )
    APP_LLMCLIENT_TASKS_CREATE_INGRESS_MANIFEST: bool = bool_environment_variable(
        "APP_LLMCLIENT_TASKS_CREATE_INGRESS_MANIFEST", True
    )
    APP_LLMCLIENT_TASKS_DEFAULT_TTL: int = get_env("APP_LLMCLIENT_TASKS_DEFAULT_TTL", 600)

    APP_LLMCLIENT_TASKS_CELERY_MAX_RETRIES: int = int(get_env("APP_LLMCLIENT_TASKS_CELERY_MAX_RETRIES", 3))
    APP_LLMCLIENT_TASKS_CELERY_RETRY_BACKOFF: bool = bool_environment_variable(
        "APP_LLMCLIENT_TASKS_CELERY_RETRY_BACKOFF", True
    )
    APP_LLMCLIENT_TASKS_CELERY_TASK_QUEUE: str = get_env(
        "APP_LLMCLIENT_TASKS_CELERY_TASK_QUEUE", "default_celery_task_queue"
    )
    APP_INFRASTRUCTURE_TASKS_CELERY_TASK_QUEUE: str = get_env(
        "APP_INFRASTRUCTURE_TASKS_CELERY_TASK_QUEUE", "infrastructure_celery_task_queue"
    )
    APP_LLMTOOL_PLUGIN_MAX_DATA_RESULTS: int = int(get_env("APP_LLMTOOL_PLUGIN_MAX_DATA_RESULTS", 50))
    APP_MCPSERVER_RATE_LIMIT: int = int(get_env("APP_MCPSERVER_RATE_LIMIT", 1200))  # requests per minute, per client IP
    APP_LLMTOOL_EXTENSION_REGISTRY_URL: str = get_env(
        "APP_LLMTOOL_EXTENSION_REGISTRY_URL", "https://smarter-sh.github.io/extensions-registry/index.json"
    )
    APP_LLMTOOL_EXTENSION_REGISTRY_PUBLIC_KEY: str = get_env("APP_LLMTOOL_EXTENSION_REGISTRY_PUBLIC_KEY", "")
    SUBSYSTEM_LOGGING_LOKI_URL: str = get_env(
        "SUBSYSTEM_LOGGING_LOKI_URL", ""
    )  # e.g. http://smarter-loki:3100. Empty: no pod log store
    # the user's own Django settings: see smarter.settings.user, which reads the same variable.
    USER_SETTINGS_FILE: str = get_env("USER_SETTINGS_FILE", "/home/smarter_user/user-settings/settings.yaml")

    PLATFORM_SENSITIVE_FILES_AMNESTY_PATTERNS: List[Pattern] = [
        re.compile(r"^/$"),
        re.compile(r"^/static(/.*)?$"),
        re.compile(r"^/api/v\d+(\.\d+)?/.+"),
        re.compile(r"^/api/web/.+"),
        re.compile(r"^/dashboard(/.*)?$"),
        re.compile(r"^/docs/manifest(/.*)?$"),
        re.compile(r"^/docs/json-schema(/.*)?$"),
        re.compile(r"^/config/?$"),
        re.compile(r"^/login/?$"),
        re.compile(r"^/admin/?$"),
    ]

    DEBUG_MODE: bool = bool_environment_variable("DEBUG_MODE", False)
    DEVELOPER_MODE: bool = bool_environment_variable("DEVELOPER_MODE", False)

    DUMP_DEFAULTS: bool = bool(get_env("DUMP_DEFAULTS", False))
    PLATFORM_EMAIL_ADMIN: EmailStr = get_env("PLATFORM_EMAIL_ADMIN", "admin@example.com")
    ENVIRONMENT = get_env("ENVIRONMENT", SmarterEnvironments.LOCAL)

    APP_CONNECTION_ENABLE: bool = bool_environment_variable("APP_CONNECTION_ENABLE", True)
    APP_GUARDRAIL_ENABLE: bool = bool_environment_variable("APP_GUARDRAIL_ENABLE", True)
    APP_LLMCLIENT_ENABLE: bool = bool_environment_variable("APP_LLMCLIENT_ENABLE", True)
    APP_LLMHOST_ENABLE: bool = bool_environment_variable("APP_LLMHOST_ENABLE", True)
    APP_LLMTOOL_ENABLE: bool = bool_environment_variable("APP_LLMTOOL_ENABLE", True)
    APP_MCPCLIENT_ENABLE: bool = bool_environment_variable("APP_MCPCLIENT_ENABLE", True)
    APP_ORCHESTRATOR_ENABLE: bool = bool_environment_variable("APP_ORCHESTRATOR_ENABLE", True)
    APP_PROVIDER_ENABLE: bool = bool_environment_variable("APP_PROVIDER_ENABLE", True)
    APP_SECRET_ENABLE: bool = bool_environment_variable("APP_SECRET_ENABLE", True)
    APP_VECTORSEARCH_ENABLE: bool = bool_environment_variable("APP_VECTORSEARCH_ENABLE", True)
    APP_VECTORSTORE_ENABLE: bool = bool_environment_variable("APP_VECTORSTORE_ENABLE", True)
    APP_DASHBOARD_MANIFEST_DROPZONE_ENABLE: bool = bool_environment_variable(
        "APP_DASHBOARD_MANIFEST_DROPZONE_ENABLE", True
    )
    APP_DASHBOARD_SERVER_LOGS_ENABLE: bool = bool_environment_variable("APP_DASHBOARD_SERVER_LOGS_ENABLE", True)
    APP_DASHBOARD_WEB_CONSOLE_TERMINAL_ENABLE: bool = bool_environment_variable(
        "APP_DASHBOARD_WEB_CONSOLE_TERMINAL_ENABLE", False
    )
    PLATFORM_STATIC_FILES_ON_CDN: bool = bool_environment_variable("PLATFORM_STATIC_FILES_ON_CDN", False)
    APP_DASHBOARD_PASSTHROUGH_PROMPT_ENABLE: bool = bool_environment_variable(
        "APP_DASHBOARD_PASSTHROUGH_PROMPT_ENABLE", True
    )
    APP_PROXY_ENABLE: bool = bool_environment_variable("APP_PROXY_ENABLE", True)

    fernet = get_env("PLATFORM_FERNET_ENCRYPTION_KEY", default=None, is_secret=True)
    if fernet is None:
        warnings.warn(
            "PLATFORM_FERNET_ENCRYPTION_KEY is not set. "
            "A new encryption key will be generated. This may cause existing encrypted data to become inaccessible. "
            "You can safely disregard this warning if this is a new installation, test environment or CI-CD process.",
            UserWarning,
        )
        fernet = generate_fernet_encryption_key()
    PLATFORM_FERNET_ENCRYPTION_KEY = SecretStr(fernet)

    GITHUB_TOKEN: Optional[SecretStr] = github_token_env()

    PLATFORM_INTERNAL_IP_PREFIXES: List[str] = get_env("PLATFORM_INTERNAL_IP_PREFIXES", ["192.168."])

    LLM_DEFAULT_PROVIDER = "openai"
    LLM_DEFAULT_MODEL = "gpt-6-luna"
    LLM_DEFAULT_SYSTEM_ROLE = (
        "You are a helpful llmclient. When given the opportunity to utilize "
        "function calling, you should always do so. This will allow you to "
        "provide the best possible responses to the user. If you are unable to "
        "provide a response, you should prompt the user for more information. If "
        "you are still unable to provide a response, you should inform the user "
        "that you are unable to help them at this time."
    )
    LLM_DEFAULT_TEMPERATURE = 1.0
    LLM_DEFAULT_MAX_TOKENS = 2048

    LOCAL_HOSTS = ["localhost", "127.0.0.1"]
    LOCAL_HOSTS += [host + f":{SMARTER_LOCAL_PORT}" for host in LOCAL_HOSTS]
    LOCAL_HOSTS.append("localhost:5173")  # for react dev server
    LOCAL_HOSTS.append("testserver")

    LOG_LEVEL: int = logging.DEBUG if get_env("DEBUG_MODE", False) else logging.INFO

    PLATFORM_BRANDING_LOGO: AnyUrl = AnyUrl(
        get_env("PLATFORM_BRANDING_LOGO", urljoin(str(PLATFORM_BRANDING_CDN_URL), "/images/logo/smarter-crop.png"))
    )

    PLATFORM_BRANDING_MARKETING_SITE_URL: HttpUrl = HttpUrl(
        get_env("PLATFORM_BRANDING_MARKETING_SITE_URL", f"https://{PLATFORM_ROOT_DOMAIN}")
    )

    # the database server's administrator, whom manage.py load_from_github --run_scripts passes to a
    # repository's scripts, e.g. to the Stackademy script that creates its course database and its users.
    SUBSYSTEM_SQL_ROOT_USERNAME: str = get_env("SUBSYSTEM_SQL_ROOT_USERNAME", "root")
    SUBSYSTEM_SQL_ROOT_PASSWORD: Optional[SecretStr] = optional_secret_env("SUBSYSTEM_SQL_ROOT_PASSWORD")

    # the platform's own database, Django's DATABASES["default"]. The defaults are docker-compose.yml's
    # smarter-mariadb service. Its password is a default only locally: elsewhere it must be set.
    SUBSYSTEM_SQL_HOST: str = get_env("SUBSYSTEM_SQL_HOST", "smarter-mariadb")
    SUBSYSTEM_SQL_PORT: int = get_env("SUBSYSTEM_SQL_PORT", 3306)
    SUBSYSTEM_SQL_DATABASE: str = get_env("SUBSYSTEM_SQL_DATABASE", "smarter")
    SUBSYSTEM_SQL_USER: str = get_env("SUBSYSTEM_SQL_USER", "smarter")
    SUBSYSTEM_SQL_PASSWORD: Optional[SecretStr] = optional_secret_env("SUBSYSTEM_SQL_PASSWORD") or (
        SecretStr("smarter") if ENVIRONMENT == SmarterEnvironments.LOCAL else None
    )
    DATABASE_READ_TIMEOUT: int = int(get_env("DATABASE_READ_TIMEOUT", 0))  # 0: no timeout

    # the threads per web server process that run streamed chat prompts, smarter.apps.prompt.progress.
    PROMPT_THREADS: int = int(get_env("PROMPT_THREADS", 32))

    PLATFORM_SUBDOMAIN = get_env("PLATFORM_SUBDOMAIN", "platform")

    # DJANGO_SECRET_KEY, the name of every other Django setting's variable, then SECRET_KEY or
    # SMARTER_SECRET_KEY. It is read here, not by smarter.settings.user, so that
    # smarter_settings.require_secret_key() sees it, and validates it, before Django starts.
    secret = get_env("DJANGO_SECRET_KEY", default=None, is_secret=True)
    if secret is None:
        secret = get_env("SECRET_KEY", default=None, is_secret=True)
    SECRET_KEY_IS_GENERATED: bool = secret is None
    if secret is None:
        warnings.warn(
            "SECRET_KEY is not set. A new secret key will be generated. "
            "This may cause existing sessions and other cryptographic operations to become invalid. "
            "You can safely disregard this warning if this is a new installation or test environment. "
            "Outside of the local environment, Smarter refuses to start without a SECRET_KEY.",
            UserWarning,
        )
        secret = base64.urlsafe_b64encode(os.urandom(32)).decode()
    SECRET_KEY: SecretStr = SecretStr(secret)
    PLATFORM_SETTINGS_OUTPUT: bool = bool_environment_variable("PLATFORM_SETTINGS_OUTPUT", False)

    PLATFORM_SHARED_RESOURCE_IDENTIFIER = get_env("PLATFORM_SHARED_RESOURCE_IDENTIFIER", "smarter")

    # Slack is optional: without a bot token, the Kubernetes jobs' logs are not posted to Slack.
    SUBSYSTEM_SLACK_BOT_TOKEN: Optional[SecretStr] = optional_secret_env("SUBSYSTEM_SLACK_BOT_TOKEN")

    # SMTP is optional: without credentials, email is not sent, and each email that is not sent is logged.
    SUBSYSTEM_SMTP_SENDER = get_env("SUBSYSTEM_SMTP_SENDER", f"admin@{PLATFORM_ROOT_DOMAIN}")
    # None unless set: smarter_settings derives the from address from the platform domain.
    SUBSYSTEM_SMTP_FROM_EMAIL: Optional[str] = get_env("SUBSYSTEM_SMTP_FROM_EMAIL", default=None)
    # None unless set: smarter_settings derives the AWS SES endpoint of AWS_REGION.
    SUBSYSTEM_SMTP_HOST: Optional[str] = get_env("SUBSYSTEM_SMTP_HOST", default=None)
    SUBSYSTEM_SMTP_PORT = int(get_env("SUBSYSTEM_SMTP_PORT", "587"))
    SUBSYSTEM_SMTP_USE_SSL = bool(get_env("SUBSYSTEM_SMTP_USE_SSL", False))
    SUBSYSTEM_SMTP_USE_TLS = bool(get_env("SUBSYSTEM_SMTP_USE_TLS", True))
    SUBSYSTEM_SMTP_PASSWORD: Optional[SecretStr] = optional_secret_env("SUBSYSTEM_SMTP_PASSWORD")
    SUBSYSTEM_SMTP_USERNAME: Optional[SecretStr] = optional_secret_env("SUBSYSTEM_SMTP_USERNAME")

    # -------------------------------------------------------------------------
    # see: https://console.cloud.google.com/apis/credentials/oauthclient/231536848926-egabg8jas321iga0nmleac21ccgbg6tq.apps.googleusercontent.com?project=smarter-sh
    # -------------------------------------------------------------------------
    SUBSYSTEM_SOCIAL_AUTH_GOOGLE_OAUTH2_KEY: SecretStr = SecretStr(
        get_env("SUBSYSTEM_SOCIAL_AUTH_GOOGLE_OAUTH2_KEY", is_secret=True)
    )
    SUBSYSTEM_SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET: SecretStr = SecretStr(
        get_env("SUBSYSTEM_SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET", is_secret=True)
    )
    # -------------------------------------------------------------------------
    # see: https://github.com/settings/applications/2620957
    # -------------------------------------------------------------------------
    SUBSYSTEM_SOCIAL_AUTH_GITHUB_KEY: SecretStr = SecretStr(get_env("SUBSYSTEM_SOCIAL_AUTH_GITHUB_KEY", is_secret=True))
    SUBSYSTEM_SOCIAL_AUTH_GITHUB_SECRET: SecretStr = SecretStr(
        get_env("SUBSYSTEM_SOCIAL_AUTH_GITHUB_SECRET", is_secret=True)
    )
    # -------------------------------------------------------------------------
    # see:  https://www.linkedin.com/developers/apps/221422881/settings
    #       https://www.linkedin.com/developers/apps/221422881/products?refreshKey=1734980684455
    # verification url: https://www.linkedin.com/developers/apps/verification/3ac34414-09a4-433b-983a-0d529fa486f1
    # -------------------------------------------------------------------------
    SUBSYSTEM_SOCIAL_AUTH_LINKEDIN_OAUTH2_KEY: SecretStr = SecretStr(
        get_env("SUBSYSTEM_SOCIAL_AUTH_LINKEDIN_OAUTH2_KEY", is_secret=True)
    )
    SUBSYSTEM_SOCIAL_AUTH_LINKEDIN_OAUTH2_SECRET: SecretStr = SecretStr(
        get_env("SUBSYSTEM_SOCIAL_AUTH_LINKEDIN_OAUTH2_SECRET", is_secret=True)
    )

    STRIPE_LIVE_SECRET_KEY: SecretStr = SecretStr(get_env("STRIPE_LIVE_SECRET_KEY", is_secret=True))
    STRIPE_TEST_SECRET_KEY: SecretStr = SecretStr(get_env("STRIPE_TEST_SECRET_KEY", is_secret=True))

    # Django REST Framework throttle rates, e.g. 120/minute. "none" disables a throttle.
    APP_API_THROTTLE_RATE_ANON = get_env("APP_API_THROTTLE_RATE_ANON", "120/minute")
    APP_API_THROTTLE_RATE_USER = get_env("APP_API_THROTTLE_RATE_USER", "600/minute")

    VERBOSE_LOGGING: bool = bool_environment_variable("VERBOSE_LOGGING", False)

    @classmethod
    def to_dict(cls):
        """Convert SettingsDefaults to dict."""
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
