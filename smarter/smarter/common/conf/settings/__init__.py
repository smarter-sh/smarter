# pylint: disable=no-member,no-self-argument,unused-argument,R0801
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

import logging
from functools import lru_cache
from typing import Any

from pydantic import ValidationError
from pydantic import __version__ as pydantic_version
from pydantic_settings import BaseSettings, SettingsConfigDict

from smarter.common.conf.const import DEFAULT_ROOT_DOMAIN
from smarter.common.conf.defaults import settings_defaults
from smarter.common.conf.settings.app_keys import AppKeySettings
from smarter.common.conf.settings.aws import AwsSettings
from smarter.common.conf.settings.branding import BrandingSettings
from smarter.common.conf.settings.cache import CacheSettings
from smarter.common.conf.settings.database import DatabaseSettings
from smarter.common.conf.settings.domains import DomainSettings
from smarter.common.conf.settings.email import EmailSettings
from smarter.common.conf.settings.features import FeatureSettings
from smarter.common.conf.settings.integrations import IntegrationSettings
from smarter.common.conf.settings.llm import LLMSettings
from smarter.common.conf.settings.platform import PlatformSettings
from smarter.common.conf.settings.project import ProjectSettings
from smarter.common.conf.settings.security import SecuritySettings
from smarter.common.conf.settings.tasks import TaskSettings
from smarter.common.exceptions import SmarterConfigurationError
from smarter.common.helpers.console_helpers import SmarterFormattedText
from smarter.common.helpers.processes import is_first_worker
from smarter.common.utils import get_diagnostics, recursive_sort_dict
from smarter.lib.logging.waffle_switched_logger import WaffleSwitchedLoggerWrapper
from smarter.lib.typing import SmarterDictType

logger = WaffleSwitchedLoggerWrapper(logging.getLogger(__name__))


# pylint: disable=too-many-instance-attributes,too-many-public-methods,too-many-ancestors
class Settings(
    AppKeySettings,
    DomainSettings,
    EmailSettings,
    AwsSettings,
    PlatformSettings,
    BrandingSettings,
    CacheSettings,
    DatabaseSettings,
    FeatureSettings,
    IntegrationSettings,
    LLMSettings,
    ProjectSettings,
    SecuritySettings,
    TaskSettings,
    BaseSettings,
):
    """
    See: https://docs.pydantic.dev/latest/concepts/pydantic_settings/.

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
    Pydantic v2 Configuration class for the Settings model.

    This configuration enforces strict type checking,
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
        # The prefix is gray rather than the usual red, so that a healthy start doesn't
        # look like an error. READY is logged by one uvicorn worker per server, and
        # NOT_READY by every process.
        prefix_format = SmarterFormattedText.LIGHT_GRAY
        if not self.ready():
            logger.warning(
                "Pydantic version: %s smarter_settings are %s.",
                pydantic_version,
                SmarterFormattedText.text("NOT_READY", SmarterFormattedText.DARK_RED),
                prefix_format=prefix_format,
            )
        elif is_first_worker("settings-ready"):
            logger.warning(
                "Pydantic version: %s smarter_settings are %s.",
                pydantic_version,
                SmarterFormattedText.text("READY", SmarterFormattedText.BRIGHT_GREEN),
                prefix_format=prefix_format,
            )
        else:
            logger.debug(
                "Pydantic version: %s smarter_settings are %s.",
                pydantic_version,
                SmarterFormattedText.text("READY", SmarterFormattedText.BRIGHT_GREEN),
                prefix_format=prefix_format,
            )

    def ready(self) -> bool:
        """
        Returns True if the settings are complete enough for a deployment that real users can reach.

        Nothing here is needed to run the platform locally: a missing value is reported with a
        console warning, and the features that depend on it degrade gracefully.

        - is the root domain set? Only checked outside of the local environment, which serves
          the platform from localhost.
        - is AWS configured? Needed for DNS, TLS certificates, and deploying LLMClients to
          Kubernetes when ``cloud_provider`` is ``aws``.

        SMTP is not checked: without it, email is not sent, and each email that is not sent is
        logged with instructions. See :attr:`smtp_is_configured`.

        :type: bool
        """
        retval = True
        if self.platform_root_domain == DEFAULT_ROOT_DOMAIN and not self.environment_is_local:
            print(
                SmarterFormattedText.text(
                    "\n"
                    + "=" * 80
                    + "\n[WARNING] ROOT_DOMAIN is set to the default value 'example.com'.\n"
                    + "This is not recommended for production deployments. Please set ROOT_DOMAIN to your actual domain.\n"
                    + "=" * 80
                    + "\n",
                    SmarterFormattedText.DARK_RED,
                )
            )
            logger.warning(
                "ROOT_DOMAIN is set to the default value 'example.com'. This is not recommended for production deployments."
            )
            retval = False

        if not self.aws_is_configured:
            print(
                SmarterFormattedText.text(
                    "\n"
                    + "=" * 80
                    + "\n[WARNING] AWS is not configured properly. Some features may not work as expected.\n"
                    + "Ensure that AWS credentials are set in environment variables, .env file, or AWS config files.\n"
                    + "=" * 80
                    + "\n",
                    SmarterFormattedText.DARK_RED,
                )
            )
            logger.warning("AWS is not configured properly. Some features may not work as expected.")
            retval = False

        self._ready = retval
        return self._ready

    def require_secret_key(self) -> None:
        """
        Refuse to run outside of the local environment without a Django secret key.

        Without a configured key, every process generates its own random key, so sessions,
        password reset tokens and other signed values break across pods and restarts. A
        placeholder key is worse: it is published in this repository, so anyone could forge
        signed values with it. Locally, a generated key is fine, and only logs a warning.

        :raises SmarterConfigurationError: If the secret key is not configured, and the
            environment is not local.

        See Also:
            - smarter_settings.secret_key_is_set
        """
        if self.secret_key_is_set:
            return
        if not self.environment_is_local:
            raise SmarterConfigurationError(
                f"SECRET_KEY is not set. It is required in the {self.environment} environment. "
                "Set SMARTER_SECRET_KEY to a long (50+ characters), random string that is the same for every pod."
            )
        logger.warning("SECRET_KEY is not set. Using a randomized value.")

    def to_json(self) -> SmarterDictType:
        """
        Dump all settings.

        Useful for debugging and logging.

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
    """
    Lazily get the singleton settings instance.

    This approach is intended
    to speed up the app startup time by deferring the creation of the Settings instance
    until it is first needed. This *might* also be useful for deferring loading
    environment variables until they are actually needed, but that is not the primary goal.
    """
    try:
        return Settings()
    except ValidationError as e:
        raise SmarterConfigurationError("Invalid configuration: " + str(e)) from e


smarter_settings = get_settings()

__all__ = [
    "smarter_settings",
    "Settings",
    "AwsSettings",
    "BrandingSettings",
    "CacheSettings",
    "DatabaseSettings",
    "DomainSettings",
    "EmailSettings",
    "FeatureSettings",
    "IntegrationSettings",
    "LLMSettings",
    "PlatformSettings",
    "ProjectSettings",
    "SecuritySettings",
    "TaskSettings",
]
