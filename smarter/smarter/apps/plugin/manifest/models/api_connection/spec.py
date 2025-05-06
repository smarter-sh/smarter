"""Smarter API Manifest - Plugin.spec"""

import logging
import os
from typing import ClassVar, Optional

from pydantic import Field, field_validator

from smarter.apps.plugin.manifest.models.plugin.const import MANIFEST_KIND
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.manifest.models import AbstractSAMSpecBase, SmarterBaseModel

from .enum import AuthMethods


logger = logging.getLogger(__name__)
filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"
SMARTER_PLUGIN_MAX_SYSTEM_ROLE_LENGTH = 2048


class ApiConnection(SmarterBaseModel):
    """Smarter API - generic API Connection class."""

    name: str = Field(
        ...,
        max_length=255,
        description="The name of the API connection, camelCase, without spaces. Example: 'weatherApi', 'stockApi'.",
    )
    description: str = Field(
        ...,
        description="A brief description of the API connection. Be verbose, but not too verbose.",
    )
    root_domain: str = Field(
        ...,
        description="The root domain of the API. Example: 'https://api.example.com'.",
    )
    api_key: Optional[str] = Field(
        None,
        description="The API key for authentication, if required.",
    )
    auth_method: str = Field(
        "none",
        description="The authentication method to use. Example: 'Basic Auth', 'Token Auth'.",
    )
    timeout: int = Field(
        30,
        description="The timeout for the API request in seconds. Default is 30 seconds.",
        ge=1,
    )
    version: str = Field(
        "1.0.0",
        description="The version of the API connection.",
    )

    # Proxy fields
    proxy_host: Optional[str] = Field(
        None,
        description="The remote host of the proxy connection.",
    )
    proxy_port: Optional[int] = Field(
        None,
        description="The port of the proxy connection.",
    )
    proxy_username: Optional[str] = Field(
        None,
        description="The username for the proxy connection.",
    )
    proxy_password: Optional[str] = Field(
        None,
        description="The password for the proxy connection.",
    )

    @field_validator("name")
    def validate_name(cls, v):
        if SmarterValidator.is_valid_cleanstring(v):
            return v
        raise SAMValidationError(f"Invalid Api connection name: {v}. Must be a valid cleanstring.")

    @field_validator("description")
    def validate_description(cls, v):
        if SmarterValidator.is_not_none(v):
            return v
        raise SAMValidationError("Description cannot be None.")

    @field_validator("root_domain")
    def validate_root_domain(cls, v):
        if SmarterValidator.is_valid_domain(v):
            return v
        raise SAMValidationError(f"Invalid root domain: {v}. Must be a valid domain.")

    @field_validator("api_key")
    def validate_api_key(cls, v):
        return v

    @field_validator("auth_method")
    def validate_auth_method(cls, v):
        valid_methods = AuthMethods.all_values()
        if v not in valid_methods:
            raise SAMValidationError(f"Invalid authentication method: {v}. Must be one of {valid_methods}.")
        return v

    @field_validator("timeout")
    def validate_timeout(cls, v):
        if v < 1:
            raise SAMValidationError("Timeout must be greater than or equal to 1.")
        return v

    @field_validator("version")
    def validate_version(cls, v):
        if SmarterValidator.is_valid_semantic_version(v):
            return v
        raise SAMValidationError(
            f"Invalid version: {v}. Must be a valid semantic version. example: 1.0.0, 2.1.0, 3.2.1-alpha, 4.0.0-beta+exp.sha.5114f85"
        )

    @field_validator("proxy_host")
    def validate_proxy_host(cls, v):
        if SmarterValidator.is_valid_url(v):
            return v
        raise SAMValidationError(f"Invalid proxy host: {v}. Must be a valid URL.")

    @field_validator("proxy_port")
    def validate_proxy_port(cls, v):
        if v is not None and (v < 1 or v > 65535):
            raise SAMValidationError("Proxy port must be between 1 and 65535.")
        return v

    @field_validator("proxy_username")
    def validate_proxy_username(cls, v):
        if not SmarterValidator.is_valid_cleanstring(v):
            raise SAMValidationError("Proxy username cannot be an empty string.")
        return v

    @field_validator("proxy_password")
    def validate_proxy_password(cls, v):
        return v


class SAMPluginDataApiConnectionSpec(AbstractSAMSpecBase):
    """Smarter API Api Connection Manifest ApiConnection.spec"""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    connection: ApiConnection = Field(
        ..., description=f"{class_identifier}.selector[obj]: the selector logic to use for the {MANIFEST_KIND}"
    )
