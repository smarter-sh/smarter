"""Smarter API Manifest - Plugin.spec"""

import logging
import os
from typing import Any, ClassVar, List, Optional, Union

from pydantic import Field, field_validator

from smarter.apps.plugin.manifest.models.api_plugin.const import MANIFEST_KIND
from smarter.apps.plugin.manifest.models.common import (
    Parameter,
    RequestHeader,
    TestValue,
    UrlParam,
)
from smarter.apps.plugin.manifest.models.common.plugin.spec import SAMPluginCommonSpec
from smarter.common.exceptions import SmarterValueError
from smarter.lib.django import waffle
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.manifest.models import SmarterBasePydanticModel


filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"
SMARTER_PLUGIN_MAX_SYSTEM_ROLE_LENGTH = 2048


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.PLUGIN_LOGGING) and level >= logging.INFO


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class ApiData(SmarterBasePydanticModel):
    """Smarter API - apiData class."""

    endpoint: str = Field(
        ...,
        max_length=255,
        description="The endpoint path for the API. Example: '/v1/weather'.",
    )
    method: str = Field(
        default="GET",
        description="The HTTP method to use for the API request. Default is 'GET'.",
        max_length=10,
    )
    url_params: Optional[List[UrlParam]] = Field(
        default=None,
        description="A list of URL parameters to be included in the API request. Example: {'city': 'San Francisco'}",
    )
    headers: Optional[List[RequestHeader]] = Field(
        default=None,
        description="A list of JSON dict containing headers to be sent with the API request. Example: {'Authorization': 'Bearer <token>'}",
    )
    body: Optional[Union[dict[str, Any], list[Any]]] = Field(
        default=None,
        description="Any valid JSON object containing the body of the API request, if applicable.",
    )
    parameters: Optional[List[Parameter]] = Field(
        default=None,
        description="A JSON dict containing parameter names and data types. Example: {'city': {'type': 'string', 'description': 'City name'}}",
    )
    test_values: Optional[List[TestValue]] = Field(
        default=None,
        description="A JSON dict containing test values for each parameter. Example: {'city': 'San Francisco'}",
    )
    limit: Optional[int] = Field(
        default=100,
        description="The maximum number of records to return from the API. Default is 100.",
    )

    @field_validator("endpoint")
    def validate_endpoint(cls, v):
        try:
            SmarterValidator.validate_url_endpoint(v)
        except (SAMValidationError, SmarterValueError) as e:
            raise SAMValidationError(f"Invalid endpoint: {e}") from e
        return v

    @field_validator("method")
    def validate_method(cls, v):
        valid_methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
        if v.upper() not in valid_methods:
            raise SAMValidationError(f"Invalid HTTP method: {v}. Must be one of {valid_methods}.")
        return v.upper()


class SAMApiPluginSpec(SAMPluginCommonSpec):
    """Smarter API Manifest ApiConnection.spec"""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    connection: str = Field(
        ...,
        description=f"{class_identifier}.selector[obj]: the name of an existing SqlConnector to use for the {MANIFEST_KIND}",
    )

    apiData: ApiData = Field(
        ..., description=f"{class_identifier}.selector[obj]: the ApiData to use for the {MANIFEST_KIND}"
    )

    @field_validator("connection")
    def validate_connection(cls, v):
        if not SmarterValidator.is_valid_cleanstring(v):
            raise SAMValidationError(f"Connection, '{v}' must be a valid cleanstring.")
        return v
