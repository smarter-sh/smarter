"""A PLugin that uses a remote SQL database server to retrieve its return data"""

import json
import logging
from typing import Any, Optional, Type

from smarter.apps.plugin.manifest.enum import (
    SAMPluginCommonMetadataClass,
    SAMPluginCommonMetadataClassValues,
    SAMPluginCommonMetadataKeys,
    SAMPluginCommonSpecPromptKeys,
    SAMPluginCommonSpecSelectorKeys,
    SAMPluginSpecKeys,
)
from smarter.apps.plugin.models import PluginDataSql, SqlConnection
from smarter.apps.plugin.serializers import PluginSqlSerializer
from smarter.common.api import SmarterApiVersions
from smarter.common.conf import SettingsDefaults
from smarter.common.exceptions import SmarterConfigurationError
from smarter.common.utils import camel_to_snake
from smarter.lib.manifest.enum import SAMKeys, SAMMetadataKeys

from ..manifest.models.sql_plugin.const import MANIFEST_KIND
from ..manifest.models.sql_plugin.enum import SAMSqlPluginSpecSqlData
from ..manifest.models.sql_plugin.model import SAMSqlPlugin
from .base import PluginBase


logger = logging.getLogger(__name__)


class SqlPlugin(PluginBase):
    """A PLugin that uses an SQL query executed on a remote SQL database server to retrieve its return data"""

    _metadata_class = SAMPluginCommonMetadataClass.SQL.value
    _plugin_data: PluginDataSql | None = None
    _plugin_data_serializer: PluginSqlSerializer | None = None
    _manifest: SAMSqlPlugin | None = None

    @property
    def manifest(self) -> Optional[SAMSqlPlugin]:
        """Return the Pydandic model of the plugin."""
        if not self._manifest and self.ready:
            # if we don't have a manifest but we do have Django ORM data then
            # we can work backwards to the Pydantic model
            self._manifest = SAMSqlPlugin(**self.to_json())  # type: ignore[call-arg]
        return self._manifest

    @property
    def plugin_data(self) -> Optional[PluginDataSql]:
        """
        Return the plugin data as a Django ORM instance.
        """
        if self._plugin_data:
            return self._plugin_data
        # we only want a preexisting manifest ostensibly sourced
        # from the cli, not a lazy-loaded
        if self._manifest and self.plugin_meta:
            # this is an update scenario. the Plugin exists in the database,
            # AND we've received manifest data from the cli.
            self._plugin_data = PluginDataSql(**self.plugin_data_django_model)
        if self.plugin_meta:
            # we don't have a Pydantic model but we do have an existing
            # Django ORM model instance, so we can use that directly.
            self._plugin_data = PluginDataSql.objects.get(
                plugin=self.plugin_meta,
            )
        # new Plugin scenario. there's nothing in the database yet.
        return self._plugin_data

    @property
    def plugin_data_class(self) -> type:
        """Return the plugin data class."""
        return PluginDataSql

    @property
    def plugin_data_serializer(self) -> Optional[PluginSqlSerializer]:
        """Return the plugin data serializer."""
        if not self._plugin_data_serializer:
            self._plugin_data_serializer = PluginSqlSerializer(self.plugin_data)
        return self._plugin_data_serializer

    @property
    def plugin_data_serializer_class(self) -> Type[PluginSqlSerializer]:
        """Return the plugin data serializer class."""
        return PluginSqlSerializer

    @property
    def plugin_data_django_model(self) -> Optional[dict[str, Any]]:
        """
        transform the Pydantic model to the PluginDataSql Django ORM model.
        Return the plugin data definition as a json object.
        """
        if self._manifest:
            # recast the Pydantic model to the PluginDataSql Django ORM model
            plugin_data_sqlconnection = SqlConnection.objects.get(
                account=self.user_profile.account if self.user_profile else None,
                name=self.manifest.spec.connection if self.manifest else None,
            )
            sql_data = self.manifest.spec.sqlData.model_dump() if self.manifest else None
            if not sql_data:
                raise SmarterConfigurationError(
                    f"{self.formatted_class_name}.plugin_data_django_model() error: {self.name} missing required SQL data."
                )
            sql_data = {camel_to_snake(key): value for key, value in sql_data.items()}
            sql_data["connection"] = plugin_data_sqlconnection
            return {
                "plugin": self.plugin_meta,
                "description": self.plugin_meta.description if self.plugin_meta else None,
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
                    f"{self.formatted_class_name}.custom_tool() error: {self.name} missing required parameter key: {e}"
                ) from e

            param_required = param.get("required", False)
            param_default = param.get("default", None)

            if param_type not in PluginDataSql.DataTypes.all():
                raise SmarterConfigurationError(
                    f"{self.formatted_class_name}.custom_tool() error: {self.name} invalid parameter type: {param_type}"
                )

            if param_enum and not isinstance(param_enum, list):
                raise SmarterConfigurationError(
                    f"{self.formatted_class_name}.custom_tool() error: {self.name} invalid parameter enum: {param_enum}. Must be a list."
                )

            retval = {
                "type": param_type,
                "enum": param_enum,
                "description": param_description,
                "required": param_required,
            }
            if param_default is not None:
                retval["default"] = param_default
            return retval

        # parameters Example:
        # {
        #   'unit': {
        #       'type': 'string',
        #       'enum': ['Celsius', 'Fahrenheit'],
        #       'required': False,
        #       'default': 'Celsius',
        #       'description': 'The temperature unit to use. Infer this from the user's location.'
        #   },
        #   'username': {
        #       'type': 'string',
        #       'description': 'The username to query.',
        #       'required': True,
        #       'default': 'admin'
        #   }
        # }
        properties = {}
        parameters: dict = self.plugin_data.parameters if self.plugin_data else None
        for key in parameters.keys() if parameters else {}:
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
        sql_plugin = {
            SAMKeys.APIVERSION.value: SmarterApiVersions.V1,
            SAMKeys.KIND.value: MANIFEST_KIND,
            SAMKeys.METADATA.value: {
                SAMMetadataKeys.NAME.value: "sql_example",
                SAMPluginCommonMetadataKeys.PLUGIN_CLASS.value: SAMPluginCommonMetadataClassValues.SQL.value,
                SAMMetadataKeys.DESCRIPTION.value: "Get additional information about the admin account of the Smarter platform.",
                SAMMetadataKeys.VERSION.value: "0.1.0",
                SAMMetadataKeys.TAGS.value: ["db", "sql", "database"],
            },
            SAMKeys.SPEC.value: {
                SAMPluginSpecKeys.SELECTOR.value: {
                    SAMPluginCommonSpecSelectorKeys.DIRECTIVE.value: SAMPluginCommonSpecSelectorKeys.SEARCHTERMS.value,
                    SAMPluginCommonSpecSelectorKeys.SEARCHTERMS.value: [
                        "smarter",
                        "users",
                        "admin",
                    ],
                },
                SAMPluginSpecKeys.PROMPT.value: {
                    SAMPluginCommonSpecPromptKeys.PROVIDER.value: SettingsDefaults.LLM_DEFAULT_PROVIDER,
                    SAMPluginCommonSpecPromptKeys.SYSTEMROLE.value: "You are a helpful assistant for Smarter platform. You can provide information about the admin account of the Smarter platform.\n",
                    SAMPluginCommonSpecPromptKeys.MODEL.value: SettingsDefaults.LLM_DEFAULT_MODEL,
                    SAMPluginCommonSpecPromptKeys.TEMPERATURE.value: SettingsDefaults.LLM_DEFAULT_TEMPERATURE,
                    SAMPluginCommonSpecPromptKeys.MAXTOKENS.value: SettingsDefaults.LLM_DEFAULT_MAX_TOKENS,
                },
                SAMPluginSpecKeys.CONNECTION.value: "example_connection",
                SAMPluginSpecKeys.SQL_DATA.value: {
                    "description": "Query the Django User model to retrieve detailed account information about the admin account for the Smarter platform .",
                    SAMSqlPluginSpecSqlData.SQL_QUERY.value: "SELECT * FROM auth_user WHERE username = '{username}';\n",
                    SAMSqlPluginSpecSqlData.PARAMETERS.value: [
                        {
                            "name": "username",
                            "type": "string",
                            "description": "The username to query.",
                            "required": True,
                            "default": "admin",
                        },
                        {
                            "name": "unit",
                            "type": "string",
                            "enum": ["Celsius", "Fahrenheit"],
                            "description": "The temperature unit to use.",
                            "required": False,
                            "default": "Celsius",
                        },
                    ],
                    SAMSqlPluginSpecSqlData.TEST_VALUES.value: [
                        {"name": "username", "value": "admin"},
                        {"name": "unit", "value": "Celsius"},
                    ],
                    SAMSqlPluginSpecSqlData.LIMIT.value: 1,
                },
            },
        }
        # recast the Python dict to the Pydantic model
        # in order to validate our output
        pydantic_model = SAMSqlPlugin(**sql_plugin)
        return json.loads(pydantic_model.model_dump_json())

    def create(self):
        super().create()

        logger.info("PluginDataSql.create() called.")
