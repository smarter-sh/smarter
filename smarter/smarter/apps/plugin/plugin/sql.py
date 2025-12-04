"""A PLugin that uses a remote SQL database server to retrieve its return data"""

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
from smarter.common.conf import settings as smarter_settings
from smarter.common.exceptions import SmarterConfigurationError
from smarter.common.utils import camel_to_snake
from smarter.lib import json
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper
from smarter.lib.manifest.enum import SAMKeys, SAMMetadataKeys

from ..manifest.models.common.plugin.enum import SAMPluginCommonSpecTestValues
from ..manifest.models.sql_plugin.const import MANIFEST_KIND
from ..manifest.models.sql_plugin.enum import SAMSqlPluginSpecSqlData
from ..manifest.models.sql_plugin.model import SAMSqlPlugin
from ..models import PluginMeta
from .base import PluginBase, SmarterPluginError


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.PLUGIN_LOGGING) and level >= smarter_settings.log_level


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)
MAX_SQL_QUERY_LENGTH = 1000  # Maximum length of SQL query to prevent excessive load on the database


class SmarterSqlPluginError(SmarterPluginError):
    """Base class for all SQL plugin errors."""


class SqlPlugin(PluginBase):
    """
    Implements a plugin that executes SQL queries on a remote SQL database server to retrieve data.

    This class provides the logic for integrating SQL-based plugins into the Smarter platform. It supports
    manifest-driven configuration, parameter validation, and secure query execution. The plugin can be
    instantiated from either a manifest (Pydantic model) or an existing Django ORM instance.

    Key Features:
        - Accepts plugin configuration via manifest or ORM model.
        - Validates and recasts parameter definitions to conform to OpenAI function calling schema.
        - Interpolates user-provided arguments into SQL queries, with basic escaping for safety.
        - Executes queries using a remote SQL connection and returns results in JSON format.
        - Handles errors related to configuration, connection, and query execution.
        - Provides example manifest generation for testing and documentation.

    Usage:
        - Instantiate with a manifest or ORM model.
        - Use `tool_call_fetch_plugin_response()` to execute SQL queries with arguments from OpenAI tool calls.
        - Use `plugin_data_django_model` to convert manifest data to a Django ORM-compatible dictionary.
        - Use `example_manifest()` to generate a sample manifest for this plugin type.

    Notes:
        - SQL queries are interpolated using simple string replacement; ensure queries are safe and parameterized.
        - The maximum query length is limited to prevent excessive database load.
        - Logging is controlled via feature switches and log level settings.

    See Also:
        - OpenAI Function Calling: https://platform.openai.com/docs/guides/function-calling?api-mode=chat
        - Smarter Plugin Manifest Documentation
    """

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
        """
        Returns the kind identifier for this plugin.

        This property provides the canonical string used to distinguish the plugin type within the Smarter platform.
        The value is derived from the plugin manifest constant and is used for registration, serialization, and
        manifest validation.

        The kind is typically referenced in plugin manifests and API payloads to ensure the correct plugin logic
        is invoked for SQL-based plugins.

        :returns: The string identifier representing the plugin kind.
        :rtype: str

        :example:

            >>> plugin = SqlPlugin()
            >>> plugin.kind
            'sql'
        """
        return MANIFEST_KIND

    @property
    def manifest(self) -> Optional[SAMSqlPlugin]:
        """
        Retrieve the manifest for this plugin as a Pydantic model.

        This property returns the plugin's manifest, which contains the configuration and specification
        for the SQL plugin in the form of a validated Pydantic model. If the manifest is not already set
        and the plugin is ready, it will be constructed from the current plugin data using the appropriate
        Pydantic model class.

        The manifest is essential for validating plugin configuration, generating OpenAI-compatible schemas,
        and ensuring the plugin operates with the correct parameters and metadata.

        :returns: The manifest as a ``SAMSqlPlugin`` Pydantic model instance, or ``None`` if unavailable.
        :rtype: Optional[SAMSqlPlugin]

        .. note::

            If the manifest is not present but the plugin is ready, this property will attempt to reconstruct
            the manifest from the plugin's JSON representation.

        :example:

            >>> plugin = SqlPlugin()
            >>> manifest = plugin.manifest
            >>> print(manifest.spec.sqlData.sql_query)
            SELECT * FROM auth_user WHERE username = '{username}';
        """
        if not self._manifest and self.ready:
            # if we don't have a manifest but we do have Django ORM data then
            # we can work backwards to the Pydantic model
            self._manifest = self.SAMPluginType(**self.to_json())  # type: ignore[call-arg]
        return self._manifest

    @property
    def plugin_data(self) -> Optional[PluginDataSql]:
        """
        Return the plugin data as a Django ORM instance.

        This property provides access to the plugin's data in the form of a Django ORM model instance.
        It handles multiple scenarios for retrieving or constructing the plugin data:

        - If the plugin data has already been set, it is returned directly.
        - If both a manifest and plugin metadata are present, the plugin data is constructed from the manifest and metadata.
        - If only plugin metadata is present, the plugin data is retrieved from the database using the metadata.
        - If neither is available, the property returns ``None``.

        This logic ensures that the plugin data is always consistent with the current manifest and database state,
        supporting both creation and update workflows.

        :returns: The plugin data as a ``PluginDataSql`` Django ORM instance, or ``None`` if unavailable.
        :rtype: Optional[PluginDataSql]

        :raises PluginDataSql.DoesNotExist: If the plugin metadata is present but no corresponding database entry exists.

        .. note::

            This property does not create new database entries; it only retrieves or constructs plugin data
            based on existing manifest and metadata.

        :example:

            >>> plugin = SqlPlugin()
            >>> data = plugin.plugin_data
            >>> print(data.sql_query)
            SELECT * FROM auth_user WHERE username = '{username}';
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
        """
        Return the Django ORM model class used for plugin data.

        This property provides the class reference for the Django model that stores
        SQL plugin data in the Smarter platform. It is useful for type checking,
        serialization, and for constructing new instances of plugin data objects.

        The returned class can be used to create, query, or update plugin data
        records in the database. This is especially relevant when integrating
        with Django's ORM or when performing migrations and schema validation.

        :returns: The Django ORM model class for SQL plugin data.
        :rtype: Type[PluginDataSql]

        :example:

            >>> plugin = SqlPlugin()
            >>> model_cls = plugin.plugin_data_class
            >>> isinstance(model_cls(), PluginDataSql)
            True
        """
        return PluginDataSql

    @property
    def plugin_data_serializer(self) -> Optional[PluginSqlSerializer]:
        """
        Return the serializer instance for plugin data.

        This property provides a serializer object for the SQL plugin's data, allowing
        conversion between Django ORM model instances and JSON-compatible representations.
        The serializer is used for validating, serializing, and deserializing plugin data,
        especially when preparing data for API responses or manifest generation.

        If the serializer has not yet been instantiated, it will be created using the
        current plugin data. This ensures that the serializer always reflects the latest
        state of the plugin's data.

        :returns: An instance of ``PluginSqlSerializer`` for the plugin data, or ``None`` if plugin data is unavailable.
        :rtype: Optional[PluginSqlSerializer]

        :example:

            >>> plugin = SqlPlugin()
            >>> serializer = plugin.plugin_data_serializer
            >>> print(serializer.data)
            {'sql_query': "SELECT * FROM auth_user WHERE username = '{username}';", ...}
        """
        if not self._plugin_data_serializer:
            self._plugin_data_serializer = PluginSqlSerializer(self.plugin_data)
        return self._plugin_data_serializer

    @property
    def plugin_data_serializer_class(self) -> Type[PluginSqlSerializer]:
        """
        Return the serializer class used for SQL plugin data.

        This property provides the class reference for the serializer that is responsible
        for converting SQL plugin data between Django ORM model instances and JSON-compatible
        representations. The serializer class is essential for validation, serialization,
        and deserialization of plugin data, especially when integrating with APIs or
        generating manifests.

        Use this property when you need to instantiate a new serializer for SQL plugin data,
        perform type checks, or access serializer-specific methods and attributes.

        :returns: The serializer class for SQL plugin data.
        :rtype: Type[PluginSqlSerializer]

        :example:

            >>> plugin = SqlPlugin()
            >>> serializer_cls = plugin.plugin_data_serializer_class
            >>> serializer = serializer_cls(plugin.plugin_data)
            >>> isinstance(serializer, PluginSqlSerializer)
            True
        """
        return PluginSqlSerializer

    @property
    def plugin_data_django_model(self) -> Optional[dict[str, Any]]:
        """
        Transform the Pydantic model to the PluginDataSql Django ORM model and return the plugin data definition as a JSON object.

        See the OpenAI documentation:
        https://platform.openai.com/docs/guides/function-calling?api-mode=chat

        The Pydantic 'Parameters' model is not directly compatible with OpenAI's function calling schema,
        and our Django ORM model expects a dictionary format for the parameters. This method converts
        the Pydantic model to a dictionary suitable for creating a Django ORM model instance.

        :raises SmarterSqlPluginError: If the plugin manifest or SQL data is missing or invalid.
        :raises SmarterConfigurationError: If the parameters are not in the expected format.
        :returns: A dictionary representing the PluginDataSql Django ORM model.
        :rtype: Optional[dict[str, Any]]

        **Example of a correctly formatted dictionary:**

        .. code-block:: python

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

        **Example of a Pydantic model:**

        .. code-block:: python

            [
                {
                    "name": "max_cost",
                    "type": "float",
                    "description": "the maximum cost that a student is willing to pay for a course.",
                    "required": False,
                    "enum": None,
                    "default": None
                },
                {
                    "name": "description",
                    "type": "string",
                    "description": "areas of specialization for courses in the catalogue.",
                    "required": False,
                    "enum": ["AI", "mobile", "web", "database", "network", "neural networks"],
                    "default": None
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

        if not isinstance(self.plugin_meta, PluginMeta):
            raise SmarterSqlPluginError(
                f"{self.formatted_class_name}.plugin_data_django_model() error: {self.name} plugin metadata is not available."
            )

        if not isinstance(self.manifest, SAMSqlPlugin):
            raise SmarterSqlPluginError(
                f"{self.formatted_class_name}.plugin_data_django_model() error: {self.name} plugin manifest is not available."
            )
        if not isinstance(sql_data, dict):
            raise SmarterSqlPluginError(
                f"{self.formatted_class_name}.plugin_data_django_model() error: {self.name} plugin SQL data is not a valid dictionary."
            )

        return {
            "plugin": self.plugin_meta,
            "description": (
                self.manifest.metadata.description
                if self.manifest and self.manifest.metadata
                else self.plugin_meta.description if self.plugin_meta else None
            ),
            **sql_data,
        }  # type: ignore[call-arg]

    @classmethod
    def example_manifest(cls, kwargs: Optional[dict] = None) -> dict:
        """
        Generate an example manifest for the SqlPlugin.

        This class method creates a sample manifest dictionary for the SqlPlugin,
        illustrating the required structure and fields. The example manifest includes
        metadata, specification, and SQL query details, demonstrating how to configure
        the plugin for use within the Smarter platform.

        :param kwargs: Optional dictionary of additional fields to include in the manifest.
        :returns: A dictionary representing the example manifest for the SqlPlugin.
        :rtype: dict

        See Also:

        - :py:class:`smarter.lib.manifest.enum.SAMKeys`
        - :py:class:`smarter.lib.manifest.enum.SAMMetadataKeys`
        - :py:class:`smarter.apps.plugin.manifest.models.sql_plugin.model.SAMSqlPlugin`
        - :py:class:`smarter.apps.plugin.manifest.models.common.plugin.enum.SAMPluginCommonMetadataClassValues`
        - :py:class:`smarter.apps.plugin.manifest.models.common.plugin.enum.SAMPluginCommonSpecSelectorKeyDirectiveValues`
        - :py:class:`smarter.apps.plugin.manifest.models.common.plugin.enum.SAMPluginCommonSpecPromptKeys`
        """
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
        """
        Create the plugin in the database.

        This method handles the creation of the SQL plugin in the database by invoking
        the superclass's create method. It ensures that all necessary data is properly
        initialized and stored according to the plugin's configuration.

        .. note::

            This method currently does not implement any additional logic beyond calling
            the superclass's create method.

        :returns: None
        :rtype: None
        """
        logger.info("PluginDataSql.create() called.")
        super().create()

    def tool_call_fetch_plugin_response(self, function_args: Union[dict[str, Any], list]) -> Optional[str]:
        """
        Fetch information from a Plugin object in response to an OpenAI API tool call.

        This method processes the arguments received from an OpenAI function call,
        interpolates them into the SQL query, executes the query, and returns the result.

        See the OpenAI documentation:
        https://platform.openai.com/docs/assistants/tools/function-calling/quickstart

        **Example tool call payload:**

        .. code-block:: python

            "tool_calls": [
                {
                    "id": "call_1Ucn2R5WmBh7TtoE197SsP3p",
                    "function": {
                        "arguments": "{\"description\":\"AI\"}",  # these are the function_args
                        "name": "smarter_plugin_0000004468"
                    },
                    "type": "function"
                }
            ]

        :param function_args: Arguments for the function call, as a dict, list, or JSON string.
        :return: The result of the SQL query as a string, or an empty string if no results.
        :raises SmarterSqlPluginError: If plugin data or SQL connection is invalid, or arguments are malformed.
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
            retval = json.dumps(retval)
        elif not isinstance(retval, str):
            raise SmarterSqlPluginError(
                f"{self.formatted_class_name}.tool_call_fetch_plugin_response() error: {self.name} SQL query returned an unexpected type: {type(retval)}. Expected str, list, or dict."
            )
        return retval

    def to_json(self, version: str = "v1") -> Optional[dict[str, Any]]:
        """
        Serialize the SqlPlugin instance to a JSON-compatible dictionary suitable for Pydantic import.

        This method transforms the plugin's internal state, including its manifest and data,
        into a dictionary format that can be used to instantiate a Pydantic model. This is
        primarily used for rendering a plugin manifest for the Smarter API, enabling
        interoperability between Django ORM models and Pydantic schemas.

        The output includes all relevant plugin fields, with the SQL data section populated
        from the plugin's serializer. This ensures that the manifest is complete and
        conforms to the expected schema for API consumption or further validation.

        :param version: The API version to use for serialization. Only "v1" is supported.
        :type version: str

        :returns: A dictionary representing the plugin in JSON format, or ``None`` if the plugin is not ready.
        :rtype: Optional[dict[str, Any]]

        :raises SmarterPluginError: If the plugin is not ready, the data is not a valid JSON object, or an unsupported version is specified.

        :note:
            The returned dictionary is structured for compatibility with Pydantic models and
            the Smarter API manifest specification. The SQL data is injected from the plugin's
            serializer to ensure accurate representation.

        :example:

            >>> plugin = SqlPlugin()
            >>> manifest_json = plugin.to_json()
            >>> print(manifest_json["spec"]["sqlData"]["sql_query"])
            SELECT * FROM auth_user WHERE username = '{username}';
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
