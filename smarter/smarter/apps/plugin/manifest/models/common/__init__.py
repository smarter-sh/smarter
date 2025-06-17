"""Smarter API Manifest - Plugin.spec"""

from enum import Enum
from typing import Any, List, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator

from smarter.common.exceptions import SmarterValueError
from smarter.lib.django.validators import SmarterValidator


class UrlParam(BaseModel):
    """
    Model for storing url param k-v pairs.
    """

    key: str = Field(..., description="The key (ie 'name') of the url param.")
    value: Union[str, int, float, bool] = Field(..., description="The value for the key.")

    @field_validator("key")
    def validate_name(cls, v):
        v = str(v)
        if not SmarterValidator.is_valid_cleanstring(v):
            raise SmarterValueError("Key must be a valid cleanstring.")
        return v

    @field_validator("value")
    def validate_value(cls, v):
        v = str(v)
        if not SmarterValidator.is_valid_cleanstring(v):
            raise SmarterValueError("Value must be a valid cleanstring.")
        return v


class RequestHeader(BaseModel):
    """
    Model for storing HTTP request headers.
    """

    name: str = Field(..., description="The name of the HTTP header.")
    value: Union[str, int, float, bool] = Field(..., description="The value of the HTTP header.")

    @field_validator("name")
    def validate_name(cls, v):
        v = str(v)

        if not SmarterValidator.is_valid_http_request_header_key(v):
            raise SmarterValueError("Header name contains invalid characters or is not ASCII.")
        return v

    @field_validator("value")
    def validate_value(cls, v):
        v = str(v)

        if not SmarterValidator.is_valid_http_request_header_value(v):
            raise SmarterValueError("Header value contains invalid characters (e.g., control characters).")
        return v


class TestValue(BaseModel):
    """TestValue class for SqlPlugin and ApiPlugin test values."""

    name: str = Field(..., description="The name of the parameter being tested.")
    value: Any = Field(..., description="The test value for the parameter.")

    @field_validator("value")
    def validate_value(cls, v) -> str:
        if isinstance(v, str):
            return v
        if v is None:
            return v
        return str(v)


class ParameterType(str, Enum):
    """Enum for parameter types."""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"


class Parameter(BaseModel):
    """
    Parameter class for parameterized Plugins. This structure is
    intended to match that which is used in the OpenAPI
    function calling specification.
    It is used to define the parameters that a plugin can accept,
    and also for creating the function calling prompt api.
    """

    class Config:
        use_enum_values = True

    name: str = Field(..., description="The name of the parameter.")
    type: ParameterType = Field(..., description="The data type of the parameter (e.g., string, integer).")
    description: Optional[str] = Field(default=None, description="A description of the parameter.")
    required: bool = Field(default=False, description="Whether the parameter is required.")
    enum: Optional[List[str]] = Field(
        default=None,
        description="A list of allowed values for the parameter. Example: ['Celsius', 'Fahrenheit']",
    )
    default: Optional[str] = Field(None, description="The default value of the parameter, if any.")

    @field_validator("default")
    def validate_default(cls, v):
        if v is None:
            return v
        if isinstance(v, str):
            return v
        return str(v)

    @model_validator(mode="after")
    def validate_enum_and_default(self):
        if self.default is None:
            return self
        if self.enum is None:
            return self
        # pylint: disable=E1135
        if self.default not in self.enum:
            raise SmarterValueError(
                f"The default value '{self.default}' must be one of the allowed enum values: {self.enum}"
            )
        return self
