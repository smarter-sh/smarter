# pylint: disable=no-member,no-self-argument,unused-argument,R0801
"""The security settings: the superuser, encryption keys, trusted hosts and throttling."""

import base64
import binascii
import re
from typing import List, Optional, Pattern, Union

from pydantic import BaseModel, Field, SecretStr, ValidationError

from smarter.common.conf.const import THE_EMPTY_SET
from smarter.common.conf.defaults import settings_defaults
from smarter.common.conf.env import is_missing_value
from smarter.common.conf.util import before_field_validator, validate_throttle_rate
from smarter.common.exceptions import SmarterConfigurationError, SmarterValueError


def compile_amnesty_pattern(item: object) -> Pattern:
    """
    Compile one of the sensitive files amnesty patterns.

    :param item: A regular expression, as a string or already compiled.
    :returns: The compiled pattern.
    :raises SmarterConfigurationError: If the item is not a valid regular expression.
    """
    if isinstance(item, re.Pattern):
        return item
    if not isinstance(item, str):
        raise SmarterConfigurationError(
            "sensitive_files_amnesty_patterns must be a list of strings or compiled regex patterns."
        )
    try:
        return re.compile(item)
    except re.error as e:
        raise SmarterConfigurationError(f"Invalid regex pattern: {item}") from e


class SecuritySettings(BaseModel):
    """The superuser, encryption keys, trusted hosts and request throttling."""

    admin_username: str = Field(
        settings_defaults.ADMIN_USERNAME,
        description="The username of the platform's superuser, which manage.py initialize_platform creates.",
        examples=["admin"],
        title="Administrator Username",
    )
    """
    The username of the platform's superuser.

    ``manage.py initialize_platform`` creates this superuser, unless ``--username`` names
    another. Set it with ``SMARTER_ADMIN_USERNAME``.

    :type: str
    :default: Value from ``settings_defaults.ADMIN_USERNAME``, ``admin`` if it is not set.
    :raises SmarterConfigurationError: If the value is not a non-empty string.
    """

    @before_field_validator("admin_username")
    def validate_admin_username(cls, v: Optional[str]) -> str:
        """Validates the `admin_username` field.

        Args:
            v (Optional[str]): The administrator username to validate.
        Returns:
            str: The validated administrator username.
        """
        if v in THE_EMPTY_SET:
            v = settings_defaults.ADMIN_USERNAME
        if not isinstance(v, str) or not v:
            raise SmarterConfigurationError(f"admin_username of type {type(v)} is not a non-empty string.")
        return v

    admin_password: Optional[SecretStr] = Field(
        settings_defaults.ADMIN_PASSWORD,
        description="The password of the platform's superuser, which manage.py initialize_platform creates.",
        examples=["your-admin-password"],
        title="Administrator Password",
    )
    """
    The password of the platform's superuser.

    ``manage.py initialize_platform`` gives the superuser and the example users this password,
    unless ``--password`` gives another. Set it with ``SMARTER_ADMIN_PASSWORD``. Reading it from
    the environment keeps it off the command line, and out of the init Job's log.

    :type: Optional[SecretStr]
    :default: Value from ``settings_defaults.ADMIN_PASSWORD``, None if it is not set.
    :raises SmarterConfigurationError: If the value is not a SecretStr.
    """

    @before_field_validator("admin_password")
    def validate_admin_password(cls, v: Optional[SecretStr]) -> Optional[SecretStr]:
        """Validates the `admin_password` field.

        Args:
            v (Optional[SecretStr]): The administrator password to validate.
        Returns:
            Optional[SecretStr]: The validated administrator password, or None if it is missing or a placeholder.
        """
        if v in THE_EMPTY_SET:
            v = settings_defaults.ADMIN_PASSWORD
        if is_missing_value(v):
            return None
        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError(f"admin_password of type {type(v)} is not a SecretStr")
        return v

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
                pattern = compile_amnesty_pattern(item)
                patterns.append(pattern)
            return patterns
        if v in THE_EMPTY_SET:
            return settings_defaults.SENSITIVE_FILES_AMNESTY_PATTERNS
        if isinstance(v, str):
            pattern = compile_amnesty_pattern(v)
            return [pattern]

        raise SmarterConfigurationError(f"could not validate sensitive_files_amnesty_patterns: {v}")

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
        encryption_key = v.get_secret_value()
        try:
            # Decode the key using URL-safe base64
            decoded_key = base64.urlsafe_b64decode(encryption_key)
            # Ensure the decoded key is exactly 32 bytes
            if len(decoded_key) != 32:
                raise ValueError("Fernet key must be exactly 32 bytes when decoded.")
        except (TypeError, ValueError, binascii.Error) as e:
            # never put the key itself in the message: it is a secret, and errors are logged.
            raise SmarterValueError(f"Invalid Fernet encryption key. Error: {e}") from e

        return v

    internal_ip_prefixes: List[str] = Field(
        settings_defaults.INTERNAL_IP_PREFIXES,
        description="A list of internal IP prefixes used for security and middleware features.",
        examples=settings_defaults.INTERNAL_IP_PREFIXES,
        title="Internal IP Prefixes",
    )
    """
    Supplemental list of internal IP prefixes used in smarter.apps.llmclient.middleware.security.SmarterSecurityMiddleware.

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

    throttle_rate_anon: Optional[str] = Field(
        settings_defaults.THROTTLE_RATE_ANON,
        description="The request rate limit of each anonymous client, by IP address. None disables it.",
        examples=["120/minute", "10/second", "none"],
        title="Anonymous Throttle Rate",
    )
    """
    The request rate limit of each anonymous client, by IP address.

    Applies to Django REST Framework views and to the apis that a deployed LLMClient serves,
    e.g. the prompt api of a page that embeds Smarter Chat. A client that exceeds it receives
    HTTP 429 Too Many Requests with a ``Retry-After`` header. See :mod:`smarter.lib.drf.throttling`.

    :type: Optional[str]
    :default: Value from ``settings_defaults.THROTTLE_RATE_ANON``
    :raises SmarterConfigurationError: If the value is not a rate, e.g. ``120/minute``, or ``none``.
    """

    @before_field_validator("throttle_rate_anon")
    def validate_throttle_rate_anon(cls, v: Optional[str]) -> Optional[str]:
        """Validates the `throttle_rate_anon` field.

        Args:
            v (Optional[str]): The rate, e.g. ``120/minute``, or ``none`` to disable the throttle.

        Returns:
            Optional[str]: The validated rate, or None if the throttle is disabled.
        """
        return validate_throttle_rate("throttle_rate_anon", v, settings_defaults.THROTTLE_RATE_ANON)

    throttle_rate_user: Optional[str] = Field(
        settings_defaults.THROTTLE_RATE_USER,
        description="The request rate limit of each authenticated user. None disables it.",
        examples=["600/minute", "20/second", "none"],
        title="User Throttle Rate",
    )
    """
    The request rate limit of each authenticated user.

    Applies to Django REST Framework views and to the apis that a deployed LLMClient serves.
    A user who exceeds it receives HTTP 429 Too Many Requests with a ``Retry-After`` header.
    See :mod:`smarter.lib.drf.throttling`.

    :type: Optional[str]
    :default: Value from ``settings_defaults.THROTTLE_RATE_USER``
    :raises SmarterConfigurationError: If the value is not a rate, e.g. ``600/minute``, or ``none``.
    """

    @before_field_validator("throttle_rate_user")
    def validate_throttle_rate_user(cls, v: Optional[str]) -> Optional[str]:
        """Validates the `throttle_rate_user` field.

        Args:
            v (Optional[str]): The rate, e.g. ``600/minute``, or ``none`` to disable the throttle.

        Returns:
            Optional[str]: The validated rate, or None if the throttle is disabled.
        """
        return validate_throttle_rate("throttle_rate_user", v, settings_defaults.THROTTLE_RATE_USER)

    @property
    def secret_key_is_set(self) -> bool:
        """
        Return True if a Django secret key was configured.

        A secret key is not configured if it is missing, if it is a placeholder such as
        ``helm/charts/smarter/values.yaml``'s ``SET-ME-IN-helm/...``, or if it is the random
        key that ``settings_defaults`` generates when ``SECRET_KEY`` is not set.

        Example:
            >>> print(smarter_settings.secret_key_is_set)
            True

        See Also:
            - smarter_settings.secret_key
            - smarter_settings.require_secret_key()
        """
        if is_missing_value(self.secret_key):
            return False
        if settings_defaults.SECRET_KEY_IS_GENERATED and self.secret_key is not None:
            generated = settings_defaults.SECRET_KEY.get_secret_value()
            return self.secret_key.get_secret_value() != generated
        return True


__all__ = ["SecuritySettings", "compile_amnesty_pattern"]
