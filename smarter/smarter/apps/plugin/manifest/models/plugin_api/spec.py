"""Smarter API Manifest - Plugin.spec"""

import logging
import os
from typing import ClassVar, Optional

from pydantic import Field, field_validator

from smarter.apps.plugin.manifest.models.plugin_api.const import MANIFEST_KIND
from smarter.apps.plugin.models import ApiConnection
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.manifest.models import AbstractSAMSpecBase, SmarterBaseModel


logger = logging.getLogger(__name__)
filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"
SMARTER_PLUGIN_MAX_SYSTEM_ROLE_LENGTH = 2048


class ApiData(SmarterBaseModel):
    """Smarter API - apiData class."""

    connection: ApiConnection = Field(
        ...,
        description="The API connection associated with this plugin.",
    )
    endpoint: str = Field(
        ...,
        max_length=255,
        description="The endpoint path for the API. Example: '/v1/weather'.",
    )
    parameters: Optional[dict] = Field(
        default_factory=dict,
        description="A JSON dict containing parameter names and data types. Example: {'city': {'type': 'string', 'description': 'City name'}}",
    )
    headers: Optional[dict] = Field(
        default_factory=dict,
        description="A JSON dict containing headers to be sent with the API request. Example: {'Authorization': 'Bearer <token>'}",
    )
    body: Optional[dict] = Field(
        default_factory=dict,
        description="A JSON dict containing the body of the API request, if applicable.",
    )
    test_values: Optional[dict] = Field(
        default_factory=dict,
        description="A JSON dict containing test values for each parameter. Example: {'city': 'San Francisco'}",
    )

    @field_validator("connection")
    def validate_connection(cls, v):
        if not isinstance(v, ApiConnection):
            raise SAMValidationError("Connection must be a valid ApiData instance.")
        return v

    @field_validator("endpoint")
    def validate_endpoint(cls, v):
        if not SmarterValidator.is_valid_cleanstring(v):
            raise SAMValidationError("Endpoint must be a valid cleanstring.")
        if not v.startswith("/"):
            raise SAMValidationError("Endpoint must start with a '/'.")
        return v

    @field_validator("parameters")
    def validate_parameters(cls, v):
        if not SmarterValidator.is_valid_json(v):
            raise SAMValidationError("Parameters must be a valid JSON object.")
        return v

    @field_validator("headers")
    def validate_headers(cls, v):
        if not SmarterValidator.is_valid_json(v):
            raise SAMValidationError("Headers must be a valid JSON object.")
        return v

    @field_validator("body")
    def validate_body(cls, v):
        if not SmarterValidator.is_valid_json(v):
            raise SAMValidationError("Body must be a valid JSON object.")
        return v

    @field_validator("test_values")
    def validate_test_values(cls, v):
        if not SmarterValidator.is_valid_json(v):
            raise SAMValidationError("Test values must be a valid JSON object.")
        return v


class SAMApiConnectionSpec(AbstractSAMSpecBase):
    """Smarter API Manifest ApiConnection.spec"""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    connection: ApiData = Field(
        ..., description=f"{class_identifier}.selector[obj]: the selector logic to use for the {MANIFEST_KIND}"
    )
