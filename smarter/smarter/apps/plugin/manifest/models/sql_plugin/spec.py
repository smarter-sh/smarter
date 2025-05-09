"""Smarter API Manifest - Plugin.spec"""

import logging
import os
from enum import Enum
from typing import Any, ClassVar, List, Optional

import sqlparse
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlparse.exceptions import SQLParseError

from smarter.lib.django.validators import SmarterValidator
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.manifest.models import AbstractSAMSpecBase, SmarterBaseModel

from .const import MANIFEST_KIND


logger = logging.getLogger(__name__)
filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"
SMARTER_PLUGIN_MAX_SYSTEM_ROLE_LENGTH = 2048


class ParameterType(str, Enum):
    """Enum for parameter types."""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"


class Parameter(BaseModel):
    """Parameter class for SQL Data."""

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
    def validate_enum_and_default(cls, values: dict[str, Any]) -> dict[str, Any]:
        enum = values.get("enum")
        default = values.get("default")
        if enum and default and default not in enum:
            raise ValueError(f"The default value '{default}' must be one of the allowed enum values: {enum}")
        return values


class TestValue(BaseModel):
    """TestValue class for SQL Data."""

    name: str = Field(..., description="The name of the parameter being tested.")
    value: Any = Field(..., description="The test value for the parameter.")


class SqlData(SmarterBaseModel):
    """Smarter API - generic API Connection class."""

    sqlQuery: str = Field(
        ...,
        description="The SQL query that this plugin will execute when invoked by the user prompt.",
    )
    parameters: Optional[List[Parameter]] = Field(
        default=None,
        description="A JSON dict containing parameter names and data types. Example: {'unit': {'type': 'string', 'enum': ['Celsius', 'Fahrenheit'], 'description': 'The temperature unit to use.'}}",
    )
    testValues: Optional[List[TestValue]] = Field(
        default=None,
        description="A JSON dict containing test values for each parameter. Example: {'product_id': 1234}.",
    )
    limit: Optional[int] = Field(
        default=100,
        description="The maximum number of rows to return from the query. Must be a non-negative integer.",
    )

    @field_validator("sqlQuery")
    def validate_sql_query(cls, v):
        if not v:
            raise SAMValidationError("sqlQuery must be a non-empty string.")
        if not isinstance(v, str):
            raise SAMValidationError("sqlQuery must be a string.")
        try:
            sqlparse.parse(v)
        except SQLParseError as e:
            raise SAMValidationError(f"sqlQuery is not valid ANSI SQL: {e}") from e
        return v

    @field_validator("limit")
    def validate_limit(cls, v):
        if not v:
            return 100
        if not isinstance(v, int) or v < 0:
            raise SAMValidationError("Limit must be a non-negative integer.")
        return v


class SAMSqlPluginSpec(AbstractSAMSpecBase):
    """Smarter API SqlData Connection Manifest SqlConnection.spec"""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    connection: str = Field(
        ...,
        description=f"{class_identifier}.selector[obj]: the name of an existing SqlConnector to use for the {MANIFEST_KIND}",
    )

    sqlData: SqlData = Field(
        ..., description=f"{class_identifier}.selector[obj]: the SqlData to use for the {MANIFEST_KIND}"
    )

    @field_validator("connection")
    def validate_limit(cls, v):
        if not SmarterValidator.is_valid_cleanstring(v):
            raise SAMValidationError("connection must be a valid cleanstring with no illegal characters.")
        return v
