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
from smarter.apps.plugin.manifest.models.common import Parameter
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
from .base import PluginBase, SmarterPluginError


logger = logging.getLogger(__name__)


class SmarterSqlPluginError(SmarterPluginError):
    """Base class for all SQL plugin errors."""


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
            self._plugin_data = PluginDataSql(**self.plugin_data_django_model)  # type: ignore[call-arg]
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

        Pydantic 'Parameters' model is not directly compatible with OpenAI's function calling schema,
        and our Django ORM model expects a dictionary format for the parameters.
        Therefore, we need to convert the Pydantic model to a dictionary that can be
        used to create a Django ORM model instance.

        example of a correctly formatted dictionary:
        {
            "properties": {
                "location": {
                    "type": "string",
                    "description": "The city and state, e.g., San Francisco, CA"
                },
                "unit": {
                    "type": "string",
                    "enum": ["Celsius", "Fahrenheit"],
                    "description": "The temperature unit to use. Infer this from the user's location."
                }
            },
            "required": ["location", "unit"]
        }


        example of a Pydantic model:
        [
            {
                'name': 'max_cost',
                'type': 'float',
                'description': 'the maximum cost that a student is willing to pay for a course.',
                'required': False,
                'enum': None,
                'default': None
            },
            {
                'name': 'description',
                'type': 'string',
                'description': 'areas of specialization for courses in the catalogue.',
                'required': False,
                'enum': ['AI', 'mobile', 'web', 'database', 'network', 'neural networks'],
                'default': None
            }
        ]
        """
        if self._manifest:
            # recast the Pydantic model to the PluginDataSql Django ORM model
            plugin_data_sqlconnection = SqlConnection.objects.get(
                account=self.user_profile.account if self.user_profile else None,
                name=self.manifest.spec.connection if self.manifest else None,
            )
            sql_data = self.manifest.spec.sqlData.model_dump() if self.manifest else None
            if not sql_data:
                raise SmarterSqlPluginError(
                    f"{self.formatted_class_name}.plugin_data_django_model() error: {self.name} missing required SQL data."
                )
            sql_data = {camel_to_snake(key): value for key, value in sql_data.items()}
            sql_data["connection"] = plugin_data_sqlconnection

            # recast the Pydantic model's parameters field
            # to conform to openai's function calling schema.
            recasted_parameters = {
                "properties": {},
                "required": [],
            }
            parameters = self.manifest.spec.sqlData.parameters if self.manifest and self.manifest.spec else None
            logger.info("plugin_data_django_model() recasting parameters: %s", parameters)
            if isinstance(parameters, list):
                for parameter in parameters:
                    if isinstance(parameter, Parameter):
                        # if the parameter is a Pydantic model, we need to convert it to a
                        # standard json dict.
                        parameter = parameter.model_dump()
                    logger.info("plugin_data_django_model() processing parameter: %s %s", type(parameter), parameter)
                    if not isinstance(parameter, dict):
                        raise SmarterConfigurationError(
                            f"{self.formatted_class_name}.plugin_data_django_model() error: {self.name} each parameter must be a valid json dict. Received: {parameter} {type(parameter)}"
                        )
                    if "name" not in parameter or "type" not in parameter:
                        raise SmarterConfigurationError(
                            f"{self.formatted_class_name}.plugin_data_django_model() error: {self.name} each parameter must have a 'name' and 'type' field. Received: {parameter}"
                        )
                    recasted_parameters["properties"][parameter["name"]] = {
                        "type": parameter["type"],
                        "description": parameter.get("description", ""),
                    }
                    if "enum" in parameter and parameter["enum"]:
                        if not isinstance(parameter["enum"], list):
                            raise SmarterConfigurationError(
                                f"{self.formatted_class_name}.plugin_data_django_model() error: {self.name} parameter 'enum' must be a list. Received: {parameter['enum']} {type(parameter['enum'])}"
                            )
                        recasted_parameters["properties"][parameter["name"]]["enum"] = parameter["enum"]
                    if parameter.get("required", False):
                        recasted_parameters["required"].append(parameter["name"])

                sql_data["parameters"] = recasted_parameters
            else:
                raise SmarterConfigurationError(
                    f"{self.formatted_class_name}.plugin_data_django_model() error: {self.name} parameters must be a list of dictionaries. Received: {parameters} {type(parameters)}"
                )

            return {
                "plugin": self.plugin_meta,
                "description": self.plugin_meta.description if self.plugin_meta else None,
                **sql_data,
            }

    @property
    def function_parameters(self) -> Optional[dict[str, Any]]:
        """
        Fetch the function parameters from the Django model.
        - format according to the OpenAI function calling schema.
        """
        if not self.plugin_data:
            raise SmarterSqlPluginError(
                f"{self.formatted_class_name}.function_parameters() error: {self.name} plugin data is not available."
            )
        retval = self.plugin_data.parameters
        if not isinstance(retval, dict):
            raise SmarterConfigurationError(
                f"{self.formatted_class_name}.function_parameters() error: {self.name} parameters must be a dictionary."
            )

        if "required" not in retval.keys():
            retval["required"] = []  # type: ignore[index]

        return retval

    @property
    def custom_tool(self) -> dict[str, Any]:
        """
        Return the plugin tool. see https://platform.openai.com/docs/assistants/tools/function-calling/quickstart

        example:
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "get_current_temperature",
                    "description": "Get the current temperature for a specific location",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "The city and state, e.g., San Francisco, CA"
                            },
                            "unit": {
                                "type": "string",
                                "enum": ["Celsius", "Fahrenheit"],
                                "description": "The temperature unit to use. Infer this from the user's location."
                            }
                        },
                        "required": ["location", "unit"]
                    }
                }
            }
        ]
        """
        if not self.ready:
            raise SmarterPluginError(
                f"{self.formatted_class_name}.custom_tool() error: {self.name} plugin is not ready."
            )
        if not self.plugin_data:
            raise SmarterPluginError(
                f"{self.formatted_class_name}.custom_tool() error: {self.name} plugin data is not available."
            )
        if not isinstance(self.plugin_data.parameters, dict):
            raise SmarterConfigurationError(
                f"{self.formatted_class_name}.custom_tool() error: {self.name} parameters must be a dictionary."
            )

        return {
            "type": "function",
            "function": {
                "name": self.function_calling_identifier,
                "description": self.plugin_data.description,
                "parameters": self.function_parameters,
            },
        }

    @classmethod
    def parameter_factory(
        cls,
        name: str,
        data_type: str,
        description: str,
        enum: Optional[list] = None,
        required: Optional[bool] = False,
        default: Optional[Any] = None,
    ) -> dict[str, Any]:
        """
        Factory method to create a parameter dictionary for the SQL plugin.
        """
        retval = {
            "name": name,
            "type": data_type,
            "description": description,
            "required": required,
            "default": default,
        }
        if enum:
            if not isinstance(enum, list):
                raise SmarterConfigurationError(
                    f"{cls.formatted_class_name}.parameter_factory() error: {name} enum must be a list."
                )
            retval["enum"] = enum
        return retval

    @classmethod
    def example_manifest(cls, kwargs: Optional[dict] = None) -> dict:
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
                        cls.parameter_factory(
                            name="username",
                            data_type="string",
                            description="The username to query.",
                            required=True,
                            default="admin",
                        ),
                        cls.parameter_factory(
                            name="unit",
                            data_type="string",
                            enum=["Celsius", "Fahrenheit"],
                            description="The temperature unit to use. Infer this from the user's location.",
                            default="Celsius",
                        ),
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
        logger.info("PluginDataSql.create() called.")
        super().create()

    def tool_call_fetch_plugin_response(self, function_args: dict[str, Any]) -> Optional[str]:
        """
        Fetch information from a Plugin object.
        """
        raise NotImplementedError("tool_call_fetch_plugin_response() must be implemented in a subclass of PluginBase.")
