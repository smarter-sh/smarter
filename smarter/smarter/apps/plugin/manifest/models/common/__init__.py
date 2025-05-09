"""Smarter API Manifest - Plugin.spec"""

from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


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

    name: str = Field(..., description="The name of the parameter.")
    type: ParameterType = Field(..., description="The data type of the parameter (e.g., string, integer).")
    description: Optional[str] = Field(default=None, description="A description of the parameter.")
    required: bool = Field(default=False, description="Whether the parameter is required.")
    enum: Optional[List[str]] = Field(
        default=None,
        description="A list of allowed values for the parameter. Example: ['Celsius', 'Fahrenheit']",
    )
    default: Optional[str] = Field(None, description="The default value of the parameter, if any.")

    @model_validator(mode="after")
    def validate_enum_and_default(self):
        if self.default is None:
            return self
        if self.enum is None:
            return self
        # pylint: disable=E1135
        if self.default not in self.enum:
            raise ValueError(f"The default value '{self.default}' must be one of the allowed enum values: {self.enum}")
        return self
