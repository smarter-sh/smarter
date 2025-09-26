"""A PLugin that uses a remote SQL database server to retrieve its return data"""

import json
import logging
import re
from typing import Any, Optional, Type, Union

from smarter.apps.plugin.manifest.enum import (
    SAMPluginCommonMetadataClass,
    SAMPluginCommonMetadataClassValues,
    SAMPluginCommonMetadataKeys,
    SAMPluginCommonSpecPromptKeys,
    SAMPluginCommonSpecSelectorKeyDirectiveValues,
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
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper
from smarter.lib.manifest.enum import SAMKeys, SAMMetadataKeys

from ..manifest.models.common.plugin.enum import SAMPluginCommonSpecTestValues
from ..manifest.models.sql_plugin.const import MANIFEST_KIND
from ..manifest.models.sql_plugin.enum import SAMSqlPluginSpecSqlData
from ..manifest.models.sql_plugin.model import SAMSqlPlugin
from .base import PluginBase, SmarterPluginError


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.PLUGIN_LOGGING) and level >= logging.INFO


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)
MAX_SQL_QUERY_LENGTH = 1000  # Maximum length of SQL query to prevent excessive load on the database


class SmarterSqlPluginError(SmarterPluginError):
    """Base class for all SQL plugin errors."""


class SqlPlugin(PluginBase):
    """A PLugin that uses an SQL query executed on a remote SQL database server to retrieve its return data"""

    SAMPluginType = SAMSqlPlugin

    _manifest: Optional[SAMSqlPlugin] = None
    _metadata_class = SAMPluginCommonMetadataClass.SQL.value
    _plugin_data: PluginDataSql | None = None
    _plugin_data_serializer: PluginSqlSerializer | None = None

    def __init__(
        self,
        *args,
        manifest: Optional[SAMSqlPlugin] = None,
        **kwargs,
    ):
        super().__init__(*args, manifest=manifest, **kwargs)

    @property
    def kind(self) -> str:
        """Return the kind of the plugin."""
        return MANIFEST_KIND

    @property
    def manifest(self) -> Optional[SAMSqlPlugin]:
        """Return the Pydandic model of the plugin."""
        if not self._manifest and self.ready:
            # if we don't have a manifest but we do have Django ORM data then
            # we can work backwards to the Pydantic model
            self._manifest = self.SAMPluginType(**self.to_json())  # type: ignore[call-arg]
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
    def plugin_data_class(self) -> Type[PluginDataSql]:
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
        see: https://platform.openai.com/docs/guides/function-calling?api-mode=chat
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
        if not self._manifest:
            return None

        sql_data = self.manifest.spec.sqlData.model_dump() if self.manifest else None
        if not sql_data:
            raise SmarterSqlPluginError(
                f"{self.formatted_class_name}.plugin_data_django_model() error: {self.name} missing required SQL data."
            )
        sql_data = {camel_to_snake(key): value for key, value in sql_data.items()}
        connection_name = self._manifest.spec.connection if self._manifest else None
        if connection_name:
            # recast the Pydantic model to the PluginDataSql Django ORM model
            try:
                account = self.user_profile.account if self.user_profile else None
                plugin_data_sqlconnection = SqlConnection.objects.get(
                    account=account,
                    name=connection_name,
                )
                sql_data["connection"] = plugin_data_sqlconnection
            except SqlConnection.DoesNotExist as e:
                raise SmarterSqlPluginError(
                    f"{self.formatted_class_name}.plugin_data_django_model() error: SqlConnection {connection_name} does not exist for account {account}. Error: {e}"
                ) from e

        # recast the Pydantic model's parameters field
        # to conform to openai's function calling schema.
        recasted_parameters = {"type": "object", "properties": {}, "required": [], "additionalProperties": False}
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
            "description": (
                self.manifest.metadata.description
                if self.manifest and self.manifest.metadata
                else self.plugin_meta.description if self.plugin_meta else None
            ),
            **sql_data,
        }

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
                    SAMPluginCommonSpecSelectorKeys.DIRECTIVE.value: SAMPluginCommonSpecSelectorKeyDirectiveValues.SEARCHTERMS.value,
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
                        {
                            SAMPluginCommonSpecTestValues.NAME.value: "username",
                            SAMPluginCommonSpecTestValues.VALUE.value: "admin",
                        },
                        {
                            SAMPluginCommonSpecTestValues.NAME.value: "unit",
                            SAMPluginCommonSpecTestValues.VALUE.value: "Celsius",
                        },
                    ],
                    SAMSqlPluginSpecSqlData.LIMIT.value: 1,
                },
            },
        }
        # recast the Python dict to the Pydantic model
        # in order to validate our output
        pydantic_model = cls.SAMPluginType(**sql_plugin)
        return json.loads(pydantic_model.model_dump_json())

    def create(self):
        logger.info("PluginDataSql.create() called.")
        super().create()

    def tool_call_fetch_plugin_response(self, function_args: Union[dict[str, Any], list]) -> Optional[str]:
        """
        Fetch information from a Plugin object. We're resonding to an iteration 1 request
        from openai api to fetch the plugin response for a tool call.

        example:
        "tool_calls": [
            {
                "id": "call_1Ucn2R5WmBh7TtoE197SsP3p",
                "function": {
                    "arguments": "{\"description\":\"AI\"}",          <--- these are the function_args
                    "name": "smarter_plugin_0000004468"
                },
                "type": "function"
            }
        ],

        """

        def sql_value(val):
            if val is None:
                return "NULL"
            if isinstance(val, str):
                # Escape single quotes for SQL
                return "'" + val.replace("'", "''") + "'"
            return str(val)

        def interpolate(sql, params):
            def repl(match):
                key = match.group(1)
                return sql_value(params.get(key))

            return re.sub(r"\{(\w+)\}", repl, sql)

        if not self.plugin_data:
            raise SmarterSqlPluginError(
                f"{self.formatted_class_name}.tool_call_fetch_plugin_response() error: {self.name} plugin data is not available."
            )
        sql_connection = self.plugin_data.connection
        if not isinstance(sql_connection, SqlConnection):
            raise SmarterSqlPluginError(
                f"{self.formatted_class_name}.tool_call_fetch_plugin_response() error: {self.name} plugin data SqlConnection is not a valid SqlConnection instance."
            )

        function_args = function_args or []
        if isinstance(function_args, str):
            try:
                function_args = json.loads(function_args)
            except json.JSONDecodeError as e:
                raise SmarterSqlPluginError(
                    f"{self.formatted_class_name}.tool_call_fetch_plugin_response() error: {self.name} function_args is not a valid JSON string. Error: {e}"
                ) from e
        if isinstance(function_args, dict):
            function_args = [function_args]

        if not isinstance(function_args, list):
            raise SmarterSqlPluginError(
                f"{self.formatted_class_name}.tool_call_fetch_plugin_response() error: {self.name} function_args must be a dict or a JSON string."
            )

        # combine the list of dictionaries into a single dictionary
        params = {}
        for d in function_args:
            params.update(d)

        # example sql query:
        # SELECT c.course_code, c.course_name, c.description, prerequisite.course_code AS prerequisite_course_code
        # FROM courses c
        #      LEFT JOIN courses prerequisite ON c.prerequisite_id = prerequisite.course_id
        # WHERE ((description LIKE '%' || {description}) OR ({description} IS NULL))
        #   AND (c.cost <= {max_cost} OR {max_cost} IS NULL)
        # ORDER BY c.prerequisite_id;
        sql = self.plugin_data.sql_query
        if not isinstance(sql, str):
            raise SmarterSqlPluginError(
                f"{self.formatted_class_name}.tool_call_fetch_plugin_response() error: {self.name} sql_query must be a string."
            )

        # function_args example: [{"description":"AI"}]
        # iterate the list and replace the placeholders in the SQL query
        # for arg in function_args:
        #     if not isinstance(arg, dict):
        #         raise SmarterSqlPluginError(
        #             f"{self.formatted_class_name}.tool_call_fetch_plugin_response() error: {self.name} function_args must be a list of dictionaries."
        #         )
        #     for key, value in arg.items():
        #         if not isinstance(key, str):
        #             raise SmarterSqlPluginError(
        #                 f"{self.formatted_class_name}.tool_call_fetch_plugin_response() error: {self.name} function_args keys must be strings."
        #             )
        #         sql = sql.replace(f"{{{key}}}", str(value))

        sql = interpolate(sql, params)
        sql = sql.strip()
        sql = sql.replace("\n", " ")
        sql = re.sub(r"\\.", "", sql)
        if not sql.endswith(";"):
            sql += ";"

        logger.info(
            "%s.tool_call_fetch_plugin_response() executing remote SQL query: %s", self.formatted_class_name, sql
        )

        retval = sql_connection.execute_query(
            sql=sql,
            limit=(
                self.plugin_data.limit
                if self.plugin_data.limit and self.plugin_data.limit < MAX_SQL_QUERY_LENGTH
                else MAX_SQL_QUERY_LENGTH
            ),
        )

        if not retval:
            logger.warning(
                "%s.tool_call_fetch_plugin_response() SQL query returned no results. Returning empty string.",
                self.formatted_class_name,
            )
            return ""
        if isinstance(retval, list) or isinstance(retval, dict):
            # convert the result to a JSON string
            retval = json.dumps(retval, indent=2)
        elif not isinstance(retval, str):
            raise SmarterSqlPluginError(
                f"{self.formatted_class_name}.tool_call_fetch_plugin_response() error: {self.name} SQL query returned an unexpected type: {type(retval)}. Expected str, list, or dict."
            )
        return retval

    def to_json(self, version: str = "v1") -> Optional[dict[str, Any]]:
        """
        Serialize a SqlPlugin in JSON format that is importable by Pydantic. This
        is used to create a Pydantic model from a Django ORM model
        for purposes of rendering a Plugin manifest for the Smarter API.
        """
        if self.ready:
            if version == "v1":
                retval = super().to_json(version=version)
                if not retval:
                    raise SmarterPluginError(
                        f"{self.formatted_class_name}.to_json() error: {self.name} plugin is not ready."
                    )
                if not isinstance(retval, dict):
                    raise SmarterPluginError(
                        f"{self.formatted_class_name}.to_json() error: {self.name} plugin data is not a valid JSON object. Received: {type(retval)}"
                    )
                retval[SAMKeys.SPEC.value][SAMPluginSpecKeys.SQL_DATA.value] = (
                    self.plugin_data_serializer.data if self.plugin_data_serializer else None
                )
                return json.loads(json.dumps(retval))
            raise SmarterPluginError(f"Invalid version: {version}")
        return None
