# pylint: disable=no-member,no-self-argument,unused-argument,R0801
"""The security settings: the superuser, encryption keys, trusted hosts and throttling."""

import base64
import binascii
import os
import warnings
from typing import List, Optional

from pydantic import BaseModel, Field, SecretStr, ValidationError

from smarter.common.conf.const import THE_EMPTY_SET
from smarter.common.conf.env import is_missing_value
from smarter.common.conf.util import (
    before_field_validator,
    comma_separated,
    field_default,
    validate_throttle_rate,
)
from smarter.common.exceptions import SmarterConfigurationError, SmarterValueError
from smarter.common.utils.utils import generate_fernet_encryption_key

_generated_django_secret_key: Optional[SecretStr] = None
"""The Django secret key that this process generated, because none was configured, or None."""

_generated_fernet_encryption_key: Optional[SecretStr] = None
"""The Fernet encryption key that this process generated, because none was configured, or None."""


def generated_django_secret_key() -> SecretStr:
    """
    Return a random Django secret key, the same one for the life of the process: the default of ``django_secret_key``.

    It is generated, with a warning, the first time a ``django_secret_key`` isn't configured. Outside of the
    local environment, Smarter refuses to start with it: see :meth:`SecuritySettings.django_secret_key_is_set`.

    :returns: The key.
    """
    global _generated_django_secret_key  # pylint: disable=global-statement
    if _generated_django_secret_key is None:
        warnings.warn(
            "DJANGO_SECRET_KEY is not set. A new secret key will be generated. "
            "This may cause existing sessions and other cryptographic operations to become invalid. "
            "You can safely disregard this warning if this is a new installation or test environment. "
            "Outside of the local environment, Smarter refuses to start without a DJANGO_SECRET_KEY.",
            UserWarning,
        )
        random_key = base64.urlsafe_b64encode(os.urandom(32)).decode()
        _generated_django_secret_key = SecretStr(random_key)
    return _generated_django_secret_key


def generated_fernet_encryption_key() -> SecretStr:
    """
    Return a new Fernet key, the same one for the life of the process: the default of ``platform_fernet_encryption_key``.

    It is generated, with a warning, the first time the key isn't configured. Secrets encrypted with
    it can't be read by another process, or after a restart.

    :returns: The key.
    """
    global _generated_fernet_encryption_key  # pylint: disable=global-statement
    if _generated_fernet_encryption_key is None:
        warnings.warn(
            "PLATFORM_FERNET_ENCRYPTION_KEY is not set. "
            "A new encryption key will be generated. This may cause existing encrypted data to become inaccessible. "
            "You can safely disregard this warning if this is a new installation, test environment or CI-CD process.",
            UserWarning,
        )
        new_key = generate_fernet_encryption_key()
        _generated_fernet_encryption_key = SecretStr(new_key)
    return _generated_fernet_encryption_key


class SecuritySettings(BaseModel):
    """The superuser, encryption keys, trusted hosts and request throttling."""

    platform_admin_username: str = Field(
        "admin",
        description="The username of the platform's superuser, which manage.py initialize_platform creates.",
        examples=["admin"],
        title="Administrator Username",
    )
    """
    The username of the platform's superuser.

    ``manage.py initialize_platform`` creates this superuser, unless ``--username`` names
    another. Set it with ``SMARTER_PLATFORM_ADMIN_USERNAME``.

    :type: str
    :default: ``admin`` if it is not set.
    :raises SmarterConfigurationError: If the value is not a non-empty string.
    """

    @before_field_validator("platform_admin_username")
    def validate_platform_admin_username(cls, v: Optional[str]) -> str:
        """Validates the `admin_username` field.

        Args:
            v (Optional[str]): The administrator username to validate.
        Returns:
            str: The validated administrator username.
        """
        if v in THE_EMPTY_SET:
            v = field_default(cls, "platform_admin_username")
        if not isinstance(v, str) or not v:
            raise SmarterConfigurationError(f"admin_username of type {type(v)} is not a non-empty string.")
        return v

    platform_admin_password: Optional[SecretStr] = Field(
        None,
        description="The password of the platform's superuser, which manage.py initialize_platform creates.",
        examples=["your-admin-password"],
        title="Administrator Password",
    )
    """
    The password of the platform's superuser.

    ``manage.py initialize_platform`` gives the superuser and the example users this password,
    unless ``--password`` gives another. Set it with ``SMARTER_PLATFORM_ADMIN_PASSWORD``. Reading it from
    the environment keeps it off the command line, and out of the init Job's log.

    :type: Optional[SecretStr]
    :default: None if it is not set.
    :raises SmarterConfigurationError: If the value is not a SecretStr.
    """

    @before_field_validator("platform_admin_password")
    def validate_platform_admin_password(cls, v: Optional[SecretStr]) -> Optional[SecretStr]:
        """Validates the `admin_password` field.

        Args:
            v (Optional[SecretStr]): The administrator password to validate.
        Returns:
            Optional[SecretStr]: The validated administrator password, or None if it is missing or a placeholder.
        """
        if v in THE_EMPTY_SET:
            v = field_default(cls, "platform_admin_password")
        if is_missing_value(v):
            return None
        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError(f"admin_password of type {type(v)} is not a SecretStr")
        return v

    platform_fernet_encryption_key: SecretStr = Field(
        default_factory=generated_fernet_encryption_key,
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
    :default: a key that the process generates, with a warning: see :func:`generated_fernet_encryption_key`
    :raises SmarterConfigurationError: If the value is not a valid Fernet key.
    """

    @before_field_validator("platform_fernet_encryption_key")
    def validate_platform_fernet_encryption_key(cls, v: Optional[SecretStr]) -> Optional[SecretStr]:
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
            return field_default(cls, "platform_fernet_encryption_key")

        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError(f"fernet_encryption_key of type {type(v)} is not a SecretStr.")
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

    platform_internal_ip_prefixes: List[str] = Field(
        ["192.168."],
        description="A list of internal IP prefixes used for security and middleware features.",
        examples=[["192.168.", "10.0."]],
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
    :default: ``["192.168."]``
    :raises SmarterConfigurationError: If the value is not a list of strings
    """

    @before_field_validator("platform_internal_ip_prefixes")
    def validate_platform_internal_ip_prefixes(cls, v: Optional[List[str]]) -> List[str]:
        """Validates the `internal_ip_prefixes` field.

        Args:
            v (Optional[List[str]]): The internal IP prefixes value to validate.

        Returns:
            List[str]: The validated internal IP prefixes.
        """
        if v in THE_EMPTY_SET:
            return field_default(cls, "platform_internal_ip_prefixes")
        v = comma_separated(v)
        if not isinstance(v, list):
            raise SmarterConfigurationError(f"internal_ip_prefixes of type {type(v)} is not a list: {v}")
        return v

    django_secret_key: Optional[SecretStr] = Field(
        validation_alias="DJANGO_SECRET_KEY",
        default_factory=generated_django_secret_key,
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
    :default: a key that the process generates, with a warning: see :func:`generated_django_secret_key`
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("django_secret_key")
    def validate_secret_key(cls, v: Optional[SecretStr]) -> SecretStr:
        """Validates the `django_secret_key` field.

        Args:
            v (Optional[SecretStr]): The secret key value to validate.
        Returns:
            SecretStr: The validated secret key.
        """
        if v is None:
            return field_default(cls, "django_secret_key")

        if isinstance(v, str):
            try:
                v = SecretStr(v)
            except ValidationError as e:
                raise SmarterConfigurationError("django_secret_key is not a valid SecretStr.") from e

        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError(f"django_secret_key {type(v)} is not a SecretStr.")
        return v

    app_api_throttle_rate_anon: Optional[str] = Field(
        "120/minute",
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
    :default: ``"120/minute"``
    :raises SmarterConfigurationError: If the value is not a rate, e.g. ``120/minute``, or ``none``.
    """

    @before_field_validator("app_api_throttle_rate_anon")
    def validate_app_api_throttle_rate_anon(cls, v: Optional[str]) -> Optional[str]:
        """Validates the `throttle_rate_anon` field.

        Args:
            v (Optional[str]): The rate, e.g. ``120/minute``, or ``none`` to disable the throttle.

        Returns:
            Optional[str]: The validated rate, or None if the throttle is disabled.
        """
        return validate_throttle_rate("app_api_throttle_rate_anon", v, field_default(cls, "app_api_throttle_rate_anon"))

    app_api_throttle_rate_user: Optional[str] = Field(
        "600/minute",
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
    :default: ``"600/minute"``
    :raises SmarterConfigurationError: If the value is not a rate, e.g. ``600/minute``, or ``none``.
    """

    @before_field_validator("app_api_throttle_rate_user")
    def validate_app_api_throttle_rate_user(cls, v: Optional[str]) -> Optional[str]:
        """Validates the `throttle_rate_user` field.

        Args:
            v (Optional[str]): The rate, e.g. ``600/minute``, or ``none`` to disable the throttle.

        Returns:
            Optional[str]: The validated rate, or None if the throttle is disabled.
        """
        return validate_throttle_rate("app_api_throttle_rate_user", v, field_default(cls, "app_api_throttle_rate_user"))

    @property
    def django_secret_key_is_set(self) -> bool:
        """
        Return True if a Django secret key was configured.

        A secret key is not configured if it is missing, if it is a placeholder such as
        ``helm/charts/smarter/values.yaml``'s ``SET-ME-IN-helm/...``, or if it is the random
        key that :func:`generated_django_secret_key` generates when ``DJANGO_SECRET_KEY`` is not set.

        Example:
            >>> print(smarter_settings.django_secret_key_is_set)
            True

        See Also:
            - smarter_settings.django_secret_key
            - smarter_settings.require_django_secret_key()
        """
        if is_missing_value(self.django_secret_key):
            return False
        if _generated_django_secret_key is not None and self.django_secret_key is not None:
            generated = _generated_django_secret_key.get_secret_value()
            return self.django_secret_key.get_secret_value() != generated
        return True


__all__ = [
    "SecuritySettings",
    "generated_fernet_encryption_key",
    "generated_django_secret_key",
]
