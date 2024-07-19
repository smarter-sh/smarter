"""A PLugin that uses a remote SQL database server to retrieve its return data"""

import logging
import re

from smarter.apps.plugin.manifest.enum import (
    SAMPluginMetadataClass,
    SAMPluginMetadataClassValues,
    SAMPluginMetadataKeys,
    SAMPluginSpecKeys,
    SAMPluginSpecPromptKeys,
    SAMPluginSpecSelectorKeys,
)
from smarter.apps.plugin.models import PluginDataSql, PluginDataSqlConnection
from smarter.apps.plugin.serializers import PluginDataSqlSerializer
from smarter.common.api import SmarterApiVersions
from smarter.common.const import SmarterLLMDefaults
from smarter.common.exceptions import SmarterConfigurationError
from smarter.lib.manifest.enum import SAMKeys, SAMMetadataKeys

from ..manifest.models.plugin.const import MANIFEST_KIND
from ..models import PluginDataSql
from .base import PluginBase


logger = logging.getLogger(__name__)


class PluginSql(PluginBase):
    """A PLugin that uses an SQL query executed on a remote SQL database server to retrieve its return data"""

    _metadata_class = SAMPluginMetadataClass.SQL_DATA.value
    _plugin_data: PluginDataSql = None
    _plugin_data_serializer: PluginDataSqlSerializer = None

    @property
    def plugin_data(self) -> PluginDataSql:
        """Return the plugin data."""
        return self._plugin_data

    @property
    def plugin_data_class(self) -> type:
        """Return the plugin data class."""
        return PluginDataSql

    @property
    def plugin_data_serializer(self) -> PluginDataSqlSerializer:
        """Return the plugin data serializer."""
        if not self._plugin_data_serializer:
            self._plugin_data_serializer = PluginDataSqlSerializer(self.plugin_data)
        return self._plugin_data_serializer

    @property
    def plugin_data_serializer_class(self) -> PluginDataSqlSerializer:
        """Return the plugin data serializer class."""
        return PluginDataSqlSerializer

    @property
    def plugin_data_django_model(self) -> dict:
        """Return the plugin data definition as a json object."""

        def camel_to_snake(name):
            name = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
            return re.sub("([a-z0-9])([A-Z])", r"\1_\2", name).lower()

        # recast the Pydantic model to the PluginDataSql Django ORM model
        plugin_data_sqlconnection = PluginDataSqlConnection.objects.get(
            account=self.user_profile.account, name=self.manifest.spec.data.sqlData.connection
        )
        sql_data = self.manifest.spec.data.sqlData.model_dump()
        sql_data = {camel_to_snake(key): value for key, value in sql_data.items()}
        sql_data["connection"] = plugin_data_sqlconnection
        return {
            "plugin": self.plugin_meta,
            "description": self.manifest.spec.data.description,
            **sql_data,
        }

    @property
    def custom_tool(self) -> dict:
        """Return the plugin tool. see https://platform.openai.com/docs/assistants/tools/function-calling/quickstart"""

        def property_factory(param) -> dict:
            try:
                param_type = param["type"]
                param_enum = param["enum"] if "enum" in param else None
                param_description = param["description"]
            except KeyError as e:
                raise SmarterConfigurationError(
                    f"{self.name} PluginSql custom_tool() error: missing required parameter key: {e}"
                ) from e

            if param_type not in PluginDataSql.DataTypes.all():
                raise SmarterConfigurationError(
                    f"{self.name} PluginSql custom_tool() error: invalid parameter type: {param_type}"
                )

            if param_enum and not isinstance(param_enum, list):
                raise SmarterConfigurationError(
                    f"{self.name} PluginSql custom_tool() error: invalid parameter enum: {param_enum}. Must be a list."
                )

            return {
                "type": param_type,
                "enum": param_enum,
                "description": param_description,
            }

        properties = {}
        for key in self.plugin_data.parameters.keys() if self.plugin_data.parameters else {}:
            properties[key] = property_factory(param=self.plugin_data.parameters[key])

        if self.ready:
            return {
                "type": "function",
                "function": {
                    "name": self.function_calling_identifier,
                    "description": self.plugin_data.description,
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": [],
                    },
                },
            }
        return None

    @classmethod
    def example_manifest(cls, kwargs: dict = None) -> dict:
        return {
            SAMKeys.APIVERSION.value: SmarterApiVersions.V1,
            SAMKeys.KIND.value: MANIFEST_KIND,
            SAMKeys.METADATA.value: {
                SAMMetadataKeys.name: "SqlExample",
                SAMPluginMetadataKeys.PLUGIN_CLASS.value: SAMPluginMetadataClassValues.SQL.value,
                SAMMetadataKeys.DESCRIPTION.value: "Get additional information about the admin account of the Smarter platform.",
                SAMMetadataKeys.VERSION.value: "0.1.0",
                SAMMetadataKeys.TAGS.value: ["db", "sql", "database"],
            },
            SAMKeys.SPEC.value: {
                SAMPluginSpecKeys.SELECTOR.value: {
                    SAMPluginSpecSelectorKeys.DIRECTIVE.value: SAMPluginSpecSelectorKeys.SEARCHTERMS.value,
                    SAMPluginSpecSelectorKeys.SEARCHTERMS.value: ["admin", "Smarter platform", "admin account"],
                },
                SAMPluginSpecKeys.PROMPT.value: {
                    SAMPluginSpecPromptKeys.LLM_VENDOR.value: SmarterLLMDefaults.LLM_VENDOR,
                    SAMPluginSpecPromptKeys.SYSTEMROLE.value: SmarterLLMDefaults.SYSTEM_ROLE,
                    SAMPluginSpecPromptKeys.MODEL.value: SmarterLLMDefaults.MODEL,
                    SAMPluginSpecPromptKeys.TEMPERATURE.value: SmarterLLMDefaults.TEMPERATURE,
                    SAMPluginSpecPromptKeys.MAXTOKENS.value: SmarterLLMDefaults.MAX_TOKENS,
                },
                SAMPluginSpecKeys.DATA.value: {
                    "description": "Query the Django User model to retrieve detailed account information about the admin account for the Smarter platform .",
                    SAMPluginMetadataClass.SQL_DATA.value: {
                        "connection": "exampleConnection",
                        "sqlQuery": "SELECT * FROM auth_user WHERE username = 'admin';\n",
                        "parameters": None,
                        "testValues": None,
                        "limit": 1,
                    },
                },
            },
        }

    def create(self):
        super().create()

        logger.info("PluginSql.create() called.")
