"""Smarter API Manifest - Plugin.spec"""

import logging
import os
from typing import Any, ClassVar, Dict, List, Optional

import sqlparse
from pydantic import Field, field_validator
from sqlparse.exceptions import SQLParseError

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

    sqlQuery: str = Field(
        ...,
        description="The SQL query that this plugin will execute when invoked by the user prompt.",
    )
    parameters: Optional[List[Dict[str, Any]]] = Field(
        default_factory=dict,
        description="A JSON dict containing parameter names and data types. Example: {'unit': {'type': 'string', 'enum': ['Celsius', 'Fahrenheit'], 'description': 'The temperature unit to use.'}}",
    )
    testValues: Optional[List[Dict[str, Any]]] = Field(
        default_factory=dict,
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
