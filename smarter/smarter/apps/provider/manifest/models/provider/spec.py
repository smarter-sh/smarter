"""Smarter API Manifest - Plugin.spec"""

import logging
import os
from typing import ClassVar, Optional

from pydantic import EmailStr, Field, field_validator

from smarter.apps.provider.manifest.models.provider.const import MANIFEST_KIND
from smarter.common.conf import settings as smarter_settings
from smarter.lib.django import waffle
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.manifest.models import AbstractSAMSpecBase, SmarterBasePydanticModel


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return (
        waffle.switch_is_active(SmarterWaffleSwitches.PROVIDER_LOGGING)
        and waffle.switch_is_active(SmarterWaffleSwitches.PLUGIN_LOGGING)
        and level >= smarter_settings.log_level
    )


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)

filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"


class Provider(SmarterBasePydanticModel):
    """Smarter API - generic API Connection class."""

    name: str = Field(
        ...,
        description="The name of the Provider. Case sensitive. Must be unique and not empty, with no leading or trailing whitespace and no special characters. example: 'OpenAI', 'GoogleAI', 'MetaAI'.",
    )
    description: Optional[str] = Field(
        None,
        description="A brief description of the Provider.",
    )
    base_url: Optional[str] = Field(
        None,
        description="The base URL for the Provider's API.",
    )
    api_key: Optional[str] = Field(
        None,
        description="The name of the Smarter Secret containing the API key to use for verification tests.",
    )
    connectivity_test_path: Optional[str] = Field(
        default="",
        description="The URL path to test connectivity with the Provider's API.",
    )
    logo: Optional[str] = Field(
        None,
        description="The logo of the Provider.",
    )
    website_url: Optional[str] = Field(
        None,
        description="The website_url URL of the Provider.",
    )
    contact_email: Optional[EmailStr] = Field(
        None,
        description="The contact email of the Provider.",
    )
    support_email: Optional[EmailStr] = Field(
        None,
        description="The support email of the Provider.",
    )
    terms_of_service_url: Optional[str] = Field(
        None,
        description="The terms of service URL of the Provider.",
    )
    docs_url: Optional[str] = Field(
        None,
        description="The documentation URL of the Provider.",
    )
    privacy_policy_url: Optional[str] = Field(
        None,
        description="The privacy policy URL of the Provider.",
    )

    @field_validator("name")
    def validate_name(cls, v):
        if SmarterValidator.is_valid_cleanstring(v):
            return v
        raise SAMValidationError(
            f"Invalid name: {v}. Must be a valid clean string. Case sensitive. Must be unique and not empty, with no leading or trailing whitespace and no special characters. example: 'OpenAI', 'GoogleAI', 'MetaAI'."
        )

    @field_validator("base_url")
    def validate_api_url(cls, v):
        if v is None or SmarterValidator.is_valid_url(v):
            return v
        raise SAMValidationError(f"Invalid API URL: {v}. Must be a valid URL.")

    @field_validator("api_key")
    def validate_api_key(cls, v):
        if v is None or SmarterValidator.is_valid_cleanstring(v):
            return v
        raise SAMValidationError(f"Invalid API key: {v}. Must be a valid clean string.")

    @field_validator("connectivity_test_path")
    def validate_connectivity_test_path(cls, v):
        if v is None or SmarterValidator.is_valid_cleanstring(v):
            return v
        raise SAMValidationError(f"Invalid connectivity test path: {v}. Must be a valid clean string.")

    @field_validator("logo")
    def validate_logo(cls, v):
        if v is None or SmarterValidator.is_valid_url(v):
            return v
        raise SAMValidationError(f"Invalid logo URL: {v}. Must be a valid URL.")

    @field_validator("website_url")
    def validate_website(cls, v):
        if v is None or SmarterValidator.is_valid_url(v):
            return v
        raise SAMValidationError(f"Invalid website_url URL: {v}. Must be a valid URL.")

    @field_validator("contact_email")
    def validate_contact_email(cls, v):
        if v is None or SmarterValidator.is_valid_email(v):
            return v
        raise SAMValidationError(f"Invalid contact email: {v}. Must be a valid email address.")

    @field_validator("support_email")
    def validate_support_email(cls, v):
        if v is None or SmarterValidator.is_valid_email(v):
            return v
        raise SAMValidationError(f"Invalid support email: {v}. Must be a valid email address.")

    @field_validator("terms_of_service_url")
    def validate_terms_of_service_url(cls, v):
        if v is None or SmarterValidator.is_valid_url(v):
            return v
        raise SAMValidationError(f"Invalid terms of service URL: {v}. Must be a valid URL.")

    @field_validator("docs_url")
    def validate_docs_url(cls, v):
        if v is None or SmarterValidator.is_valid_url(v):
            return v
        raise SAMValidationError(f"Invalid documentation URL: {v}. Must be a valid URL.")

    @field_validator("privacy_policy_url")
    def validate_privacy_policy_url(cls, v):
        if v is None or SmarterValidator.is_valid_url(v):
            return v
        raise SAMValidationError(f"Invalid privacy policy URL: {v}. Must be a valid URL.")


class SAMProviderSpec(AbstractSAMSpecBase):
    """Smarter API Api Connection Manifest ApiConnection.spec"""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    provider: Provider = Field(..., description=f"{class_identifier}.selector[obj]: the spec for the {MANIFEST_KIND}")
