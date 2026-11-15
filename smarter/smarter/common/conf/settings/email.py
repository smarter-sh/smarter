# pylint: disable=no-member,no-self-argument,unused-argument,R0801
"""The email settings: SMTP, the administrator's address, and the mailing list."""

from functools import cached_property
from typing import Optional, Union

from pydantic import EmailStr, Field, SecretStr

from smarter.common.conf.const import THE_EMPTY_SET
from smarter.common.conf.defaults import settings_defaults
from smarter.common.conf.env import is_missing_value
from smarter.common.conf.settings.aws import AwsSettings
from smarter.common.conf.settings.platform import PlatformSettings
from smarter.common.conf.util import before_field_validator, parse_int_setting
from smarter.common.exceptions import SmarterConfigurationError
from smarter.lib.django.validators import SmarterValidator


class EmailSettings(AwsSettings, PlatformSettings):
    """Outgoing email: SMTP, the administrator's address, and the mailing list."""

    email_admin: EmailStr = Field(
        settings_defaults.EMAIL_ADMIN,
        description="The administrator email address used for system notifications and alerts.",
        examples=["admin@example.com"],
        title="Administrator Email Address",
    )
    """
    The administrator email address used for system notifications and alerts.

    This email address is used as the primary contact for system notifications,
    alerts, and other administrative communications related to the platform.

    :type: str
    :default: Value from ``settings_defaults.EMAIL_ADMIN``
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
        if v in THE_EMPTY_SET:
            return settings_defaults.EMAIL_ADMIN
        if not isinstance(v, str):
            raise SmarterConfigurationError(f"email_admin is not a valid EmailStr: {v}")
        return v

    mailchimp_api_key: Optional[SecretStr] = Field(
        settings_defaults.MAILCHIMP_API_KEY,
        description="The API key for Mailchimp services. Masked by pydantic SecretStr.",
        examples=["sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"],
        title="Mailchimp API Key",
    )
    """
    The API key for Mailchimp services.

    Masked by pydantic SecretStr.
    This setting provides the API key used to authenticate with Mailchimp services.
    It is required for accessing Mailchimp's APIs and services.

    :type: Optional[SecretStr]
    :default: Value from ``settings_defaults.MAILCHIMP_API_KEY``
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
        if str(v) in THE_EMPTY_SET and settings_defaults.MAILCHIMP_API_KEY is not None:
            return settings_defaults.MAILCHIMP_API_KEY

        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError(f"mailchimp_api_key of type {type(v)} is not a SecretStr")
        return v

    mailchimp_list_id: Optional[str] = Field(
        settings_defaults.MAILCHIMP_LIST_ID,
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
    :default: Value from ``settings_defaults.MAILCHIMP_LIST_ID``
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
        if str(v) in THE_EMPTY_SET and settings_defaults.MAILCHIMP_LIST_ID is not None:
            return settings_defaults.MAILCHIMP_LIST_ID
        return v

    smtp_sender: Optional[EmailStr] = Field(
        settings_defaults.SMTP_SENDER,
        description="The sender email address for SMTP emails.",
        examples=["sender@example.com"],
        title="SMTP Sender Email Address",
    )
    """
    The sender email address for SMTP emails.

    This setting specifies the email address that will appear as the sender
    in outgoing SMTP emails sent by the platform.

    :type: Optional[EmailStr]
    :default: Value from ``settings_defaults.SMTP_SENDER``
    :raises SmarterConfigurationError: If the value is not a valid email address.
    """

    @before_field_validator("smtp_sender")
    def validate_smtp_sender(cls, v: Optional[str]) -> str:
        """Validates the `smtp_sender` field.

        Args:
            v (Optional[str]): The SMTP sender email address to validate.

        Returns:
            Optional[str]: The validated SMTP sender email address.
        """
        if v in THE_EMPTY_SET:
            v = settings_defaults.SMTP_SENDER
            SmarterValidator.validate_domain(v)

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"smtp_sender of type {type(v)} is not a str: {v}")
        return v

    smtp_password: Optional[SecretStr] = Field(
        settings_defaults.SMTP_PASSWORD,
        description="The SMTP password for authentication. Assumed to be an AWS SES-generated IAM keypair secret.",
        examples=["your-smtp-password"],
        title="SMTP Password",
    )
    """
    The SMTP password for authentication.

    This setting provides the password used to authenticate with the SMTP server.
    It is required for sending emails through the SMTP server, which is optional.

    :type: Optional[SecretStr]
    :default: Value from ``settings_defaults.SMTP_PASSWORD``, None if it is not set.
    :raises SmarterConfigurationError: If the value is not a valid password.
    """

    @before_field_validator("smtp_password")
    def validate_smtp_password(cls, v: Optional[SecretStr]) -> Optional[SecretStr]:
        """Validates the `smtp_password` field.

        Args:
            v (Optional[SecretStr]): The SMTP password to validate.
        Returns:
            Optional[SecretStr]: The validated SMTP password, or None if it is missing or a placeholder.
        """
        if v in THE_EMPTY_SET:
            v = settings_defaults.SMTP_PASSWORD
        if is_missing_value(v):
            return None

        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError(f"smtp_password of type {type(v)} is not a SecretStr")
        return v

    smtp_port: Optional[int] = Field(
        settings_defaults.SMTP_PORT,
        description="The SMTP port for sending emails.",
        examples=[25, 465, 587],
        title="SMTP Port Number",
    )
    """
    The SMTP port for sending emails.

    This setting specifies the port number used to connect to the SMTP server
    for sending outgoing emails.

    :type: Optional[int]
    :default: Value from ``settings_defaults.SMTP_PORT``
    :raises SmarterConfigurationError: If the value is not a valid port number.
    """

    @before_field_validator("smtp_port")
    def validate_smtp_port(cls, v: Optional[Union[int, str]]) -> int:
        """Validates the `smtp_port` field.

        Args:
            v (Optional[int]): The SMTP port to validate.

        Returns:
            int: The validated SMTP port.
        """
        return parse_int_setting("smtp_port", v, settings_defaults.SMTP_PORT, minimum=1, maximum=65535)

    smtp_use_ssl: Optional[bool] = Field(
        settings_defaults.SMTP_USE_SSL,
        description="Whether to use SSL for SMTP connections.",
        examples=[True, False],
        title="SMTP Use SSL",
    )
    """
    Whether to use SSL for SMTP connections.

    This setting indicates whether SSL (Secure Sockets Layer) should be used
    when connecting to the SMTP server for sending emails.

    :type: Optional[bool]
    :default: Value from ``settings_defaults.SMTP_USE_SSL``
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
        if v in THE_EMPTY_SET:
            return settings_defaults.SMTP_USE_SSL
        return str(v).lower() in ["true", "1", "yes", "on"]

    smtp_use_tls: Optional[bool] = Field(
        settings_defaults.SMTP_USE_TLS,
        description="Whether to use TLS for SMTP connections.",
        examples=[True, False],
        title="SMTP Use TLS",
    )
    """
    Whether to use TLS for SMTP connections.

    This setting indicates whether TLS (Transport Layer Security) should be used
    when connecting to the SMTP server for sending emails.

    :type: Optional[bool]
    :default: Value from ``settings_defaults.SMTP_USE_TLS``
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
        if v in THE_EMPTY_SET:
            return settings_defaults.SMTP_USE_TLS
        return str(v).lower() in ["true", "1", "yes", "on"]

    smtp_username: Optional[SecretStr] = Field(
        settings_defaults.SMTP_USERNAME,
        description="The SMTP username for authentication. Assumed to be an AWS SES-generatred IAM keypair username.",
        examples=["your-smtp-username"],
        title="SMTP Username",
    )
    """
    The SMTP username for authentication.

    This setting provides the username used to authenticate with the SMTP server.
    It is required for sending emails through the SMTP server, which is optional.

    :type: Optional[SecretStr]
    :default: Value from ``settings_defaults.SMTP_USERNAME``, None if it is not set.
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("smtp_username")
    def validate_smtp_username(cls, v: Optional[SecretStr]) -> Optional[SecretStr]:
        """Validates the `smtp_username` field.

        Args:
            v (Optional[str]): The SMTP username to validate.

        Returns:
            Optional[SecretStr]: The validated SMTP username, or None if it is missing or a placeholder.
        """
        if v in THE_EMPTY_SET:
            v = settings_defaults.SMTP_USERNAME
        if is_missing_value(v):
            return None
        return v

    @cached_property
    def smtp_is_configured(self) -> bool:
        """
        Return True if SMTP is configured.

        All required smtp fields must be set.

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
        return not any(is_missing_value(field) for field in required_fields)

    @property
    def smtp_from_email(self) -> str:
        """
        Return the email address that will appear in the "From" field of outgoing SMTP emails.

        ``SMTP_FROM_EMAIL`` if it is set, and otherwise ``no-reply@`` the platform's domain.

        Example:
            >>> print(smarter_settings.smtp_from_email)
            'no-reply@platform.example.com'
        """
        if not is_missing_value(settings_defaults.SMTP_FROM_EMAIL):
            return str(settings_defaults.SMTP_FROM_EMAIL)
        return f"no-reply@{self.platform_subdomain}.{self.root_domain}"

    @property
    def smtp_host(self) -> Optional[str]:
        """
        Return the SMTP host address for sending emails.

        ``SMTP_HOST`` if it is set, and otherwise the AWS Simple Email Service endpoint of
        ``aws_region``. None if neither is set.

        Example:
            >>> print(smarter_settings.smtp_host)
            'email-smtp.us-east-1.amazonaws.com'
        """
        if not is_missing_value(settings_defaults.SMTP_HOST):
            return str(settings_defaults.SMTP_HOST)
        if is_missing_value(self.aws_region):
            return None
        return f"email-smtp.{self.aws_region}.amazonaws.com"


__all__ = ["EmailSettings"]
