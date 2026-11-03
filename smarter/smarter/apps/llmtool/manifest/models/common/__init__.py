"""Smarter API Manifest - Plugin.spec."""

from enum import Enum
from typing import Any, List, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator

from smarter.common.exceptions import SmarterValueError
from smarter.lib.django.validators import SmarterValidator


class UrlParam(BaseModel):
    """Model for storing url param k-v pairs."""

    key: str = Field(..., description="The key (ie 'name') of the url param.")
    value: Union[str, int, float, bool] = Field(..., description="The value for the key.")

    @field_validator("key")
    def validate_name(cls, v):
        """
        Validate the url param's key as a clean string.

        :param v: The key.
        :returns: The key, as a string.
        :raises SmarterValueError: If it is not a clean string.
        """
        v = str(v)
        if not SmarterValidator.is_valid_cleanstring(v):
            raise SmarterValueError("Key must be a valid cleanstring.")
        return v

    @field_validator("value")
    def validate_value(cls, v):
        """
        Validate the url param's value as a clean string.

        :param v: The value.
        :returns: The value, as a string.
        :raises SmarterValueError: If it is not a clean string.
        """
        v = str(v)
        if not SmarterValidator.is_valid_cleanstring(v):
            raise SmarterValueError("Value must be a valid cleanstring.")
        return v


class RequestHeader(BaseModel):
    """Model for storing HTTP request headers."""

    name: str = Field(..., description="The name of the HTTP header.")
    value: Union[str, int, float, bool] = Field(..., description="The value of the HTTP header.")

    @field_validator("name")
    def validate_name(cls, v):
        """
        Validate the HTTP header's name.

        :param v: The header's name.
        :returns: The name, as a string.
        :raises SmarterValueError: If it has characters that a header name can't have, or is not ASCII.
        """
        v = str(v)

        if not SmarterValidator.is_valid_http_request_header_key(v):
            raise SmarterValueError("Header name contains invalid characters or is not ASCII.")
        return v

    @field_validator("value")
    def validate_value(cls, v):
        """
        Validate the HTTP header's value.

        :param v: The header's value.
        :returns: The value, as a string.
        :raises SmarterValueError: If it has characters that a header value can't have, e.g. control characters.
        """
        v = str(v)

        if not SmarterValidator.is_valid_http_request_header_value(v):
            raise SmarterValueError("Header value contains invalid characters (e.g., control characters).")
        return v


class TestValue(BaseModel):
    """TestValue class for SqlPlugin and ApiPlugin test values."""

    name: str = Field(..., description="The name of the parameter being tested.")
    value: Any = Field(..., description="The test value for the parameter.")

    @field_validator("value")
    def validate_value(cls, v) -> Optional[str]:
        """
        Convert the test value to a string, keeping None.

        :param v: The test value.
        :returns: The value as a string, or None.
        """
        if isinstance(v, str):
            return v
        if v is None:
            return v
        return str(v)


class ParameterType(str, Enum):
    """Enum for parameter types."""

    STRING = "string"
    NUMBER = "number"  # Used for both float and double
    INTEGER = "integer"
    BOOLEAN = "boolean"
    OBJECT = "object"
    ARRAY = "array"
    NULL = "null"


class Parameter(BaseModel):
    """
    Parameter class for parameterized Plugins.

    This structure is
    intended to match that which is used in the OpenAPI
    function calling specification.
    It is used to define the parameters that a plugin can accept,
    and also for creating the function calling prompt api.
    """

    class Config:
        use_enum_values = True

    name: str = Field(..., description="The name of the parameter.")
    type: ParameterType = Field(
        ...,
        description="The data type of the parameter (one of: string, number, integer, boolean, object, array, null).",
    )
    description: Optional[str] = Field(default=None, description="A description of the parameter.")
    required: bool = Field(default=False, description="Whether the parameter is required.")
    enum: Optional[List[str]] = Field(
        default=None,
        description="A list of allowed values for the parameter. Example: ['Celsius', 'Fahrenheit']",
    )
    default: Any = Field(None, description="The default value of the parameter, if any.")

    @field_validator("default")
    def validate_default(cls, v):
        """
        Convert the default value to a string, keeping None.

        :param v: The default value.
        :returns: The value as a string, or None.
        """
        return str(v) if v is not None else v

    @model_validator(mode="after")
    def validate_enum_and_default(self):
        """
        Check that the default value, if there is one, is one of the enum's values, if there are any.

        :returns: The parameter.
        :raises SmarterValueError: If the default is not one of the enum's values.
        """
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
