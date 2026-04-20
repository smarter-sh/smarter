"""Connection app models."""

import io
import logging
import tempfile
from http import HTTPStatus
from socket import socket
from typing import Optional, Union

import paramiko
import requests
from django.core.exceptions import ImproperlyConfigured
from django.core.validators import MinValueValidator
from django.db import DatabaseError, models
from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.utils import ConnectionHandler

from smarter.apps.account.models import (
    MetaDataWithOwnershipModelManager,
)
from smarter.apps.connection.manifest.models.sql_connection.enum import (
    DbEngines,
    DBMSAuthenticationMethods,
)
from smarter.apps.connection.signals import (
    sql_connection_attempted,
    sql_connection_failed,
    sql_connection_query_attempted,
    sql_connection_query_failed,
    sql_connection_query_success,
    sql_connection_success,
    sql_connection_validated,
)
from smarter.apps.secret.models import Secret
from smarter.common.exceptions import SmarterValueError
from smarter.common.helpers.logger_helpers import formatted_text
from smarter.common.utils import camel_to_snake
from smarter.lib import json
from smarter.lib.django import waffle
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

from .connection_base import ConnectionBase


# pylint: disable=W0613
def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.CONNECTION_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)
logger_prefix = formatted_text(f"{__name__}")


class SqlConnection(ConnectionBase):
    """
    Stores SQL connection configuration.

    This model defines the connection details for a SQL database,
    including database engine, authentication method, host, port, credentials, SSL/TLS,
    and proxy settings. It provides methods for establishing connections using various
    authentication methods (TCP/IP, SSH, LDAP), executing queries, and validating the connection.

    ``SqlConnection`` is a concrete subclass of :class:`ConnectionBase` and is referenced by
    :class:`PluginDataSql` to provide the database connection. It supports
    advanced features such as connection pooling, SSL configuration, SSH tunneling, and proxy
    authentication, enabling secure and flexible integration with a wide range of SQL databases.

    This model is responsible for:
      - Managing connection credentials and secrets using the :class:`Secret` model.
      - Constructing Django-compatible database connection settings and connection strings.
      - Providing methods for testing connectivity, executing SQL queries, and handling connection errors.
      - Supporting multiple authentication methods, including TCP/IP, SSH tunneling, and LDAP.
      - Integrating with Django's database backend and connection pooling mechanisms.
      - Emitting signals for connection attempts, successes, failures, and query events for observability.

    Typical use cases include plugins that need to query organizational databases, perform analytics,
    or retrieve structured data from remote SQL servers as part of the Smarter plugin ecosystem.

    See also:

    - :class:`ConnectionBase`
    - :class:`PluginDataSql`
    - :class:`smarter.apps.account.models.Secret`
    """

    class Meta:
        verbose_name = "SQL Connection"
        verbose_name_plural = "SQL Connections"
        unique_together = (
            "user_profile",
            "name",
        )

    objects: MetaDataWithOwnershipModelManager["SqlConnection"] = MetaDataWithOwnershipModelManager()

    _connection: Optional[BaseDatabaseWrapper] = None

    def __del__(self):
        """Close the database connection when the object instance is destroyed."""
        self.close()

    class ParamikoUpdateKnownHostsPolicy(paramiko.MissingHostKeyPolicy):
        """
        Custom Paramiko policy to automatically add missing SSH host keys to the known_hosts field.
        This policy extends Paramiko's MissingHostKeyPolicy to handle unknown host keys by appending
        them to the ``ssh_known_hosts`` field of the associated :class:`SqlConnection`
        model instance. When an unknown host key is encountered during an SSH connection attempt,
        this policy captures the key and updates the database record accordingly.
        """

        def __init__(self, sql_connection: "SqlConnection"):
            self.sql_connection = sql_connection

        # pylint: disable=W0613
        def missing_host_key(self, client, hostname, key):
            # Add the new host key to the known_hosts field
            new_entry = f"{hostname} {key.get_name()} {key.get_base64()}\n"
            if self.sql_connection.ssh_known_hosts:
                self.sql_connection.ssh_known_hosts += new_entry
            else:
                self.sql_connection.ssh_known_hosts = new_entry
            self.sql_connection.save()
            logger.warning(
                "%s. Unknown host key for %s. Key added to known_hosts.",
                self.sql_connection.formatted_class_name,
                hostname,
            )

    DBMS_DEFAULT_TIMEOUT = 30
    """
    The default timeout for database connections in seconds.
    30 seconds is a reasonable default that balances responsiveness with network latency.
    """
    DBMS_CHOICES = [
        (DbEngines.MYSQL.value, DbEngines.MYSQL.value),
        (DbEngines.POSTGRES.value, DbEngines.POSTGRES.value),
        (DbEngines.SQLITE.value, DbEngines.SQLITE.value),
        (DbEngines.ORACLE.value, DbEngines.ORACLE.value),
        (DbEngines.MSSQL.value, DbEngines.MSSQL.value),
        (DbEngines.SYBASE.value, DbEngines.SYBASE.value),
    ]
    """
    The supported database management systems (DBMS) for SQL connections.
    """
    DBMS_AUTHENITCATION_METHODS = [
        (DBMSAuthenticationMethods.NONE.value, "None"),
        (DBMSAuthenticationMethods.TCPIP.value, "Standard TCP/IP"),
        (DBMSAuthenticationMethods.TCPIP_SSH.value, "Standard TCP/IP over SSH"),
        (DBMSAuthenticationMethods.LDAP_USER_PWD.value, "LDAP User/Password"),
    ]
    """
    The supported authentication methods for SQL connections.
    """
    db_engine = models.CharField(
        help_text="The type of database management system. Example: 'MySQL', 'PostgreSQL', 'MS SQL Server', 'Oracle'.",
        default=DbEngines.MYSQL.value,
        max_length=255,
        choices=DBMS_CHOICES,
        blank=True,
        null=True,
    )
    """
    The type of database management system. Example: 'MySQL', 'PostgreSQL', 'MS SQL Server', 'Oracle'.
    """
    authentication_method = models.CharField(
        help_text="The authentication method to use for the connection. Example: 'Standard TCP/IP', 'Standard TCP/IP over SSH', 'LDAP User/Password'.",
        max_length=255,
        choices=DBMSAuthenticationMethods.choices(),
        default=DBMSAuthenticationMethods.TCPIP.value,
    )
    """
    The authentication method to use for the connection. Example: 'Standard TCP/IP', 'Standard TCP/IP over SSH', 'LDAP User/Password'.
    """
    timeout = models.IntegerField(
        help_text="The timeout for the database connection in seconds. Default is 30 seconds.",
        default=DBMS_DEFAULT_TIMEOUT,
        validators=[MinValueValidator(1)],
        blank=True,
    )
    """
    The timeout for the database connection in seconds. Default is 30 seconds.
    """

    # SSL/TLS fields
    use_ssl = models.BooleanField(
        default=False, help_text="Whether to use SSL/TLS for the connection.", blank=True, null=True
    )
    """
    Whether to use SSL/TLS for the connection.
    """
    ssl_cert = models.TextField(blank=True, null=True, help_text="The SSL certificate for the connection, if required.")
    ssl_key = models.TextField(blank=True, null=True, help_text="The SSL key for the connection, if required.")
    ssl_ca = models.TextField(
        blank=True, null=True, help_text="The Certificate Authority (CA) certificate for verifying the server."
    )
    """
    The SSL certificate for the connection, if required.
    The SSL key for the connection, if required.
    The Certificate Authority (CA) certificate for verifying the server.
    """

    # connection fields
    hostname = models.CharField(
        max_length=255, help_text="The remote host of the SQL connection. Should be a valid internet domain name."
    )
    """
    The remote host of the SQL connection. Should be a valid internet domain name.
    """
    port = models.IntegerField(
        default=3306, help_text="The port of the SQL connection. example: 3306 for MySQL.", blank=True, null=True
    )
    """
    The port of the SQL connection. example: 3306 for MySQL.
    5432 for PostgreSQL, 1521 for Oracle, 1433 for MS SQL Server.
    5000 for Sybase.
    1234 for SQLite (not commonly used).
    3306 is a reasonable default as MySQL is widely used.
    5432 could also be a reasonable default as PostgreSQL is also widely used.
    """
    database = models.CharField(max_length=255, help_text="The name of the database to connect to.")
    """
    The name of the database to connect to.
    """
    username = models.CharField(max_length=255, blank=True, null=True, help_text="The database username.")
    """
    The database username.
    """
    password = models.ForeignKey(
        Secret,
        on_delete=models.CASCADE,
        related_name="sql_connections_password",
        help_text="The password for authentication, if required.",
        blank=True,
        null=True,
    )
    """
    The password for authentication, if required.

    See: :class:`smarter.apps.account.models.Secret`
    """
    pool_size = models.IntegerField(default=5, help_text="The size of the connection pool.", blank=True, null=True)
    """
    The size of the connection pool.
    """
    max_overflow = models.IntegerField(
        default=10,
        help_text="The maximum number of connections to allow beyond the pool size.",
        validators=[MinValueValidator(1)],
        blank=True,
        null=True,
    )
    """
    The maximum number of connections to allow beyond the pool size.
    """

    # Proxy fields
    proxy_protocol = models.CharField(
        max_length=10,
        choices=[("http", "HTTP"), ("https", "HTTPS"), ("socks", "SOCKS")],
        default="http",
        help_text="The protocol to use for the proxy connection.",
        blank=True,
        null=True,
    )
    """
    The protocol to use for the proxy connection.
    """
    proxy_host = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="The remote host of the SQL proxy connection. Should be a valid internet domain name.",
    )
    """
    The remote host of the SQL proxy connection. Should be a valid internet domain name.
    """
    proxy_port = models.IntegerField(blank=True, null=True, help_text="The port of the SQL proxy connection.")
    """
    The port of the SQL proxy connection.
    8080 is a common default for HTTP proxies.
    3128 is another common default for HTTP proxies.
    1080 is a common default for SOCKS proxies.
    8080 is a reasonable default as it is widely used for HTTP proxies.
    """
    proxy_username = models.CharField(
        max_length=255, blank=True, null=True, help_text="The username for the proxy connection."
    )
    """
    The username for the proxy connection.
    """
    proxy_password = models.ForeignKey(
        Secret,
        on_delete=models.CASCADE,
        related_name="sql_connections_proxy_password",
        help_text="The API key for authentication, if required.",
        blank=True,
        null=True,
    )
    """
    The password for the proxy connection, if required.

    See: :class:`smarter.apps.account.models.Secret`
    """
    ssh_known_hosts = models.TextField(
        blank=True,
        null=True,
        help_text="The known_hosts file content for verifying SSH connections. Usually comes from ~/.ssh/known_hosts.",
    )
    """
    The known_hosts file content for verifying SSH connections. Usually comes from ~/.ssh/known_hosts.
    """

    @property
    def connection(self) -> Optional[BaseDatabaseWrapper]:
        """
        Return the database connection if it exists, otherwise create a new one.

        This property returns the current database connection for this SQL connection instance.
        If a connection has already been established, it is returned; otherwise, a new connection
        is created using the configured authentication method and connection parameters.

        :return: The database connection object, or None if the connection could not be established.
        :rtype: Optional[BaseDatabaseWrapper]

        **Example:**

        .. code-block:: python

            conn = sql_connection.connection
            if conn:
                # Use the database connection
                ...

        See also:

        - :meth:`get_connection`
        """
        if self._connection:
            return self._connection
        self._connection = self.get_connection()
        return self._connection

    @property
    def db_options(self) -> dict:
        """
        Return the database connection options.

        This property constructs and returns a dictionary of options for the database connection,
        including SSL/TLS settings and authentication method if applicable.

        - If SSL is enabled (``use_ssl`` is True), the returned dictionary includes the keys ``ca``, ``cert``, and ``key`` for SSL configuration.
        - If the authentication method is LDAP user/password, the dictionary includes an ``authentication`` key set to ``LDAP``.

        :return: A dictionary of database connection options.
        :rtype: dict

        **Example:**

        .. code-block:: python

            options = sql_connection.db_options
            # returns: {'ssl': {'ca': '...', 'cert': '...', 'key': '...'}, 'authentication': 'LDAP'}
        """
        retval = {}
        if self.use_ssl:
            retval["ssl"] = {
                "ca": self.ssl_ca,
                "cert": self.ssl_cert,
                "key": self.ssl_key,
            }
        if self.authentication_method == "ldap_user_pwd":
            retval["authentication"] = "LDAP"
        return retval

    @property
    def django_db_connection(self) -> dict:
        """
        Return the database connection settings for Django.

        This property constructs and returns a dictionary of settings compatible with Django's database
        connection handler, using the current SQL connection instance's configuration.

        The returned dictionary includes the following keys:

        - ``ENGINE``: The database backend engine (e.g., ``django.db.backends.mysql``).
        - ``NAME``: The name of the database.
        - ``USER``: The database username.
        - ``PASSWORD``: The password for authentication, if set.
        - ``HOST``: The database host.
        - ``PORT``: The database port as a string.
        - ``OPTIONS``: Additional database connection options (such as SSL or authentication settings).

        :return: A dictionary of Django database connection settings.
        :rtype: dict

        **Example:**

        .. code-block:: python

            settings = sql_connection.django_db_connection
            # returns:
            # {
            #     "ENGINE": "django.db.backends.mysql",
            #     "NAME": "mydb",
            #     "USER": "myuser",
            #     "PASSWORD": "mypassword",
            #     "HOST": "localhost",
            #     "PORT": "3306",
            #     "OPTIONS": {...}
            # }
        """
        retval = {
            "ENGINE": self.db_engine,
            "NAME": self.database,
            "USER": self.username,
            "PASSWORD": self.password.get_secret() if self.password else None,
            "HOST": self.hostname,
            "PORT": str(self.port),
            "OPTIONS": self.db_options,
        }
        return retval

    @property
    def connection_string(self) -> str:
        """
        Return the database connection string.
        This property constructs and returns a database connection string based on the current
        SQL connection instance's configuration.

        :return: A database connection string.
        :rtype: str
        """
        return self.get_connection_string()

    def connect_tcpip(self) -> Optional[BaseDatabaseWrapper]:
        """
        Establish a test database connection using Standard TCP/IP.

        This method attempts to create and validate a database connection using the standard TCP/IP authentication method,
        based on the current SQL connection instance's configuration. It emits signals for connection attempts, successes,
        and failures for observability.

        :return: The database connection object if successful, otherwise None.
        :rtype: Optional[BaseDatabaseWrapper]

        **Example:**

        .. code-block:: python

            db_wrapper = sql_connection.connect_tcpip()
            if db_wrapper:
                # Connection established, use db_wrapper...
                pass

        See also:

        - :meth:`django.db.utils.ConnectionHandler`
        - :meth:`SqlConnection.django_db_connection`
        """
        sql_connection_attempted.send(sender=self.__class__, connection=self)
        try:
            connection_handler = ConnectionHandler({"default": self.django_db_connection})
            db_wrapper = connection_handler["default"]
            db_wrapper.ensure_connection()
            if db_wrapper.is_usable():
                sql_connection_success.send(sender=self.__class__, connection=self)
                return db_wrapper  # type: ignore[return-value]
            else:
                msg = "Failed to establish TCP/IP connection: No connection object found."
                sql_connection_failed.send(sender=self.__class__, connection=self, error=msg)
                return None
        except (DatabaseError, ImproperlyConfigured) as e:
            sql_connection_failed.send(sender=self.__class__, connection=self, error=str(e))
            return None

    def transport_handler(self, channel, src_addr, dest_addr):
        """
        (NOT IMPLEMENTED) Handler for Paramiko SSH transport channels.

        .. warning::
            This method is a placeholder and does not implement actual port forwarding logic.
        """
        logger.info(
            "%s.transport_handler() Transport handler called with channel: %s, src_addr: %s, dest_addr: %s",
            self.formatted_class_name,
            channel,
            src_addr,
            dest_addr,
        )

    def connect_tcpip_ssh(self) -> Optional[BaseDatabaseWrapper]:
        """
        Establish a database connection using Standard TCP/IP over SSH with Paramiko.

        This method attempts to create and validate a database connection using the standard TCP/IP authentication method
        over an SSH tunnel, based on the current SQL connection instance's configuration. It emits signals for connection
        attempts, successes, and failures for observability.

        :return: The database connection object if successful, otherwise None.
        :rtype: Optional[BaseDatabaseWrapper]
        """

        try:
            sql_connection_attempted.send(sender=self.__class__, connection=self)
            ssh_client = paramiko.SSHClient()
            if self.ssh_known_hosts:
                known_hosts_file = io.StringIO(self.ssh_known_hosts)
                with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                    temp_file.write(self.ssh_known_hosts.encode())
                    known_hosts_file = temp_file.name
                ssh_client.load_host_keys(known_hosts_file)
            else:
                ssh_client.load_system_host_keys()

            ssh_client.load_system_host_keys()
            ssh_client.set_missing_host_key_policy(SqlConnection.ParamikoUpdateKnownHostsPolicy(self))

            ssh_client.connect(
                hostname=self.hostname,
                port=self.port if self.port else 22,  # Default SSH port is 22
                username=self.proxy_username,
                password=self.proxy_password.get_secret(update_last_accessed=False) if self.proxy_password else None,
                timeout=self.timeout,
            )

            # Open a local port forwarding channel
            transport = ssh_client.get_transport()
            local_socket = socket()
            local_socket.bind(("127.0.0.1", 0))  # Bind to an available local port
            local_socket.listen(1)
            local_port = local_socket.getsockname()[1]

            # Forward the remote database port to the local port
            if isinstance(transport, paramiko.Transport):
                transport.request_port_forward(address="127.0.0.1", port=local_port, handler=self.transport_handler)

            connection_handler = ConnectionHandler(self.django_db_connection)
            tcpip_ssh_connection: BaseDatabaseWrapper = connection_handler["default"].connection
            tcpip_ssh_connection.ensure_connection()

            # Close the SSH connection after ensuring the database connection
            sql_connection_success.send(sender=self.__class__, connection=self)
            return connection_handler  # type: ignore[return-value]

        except (paramiko.SSHException, DatabaseError, ImproperlyConfigured) as e:
            logger.error("%s.connect_tcpip_ssh() SSH connection failed: %s", self.formatted_class_name, e)
            sql_connection_failed.send(sender=self.__class__, connection=self, error=str(e))
            return None
        # pylint: disable=W0718
        except Exception as e:
            sql_connection_failed.send(sender=self.__class__, connection=self, error=str(e))
            logger.error("%s.connect_tcpip_ssh() An unexpected error occurred: %s", self.formatted_class_name, e)
            return None

    def connect_ldap_user_pwd(self) -> Optional[BaseDatabaseWrapper]:
        """
        Establish a database connection using LDAP User/Password authentication.

        This method attempts to create and validate a database connection using LDAP User/Password authentication,
        based on the current SQL connection instance's configuration. It emits signals for connection attempts, successes,
        and failures for observability.

        :return: The database connection object if successful, otherwise None.
        :rtype: Optional[BaseDatabaseWrapper]
        """
        try:
            # Example: Customize the connection string for LDAP authentication
            sql_connection_attempted.send(sender=self.__class__, connection=self)
            databases = self.django_db_connection
            connection_handler = ConnectionHandler(databases)
            ldap_user_pwd_connection: BaseDatabaseWrapper = connection_handler["default"].connection
            ldap_user_pwd_connection.ensure_connection()
            sql_connection_success.send(sender=self.__class__, connection=self)
            return ldap_user_pwd_connection
        # pylint: disable=W0718
        except Exception as e:
            sql_connection_failed.send(sender=self.__class__, connection=self, error=str(e))
            logger.error(
                "%s.connect_ldap_user_pwd() LDAP User/Password connection failed: %s", self.formatted_class_name, e
            )
            return None

    def test_connection(self) -> bool:
        """
        Establish a database connection based on the authentication method.

        This method attempts to establish a database connection using the configured authentication method
        for this SQL connection instance. The authentication method can be standard TCP/IP, TCP/IP over SSH,
        LDAP user/password, or none. Returns True if the connection is successfully established, otherwise False.

        :return: True if the connection is established, False otherwise.
        :rtype: bool

        .. important::

            This method is called during the validation process to ensure that the connection parameters are correct
            and that a connection can be successfully made to the database. For example, it is invoked when saving
            a :class:`SqlConnection` instance to verify the connection details.

        See also:

        - :meth:`get_connection`
        """
        connection = self.get_connection()
        return connection is not None

    def get_connection(self) -> Optional[BaseDatabaseWrapper]:
        """
        Establish a database connection based on the authentication method.

        This method attempts to establish a database connection using the configured authentication method
        for this SQL connection instance. The authentication method can be standard TCP/IP, TCP/IP over SSH,
        LDAP user/password, or none. Returns the database connection object if successful, otherwise None.

        :return: The database connection object if successful, otherwise None.
        :rtype: Optional[BaseDatabaseWrapper]
        """
        if self.authentication_method == DBMSAuthenticationMethods.NONE.value:
            retval = self.connect_tcpip()
        elif self.authentication_method == DBMSAuthenticationMethods.TCPIP.value:
            retval = self.connect_tcpip()
        elif self.authentication_method == DBMSAuthenticationMethods.TCPIP_SSH.value:
            retval = self.connect_tcpip_ssh()
        elif self.authentication_method == DBMSAuthenticationMethods.LDAP_USER_PWD.value:
            retval = self.connect_ldap_user_pwd()
        else:
            raise SmarterValueError(f"Unsupported authentication method: {self.authentication_method}")

        if isinstance(retval, BaseDatabaseWrapper):
            return retval
        else:
            logger.error(
                "%s.get_connection() Failed to establish a database connection using method: %s. Got return type of %s",
                self.formatted_class_name,
                self.authentication_method,
                type(retval),
            )
            return None

    def close(self):
        """
        Close the database connection.

        This method closes the current database connection associated with this SQL connection instance,
        if it exists. If an error occurs while closing the connection, it is logged and the connection
        reference is cleared.

        :return: None
        """
        if self._connection:
            try:
                self._connection.close()
            # pylint: disable=W0718
            except Exception as e:
                logger.error("%s.close() Failed to close the database connection: %s", self.formatted_class_name, e)
            self._connection = None

    def execute_query(self, sql: str, limit: Optional[int] = None) -> Union[str, bool]:
        """
        Execute a SQL query and return the results as a JSON string.

        :param sql: The SQL query to execute.
        :param limit: Optional limit on the number of rows to return.
        :return: JSON string of query results if successful, otherwise False.

        .. warning::

            This method does not perform any SQL injection protection or parameterization.
            It is the caller's responsibility to ensure that the SQL query is safe and properly formatted.

        .. warning::

            This method does not limit the execution time nor the number of rows returned by the query,
            unless the ``limit`` parameter is provided. It is the caller's responsibility to ensure that
            the query is efficient and does not return excessive data.
        """

        def query_result_to_json(cursor) -> str:
            # Get column names from cursor description
            columns = [col[0] for col in cursor.description]
            # Fetch all rows
            rows = cursor.fetchall()
            # Convert each row to a dict
            result = [dict(zip(columns, row)) for row in rows]
            # Convert to JSON string (optional)
            return json.dumps(result)

        if not isinstance(self.connection, BaseDatabaseWrapper):
            return False
        query_connection = self.connection
        sql_connection_query_attempted.send(sender=self.__class__, connection=self, sql=sql, limit=limit)
        try:
            if limit is not None:
                sql = sql.rstrip(";")  # Remove any trailing semicolon
                sql += f" LIMIT {limit};"
            with query_connection.cursor() as cursor:
                cursor.execute(sql)
                json_str = query_result_to_json(cursor)
                sql_connection_query_success.send(sender=self.__class__, connection=self, sql=sql, limit=limit)
                return json_str
        except (DatabaseError, ImproperlyConfigured) as e:
            sql_connection_query_failed.send(sender=self.__class__, connection=self, sql=sql, limit=limit, error=str(e))
            logger.error("%s.execute_query() SQL query execution failed: %s", self.formatted_class_name, e)
            return False
        finally:
            self.close()

    def test_proxy(self) -> bool:
        """
        Test the proxy connection by making a request to a known URL through the proxy.

        :return: True if the proxy connection is successful, otherwise False.
        :rtype: bool
        """
        proxy_dict: Optional[dict] = (
            {
                self.proxy_protocol: f"{self.proxy_protocol}://{self.proxy_username}:{self.proxy_password}@{self.proxy_host}:{self.proxy_port}",
            }
            if self.proxy_protocol is not None and self.proxy_host is not None
            else None
        )
        try:
            response = requests.get("https://www.google.com", proxies=proxy_dict, timeout=self.timeout)
            return response.status_code in [HTTPStatus.OK, HTTPStatus.PERMANENT_REDIRECT]
        except requests.exceptions.RequestException as e:
            logger.error("%s.test_proxy() proxy test connection failed: %s", self.formatted_class_name, e)
            return False

    def get_connection_string(self, masked: bool = True) -> str:
        """
        Return the connection string.

        This method constructs and returns a database connection string based on the current
        connection instance's configuration. If ``masked`` is True, sensitive information such as
        the password or API key will be masked in the returned string.

        :param masked: Whether to mask sensitive information in the connection string.
        :type masked: bool
        :return: The constructed connection string.
        :rtype: str

        **Example:**

        .. code-block:: python

            conn_str = sql_connection.get_connection_string(masked=True)
            # returns: 'mysql://user:******@host:3306/dbname'

        .. important::

            Unlike most of the Smarter codebase, this method does not use Pydantic SecretStr for masking
            to avoid adding Pydantic as a dependency for the entire ``smarter`` package.
        """
        if masked:
            password = "******"
        else:
            password = self.password.get_secret() if self.password else None
        userinfo = f"{self.username}:{password}" if password else self.username
        return f"{self.db_engine}://{userinfo}@{self.hostname}:{self.port}/{self.database}"

    def validate(self) -> bool:
        """
        Override the validate method to test the SQL connection.

        :return: True if the connection test is successful, otherwise False.
        :rtype: bool
        """
        super().validate()
        retval = self.test_connection()
        sql_connection_validated.send(sender=self.__class__, connection=self)
        return retval

    def save(self, *args, **kwargs):
        """
        Override the save method to validate the field dicts.

        This method ensures that all relevant fields are validated before saving the model instance.
        For example, it checks that the name is in snake_case and converts it if necessary, logs a warning if conversion occurs,
        and calls the model's ``validate()`` method to enforce any additional validation logic defined on the model.
        After validation, it proceeds with the standard Django save operation.

        :param args: Positional arguments passed to the parent save method.
        :param kwargs: Keyword arguments passed to the parent save method.
        :return: None
        """

        # this should never happen, but the linter complains without it.
        if not isinstance(self.name, str):
            raise SmarterValueError(f"Connection name must be a string but got: {type(self.name)}")

        if not SmarterValidator.is_valid_snake_case(self.name):
            snake_case_name = camel_to_snake(self.name)
            logger.warning(
                "%s.save(): name %s was not in snake_case. Converted to snake_case: %s",
                self.formatted_class_name,
                self.name,
                snake_case_name,
            )
            self.name = snake_case_name
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name + " - " + self.get_connection_string() if isinstance(self.name, str) else "unassigned"


__all__ = ["SqlConnection"]
