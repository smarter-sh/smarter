"""Smarter API Manifest - Plugin.spec"""

import logging
import os
from typing import ClassVar, List, Optional

from pydantic import Field, field_validator

from smarter.apps.plugin.manifest.models.common import Parameter, TestValue
from smarter.apps.plugin.manifest.models.common.plugin.spec import SAMPluginCommonSpec
from smarter.lib.django import waffle
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.manifest.models import SmarterBasePydanticModel

from .const import MANIFEST_KIND


filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"
SMARTER_PLUGIN_MAX_SYSTEM_ROLE_LENGTH = 2048


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.PLUGIN_LOGGING) and level <= logging.INFO


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class SqlData(SmarterBasePydanticModel):
    """Smarter API - generic API Connection class."""

    description: Optional[str] = Field(
        default=None,
        description="A brief description what the Sql query returns.",
    )
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
        gt=0,
        description="The maximum number of rows to return from the query. Must be a non-negative integer.",
    )


class SAMSqlPluginSpec(SAMPluginCommonSpec):
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
            raise SAMValidationError(f"connection '{v}' must be a valid cleanstring with no illegal characters.")
        return v
