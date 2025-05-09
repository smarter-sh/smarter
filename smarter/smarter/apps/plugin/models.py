# pylint: disable=missing-docstring,missing-module-docstring,missing-class-docstring,missing-function-docstring
# pylint: disable=C0114,C0115
"""PluginMeta app models."""

# python stuff
import io
import json
import logging
import re
from abc import abstractmethod
from enum import Enum
from functools import lru_cache
from http import HTTPStatus
from socket import socket
from typing import Any, Union
from urllib.parse import urljoin

import paramiko
import requests
import yaml

# django stuff
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import DatabaseError, models
from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.utils import ConnectionHandler

# 3rd party stuff
from pydantic import ValidationError
from rest_framework import serializers
from taggit.managers import TaggableManager

# smarter stuff
from smarter.apps.account.models import Account, Secret, UserProfile
from smarter.common.conf import SettingsDefaults
from smarter.common.exceptions import SmarterValueError
from smarter.lib.django.model_helpers import TimestampedModel

from .manifest.enum import SAMPluginCommonMetadataClassValues

# plugin stuff
from .manifest.models.common import Parameter, TestValue
from .manifest.models.sql_connection.enum import DbEngines


logger = logging.getLogger(__name__)

SMARTER_PLUGIN_MAX_DATA_RESULTS = 50


def validate_no_spaces(value):
    """Validate that the string does not contain spaces."""
    if " " in value:
        raise SmarterValueError("Value must not contain spaces.")


def validate_camel_case(value):
    """Validate that the string is in camelCase."""
    if not re.match(r"^[a-z]+(?:[A-Z][a-z0-9]*)*$", value):
        raise SmarterValueError("Value must be in camelCase format.")


def dict_key_cleaner(key: str) -> str:  # pragma: no cover
    """Clean a key by replacing spaces with underscores."""
    return str(key).replace("\n", "").replace("\r", "").replace("\t", "").replace(" ", "_")


def dict_keys_to_list(data: dict, keys=None) -> list[str]:  # pragma: no cover
    """recursive function to extract all keys from a nested dictionary."""
    if keys is None:
        keys = []
    for key, value in data.items():
        keys.append(key)
        if isinstance(value, dict):
            dict_keys_to_list(value, keys)
    return keys


def list_of_dicts_to_list(data: list[dict]) -> list[str]:  # pragma: no cover
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


def list_of_dicts_to_dict(data: list[dict]) -> dict:  # pragma: no cover
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


class PluginMeta(TimestampedModel):  # pragma: no cover
    """PluginMeta model."""

    PLUGIN_CLASSES = [
        (SAMPluginCommonMetadataClassValues.STATIC.value, SAMPluginCommonMetadataClassValues.STATIC.value),
        (SAMPluginCommonMetadataClassValues.SQL.value, SAMPluginCommonMetadataClassValues.SQL.value),
        (SAMPluginCommonMetadataClassValues.API.value, SAMPluginCommonMetadataClassValues.API.value),
    ]

    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="plugin_meta_account")
    name = models.CharField(
        help_text="The name of the plugin. Example: 'HR Policy Update' or 'Public Relation Talking Points'.",
        max_length=255,
        validators=[validate_camel_case],
    )
    description = models.TextField(
        help_text="A brief description of the plugin. Be verbose, but not too verbose.",
    )
    plugin_class = models.CharField(
        choices=PLUGIN_CLASSES, help_text="The class name of the plugin", max_length=255, default="PluginMeta"
    )
    version = models.CharField(max_length=255, default="1.0.0")
    author = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="plugin_meta_author")
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


class PluginSelector(TimestampedModel):  # pragma: no cover
    """PluginSelector model."""

    plugin = models.OneToOneField(PluginMeta, on_delete=models.CASCADE, related_name="plugin_selector_plugin")
    directive = models.CharField(
        help_text="The selection strategy to use for this plugin.", max_length=255, default="search_terms"
    )
    search_terms = models.JSONField(
        help_text="search terms in JSON format that, if detected in the user prompt, will incentivize Smarter to load this plugin.",
        default=list,
        blank=True,
        null=True,
    )

    def __str__(self) -> str:
        search_terms = json.dumps(self.search_terms)[:50]
        return f"{str(self.directive)} - {search_terms}"


class PluginSelectorSerializer(serializers.ModelSerializer):

    class Meta:
        model = PluginSelector
        fields = "__all__"


class PluginSelectorHistory(TimestampedModel):  # pragma: no cover
    """PluginSelectorHistory model."""

    plugin_selector = models.ForeignKey(
        PluginSelector, on_delete=models.CASCADE, related_name="plugin_selector_history_plugin_selector"
    )
    search_term = models.CharField(max_length=255, blank=True, null=True, default="")
    messages = models.JSONField(help_text="The user prompt messages.", default=list, blank=True, null=True)
    session_key = models.CharField(max_length=255, blank=True, null=True, default="")

    def __str__(self) -> str:
        return f"{str(self.plugin_selector.plugin.name)} - {self.search_term}"

    class Meta:
        verbose_name_plural = "Plugin Selector History"


class PluginSelectorHistorySerializer(serializers.ModelSerializer):

    plugin_selector = PluginSelectorSerializer()

    class Meta:
        model = PluginSelectorHistory
        fields = "__all__"


class PluginPrompt(TimestampedModel):  # pragma: no cover
    """PluginPrompt model."""

    plugin = models.OneToOneField(PluginMeta, on_delete=models.CASCADE, related_name="plugin_prompt_plugin")
    provider = models.TextField(
        help_text="The name of the LLM provider for the plugin. Example: 'openai'.",
        null=True,
        blank=True,
        default=SettingsDefaults.LLM_DEFAULT_PROVIDER,
    )
    system_role = models.TextField(
        help_text="The role of the system in the conversation.",
        null=True,
        blank=True,
        default="You are a helful assistant.",
    )
    model = models.CharField(
        help_text="The model to use for the completion.", max_length=255, default=SettingsDefaults.LLM_DEFAULT_MODEL
    )
    temperature = models.FloatField(
        help_text="The higher the temperature, the more creative the result.",
        default=SettingsDefaults.LLM_DEFAULT_TEMPERATURE,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
    )
    max_tokens = models.IntegerField(
        help_text="The maximum number of tokens for both input and output.",
        default=SettingsDefaults.LLM_DEFAULT_MAX_TOKENS,
        validators=[MinValueValidator(0), MaxValueValidator(8192)],
    )

    def __str__(self) -> str:
        return str(self.plugin.name)


class PluginDataBase(TimestampedModel):  # pragma: no cover
    """PluginDataBase model."""

    plugin = models.OneToOneField(PluginMeta, on_delete=models.CASCADE, related_name="plugin_data_base_plugin")

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


class SqlConnection(TimestampedModel):
    """PluginDataSql Connection model."""

    _connection: BaseDatabaseWrapper = None

    def __del__(self):
        """Close the database connection when the object instance is destroyed."""
        self.close()

    class ParamikoUpdateKnownHostsPolicy(paramiko.MissingHostKeyPolicy):
        def __init__(self, sql_connection: "SqlConnection"):
            self.sql_connection = sql_connection

        def missing_host_key(self, client, hostname, key):
            # Add the new host key to the known_hosts field
            new_entry = f"{hostname} {key.get_name()} {key.get_base64()}\n"
            if self.sql_connection.known_hosts:
                self.sql_connection.known_hosts += new_entry
            else:
                self.sql_connection.known_hosts = new_entry
            self.sql_connection.save()
            logger.warning("Unknown host key for %s. Key added to known_hosts.", hostname)

    class DBMSAuthenticationMethods(Enum):
        NONE = "none"
        TCPIP = "tcpip"
        TCPIP_SSH = "tcpip_ssh"
        LDAP_USER_PWD = "ldap_user_pwd"

        @classmethod
        def choices(cls):
            return [(method.value, method.name.replace("_", " ").title()) for method in cls]

        @classmethod
        def all_values(cls):
            return [method.value for method in cls]

    DBMS_DEFAULT_TIMEOUT = 30
    DBMS_CHOICES = [
        (DbEngines.MYSQL.value, "MySQL"),
        (DbEngines.POSTGRES.value, "PostgreSQL"),
        (DbEngines.SQLITE.value, "SQLite3"),
        (DbEngines.ORACLE.value, "Oracle"),
        (DbEngines.MSSQL.value, "MS SQL Server"),
        (DbEngines.SYBASE.value, "Sybase"),
    ]
    DBMS_AUTHENITCATION_METHODS = [
        (DBMSAuthenticationMethods.NONE.value, "None"),
        (DBMSAuthenticationMethods.TCPIP.value, "Standard TCP/IP"),
        (DBMSAuthenticationMethods.TCPIP_SSH.value, "Standard TCP/IP over SSH"),
        (DBMSAuthenticationMethods.LDAP_USER_PWD.value, "LDAP User/Password"),
    ]
    name = models.CharField(
        help_text="The name of the connection, without spaces. Example: 'HRDatabase', 'SalesDatabase', 'InventoryDatabase'.",
        max_length=255,
        validators=[validate_camel_case],
    )
    db_engine = models.CharField(
        help_text="The type of database management system. Example: 'MySQL', 'PostgreSQL', 'MS SQL Server', 'Oracle'.",
        default=DbEngines.MYSQL.value,
        max_length=255,
        choices=DBMS_CHOICES,
        blank=True,
        null=True,
    )
    authentication_method = models.CharField(
        help_text="The authentication method to use for the connection. Example: 'Standard TCP/IP', 'Standard TCP/IP over SSH', 'LDAP User/Password'.",
        max_length=255,
        choices=DBMSAuthenticationMethods.choices(),
        default=DBMSAuthenticationMethods.TCPIP.value,
    )
    timeout = models.IntegerField(
        help_text="The timeout for the database connection in seconds. Default is 30 seconds.",
        default=DBMS_DEFAULT_TIMEOUT,
        validators=[MinValueValidator(1)],
        blank=True,
    )
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="sql_connections_account")
    description = models.TextField(
        help_text="A brief description of the connection. Be verbose, but not too verbose.", blank=True, null=True
    )

    # SSL/TLS fields
    use_ssl = models.BooleanField(
        default=False, help_text="Whether to use SSL/TLS for the connection.", blank=True, null=True
    )
    ssl_cert = models.TextField(blank=True, null=True, help_text="The SSL certificate for the connection, if required.")
    ssl_key = models.TextField(blank=True, null=True, help_text="The SSL key for the connection, if required.")
    ssl_ca = models.TextField(
        blank=True, null=True, help_text="The Certificate Authority (CA) certificate for verifying the server."
    )

    # connection fields
    hostname = models.CharField(
        max_length=255, help_text="The remote host of the SQL connection. Should be a valid internet domain name."
    )
    port = models.IntegerField(
        default=3306, help_text="The port of the SQL connection. example: 3306 for MySQL.", blank=True, null=True
    )
    database = models.CharField(max_length=255, help_text="The name of the database to connect to.")
    username = models.CharField(max_length=255, blank=True, null=True, help_text="The database username.")
    password = models.ForeignKey(
        Secret,
        on_delete=models.CASCADE,
        related_name="sql_connections_password",
        help_text="The password for authentication, if required.",
        blank=True,
        null=True,
    )
    pool_size = models.IntegerField(default=5, help_text="The size of the connection pool.", blank=True, null=True)
    max_overflow = models.IntegerField(
        default=10,
        help_text="The maximum number of connections to allow beyond the pool size.",
        validators=[MinValueValidator(1)],
        blank=True,
        null=True,
    )

    # Proxy fields
    proxy_protocol = models.CharField(
        max_length=10,
        choices=[("http", "HTTP"), ("https", "HTTPS"), ("socks", "SOCKS")],
        default="http",
        help_text="The protocol to use for the proxy connection.",
        blank=True,
        null=True,
    )
    proxy_host = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="The remote host of the SQL proxy connection. Should be a valid internet domain name.",
    )
    proxy_port = models.IntegerField(blank=True, null=True, help_text="The port of the SQL proxy connection.")
    proxy_username = models.CharField(
        max_length=255, blank=True, null=True, help_text="The username for the proxy connection."
    )
    proxy_password = models.ForeignKey(
        Secret,
        on_delete=models.CASCADE,
        related_name="sql_connections_proxy_password",
        help_text="The API key for authentication, if required.",
        blank=True,
        null=True,
    )
    ssh_known_hosts = models.TextField(
        blank=True,
        null=True,
        help_text="The known_hosts file content for verifying SSH connections. Usually comes from ~/.ssh/known_hosts.",
    )

    @property
    def connection(self) -> BaseDatabaseWrapper:
        if not self._connection:
            self._connection = self.connect()
        return self._connection

    @property
    def db_options(self) -> dict:
        """Return the database connection options."""
        retval = {
            "pool_size": self.pool_size,
            "max_overflow": self.max_overflow,
            "ssl": (
                {
                    "ca": self.ssl_ca,
                    "cert": self.ssl_cert,
                    "key": self.ssl_key,
                }
                if self.use_ssl
                else {}
            ),
        }
        if self.authentication_method == "ldap_user_pwd":
            retval["authentication"] = "LDAP"
        return retval

    @property
    def django_databases(self) -> dict:
        """Return the database connection settings for Django."""
        return {
            "ENGINE": self.db_engine,
            "NAME": self.database,
            "USER": self.username,
            "PASSWORD": self.password.get_secret() if self.password else None,
            "HOST": self.hostname,
            "PORT": str(self.port),
            "OPTIONS": self.db_options,
        }

    def connect_tcpip(self) -> Union[BaseDatabaseWrapper, bool]:
        """
        Establish a database connection using Standard TCP/IP.
        """
        try:
            connection_handler = ConnectionHandler(self.django_databases)
            connection: BaseDatabaseWrapper = connection_handler["default"]
            connection.ensure_connection()
            return connection
        except DatabaseError as e:
            logger.error("db test connection failed: %s", e)
            return False

    def connect_tcpip_ssh(self) -> Union[BaseDatabaseWrapper, bool]:
        """
        Establish a database connection using Standard TCP/IP over SSH with Paramiko.
        """

        try:
            ssh_client = paramiko.SSHClient()
            if self.ssh_known_hosts:
                known_hosts_file = io.StringIO(self.ssh_known_hosts)
                ssh_client.load_host_keys(known_hosts_file)
            else:
                ssh_client.load_system_host_keys()

            ssh_client.load_system_host_keys()
            ssh_client.set_missing_host_key_policy(SqlConnection.ParamikoUpdateKnownHostsPolicy(self))

            ssh_client.connect(
                hostname=self.hostname,
                port=self.port,
                username=self.proxy_username,
                password=self.proxy_password.get_secret() if self.proxy_password else None,
                timeout=self.timeout,
            )

            # Open a local port forwarding channel
            transport = ssh_client.get_transport()
            local_socket = socket()
            local_socket.bind(("127.0.0.1", 0))  # Bind to an available local port
            local_socket.listen(1)
            local_port = local_socket.getsockname()[1]

            # Forward the remote database port to the local port
            transport.request_port_forward("127.0.0.1", local_port, self.hostname, self.port)

            connection_handler = ConnectionHandler(self.django_databases)
            connection: BaseDatabaseWrapper = connection_handler["default"]
            connection.ensure_connection()

            # Close the SSH connection after ensuring the database connection
            ssh_client.close()
            return connection

        # pylint: disable=W0718
        except Exception as e:
            logger.error("TCP/IP over SSH connection failed: %s", e)
            return False

    def connect_ldap_user_pwd(self) -> Union[BaseDatabaseWrapper, bool]:
        """
        Establish a database connection using LDAP User/Password authentication.
        """
        try:
            # Example: Customize the connection string for LDAP authentication
            databases = self.django_databases
            connection_handler = ConnectionHandler(databases)
            connection: BaseDatabaseWrapper = connection_handler["default"]
            connection.ensure_connection()
            return connection
        # pylint: disable=W0718
        except Exception as e:
            logger.error("LDAP User/Password connection failed: %s", e)
            return False

    def connect(self) -> Union[BaseDatabaseWrapper, bool]:
        """
        Establish a database connection based on the authentication method.
        """
        if self.authentication_method == SqlConnection.DBMSAuthenticationMethods.NONE.value:
            return self.connect_tcpip()
        elif self.authentication_method == SqlConnection.DBMSAuthenticationMethods.TCPIP.value:
            return self.connect_tcpip()
        elif self.authentication_method == SqlConnection.DBMSAuthenticationMethods.TCPIP_SSH.value:
            return self.connect_tcpip_ssh()
        elif self.authentication_method == SqlConnection.DBMSAuthenticationMethods.LDAP_USER_PWD.value:
            return self.connect_ldap_user_pwd()
        else:
            raise SmarterValueError(f"Unsupported authentication method: {self.authentication_method}")

    def close(self):
        """Close the database connection."""
        if self._connection:
            try:
                self._connection.close()
            # pylint: disable=W0718
            except Exception as e:
                logger.error("Failed to close the database connection: %s", e)
            self._connection = None

    def execute_query(self, sql: str, limit: int = None) -> Union[list[tuple[Any, ...]], bool]:
        connection = self.connect()
        if not connection:
            return False
        if limit is not None:
            sql = sql.rstrip(";")  # Remove any trailing semicolon
            sql += f" LIMIT {limit};"
        with connection.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()
            return rows

    def test_proxy(self) -> bool:
        proxy_dict = {
            self.proxy_protocol: f"{self.proxy_protocol}://{self.proxy_username}:{self.proxy_password}@{self.proxy_host}:{self.proxy_port}",
        }
        try:
            response = requests.get("https://www.google.com", proxies=proxy_dict, timeout=self.timeout)
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

    connection = models.ForeignKey(SqlConnection, on_delete=models.CASCADE, related_name="plugin_data_sql_connection")
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
        validators=[MinValueValidator(0)],
        blank=True,
        null=True,
    )

    def data(self, params: dict = None) -> dict:
        return {
            "parameters": self.parameters,
            "sql_query": self.prepare_sql(params=params),
        }

    def are_test_values_pydantic(self) -> bool:
        pass

    def validate_parameters(self) -> None:
        """
        Validate if the structure of self.parameters matches the expected Json representation
        by attempting to instantiate each item in the list as a Pydantic Parameter model.
            "parameters": [
                {
                "name": "username",
                "type": "string",
                "description": "The username to query.",
                "required": true,
                "default": "admin"
                },
                {
                "name": "unit",
                "type": "string",
                "enum": [
                    "Celsius",
                    "Fahrenheit"
                ],
                "description": "The temperature unit to use.",
                "required": false,
                "default": "Celsius"
                }
            ],

        """
        if self.parameters is None:
            return None
        if not isinstance(self.parameters, list):
            if isinstance(self.parameters, dict):
                self.parameters = [self.parameters]
                logger.warning(
                    "PluginDataSql().parameters was a dict. converted to a list: %s", json.dumps(self.parameters)
                )
            else:
                raise SmarterValueError(f"parameters must be a list of dictionaries but got: {type(self.parameters)}")

        # pylint: disable=E1133
        for param_dict in self.parameters:
            try:
                # pylint: disable=E1134
                Parameter(**param_dict)
            except (ValidationError, SmarterValueError) as e:
                raise SmarterValueError(f"Invalid parameter structure: {e}") from e

    def validate_test_values(self) -> None:
        """
        Validate if the structure of self.test_values matches the expected Json representation
        by attempting to instantiate each item in the list as a Pydantic TestValue model.

            "testValues": [
                {
                "name": "username",
                "value": "admin"
                },
                {
                "name": "unit",
                "value": "Celsius"
                }
            ]
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

    def validate_all_parameters_in_test_values(self) -> None:
        """
        Validate if all parameters are present in the test values.
        """
        if self.parameters is None or self.test_values is None:
            return None

        # pylint: disable=E1133
        for param_dict in self.parameters:
            param_name = param_dict.get("name")
            if not any(test_value.get("name") == param_name for test_value in self.test_values):
                raise SmarterValueError(f"Test value for parameter '{param_name}' is missing.")

    def valdate_all_placeholders_in_parameters(self) -> None:
        """
        Validate that all placeholders in the SQL query string are present in the parameters.
        """
        placeholders = re.findall(r"{(.*?)}", self.sql_query)
        for placeholder in placeholders:
            if self.parameters is None or not any(param.get("name") == placeholder for param in self.parameters):
                raise SmarterValueError(f"Placeholder '{placeholder}' is not defined in parameters.")

    def validate(self) -> bool:
        self.validate_parameters()
        self.validate_test_values()
        self.validate_all_parameters_in_test_values()
        self.valdate_all_placeholders_in_parameters()

        return True

    def prepare_sql(self, params: dict) -> str:
        """Prepare the SQL query by replacing placeholders with values."""
        params = params or {}
        self.validate_params(params)
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

    def execute_query(self, params: dict) -> Union[list, bool]:
        """Execute the SQL query and return the results."""
        sql = self.prepare_sql(params)
        return self.connection.execute_query(sql, self.limit)

    def test(self) -> Union[list, bool]:
        """Test the SQL query using the test_values in the record."""
        return self.execute_query(self.test_values)

    def sanitized_return_data(self, params: dict = None) -> dict:
        """Return a dict by executing the query with the provided params."""
        logger.info("{self.__class__.__name__}.sanitized_return_data called. - %s", params)
        return self.execute_query(params)

    def save(self, *args, **kwargs):
        """Override the save method to validate the field dicts."""
        self.validate()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return str(self.plugin.account.account_number + " - " + self.plugin.name)


class ApiConnection(TimestampedModel):
    """
    PluginData Api Connection model.
    This model is used to store the connection details for a Rest API remote data source
    for a Smarter Plugin.
    """

    AUTH_METHOD_CHOICES = [
        ("none", "None"),
        ("basic", "Basic Auth"),
        ("token", "Token Auth"),
        ("oauth", "OAuth"),
    ]

    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="api_connections_account")
    name = models.CharField(
        help_text="The name of the API connection, camelCase, without spaces. Example: 'weatherApi', 'stockApi'.",
        max_length=255,
        validators=[validate_camel_case],
    )
    description = models.TextField(
        help_text="A brief description of the API connection. Be verbose, but not too verbose.",
    )
    base_url = models.URLField(
        help_text="The root domain of the API. Example: 'https://api.example.com'.",
    )
    api_key = models.ForeignKey(
        Secret,
        on_delete=models.CASCADE,
        related_name="api_connections_api_key",
        help_text="The API key for authentication, if required.",
        blank=True,
        null=True,
    )
    auth_method = models.CharField(
        help_text="The authentication method to use. Example: 'Basic Auth', 'Token Auth'.",
        max_length=50,
        choices=AUTH_METHOD_CHOICES,
        default="none",
    )
    timeout = models.IntegerField(
        help_text="The timeout for the API request in seconds. Default is 30 seconds.",
        default=30,
        validators=[MinValueValidator(1)],
    )
    # Proxy fields
    proxy_protocol = models.CharField(
        max_length=10,
        choices=[("http", "HTTP"), ("https", "HTTPS"), ("socks", "SOCKS")],
        default="http",
        help_text="The protocol to use for the proxy connection.",
    )
    proxy_host = models.CharField(max_length=255, blank=True, null=True)
    proxy_port = models.IntegerField(blank=True, null=True)
    proxy_username = models.CharField(max_length=255, blank=True, null=True)
    proxy_password = models.ForeignKey(
        Secret,
        on_delete=models.CASCADE,
        related_name="api_connections_proxy_password",
        help_text="The proxy password for authentication, if required.",
        blank=True,
        null=True,
    )

    def test_proxy(self) -> bool:
        proxy_dict = {
            self.proxy_protocol: f"{self.proxy_protocol}://{self.proxy_username}:{self.proxy_password}@{self.proxy_host}:{self.proxy_port}",
        }
        try:
            response = requests.get("https://www.google.com", proxies=proxy_dict, timeout=self.timeout)
            return response.status_code in [HTTPStatus.OK, HTTPStatus.PERMANENT_REDIRECT]
        except requests.exceptions.RequestException as e:
            logger.error("proxy test connection failed: %s", e)
            return False

    def test_connection(self) -> bool:
        """Test the API connection by making a simple GET request to the root domain."""
        headers = {}
        if self.auth_method == "basic" and self.api_key:
            headers["Authorization"] = f"Basic {self.api_key}"
        elif self.auth_method == "token" and self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            response = requests.get(self.base_url, headers=headers, timeout=self.timeout)
            return response.status_code in [HTTPStatus.OK, HTTPStatus.PERMANENT_REDIRECT]
        except requests.exceptions.RequestException as e:
            logger.error("API test connection failed: %s", e)
            return False

    def get_connection_string(self):
        """Return the connection string."""
        return f"{self.base_url} (Auth: {self.auth_method})"

    def validate(self) -> bool:
        """Validate the API connection."""
        return self.test_connection()

    def __str__(self) -> str:
        return self.name + " - " + self.get_connection_string()


class PluginDataApi(PluginDataBase):
    """
    PluginDataApi model.

    This model is used to store the connection endpoint details for a REST API remote data source.
    """

    connection = models.ForeignKey(
        ApiConnection,
        on_delete=models.CASCADE,
        related_name="plugin_data_api_connection",
        help_text="The API connection associated with this plugin.",
    )
    endpoint = models.CharField(
        max_length=255,
        help_text="The endpoint path for the API. Example: '/v1/weather'.",
    )
    parameters = models.JSONField(
        help_text="A JSON dict containing parameter names and data types. Example: {'city': {'type': 'string', 'description': 'City name'}}",
        default=dict,
        blank=True,
        null=True,
    )
    headers = models.JSONField(
        help_text="A JSON dict containing headers to be sent with the API request. Example: {'Authorization': 'Bearer <token>'}",
        default=dict,
        blank=True,
        null=True,
    )
    body = models.JSONField(
        help_text="A JSON dict containing the body of the API request, if applicable.",
        default=dict,
        blank=True,
        null=True,
    )
    test_values = models.JSONField(
        help_text="A JSON dict containing test values for each parameter. Example: {'city': 'San Francisco'}",
        default=dict,
        blank=True,
        null=True,
    )
    limit = models.IntegerField(
        help_text="The maximum number of rows to return from the API response.",
        validators=[MinValueValidator(0)],
        blank=True,
        null=True,
    )

    @property
    def url(self) -> str:
        """Return the full URL for the API endpoint."""
        return urljoin(self.connection.base_url, self.endpoint)

    def data(self, params: dict = None) -> dict:
        return {
            "parameters": self.parameters,
            "endpoint": self.endpoint,
            "headers": self.headers,
            "body": self.body,
        }

    def prepare_request(self, params: dict) -> dict:
        """Prepare the API request by merging parameters, headers, and body."""
        params = params or {}
        self.validate_params(params)

        request_data = {
            "url": f"{self.connection.base_url}{self.endpoint}",
            "headers": self.headers or {},
            "params": params,
            "json": self.body or {},
        }
        return request_data

    def execute_request(self, params: dict) -> Union[dict, bool]:
        """Execute the API request and return the results."""
        request_data = self.prepare_request(params)
        try:
            response = requests.get(**request_data, timeout=self.connection.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error("API request failed: %s", e)
            return False

    def test(self) -> Union[dict, bool]:
        """Test the API request using the test_values in the record."""
        return self.execute_request(self.test_values)

    def sanitized_return_data(self, params: dict = None) -> dict:
        """Return a dict by executing the API request with the provided params."""
        logger.info("{self.__class__.__name__}.sanitized_return_data called. - %s", params)
        return self.execute_request(params)

    def save(self, *args, **kwargs):
        """Override the save method to validate the field dicts."""
        self.validate()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return str(self.plugin.account.account_number + " - " + self.plugin.name)
