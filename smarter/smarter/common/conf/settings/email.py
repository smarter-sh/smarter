# pylint: disable=no-member,no-self-argument,unused-argument,R0801
"""The email settings: SMTP, the administrator's address, and the mailing list."""

from functools import cached_property
from typing import Annotated, Optional, Union

from pydantic import EmailStr, Field, SecretStr, model_validator

from smarter.common.conf.const import THE_EMPTY_SET
from smarter.common.conf.credentials import HeldBy
from smarter.common.conf.env import is_missing_value
from smarter.common.conf.settings.aws import AwsSettings
from smarter.common.conf.settings.platform import PlatformSettings
from smarter.common.conf.util import (
    before_field_validator,
    field_default,
    input_value,
    parse_int_setting,
    with_derived_default,
)
from smarter.common.const import SmarterPodCapabilities
from smarter.common.exceptions import SmarterConfigurationError


class EmailSettings(AwsSettings, PlatformSettings):
    """Outgoing email: SMTP, the administrator's address, and the mailing list."""

    platform_email_admin: EmailStr = Field(
        "admin@example.com",
        description="The administrator email address used for system notifications and alerts.",
        examples=["admin@example.com"],
        title="Administrator Email Address",
    )
    """
    The administrator email address used for system notifications and alerts.

    This email address is used as the primary contact for system notifications,
    alerts, and other administrative communications related to the platform.

    :type: str
    :default: ``"admin@example.com"``
    :raises SmarterConfigurationError: If the value is not a valid email address.
    """

    @before_field_validator("platform_email_admin")
    def validate_platform_email_admin(cls, v: Optional[EmailStr]) -> EmailStr:
        """Validates the `email_admin` field.

        Args:
            v (Optional[EmailStr]): The administrator email address value to validate.

        Returns:
            EmailStr: The validated administrator email address.
        """
        if v in THE_EMPTY_SET:
            return field_default(cls, "platform_email_admin")
        if not isinstance(v, str):
            raise SmarterConfigurationError(f"email_admin is not a valid EmailStr: {v}")
        return v

    subsystem_smtp_sender: Optional[EmailStr] = Field(
        None,
        description="The sender email address for SMTP emails.",
        examples=["sender@example.com"],
        title="SMTP Sender Email Address",
    )
    """
    The sender email address for SMTP emails.

    This setting specifies the email address that will appear as the sender
    in outgoing SMTP emails sent by the platform.

    :type: Optional[EmailStr]
    :default: ``admin@`` the root domain, e.g. ``admin@example.com``. See :meth:`derive_email_defaults`.
    :raises SmarterConfigurationError: If the value is not a valid email address.
    """

    @before_field_validator("subsystem_smtp_sender")
    def validate_subsystem_smtp_sender(cls, v: Optional[str]) -> str:
        """Validates the `smtp_sender` field.

        Args:
            v (Optional[str]): The SMTP sender email address to validate.

        Returns:
            Optional[str]: The validated SMTP sender email address.
        """
        if not isinstance(v, str):
            raise SmarterConfigurationError(f"smtp_sender of type {type(v)} is not a str: {v}")
        return v

    @model_validator(mode="before")
    @classmethod
    def derive_email_defaults(cls, data: object) -> object:
        """
        Derive the SMTP sender, the From address and the host, unless they are set.

        The sender is ``admin@`` the root domain, the From address ``no-reply@`` the platform's
        domain, and the host the AWS Simple Email Service endpoint of ``aws_region``, if it has one.

        :param data: The values to validate: the constructor's and the environment's.
        :returns: The values, with the derived defaults added.
        """
        root_domain = input_value(cls, data, "platform_root_domain")
        sender = f"admin@{root_domain}"
        data = with_derived_default(data, "subsystem_smtp_sender", sender)
        subdomain = input_value(cls, data, "platform_subdomain")
        from_email = f"no-reply@{subdomain}.{root_domain}"
        data = with_derived_default(data, "subsystem_smtp_from_email", from_email)
        aws_region = input_value(cls, data, "aws_region")
        if is_missing_value(aws_region):
            return data
        host = f"email-smtp.{aws_region}.amazonaws.com"
        return with_derived_default(data, "subsystem_smtp_host", host)

    subsystem_smtp_from_email: Optional[str] = Field(
        None,
        description="The From address of outgoing email. Set with SMARTER_SUBSYSTEM_SMTP_FROM_EMAIL.",
        examples=["no-reply@example.com"],
        title="SMTP From Address",
    )
    """
    The email address that appears in the "From" field of outgoing SMTP emails.

    Set it with ``SMARTER_SUBSYSTEM_SMTP_FROM_EMAIL``. See :meth:`derive_email_defaults`.

    :type: Optional[str]
    :default: ``no-reply@`` the platform's domain, e.g. ``no-reply@platform.example.com``
    """

    subsystem_smtp_host: Optional[str] = Field(
        None,
        description="The SMTP server. Set with SMARTER_SUBSYSTEM_SMTP_HOST.",
        examples=["email-smtp.us-east-1.amazonaws.com"],
        title="SMTP Host",
    )
    """
    The SMTP server that sends the platform's email.

    Set it with ``SMARTER_SUBSYSTEM_SMTP_HOST``. See :meth:`derive_email_defaults`.

    :type: Optional[str]
    :default: the AWS Simple Email Service endpoint of ``aws_region``, e.g.
        ``email-smtp.us-east-1.amazonaws.com``, or None without a region
    """

    @before_field_validator("subsystem_smtp_from_email", "subsystem_smtp_host")
    def validate_subsystem_smtp_optional(cls, v: Optional[str]) -> Optional[str]:
        """Validates the SMTP From address and host: None if it is missing, or a placeholder.

        Args:
            v (Optional[str]): The address, or the host.
        Returns:
            Optional[str]: The validated value.
        """
        if is_missing_value(v):
            return None
        if not isinstance(v, str):
            raise SmarterConfigurationError(f"of type {type(v)} is not a str.")
        return v.strip()

    subsystem_smtp_password: Annotated[Optional[SecretStr], HeldBy(*SmarterPodCapabilities.email)] = Field(
        None,
        description="The SMTP password for authentication. Assumed to be an AWS SES-generated IAM keypair secret.",
        examples=["your-smtp-password"],
        title="SMTP Password",
    )
    """
    The SMTP password for authentication.

    This setting provides the password used to authenticate with the SMTP server.
    It is required for sending emails through the SMTP server, which is optional.

    :type: Optional[SecretStr]
    :default: None if it is not set.
    :raises SmarterConfigurationError: If the value is not a valid password.
    """

    @before_field_validator("subsystem_smtp_password")
    def validate_subsystem_smtp_password(cls, v: Optional[SecretStr]) -> Optional[SecretStr]:
        """Validates the `smtp_password` field.

        Args:
            v (Optional[SecretStr]): The SMTP password to validate.
        Returns:
            Optional[SecretStr]: The validated SMTP password, or None if it is missing or a placeholder.
        """
        if v in THE_EMPTY_SET:
            v = field_default(cls, "subsystem_smtp_password")
        if is_missing_value(v):
            return None

        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError(f"smtp_password of type {type(v)} is not a SecretStr")
        return v

    subsystem_smtp_port: Optional[int] = Field(
        587,
        description="The SMTP port for sending emails.",
        examples=[25, 465, 587],
        title="SMTP Port Number",
    )
    """
    The SMTP port for sending emails.

    This setting specifies the port number used to connect to the SMTP server
    for sending outgoing emails.

    :type: Optional[int]
    :default: ``587``
    :raises SmarterConfigurationError: If the value is not a valid port number.
    """

    @before_field_validator("subsystem_smtp_port")
    def validate_subsystem_smtp_port(cls, v: Optional[Union[int, str]]) -> int:
        """Validates the `smtp_port` field.

        Args:
            v (Optional[int]): The SMTP port to validate.

        Returns:
            int: The validated SMTP port.
        """
        return parse_int_setting(
            "subsystem_smtp_port", v, field_default(cls, "subsystem_smtp_port"), minimum=1, maximum=65535
        )

    subsystem_smtp_use_ssl: Optional[bool] = Field(
        False,
        description="Whether to use SSL for SMTP connections.",
        examples=[True, False],
        title="SMTP Use SSL",
    )
    """
    Whether to use SSL for SMTP connections.

    This setting indicates whether SSL (Secure Sockets Layer) should be used
    when connecting to the SMTP server for sending emails.

    :type: Optional[bool]
    :default: ``False``
    :raises SmarterConfigurationError: If the value is not a boolean.
    """

    @before_field_validator("subsystem_smtp_use_ssl")
    def validate_subsystem_smtp_use_ssl(cls, v: Optional[Union[bool, str]]) -> bool:
        """Validates the `smtp_use_ssl` field.

        Args:
            v (Optional[Union[bool, str]]): The SMTP use SSL flag to validate.

        Returns:
            bool: The validated SMTP use SSL flag.
        """
        if isinstance(v, bool):
            return v
        if v in THE_EMPTY_SET:
            return field_default(cls, "subsystem_smtp_use_ssl")
        return str(v).lower() in ["true", "1", "yes", "on"]

    subsystem_smtp_use_tls: Optional[bool] = Field(
        True,
        description="Whether to use TLS for SMTP connections.",
        examples=[True, False],
        title="SMTP Use TLS",
    )
    """
    Whether to use TLS for SMTP connections.

    This setting indicates whether TLS (Transport Layer Security) should be used
    when connecting to the SMTP server for sending emails.

    :type: Optional[bool]
    :default: ``True``
    :raises SmarterConfigurationError: If the value is not a boolean.
    """

    @before_field_validator("subsystem_smtp_use_tls")
    def validate_subsystem_smtp_use_tls(cls, v: Optional[Union[bool, str]]) -> bool:
        """Validates the `smtp_use_tls` field.

        Args:
            v (Optional[Union[bool, str]]): The SMTP use TLS flag to validate.
        Returns:
            bool: The validated SMTP use TLS flag.
        """
        if isinstance(v, bool):
            return v
        if v in THE_EMPTY_SET:
            return field_default(cls, "subsystem_smtp_use_tls")
        return str(v).lower() in ["true", "1", "yes", "on"]

    subsystem_smtp_username: Annotated[Optional[SecretStr], HeldBy(*SmarterPodCapabilities.email)] = Field(
        None,
        description="The SMTP username for authentication. Assumed to be an AWS SES-generatred IAM keypair username.",
        examples=["your-smtp-username"],
        title="SMTP Username",
    )
    """
    The SMTP username for authentication.

    This setting provides the username used to authenticate with the SMTP server.
    It is required for sending emails through the SMTP server, which is optional.

    :type: Optional[SecretStr]
    :default: None if it is not set.
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("subsystem_smtp_username")
    def validate_subsystem_smtp_username(cls, v: Optional[SecretStr]) -> Optional[SecretStr]:
        """Validates the `smtp_username` field.

        Args:
            v (Optional[str]): The SMTP username to validate.

        Returns:
            Optional[SecretStr]: The validated SMTP username, or None if it is missing or a placeholder.
        """
        if v in THE_EMPTY_SET:
            v = field_default(cls, "subsystem_smtp_username")
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
            - smarter_settings.subsystem_smtp_host
            - smarter_settings.subsystem_smtp_port
            - smarter_settings.subsystem_smtp_username
            - smarter_settings.subsystem_smtp_password
            - smarter_settings.subsystem_smtp_from_email
        """
        required_fields = [
            self.subsystem_smtp_host,
            self.subsystem_smtp_port,
            self.subsystem_smtp_username,
            self.subsystem_smtp_password,
            self.subsystem_smtp_from_email,
        ]
        return not any(is_missing_value(field) for field in required_fields)


__all__ = ["EmailSettings"]
