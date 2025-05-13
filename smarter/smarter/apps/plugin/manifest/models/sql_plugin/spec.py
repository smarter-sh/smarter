"""Smarter API Manifest - Plugin.spec"""

import logging
import os
from typing import ClassVar, List, Optional

from pydantic import Field, field_validator

from smarter.apps.plugin.manifest.models.common import Parameter, TestValue
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.manifest.models import AbstractSAMSpecBase, SmarterBasePydanticModel

from .const import MANIFEST_KIND


logger = logging.getLogger(__name__)
filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"
SMARTER_PLUGIN_MAX_SYSTEM_ROLE_LENGTH = 2048


class SqlData(SmarterBasePydanticModel):
    """Smarter API - generic API Connection class."""

    sql_query: str = Field(
        ...,
        description="The SQL query that this plugin will execute when invoked by the user prompt.",
    )
    parameters: Optional[List[Parameter]] = Field(
        default=None,
        description="A JSON dict containing parameter names and data types. Example: {'unit': {'type': 'string', 'enum': ['Celsius', 'Fahrenheit'], 'description': 'The temperature unit to use.'}}",
    )
    test_values: Optional[List[TestValue]] = Field(
        default=None,
        description="A JSON dict containing test values for each parameter. Example: {'product_id': 1234}.",
    )
    limit: Optional[int] = Field(
        default=100,
        gt=0,
        description="The maximum number of rows to return from the query. Must be a non-negative integer.",
    )


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
