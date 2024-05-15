# pylint: disable=missing-docstring,missing-module-docstring,missing-class-docstring,missing-function-docstring
# pylint: disable=C0114,C0115
"""PluginMeta app models."""
import json
import logging
import re
from abc import abstractmethod
from functools import lru_cache
from http import HTTPStatus
from typing import Any, Union

import requests
import yaml
from django.contrib.auth.hashers import check_password, make_password
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import DatabaseError, models
from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.utils import ConnectionHandler
from taggit.managers import TaggableManager

from smarter.apps.account.models import Account, UserProfile
from smarter.common.exceptions import SmarterValueError
from smarter.lib.django.model_helpers import TimestampedModel

from .manifest.enum import SAMPluginMetadataClassValues
from .manifest.models.sql_connection.enum import DbEngines


logger = logging.getLogger(__name__)

SMARTER_PLUGIN_MAX_DATA_RESULTS = 50


def validate_no_spaces(value):
    if re.search(r"\s", value):
        raise SmarterValueError("The name should not include spaces.")


def dict_key_cleaner(key: str) -> str:
    """Clean a key by replacing spaces with underscores."""
    return str(key).replace("\n", "").replace("\r", "").replace("\t", "").replace(" ", "_")


def dict_keys_to_list(data: dict, keys=None) -> list[str]:
    """recursive function to extract all keys from a nested dictionary."""
    if keys is None:
        keys = []
    for key, value in data.items():
        keys.append(key)
        if isinstance(value, dict):
            dict_keys_to_list(value, keys)
    return keys


def list_of_dicts_to_list(data: list[dict]) -> list[str]:
    """Convert a list of dictionaries into a single dict with keys extracted
    from the first key in the first dict."""
    if not data or not isinstance(data[0], dict):
        return None
    logger.warning("converting list of dicts to a single dict")
    retval = []
    key = next(iter(data[0]))
    for d in data:
        if key in d:
            cleaned_key = dict_key_cleaner(d[key])
            retval.append(cleaned_key)
    return retval


def list_of_dicts_to_dict(data: list[dict]) -> dict:
    """Convert a list of dictionaries into a single dict with keys extracted
    from the first key in the first dict."""
    if not data or not isinstance(data[0], dict):
        return None
    retval = {}
    key = next(iter(data[0]))
    for d in data:
        if key in d:
            cleaned_key = dict_key_cleaner(d[key])
            retval[cleaned_key] = d[key]
    return retval


class PluginMeta(TimestampedModel):
    """PluginMeta model."""

    PLUGIN_CLASSES = [
        (SAMPluginMetadataClassValues.STATIC.value, "PluginStatic"),
        (SAMPluginMetadataClassValues.SQL.value, "PluginDataSql"),
        (SAMPluginMetadataClassValues.API.value, "PluginDataSqlConnection"),
    ]

    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="plugin_meta")
    name = models.CharField(
        help_text="The name of the plugin. Example: 'HR Policy Update' or 'Public Relation Talking Points'.",
        max_length=255,
    )
    description = models.TextField(
        help_text="A brief description of the plugin. Be verbose, but not too verbose.",
    )
    plugin_class = models.CharField(
        choices=PLUGIN_CLASSES, help_text="The class name of the plugin", max_length=255, default="PluginMeta"
    )
    version = models.CharField(max_length=255, default="1.0.0")
    author = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="plugin_meta")
    tags = TaggableManager(blank=True)

    def __str__(self):
        return str(self.name) or ""

    # pylint: disable=missing-class-docstring
    class Meta:
        unique_together = (
            "account",
            "name",
        )
        verbose_name = "Plugin"
        verbose_name_plural = "Plugins"


class PluginSelector(TimestampedModel):
    """PluginSelector model."""

    plugin = models.OneToOneField(PluginMeta, on_delete=models.CASCADE, related_name="plugin_selector")
    directive = models.CharField(
        help_text="The selection strategy to use for this plugin.", max_length=255, default="search_terms"
    )
    search_terms = models.JSONField(
        help_text="search terms in JSON format that, if detected in the user prompt, will incentivize Smarter to load this plugin.",
        default=list,
    )

    def __str__(self) -> str:
        search_terms = json.dumps(self.search_terms)[:50]
        return f"{str(self.directive)} - {search_terms}"


class PluginSelectorHistory(TimestampedModel):
    """PluginSelectorHistory model."""

    plugin_selector = models.ForeignKey(
        PluginSelector, on_delete=models.CASCADE, related_name="plugin_selector_history"
    )
    search_term = models.CharField(max_length=255, blank=True, null=True, default="")
    messages = models.JSONField(help_text="The user prompt messages.", default=list, blank=True, null=True)

    def __str__(self) -> str:
        return f"{str(self.plugin_selector.plugin.name)} - {self.search_term}"

    class Meta:
        verbose_name_plural = "Plugin Selector History"


class PluginPrompt(TimestampedModel):
    """PluginPrompt model."""

    plugin = models.OneToOneField(PluginMeta, on_delete=models.CASCADE, related_name="plugin_prompt")
    system_role = models.TextField(
        help_text="The role of the system in the conversation.",
        null=True,
        blank=True,
        default="You are a helful assistant.",
    )
    model = models.CharField(help_text="The model to use for the completion.", max_length=255, default="gpt-3.5-turbo")
    temperature = models.FloatField(
        help_text="The higher the temperature, the more creative the result.",
        default=0.5,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
    )
    max_tokens = models.IntegerField(
        help_text="The maximum number of tokens for both input and output.",
        default=256,
        validators=[MinValueValidator(0), MaxValueValidator(4096)],
    )

    def __str__(self) -> str:
        return str(self.plugin.name)


class PluginDataBase(TimestampedModel):
    """PluginDataBase model."""

    plugin = models.OneToOneField(PluginMeta, on_delete=models.CASCADE, related_name="plugin_data_base")

    description = models.TextField(
        help_text="A brief description of what this plugin returns. Be verbose, but not too verbose.",
    )

    def sanitized_return_data(self, params: dict = None) -> dict:
        """Returns a dict of custom data return results."""
        raise NotImplementedError

    @abstractmethod
    def data(self, params: dict = None) -> dict:
        raise NotImplementedError


class PluginDataStatic(PluginDataBase):
    """PluginDataStatic model."""

    static_data = models.JSONField(
        help_text="The JSON data that this plugin returns to OpenAI API when invoked by the user prompt.", default=dict
    )

    def sanitized_return_data(self, params: dict = None) -> dict:
        """Returns a dict of self.static_data."""
        retval: dict = {}
        if isinstance(self.static_data, dict):
            return self.static_data
        if isinstance(self.static_data, list):
            retval = self.static_data
            if isinstance(retval, list) and len(retval) > 0:
                if len(retval) > SMARTER_PLUGIN_MAX_DATA_RESULTS:
                    logger.warning(
                        "PluginDataStatic.sanitized_return_data: Truncating static_data to %s items.",
                        {SMARTER_PLUGIN_MAX_DATA_RESULTS},
                    )
                retval = retval[:SMARTER_PLUGIN_MAX_DATA_RESULTS]  # pylint: disable=E1136
                retval = list_of_dicts_to_dict(data=retval)
        else:
            raise SmarterValueError("static_data must be a dict or a list or None")

        return retval

    @property
    @lru_cache(maxsize=128)
    def return_data_keys(self) -> list:
        """Return all keys in the static_data."""

        retval: list = []
        if isinstance(self.static_data, dict):
            retval = dict_keys_to_list(data=self.static_data)
            retval = list(retval)
        elif isinstance(self.static_data, list):
            retval = self.static_data
            if isinstance(retval, list) and len(retval) > 0:
                if len(retval) > SMARTER_PLUGIN_MAX_DATA_RESULTS:
                    logger.warning(
                        "PluginDataStatic.return_data_keys: Truncating static_data to %s items.",
                        {SMARTER_PLUGIN_MAX_DATA_RESULTS},
                    )
                retval = retval[:SMARTER_PLUGIN_MAX_DATA_RESULTS]  # pylint: disable=E1136
                retval = list_of_dicts_to_list(data=retval)
        else:
            raise SmarterValueError("static_data must be a dict or a list or None")

        return retval[:SMARTER_PLUGIN_MAX_DATA_RESULTS]  # pylint: disable=E1136

    def data(self, params: dict = None) -> dict:
        return yaml.dump(self.static_data)

    def __str__(self) -> str:
        return str(self.plugin.name)

    class Meta:
        verbose_name = "Plugin Static Data"
        verbose_name_plural = "Plugin Static Data"


class PluginDataSqlConnection(TimestampedModel):
    """PluginDataSql Connection model."""

    DBMS_CHOICES = [
        (DbEngines.MYSQL.value, "MySQL"),
        (DbEngines.POSTGRES.value, "PostgreSQL"),
        (DbEngines.SQLITE.value, "SQLite3"),
        (DbEngines.ORACLE.value, "Oracle"),
        (DbEngines.MSSQL.value, "MS SQL Server"),
        (DbEngines.SYBASE.value, "Sybase"),
    ]
    name = models.CharField(
        help_text="The name of the connection, without spaces. Example: 'HRDatabase', 'SalesDatabase', 'InventoryDatabase'.",
        max_length=255,
        validators=[validate_no_spaces],
    )
    db_engine = models.CharField(
        help_text="The type of database management system. Example: 'MySQL', 'PostgreSQL', 'MS SQL Server', 'Oracle'.",
        max_length=255,
        choices=DBMS_CHOICES,
    )
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="plugin_data_sql_connections")
    hostname = models.CharField(max_length=255)
    port = models.IntegerField()
    database = models.CharField(max_length=255)
    username = models.CharField(max_length=255)
    password = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    # Proxy fields
    proxy_host = models.CharField(max_length=255, blank=True, null=True)
    proxy_port = models.IntegerField(blank=True, null=True)
    proxy_username = models.CharField(max_length=255, blank=True, null=True)
    proxy_password = models.CharField(max_length=255, blank=True, null=True)

    def set_password(self, raw_password):
        self.password = make_password(raw_password)
        self.save()

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    def set_proxy_password(self, raw_password):
        self.proxy_password = make_password(raw_password)
        self.save()

    def check_proxy_password(self, raw_password):
        return check_password(raw_password, self.proxy_password)

    def connect(self) -> Union[BaseDatabaseWrapper, bool]:
        databases = {
            "default": {
                "ENGINE": self.db_engine,
                "NAME": self.database,
                "USER": self.username,
                "PASSWORD": self.password,
                "HOST": self.hostname,
                "PORT": str(self.port),
            }
        }
        try:
            connection_handler = ConnectionHandler(databases)
            connection = connection_handler["default"]
            connection.ensure_connection()
            return connection
        except DatabaseError as e:
            logger.error("db test connection failed: %s", e)
            return False

    def execute_query(self, sql: str) -> Union[list[tuple[Any, ...]], bool]:
        connection = self.connect()
        if not connection:
            return False
        with connection.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()
            return rows

    def test_proxy(self) -> bool:
        proxy_dict = {
            "http": f"http://{self.proxy_username}:{self.proxy_password}@{self.proxy_host}:{self.proxy_port}",
            "https": f"https://{self.proxy_username}:{self.proxy_password}@{self.proxy_host}:{self.proxy_port}",
        }
        try:
            response = requests.get("http://www.google.com", proxies=proxy_dict, timeout=30)
            return response.status_code in [HTTPStatus.OK, HTTPStatus.PERMANENT_REDIRECT]
        except requests.exceptions.RequestException as e:
            logger.error("proxy test connection failed: %s", e)
            return False

    def get_connection_string(self):
        """Return the connection string."""
        return f"{self.db_engine}://{self.username}@{self.hostname}:{self.port}/{self.database}"

    def validate(self) -> bool:
        return isinstance(self.connect(), BaseDatabaseWrapper)

    def __str__(self) -> str:
        return self.name + " - " + self.get_connection_string()


class PluginDataSql(PluginDataBase):
    """PluginDataSql model."""

    class DataTypes:
        INT = "int"
        FLOAT = "float"
        STR = "str"
        BOOL = "bool"
        LIST = "list"
        DICT = "dict"
        NULL = "null"

        @classmethod
        def all(cls) -> list:
            return [cls.INT, cls.FLOAT, cls.STR, cls.BOOL, cls.LIST, cls.DICT, cls.NULL]

    connection = models.ForeignKey(PluginDataSqlConnection, on_delete=models.CASCADE, related_name="plugin_data_sql")
    parameters = models.JSONField(
        help_text="A JSON dict containing parameter names and data types. Example: {'unit': {'type': 'string', 'enum': ['Celsius', 'Fahrenheit'], 'description': 'The temperature unit to use. Infer this from the user's location.'}}",
        default=dict,
        blank=True,
        null=True,
    )
    sql_query = models.TextField(
        help_text="The SQL query that this plugin will execute when invoked by the user prompt.",
    )
    test_values = models.JSONField(
        help_text="A JSON dict containing test values for each parameter. Example: {'product_id': 1234}",
        default=dict,
        blank=True,
        null=True,
    )
    limit = models.IntegerField(
        help_text="The maximum number of rows to return from the query.",
        default=100,
        validators=[MinValueValidator(0)],
        blank=True,
        null=True,
    )

    def data(self, params: dict = None) -> dict:
        return {
            "parameters": self.parameters,
            "sql_query": self.prepare_sql(params=params),
        }

    def validate_parameter(self, param) -> dict:
        """
        Validate a parameter dict. The overall structure of the parameter dict is:
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
          }
        """
        try:
            param_type = param["type"]
            param_enum = param["enum"] if "enum" in param else None
            param_description = param["description"]
            param_required = param["required"] if "required" in param else False
        except KeyError as e:
            raise SmarterValueError(
                f"{self.name} PluginSql custom_tool() error: missing required parameter key: {e}"
            ) from e

        if param_type not in PluginDataSql.DataTypes.all():
            raise SmarterValueError(
                f"{self.plugin.name} PluginSql custom_tool() error: invalid parameter type: {param_type}. Valid types are: {PluginDataSql.DataTypes.all()}"
            )

        if param_enum and not isinstance(param_enum, list):
            raise SmarterValueError(
                f"{self.plugin.name} PluginSql custom_tool() error: invalid parameter enum: {param_enum}. Must be a list."
            )

        if not isinstance(param_required, bool):
            raise SmarterValueError(
                f"{self.plugin.name} PluginSql custom_tool() error: invalid parameter required: {param_required}. Must be a boolean."
            )

        if not isinstance(param_description, str):
            raise SmarterValueError(
                f"{self.plugin.name} PluginSql custom_tool() error: invalid parameter description: {param_description}. Must be a string."
            )

    def validate_test_values(self) -> bool:
        """
        Validate the test values. The overall structure of the test values is:
        {
            "key1": "value 1",
            "key2": "value 2"
        }
        """
        if not self.test_values:
            return True

        if not isinstance(self.test_values, dict):
            raise SmarterValueError(f"{self.name} PluginSql custom_tool() error: test_values must be a dict.")

        # pylint: disable=E1136
        for key, value in self.test_values.items():
            if key not in self.parameters.keys():
                raise SmarterValueError(f"Sql parameter '{key}' not found in parameters.")
            if self.parameters[key]["type"] == "int" and not isinstance(value, int):
                raise SmarterValueError(f"Parameter '{key}' must be an integer.")
            if self.parameters[key]["type"] == "str" and not isinstance(value, str):
                raise SmarterValueError(f"Parameter '{key}' must be a string.")
            if self.parameters[key]["type"] == "float" and not isinstance(value, float):
                raise SmarterValueError(f"Parameter '{key}' must be a float.")
            if self.parameters[key]["type"] == "bool" and not isinstance(value, bool):
                raise SmarterValueError(f"Parameter '{key}' must be a boolean.")
            if self.parameters[key]["type"] == "list" and not isinstance(value, list):
                raise SmarterValueError(f"Parameter '{key}' must be a list.")
            if self.parameters[key]["type"] == "dict" and not isinstance(value, dict):
                raise SmarterValueError(f"Parameter '{key}' must be a dict.")
            if self.parameters[key]["type"] == "null" and value is not None:
                raise SmarterValueError(f"Parameter '{key}' must be null.")

            enums = self.parameters[key].get("enum")
            if enums and value not in enums:
                raise SmarterValueError(f"Parameter '{key}' must be one of {enums}.")
        return True

    def validate_params(self, params: dict) -> bool:
        """validate the input params against self.parameters."""
        for key in params.keys():
            if key not in self.parameters.keys():
                raise SmarterValueError(f"Sql parameter '{key}' not found in parameters.")

        # pylint: disable=E1136
        for key, value in params.items():
            if key not in self.parameters.keys():
                raise SmarterValueError(f"Sql parameter '{key}' is not valid for this plugin.")
            if self.parameters[key]["type"] == "int" and not isinstance(value, int):
                raise SmarterValueError(f"Parameter '{key}' must be an integer.")
            if self.parameters[key]["type"] == "str" and not isinstance(value, str):
                raise SmarterValueError(f"Parameter '{key}' must be a string.")
            if self.parameters[key]["type"] == "float" and not isinstance(value, float):
                raise SmarterValueError(f"Parameter '{key}' must be a float.")
            if self.parameters[key]["type"] == "bool" and not isinstance(value, bool):
                raise SmarterValueError(f"Parameter '{key}' must be a boolean.")
            if self.parameters[key]["type"] == "list" and not isinstance(value, list):
                raise SmarterValueError(f"Parameter '{key}' must be a list.")
            if self.parameters[key]["type"] == "dict" and not isinstance(value, dict):
                raise SmarterValueError(f"Parameter '{key}' must be a dict.")
            if self.parameters[key]["type"] == "null" and value is not None:
                raise SmarterValueError(f"Parameter '{key}' must be null.")
        return True

    def validate(self) -> bool:
        if not self.parameters:
            return True
        for _, value in self.parameters.items():
            self.validate_parameter(value)
            self.validate_test_values()
        return True

    def prepare_sql(self, params: dict) -> str:
        """Prepare the SQL query by replacing placeholders with values."""
        params = params or {}
        self.validate_params(params)
        sql = self.sql_query
        for key, value in params.items():
            placeholder = "{" + key + "}"
            sql = sql.replace(placeholder, str(value))
        if self.limit:
            sql += f" LIMIT {self.limit}"
        sql += ";"
        return sql

    def execute_query(self, params: dict) -> Union[list, bool]:
        """Execute the SQL query and return the results."""
        sql = self.prepare_sql(params)
        return self.connection.execute_query(sql)

    def test(self) -> Union[list, bool]:
        """Test the SQL query using the test_values in the record."""
        return self.execute_query(self.test_values)

    def sanitized_return_data(self, params: dict = None) -> dict:
        """Return a dict by executing the query with the provided params."""
        logger.info("PluginDataSql.sanitized_return_data called. - %s", params)
        return self.execute_query(params)

    def save(self, *args, **kwargs):
        """Override the save method to validate the field dicts."""
        self.validate()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return str(self.plugin.account.account_number + " - " + self.plugin.name)
