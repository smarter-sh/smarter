"""Smarter API Manifest - Plugin.spec"""

import logging
import os
from typing import ClassVar, List, Optional, Union

from pydantic import Field, field_validator

from smarter.apps.plugin.manifest.models.api_plugin.const import MANIFEST_KIND
from smarter.apps.plugin.manifest.models.common import (
    Parameter,
    RequestHeader,
    TestValue,
    UrlParam,
)
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.manifest.models import AbstractSAMSpecBase, SmarterBaseModel


logger = logging.getLogger(__name__)
filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"
SMARTER_PLUGIN_MAX_SYSTEM_ROLE_LENGTH = 2048


class ApiData(SmarterBaseModel):
    """Smarter API - apiData class."""

    endpoint: str = Field(
        ...,
        max_length=255,
        description="The endpoint path for the API. Example: '/v1/weather'.",
    )
    url_params: Optional[List[UrlParam]] = Field(
        default=None,
        description="A list of URL parameters to be included in the API request. Example: {'city': 'San Francisco'}",
    )
    headers: Optional[List[RequestHeader]] = Field(
        default=None,
        description="A list of JSON dict containing headers to be sent with the API request. Example: {'Authorization': 'Bearer <token>'}",
    )
    body: Optional[Union[dict, list]] = Field(
        default=None,
        description="Any valid JSON object containing the body of the API request, if applicable.",
    )
    parameters: Optional[List[Parameter]] = Field(
        default=None,
        description="A JSON dict containing parameter names and data types. Example: {'city': {'type': 'string', 'description': 'City name'}}",
    )
    test_values: Optional[TestValue] = Field(
        default=None,
        description="A JSON dict containing test values for each parameter. Example: {'city': 'San Francisco'}",
    )
    limit: Optional[int] = Field(
        default=100,
        description="The maximum number of records to return from the API. Default is 100.",
    )

    @field_validator("endpoint")
    def validate_endpoint(cls, v):
        if not SmarterValidator.is_valid_cleanstring(v):
            raise SAMValidationError("Endpoint must be a valid cleanstring.")
        v = str(v)
        if not v.startswith("/"):
            raise SAMValidationError("Endpoint must start with a '/'.")
        if not v.endswith("/"):
            v += "/"
        return v


class SAMApiPluginSpec(AbstractSAMSpecBase):
    """Smarter API Manifest ApiConnection.spec"""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    connection: str = Field(
        ...,
        description=f"{class_identifier}.selector[obj]: the name of an existing SqlConnector to use for the {MANIFEST_KIND}",
    )

    apiData: ApiData = Field(
        ..., description=f"{class_identifier}.selector[obj]: the ApiData to use for the {MANIFEST_KIND}"
    )
