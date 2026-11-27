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
    2. environment variables, which include the `.env` file's: ``SMARTER_<FIELD>``.
    3. each field's default.

.. note::

    A deployment can also override any Django setting with a ``DJANGO_<SETTING>`` environment
    variable, from the Helm chart's ``env`` or ``.env``, e.g. ``DJANGO_SESSION_COOKIE_AGE=3600``: see
    :mod:`smarter.settings.overrides`. The secret key is ``DJANGO_SECRET_KEY``, which
    ``smarter_settings.django_secret_key`` reads and validates.

.. warning::

    DO NOT import Django or any Django modules in this module. This module
    sits upstream of Django and is intended to be used independently of Django.
"""

from functools import lru_cache
from typing import Any, get_args

from pydantic import SecretStr, ValidationError, ValidationInfo, field_validator
from pydantic import __version__ as pydantic_version
from pydantic_settings import BaseSettings, SettingsConfigDict

from smarter.common.conf.env import unquoted
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
from smarter.common.conf.util import field_default
from smarter.common.exceptions import SmarterConfigurationError
from smarter.common.helpers.console_helpers import SmarterFormattedText
from smarter.common.helpers.processes import is_first_worker
from smarter.common.utils import get_diagnostics, recursive_sort_dict
from smarter.lib import logging
from smarter.lib.typing import SmarterDictType

logger = logging.getSmarterLogger(__name__)


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
        2. environment variables, and the `.env` file's: ``SMARTER_<FIELD>``.
        3. each field's default, on the field.
    - The dump property returns a dictionary of all configuration values.
    - smarter_settings values should be accessed via the smarter_settings singleton instance when possible.
    """

    model_config = SettingsConfigDict(
        env_prefix="SMARTER_",
        enable_decoding=False,
        populate_by_name=True,
        frozen=True,
        extra="forbid",
        validate_default=True,
    )
    """
    Pydantic v2 Configuration class for the Settings model.

    see https://docs.pydantic.dev/latest/concepts/pydantic_settings/

    Each field is read from the environment variable ``SMARTER_<FIELD>``, e.g. ``debug_mode`` from
    ``SMARTER_DEBUG_MODE``. The `.env` file is loaded into the environment first, by
    :mod:`smarter.common.conf.const`. A field that keeps the name that other tools use, e.g.
    ``aws_region`` from ``AWS_REGION``, names it with its ``validation_alias``.

    :param env_prefix: The prefix of every field's environment variable.
    :param enable_decoding: False: a list is a comma-separated string, which the field's validator
        splits, not JSON.
    :param populate_by_name: The constructor takes a field's name as well as its alias.
    :param frozen: Make the settings instance immutable after instantiation.
    :param extra: Forbid extra fields not defined in the model.
    :param validate_default: Validate default values defined in the model.

    :type: SettingsConfigDict
    """

    _ready: bool

    @field_validator("*", mode="before")
    @classmethod
    def secret_from_string(cls, v: object, info: ValidationInfo) -> object:
        """
        Unquote a string, and wrap a secret's in a ``SecretStr``, before any of its field's validators see it.

        An environment variable is always a string. Its surrounding quotes are stripped
        (:func:`~smarter.common.conf.env.unquoted`), since ``make`` exports ``.env``'s lines with them.
        A secret is masked from the moment it is read, so that no validator, error message or log can
        show it.

        :param v: The value to validate.
        :param info: Pydantic's validation info, which names the field.
        :returns: A ``SecretStr`` for a secret's string, the unquoted string otherwise, or the value
            itself if it is not a string.
        """
        if not isinstance(v, str):
            return v
        v = unquoted(v)
        field_name = str(info.field_name)
        field = cls.model_fields[field_name]
        if field.annotation is SecretStr or SecretStr in get_args(field.annotation):
            return SecretStr(v)
        return v

    def field_defaults(self) -> SmarterDictType:
        """
        Return each field's declared default, for the settings dump.

        A default that a factory makes, e.g. a generated key, is not made: it is listed as its
        factory's name.

        :returns: The defaults, by field name.
        """
        defaults: SmarterDictType = {}
        for name, field in type(self).model_fields.items():
            if field.default_factory is not None:
                factory_name = getattr(field.default_factory, "__name__", "factory")
                defaults[name] = f"<{factory_name}()>"
                continue
            defaults[name] = field.default
        return defaults

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
        if self.database_unavailable:
            # the tool worker has no AWS credentials, by design (ADR-038): its ServiceAccount has no
            # IAM role. STS isn't asked, and nothing warns that they are missing.
            self._aws_is_configured = False
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
          Kubernetes when ``cloud_provider`` is ``aws``. Not checked in the tool worker
          (``database_unavailable``), which has no AWS credentials, by design (ADR-038).

        SMTP is not checked: without it, email is not sent, and each email that is not sent is
        logged with instructions. See :attr:`smtp_is_configured`.

        :type: bool
        """
        retval = True
        default_root_domain = field_default(type(self), "platform_root_domain")
        if self.platform_root_domain == default_root_domain and not self.environment_is_local:
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

        if not self.aws_is_configured and not self.database_unavailable:
            print(
                SmarterFormattedText.text(
                    "\n"
                    + "=" * 80
                    + "\n[WARNING] AWS is not configured properly. Some features may not work as expected.\n"
                    + "Smarter uses boto3's default credentials. On Kubernetes, that is the IAM role of the pod's\n"
                    + "ServiceAccount (IRSA: serviceAccount.awsRoleArn in the Helm chart). Locally, it is an AWS\n"
                    + "profile (AWS_PROFILE). A static key pair (AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY) also\n"
                    + "works, but is not recommended.\n"
                    + "=" * 80
                    + "\n",
                    SmarterFormattedText.DARK_RED,
                )
            )
            # aws_credentials_work() has already logged why.
            retval = False

        self._ready = retval
        return self._ready

    def require_django_secret_key(self) -> None:
        """
        Refuse to run outside of the local environment without a Django secret key.

        Without a configured key, every process generates its own random key, so sessions,
        password reset tokens and other signed values break across pods and restarts. A
        placeholder key is worse: it is published in this repository, so anyone could forge
        signed values with it. Locally, a generated key is fine, and only logs a warning.

        The tool worker (``database_unavailable``) is never given the key: it signs nothing, and
        with the key, code that a tool call runs there could forge the platform's sessions. It
        uses its own random key.

        :raises SmarterConfigurationError: If the secret key is not configured, the environment is
            not local, and this process has a database.

        See Also:
            - smarter_settings.django_secret_key_is_set
        """
        if self.django_secret_key_is_set or self.database_unavailable:
            return
        if not self.environment_is_local:
            raise SmarterConfigurationError(
                f"DJANGO_SECRET_KEY is not set. It is required in the {self.environment} environment. "
                "Set DJANGO_SECRET_KEY to a long (50+ characters), random string that is the same for every pod."
            )
        logger.warning("DJANGO_SECRET_KEY is not set. Using a randomized value.")

    @property
    def is_extension_worker(self) -> bool:
        """
        Whether this process is the Extension worker, ``smarter-worker-extensions`` (issue #1077).

        :returns: True if it is a worker without a database whose queue is the Extensions queue.
        """
        if not self.database_unavailable:
            return False
        is_extensions_queue = self.tool_worker_queue == self.app_extensions_tasks_celery_task_queue
        return is_extensions_queue

    def require_redis_password(self) -> SecretStr:
        """
        Return Redis's password, or refuse to run outside of the local environment without one.

        Redis holds the Celery queues, RedBeat's schedule, the cache and every user's session, and the
        workers behind the queues hold the platform's credentials. It is generated per environment
        (ADR-030, rule 5), so a process that doesn't have it
        stops here, with a clear message, rather than failing on its first connection. Every process needs
        it, the tool worker included, which takes its tasks from the broker and reads Extensions' archives
        from the cache. Locally, :attr:`subsystem_redis_password` defaults to docker-compose's password.

        :returns: The password.
        :raises SmarterConfigurationError: If the password is not set.
        """
        password = self.subsystem_redis_password
        if password is None:
            raise SmarterConfigurationError(
                f"SMARTER_SUBSYSTEM_REDIS_PASSWORD is not set. It is required in the {self.environment} environment. "
                "On a cluster that smarter-infrastructure built, it is read from the Kubernetes Secret "
                "smarter-redis-password."
            )
        return password

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
            retval["defaults"] = self.field_defaults()

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
