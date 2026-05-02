"""Smarter API Manifest - Plugin.spec"""

import os
from typing import ClassVar, List, Optional

from pydantic import Field, model_validator

from smarter.apps.connection.models import SqlConnection
from smarter.apps.plugin.manifest.models.common import Parameter, TestValue
from smarter.apps.plugin.manifest.models.common.plugin.spec import SAMPluginCommonSpec
from smarter.lib import logging
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.manifest.models import SmarterBasePydanticModel

from .const import MANIFEST_KIND

filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"
SMARTER_PLUGIN_MAX_SYSTEM_ROLE_LENGTH = 2048


logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.PLUGIN_LOGGING])


class SqlData(SmarterBasePydanticModel):
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

    @model_validator(mode="after")
    def validate_connection(self):
        """
        Validate that the connection value is a valid cleanstring and that at
        least 1 record exists in the SqlConnection table with the given name.

        If the model includes an authenticated user then also validate that at
        least 1 record exists in the SqlConnection table with the given name that
        is accessible by the authenticated user.
        """
        v = self.connection
        if not SmarterValidator.is_valid_cleanstring(v):
            raise SAMValidationError(f"connection '{v}' must be a valid cleanstring with no illegal characters.")
        sql_connections = SqlConnection.objects.filter(name=v)
        if self.user:
            sql_connections = sql_connections.with_read_permission_for(user=self.user)
        if not sql_connections.exists():
            raise SAMValidationError(f"connection '{v}' does not exist or is not accessible.")
        return self
