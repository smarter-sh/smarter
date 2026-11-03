"""Smarter API Manifest - ApiConnection.spec."""

import os
from typing import ClassVar, Optional

from pydantic import Field, field_validator

from smarter.apps.connection.manifest.models.api_connection.const import MANIFEST_KIND
from smarter.lib import logging
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.manifest.models import AbstractSAMSpecBase, SmarterBasePydanticModel

from .enum import AuthMethods

filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"


logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.CONNECTION_LOGGING])


class ApiConnection(SmarterBasePydanticModel):
    """Smarter API - generic API Connection class."""

    baseUrl: str = Field(
        ...,
        description="The root domain of the API. Example: 'https://api.example.com'.",
    )
    apiKey: Optional[str] = Field(
        None,
        description="The API key for authentication, if required.",
    )
    authMethod: str = Field(
        "none",
        description="The authentication method to use. Example: 'Basic Auth', 'Token Auth'.",
    )
    timeout: int = Field(
        30,
        description="The timeout for the API request in seconds. Default is 30 seconds.",
        ge=1,
    )

    # Proxy fields
    proxyProtocol: Optional[str] = Field(
        None,
        description="The protocol of the proxy connection. Example: 'http', 'https'.",
    )
    proxyHost: Optional[str] = Field(
        None,
        description="The remote host of the proxy connection.",
    )
    proxyPort: Optional[int] = Field(
        None,
        description="The port of the proxy connection.",
    )
    proxyUsername: Optional[str] = Field(
        None,
        description="The username for the proxy connection.",
    )
    proxyPassword: Optional[str] = Field(
        None,
        description="The password for the proxy connection.",
    )

    @field_validator("baseUrl")
    def validate_root_domain(cls, v):
        """
        Validate that ``baseUrl`` is a valid http or https url.

        :param v: The base url.
        :returns: The base url, unchanged.
        :raises SAMValidationError: if the url is not valid.
        """
        if SmarterValidator.is_valid_url(v):
            return v
        raise SAMValidationError(f"Invalid root domain or protocol: {v}. Must be a valid domain on http or https.")

    @field_validator("apiKey")
    def validate_api_key(cls, v):
        """
        Accept ``apiKey`` as is: it is the name of a Secret, not the key itself.

        :param v: The name of the Secret that holds the api key.
        :returns: The value, unchanged.
        """
        return v

    @field_validator("authMethod")
    def validate_auth_method(cls, v):
        """
        Validate that ``authMethod`` is one of the supported authentication methods.

        :param v: The authentication method.
        :returns: The authentication method, unchanged.
        :raises SAMValidationError: if it is not in ``AuthMethods.all()``.
        """
        valid_methods = AuthMethods.all()
        if v not in valid_methods:
            raise SAMValidationError(f"Invalid authentication method: {v}. Must be one of {valid_methods}.")
        return v

    @field_validator("timeout")
    def validate_timeout(cls, v):
        """
        Validate that ``timeout`` is at least 1.

        :param v: The timeout.
        :returns: The timeout, unchanged.
        :raises SAMValidationError: if it is less than 1.
        """
        if v < 1:
            raise SAMValidationError("Timeout must be greater than or equal to 1.")
        return v

    @field_validator("proxyProtocol")
    def validate_proxy_protocol(cls, v):
        """
        Validate that ``proxyProtocol``, when set, is ``http`` or ``https``.

        :param v: The proxy protocol, or None.
        :returns: The proxy protocol, unchanged.
        :raises SAMValidationError: if it is set to any other value.
        """
        valid_protocols = ["http", "https"]
        if v is not None and v not in valid_protocols:
            raise SAMValidationError(f"Invalid protocol {v}. Proxy protocol must be in {valid_protocols}")
        return v

    @field_validator("proxyHost")
    def validate_proxy_host(cls, v):
        """
        Validate that ``proxyHost``, when set, is a valid domain.

        :param v: The proxy host, or None.
        :returns: The proxy host, unchanged.
        :raises SAMValidationError: if it is not a valid domain.
        """
        if v is not None and not SmarterValidator.is_valid_domain(v):
            raise SAMValidationError(f"Invalid proxy host: {v}. Must be a valid URL.")
        return v

    @field_validator("proxyPort")
    def validate_proxy_port(cls, v):
        """
        Validate that ``proxyPort``, when set, is between 1 and 65535.

        :param v: The proxy port, or None.
        :returns: The proxy port, unchanged.
        :raises SAMValidationError: if it is out of range.
        """
        if v is not None and (v < 1 or v > 65535):
            raise SAMValidationError(f"Invalid proxy host: {v}. Must be between 1 and 65535.")
        return v

    @field_validator("proxyUsername")
    def validate_proxy_username(cls, v):
        """
        Validate that ``proxyUsername``, when set, contains no illegal characters.

        :param v: The proxy username, or None.
        :returns: The proxy username, unchanged.
        :raises SAMValidationError: if it is not a clean string.
        """
        if v is not None and not SmarterValidator.is_valid_cleanstring(v):
            raise SAMValidationError("Proxy username cannot contain illegal characters.")
        return v

    @field_validator("proxyPassword")
    def validate_proxy_password(cls, v):
        """
        Accept ``proxyPassword`` as is: it is the name of a Secret, not the password itself.

        :param v: The name of the Secret that holds the proxy password, or None.
        :returns: The value, unchanged.
        """
        return v


class SAMApiConnectionSpec(AbstractSAMSpecBase):
    """Smarter API Api Connection Manifest ApiConnection.spec."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    connection: ApiConnection = Field(
        ..., description=f"{class_identifier}.selector[obj]: the selector logic to use for the {MANIFEST_KIND}"
    )
