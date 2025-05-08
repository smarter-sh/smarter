"""Smarter API Manifest - Plugin.spec"""

import logging
import os
from typing import Any, ClassVar, Dict, Optional

from pydantic import Field, field_validator

from smarter.apps.plugin.models import SqlConnection
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.manifest.models import AbstractSAMSpecBase, SmarterBaseModel

from .const import MANIFEST_KIND


logger = logging.getLogger(__name__)
filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"
SMARTER_PLUGIN_MAX_SYSTEM_ROLE_LENGTH = 2048


class SqlData(SmarterBaseModel):
    """Smarter API - generic API Connection class."""

    name: str = Field(
        ...,
        max_length=255,
        description="The name of the SQL connection, camelCase, without spaces. Example: 'HRDatabase', 'SalesDatabase', 'InventoryDatabase'.",
    )
    connection: SqlConnection = Field(
        ...,
        description="The API connection associated with this plugin.",
    )
    parameters: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="A JSON dict containing parameter names and data types. Example: {'unit': {'type': 'string', 'enum': ['Celsius', 'Fahrenheit'], 'description': 'The temperature unit to use.'}}",
    )
    sql_query: str = Field(
        ...,
        description="The SQL query that this plugin will execute when invoked by the user prompt.",
    )
    test_values: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="A JSON dict containing test values for each parameter. Example: {'product_id': 1234}.",
    )
    limit: Optional[int] = Field(
        default=100,
        description="The maximum number of rows to return from the query. Must be a non-negative integer.",
    )

    @field_validator("name")
    def validate_name(cls, v):
        if not SmarterValidator.is_valid_cleanstring(v):
            raise SAMValidationError("Name must be a valid cleanstring.")
        if " " in v:
            raise SAMValidationError("Name must not contain spaces.")
        return v

    @field_validator("connection")
    def validate_connection(cls, v):
        if not isinstance(v, SqlConnection):
            raise SAMValidationError("Connection must be a valid SqlConnection instance.")
        return v

    @field_validator("parameters")
    def validate_parameters(cls, v):
        if not SmarterValidator.is_valid_json(v):
            raise SAMValidationError("Parameters must be a valid JSON object.")
        return v

    @field_validator("test_values")
    def validate_test_values(cls, v):
        if not SmarterValidator.is_valid_json(v):
            raise SAMValidationError("Test values must be a valid JSON object.")
        return v

    @field_validator("sql_query")
    def validate_sql_query(cls, v):
        if not v.strip():
            raise SAMValidationError("SQL query cannot be empty.")
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

    sql_data: SqlData = Field(
        ..., description=f"{class_identifier}.selector[obj]: the SqlData to use for the {MANIFEST_KIND}"
    )
