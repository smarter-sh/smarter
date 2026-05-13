"""
PluginDataSql model for storing SQL-based plugin data configuration.
"""

import re
from typing import Optional, Union

from django.core.validators import MinValueValidator
from django.db import models
from pydantic import ValidationError

from smarter.apps.connection.models import SqlConnection
from smarter.apps.plugin.manifest.models.common import TestValue
from smarter.common.exceptions import SmarterValueError
from smarter.common.helpers.logger_helpers import formatted_text
from smarter.lib import logging
from smarter.lib.cache import cache_results
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .plugin_data_base import PluginDataBase
from .plugin_meta import PluginMeta

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.PLUGIN_LOGGING])
logger_prefix = formatted_text(f"{__name__}")


class PluginDataSql(PluginDataBase):
    """
    Stores SQL-based data configuration for a Smarter plugin.

    This model is used for plugins that return data by executing SQL queries.
    It defines the SQL connection, query, parameters, test values, and result limits.
    The model provides methods for validating parameter and test value structures,
    preparing SQL queries with parameters, and executing queries.

    ``PluginDataSql`` is a concrete subclass of :class:`PluginDataBase` and is referenced by :class:`PluginMeta`
    to provide the data payload for SQL-type plugins. It is tightly integrated with :class:`SqlConnection` for
    managing database connectivity and query execution, and supports advanced features such as parameterized queries,
    dynamic placeholder validation, and result limiting.

    This model is responsible for:
      - Storing the SQL query template and associated parameter schema.
      - Validating that all placeholders in the SQL query are defined in the parameters.
      - Ensuring that test values are provided and conform to the expected structure.
      - Preparing and executing SQL queries with runtime parameters, including safe substitution of placeholders.
      - Enforcing result limits to prevent excessive data retrieval.
      - Providing methods for returning sanitized query results for use in LLM responses.

    Typical use cases include plugins that need to retrieve or analyze data from organizational databases,
    support dynamic user queries, or expose structured data to the Smarter LLM platform.

    See also:

    - :class:`PluginDataBase`
    - :class:`SqlConnection`
    - :class:`PluginMeta`
    """

    # pylint: disable=C0115
    class DataTypes:
        STR = "string"
        NUMBER = "number"
        INT = "integer"
        BOOL = "bool"
        OBJECT = "object"
        ARRAY = "array"
        NULL = "null"

        @classmethod
        def all(cls) -> list[str]:
            return [cls.STR, cls.NUMBER, cls.INT, cls.BOOL, cls.OBJECT, cls.ARRAY, cls.NULL]

    connection = models.ForeignKey(SqlConnection, on_delete=models.CASCADE, related_name="plugin_data_sql_connection")
    sql_query = models.TextField(
        help_text="The SQL query that this plugin will execute when invoked by the user prompt.",
    )
    limit = models.IntegerField(
        help_text="The maximum number of rows to return from the query.",
        validators=[MinValueValidator(0)],
        blank=True,
        null=True,
    )

    def data(self, params: Optional[dict] = None) -> dict:
        return {
            "parameters": self.parameters,
            "sql_query": self.prepare_sql(params=params),
        }

    def are_test_values_pydantic(self) -> bool:
        if not isinstance(self.test_values, list):
            return False
        return all(isinstance(tv, dict) and "name" in tv and "value" in tv for tv in self.test_values)  # type: ignore  # pylint: disable=not-an-iterable

    def validate_test_values(self) -> None:
        """
        Validates the structure of the ``test_values`` attribute to ensure it matches the expected JSON representation.

        Each item in ``test_values`` must be a dictionary with the keys ``name`` and ``value``. This method attempts to instantiate each item as a Pydantic ``TestValue`` model to verify the structure.

        Example of a valid ``test_values`` list:

        .. code-block:: json

            [
                {"name": "username", "value": "admin"},
                {"name": "unit", "value": "Celsius"}
            ]

        :raises SmarterValueError: If any item in ``test_values`` does not conform to the required structure.
        """
        if self.test_values is None:
            return None
        if not isinstance(self.test_values, list):
            raise SmarterValueError(f"test_values must be a list of dictionaries but got: {type(self.test_values)}")

        # pylint: disable=E1133
        for test_value in self.test_values:
            try:
                TestValue(**test_value)
            except (ValidationError, SmarterValueError) as e:
                raise SmarterValueError(f"Invalid test value structure: {e}") from e

    def validate_all_placeholders_in_parameters(self) -> None:
        """
        Validates that every placeholder found in the SQL query string is defined as a parameter.

        This method scans the ``sql_query`` attribute for placeholders in the format ``{parameter_name}``.
        It then checks that each placeholder corresponds to a key in the ``parameters['properties']`` dictionary.
        If any placeholder is not defined in the parameters, a ``SmarterValueError`` is raised.

        **Example:**

            .. code-block:: python

                plugin = {
                    'plugin': <PluginMeta: sql_test>,
                    'description': 'test plugin',
                    'sql_query': "SELECT * FROM auth_user WHERE username = '{username}';",
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'username': {
                                'type': 'string',
                                'description': 'The username of the user.'
                            }
                        },
                        'required': ['username'],
                        'additionalProperties': False
                    },
                    'test_values': 'admin',
                    'limit': 1,
                    'connection': <SqlConnection: test_sql_connection - django.db.backends.mysql://smarter:******@smarter-mysql:3306/smarter>
                }

        :raises SmarterValueError: If a placeholder in the SQL query is not defined in the parameters.

        """
        placeholders = re.findall(r"{(.*?)}", self.sql_query) or []
        parameters = self.parameters or {}
        properties = parameters.get("properties", {})
        logger.info(
            "%s.validate_all_placeholders_in_parameters() Validating all placeholders in SQL query parameters: %s\n properties: %s, placeholders: %s",
            self.formatted_class_name,
            self.sql_query,
            properties,
            placeholders,
        )
        for placeholder in placeholders:
            if self.parameters is None or placeholder not in properties:
                raise SmarterValueError(f"Placeholder '{placeholder}' is not defined in parameters.")

    def validate(self) -> bool:
        super().validate()
        self.validate_test_values()
        self.validate_all_parameters_in_test_values()
        self.validate_all_placeholders_in_parameters()

        return True

    def prepare_sql(self, params: Optional[dict]) -> str:
        """Prepare the SQL query by replacing placeholders with values."""
        params = params or {}
        sql = self.sql_query
        for key, value in params.items():
            placeholder = "{" + key + "}"
            opening_tag = "<" + key + ">"
            closing_tag = "</" + key + ">"
            sql = sql.replace(placeholder, str(value)).replace(opening_tag, "").replace(closing_tag, "")
        if self.limit:
            sql += f" LIMIT {self.limit}"
        sql += ";"

        # Remove remaining tag pairs and any text between them
        sql = re.sub("<[^>]+>.*?</[^>]+>", "", sql)

        # Remove extra blank spaces
        sql = re.sub("\\s+", " ", sql)

        return sql

    def execute_query(self, params: Optional[dict]) -> Union[str, bool]:
        """Execute the SQL query and return the results."""
        sql = self.prepare_sql(params)
        return self.connection.execute_query(sql, self.limit)

    def test(self) -> Union[str, bool]:
        """Test the SQL query using the test_values in the record."""
        return self.execute_query(self.test_values)

    def sanitized_return_data(self, params: Optional[dict] = None) -> Union[str, bool]:
        """Return a dict by executing the query with the provided params."""
        logger.info("%s.sanitized_return_data called. - %s", self.formatted_class_name, params)
        return self.execute_query(params)

    def save(self, *args, **kwargs):
        """Override the save method to validate the field dicts."""
        self.validate()
        super().save(*args, **kwargs)
        self.get_cached_data_by_plugin(self.plugin, invalidate=True)

    # pylint: disable=W0221
    @classmethod
    def get_cached_object(
        cls,
        *args,
        invalidate: Optional[bool] = False,
        pk: Optional[int] = None,
        plugin: Optional[PluginMeta] = None,
        **kwargs,
    ) -> Optional["PluginDataBase"]:
        """
        Retrieve a model instance by primary key, using caching to
        optimize performance. This method is selectively overridden in
        models that inherit from MetaDataModel to provide class-specific
        function parameters.

        Example usage:

        .. code-block:: python

            # Retrieve by primary key
            instance = MyModel.get_cached_object(pk=1)

        :param invalidate: If True, invalidate the cache for this query before retrieving the object.
        :type invalidate: bool
        :param pk: The primary key of the model instance to retrieve.
        :type pk: int
        :param plugin: The PluginMeta instance associated with the data to retrieve.
        :type plugin: PluginMeta

        :returns: The model instance if found, otherwise None.
        :rtype: Optional["PluginDataBase"]
        """
        # pylint: disable=W0621
        logger_prefix = formatted_text(f"{__name__}.{PluginDataSql.__name__}.get_cached_object()")
        logger.debug(
            "%s called with pk: %s, plugin: %s",
            logger_prefix,
            pk,
            plugin,
        )

        @cache_results()
        def _get_model_by_plugin_meta(plugin_id: int) -> Optional["PluginDataBase"]:
            try:
                logger.debug(
                    "%s._get_model_by_plugin_meta() cache miss for plugin_id: %s",
                    logger_prefix,
                    plugin_id,
                )
                return cls.objects.prefetch_related("plugin").get(plugin_id=plugin_id)
            except cls.DoesNotExist as e:
                logger.warning(
                    "%s.get_cached_data_by_plugin() - Data not found for plugin_id: %s",
                    cls.formatted_class_name,
                    plugin_id,
                )
                raise cls.DoesNotExist(f"No {cls.formatted_class_name} found for plugin_id: {plugin_id}") from e

        if invalidate and plugin:
            _get_model_by_plugin_meta.invalidate(plugin.id)  # type: ignore[union-attr]

        if pk:
            return super().get_cached_object(*args, invalidate=invalidate, pk=pk, **kwargs)  # type: ignore[return-value]

        if plugin:
            return _get_model_by_plugin_meta(plugin.id)  # type: ignore[return-value]

    @classmethod
    def get_cached_data_by_plugin(cls, plugin: PluginMeta, invalidate: bool = False) -> Union["PluginDataSql", None]:
        """
        Return a single instance of PluginDataSql by plugin.

        This method caches the results to improve performance.

        :param plugin: The plugin whose data should be retrieved.
        :type plugin: PluginMeta
        :return: A PluginDataSql instance if found, otherwise None.
        :rtype: Union[PluginDataSql, None]
        """

        @cache_results()
        def data_by_plugin_id(plugin_id: int) -> Union["PluginDataSql", None]:
            try:
                return cls.objects.select_related("plugin").get(plugin_id=plugin_id)
            except cls.DoesNotExist as e:
                logger.warning(
                    "%s.get_cached_data_by_plugin() - Data not found for plugin_id: %s",
                    cls.formatted_class_name,
                    plugin_id,
                )
                raise cls.DoesNotExist(f"No {cls.formatted_class_name} found for plugin_id: {plugin_id}") from e

        if invalidate:
            data_by_plugin_id.invalidate(plugin.id)  # type: ignore[union-attr]

        return data_by_plugin_id(plugin.id)  # type: ignore[return-value]
