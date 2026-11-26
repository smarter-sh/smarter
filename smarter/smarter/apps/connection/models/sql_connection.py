"""SqlConnection model."""

from http import HTTPStatus
from typing import Optional, Union

import requests
from django.core.exceptions import ImproperlyConfigured
from django.core.validators import MinValueValidator
from django.db import DatabaseError, models
from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.utils import ConnectionHandler

from smarter.apps.connection.execution import SqlToolCall, SshTunnelSettings
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
from smarter.apps.connection.ssh import (
    DEFAULT_SSH_PORT,
    LOOPBACK,
    SshTunnel,
    SshTunnelError,
)
from smarter.apps.llmtool.runner import get_tool_runner
from smarter.apps.secret.models import Secret
from smarter.common.exceptions import SmarterValueError
from smarter.common.utils import to_snake_case
from smarter.lib import logging
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.typing import SmarterDictType

from .connection_base import ConnectionBase

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.CONNECTION_LOGGING])


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

    # pylint: disable=C0115
    class Meta:
        verbose_name = "SQL Connection"
        verbose_name_plural = "SQL Connections"

    _connection: Optional[BaseDatabaseWrapper] = None
    _tunnel: Optional[SshTunnel] = None

    connected: Optional[bool] = None
    """
    Whether the most recent :meth:`execute_query` established a database connection, which.

    includes authenticating to the database. ``None`` until a query is executed.
    """

    def __enter__(self) -> "SqlConnection":
        """
        Use the SQL connection as a context manager, which closes its database.

        connection on exit.

        .. code-block:: python

            with SqlConnection.objects.get(name="my-database") as sql_connection:
                sql_connection.connection.cursor().execute("SELECT 1;")

        :return: This SQL connection.
        :rtype: SqlConnection
        """
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        """
        Close the database connection when the ``with`` block exits.

        Exceptions propagate.

        :param exc_type: The exception type raised in the ``with`` block, if any.
        :param exc_value: The exception raised in the ``with`` block, if any.
        :param traceback: The traceback of the exception, if any.
        :return: None
        """
        self.close()

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
    """The supported database management systems (DBMS) for SQL connections."""
    DBMS_AUTHENITCATION_METHODS = [
        (DBMSAuthenticationMethods.NONE.value, "None"),
        (DBMSAuthenticationMethods.TCPIP.value, "Standard TCP/IP"),
        (DBMSAuthenticationMethods.TCPIP_SSH.value, "Standard TCP/IP over SSH"),
        (DBMSAuthenticationMethods.LDAP_USER_PWD.value, "LDAP User/Password"),
    ]
    """The supported authentication methods for SQL connections."""
    db_engine = models.CharField(
        help_text="The type of database management system. Example: 'MariaDB', 'PostgreSQL', 'MS SQL Server', 'Oracle'.",
        default=DbEngines.MYSQL.value,
        max_length=255,
        choices=DBMS_CHOICES,
        blank=True,
        null=True,
    )
    """
    The type of database management system.

    Example: 'MariaDB', 'PostgreSQL', 'MS SQL Server', 'Oracle'.
    """
    authentication_method = models.CharField(
        help_text="The authentication method to use for the connection. Example: 'Standard TCP/IP', 'Standard TCP/IP over SSH', 'LDAP User/Password'.",
        max_length=255,
        choices=DBMSAuthenticationMethods.choices(),
        default=DBMSAuthenticationMethods.TCPIP.value,
    )
    """
    The authentication method to use for the connection.

    Example: 'Standard TCP/IP', 'Standard TCP/IP over SSH', 'LDAP User/Password'.
    """
    timeout = models.IntegerField(
        help_text="The timeout for the database connection in seconds. Default is 30 seconds.",
        default=DBMS_DEFAULT_TIMEOUT,
        validators=[MinValueValidator(1)],
        blank=True,
    )
    """
    The timeout for the database connection in seconds.

    Default is 30 seconds.
    """

    # SSL/TLS fields
    use_ssl = models.BooleanField(
        default=False, help_text="Whether to use SSL/TLS for the connection.", blank=True, null=True
    )
    """Whether to use SSL/TLS for the connection."""
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
    The remote host of the SQL connection.

    Should be a valid internet domain name.
    """
    port = models.IntegerField(
        default=3306, help_text="The port of the SQL connection. example: 3306 for MariaDB.", blank=True, null=True
    )
    """
    The port of the SQL connection.

    example: 3306 for MariaDB.
    5432 for PostgreSQL, 1521 for Oracle, 1433 for MS SQL Server.
    5000 for Sybase.
    1234 for SQLite (not commonly used).
    3306 is a reasonable default as MariaDB is widely used.
    5432 could also be a reasonable default as PostgreSQL is also widely used.
    """
    database = models.CharField(max_length=255, help_text="The name of the database to connect to.")
    """The name of the database to connect to."""
    username = models.CharField(max_length=255, blank=True, null=True, help_text="The database username.")
    """The database username."""
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
    """The size of the connection pool."""
    max_overflow = models.IntegerField(
        default=10,
        help_text="The maximum number of connections to allow beyond the pool size.",
        validators=[MinValueValidator(1)],
        blank=True,
        null=True,
    )
    """The maximum number of connections to allow beyond the pool size."""

    # Proxy fields
    proxy_protocol = models.CharField(
        max_length=10,
        choices=[("http", "HTTP"), ("https", "HTTPS"), ("socks", "SOCKS")],
        default="http",
        help_text="The protocol to use for the proxy connection.",
        blank=True,
        null=True,
    )
    """The protocol to use for the proxy connection."""
    proxy_host = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="The remote host of the SQL proxy connection. Should be a valid internet domain name.",
    )
    """
    The remote host of the SQL proxy connection.

    Should be a valid internet domain name.
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
    """The username for the proxy connection."""
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
    The known_hosts file content for verifying SSH connections.

    Usually comes from ~/.ssh/known_hosts.
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
    def db_options(self) -> SmarterDictType:
        """
        Return the database connection options.

        This property constructs and returns a dictionary of options for the database connection,
        including SSL/TLS settings and authentication method if applicable.

        - :attr:`timeout`, in the driver's own options: for MySQL, ``connect_timeout``,
          ``read_timeout`` and ``write_timeout``, and for PostgreSQL, ``connect_timeout`` and a
          ``statement_timeout``. Without them, PyMySQL waits forever for a query's reply, and a
          slow query holds the request's thread for as long as it runs. Other engines get none.
        - If SSL is enabled (``use_ssl`` is True), the returned dictionary includes the keys ``ca``, ``cert``, and ``key`` for SSL configuration.
        - If the authentication method is LDAP user/password, the dictionary includes an ``authentication`` key set to ``LDAP``.

        :return: A dictionary of database connection options.
        :rtype: dict

        **Example:**

        .. code-block:: python

            options = sql_connection.db_options
            # returns: {'connect_timeout': 30, 'read_timeout': 30, 'write_timeout': 30,
            #           'ssl': {'ca': '...', 'cert': '...', 'key': '...'}, 'authentication': 'LDAP'}
        """
        retval: SmarterDictType = {}
        timeout = self.timeout or self.DBMS_DEFAULT_TIMEOUT
        if self.db_engine == DbEngines.MYSQL.value:
            retval.update({"connect_timeout": timeout, "read_timeout": timeout, "write_timeout": timeout})
        elif self.db_engine == DbEngines.POSTGRES.value:
            retval.update({"connect_timeout": timeout, "options": f"-c statement_timeout={timeout * 1000}"})
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
    def django_db_connection(self) -> SmarterDictType:
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

    def ssh_tunnel_settings(self) -> Optional[SshTunnelSettings]:
        """
        Return the SSH tunnel's settings, with its password decrypted, or None if the connection doesn't use one.

        For ``tcpip_ssh``, ``proxy_host`` and ``proxy_port`` (22 when unset) are the SSH server,
        ``proxy_username`` and ``proxy_password`` its login, and ``ssh_known_hosts`` its host keys.
        ``hostname`` and ``port`` are the database, as the SSH server reaches it. See
        :mod:`smarter.apps.connection.ssh`.

        :returns: The settings, or None.
        :raises SmarterValueError: If the connection uses SSH, but has no ``proxy_host``.
        """
        if self.authentication_method != DBMSAuthenticationMethods.TCPIP_SSH.value:
            return None
        if not self.proxy_host:
            raise SmarterValueError(f"SqlConnection {self.name} uses tcpip_ssh, but has no proxyHost, its SSH server.")
        password = None
        if self.proxy_password:
            password = self.proxy_password.get_secret(update_last_accessed=False)
        settings = SshTunnelSettings(
            host=self.proxy_host,
            port=self.proxy_port or DEFAULT_SSH_PORT,
            username=self.proxy_username,
            password=password,
            known_hosts=self.ssh_known_hosts,
        )
        return settings

    def connect_tcpip_ssh(self) -> Optional[BaseDatabaseWrapper]:
        """
        Establish a database connection through an SSH tunnel.

        It opens an :class:`~smarter.apps.connection.ssh.SshTunnel` to the SSH server, which forwards a
        loopback port to the database, and connects the database driver to that port. The tunnel stays
        open while the connection is used, and :meth:`close` closes both. The SSH server's host key must
        be in ``ssh_known_hosts``: an unknown one is refused, never learned. It emits signals for
        connection attempts, successes, and failures for observability.

        :return: The database connection object if successful, otherwise None.
        :rtype: Optional[BaseDatabaseWrapper]
        """
        sql_connection_attempted.send(sender=self.__class__, connection=self)
        try:
            ssh = self.ssh_tunnel_settings()
            if ssh is None:
                return None
            tunnel = SshTunnel(
                ssh_host=ssh.host,
                ssh_port=ssh.port,
                username=ssh.username,
                password=ssh.password,
                known_hosts=ssh.known_hosts,
                remote_host=self.hostname,
                remote_port=self.port or 3306,
                timeout=self.timeout or self.DBMS_DEFAULT_TIMEOUT,
            )
            tunnel.open()
        except (SshTunnelError, SmarterValueError) as e:
            sql_connection_failed.send(sender=self.__class__, connection=self, stage="SSH connection", error=str(e))
            return None
        settings = self.django_db_connection
        settings["HOST"] = LOOPBACK
        settings["PORT"] = str(tunnel.local_port)
        try:
            connection_handler = ConnectionHandler({"default": settings})
            tcpip_ssh_connection: BaseDatabaseWrapper = connection_handler["default"]
            tcpip_ssh_connection.ensure_connection()
        except (DatabaseError, ImproperlyConfigured) as e:
            tunnel.close()
            sql_connection_failed.send(sender=self.__class__, connection=self, stage="SSH connection", error=str(e))
            return None
        self._tunnel = tunnel
        sql_connection_success.send(sender=self.__class__, connection=self)
        return tcpip_ssh_connection

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
            connection_handler = ConnectionHandler({"default": self.django_db_connection})
            ldap_user_pwd_connection: BaseDatabaseWrapper = connection_handler["default"]
            ldap_user_pwd_connection.ensure_connection()
            sql_connection_success.send(sender=self.__class__, connection=self)
            return ldap_user_pwd_connection
        # pylint: disable=W0718
        except Exception as e:
            sql_connection_failed.send(
                sender=self.__class__, connection=self, stage="LDAP user/password connection", error=str(e)
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
        self._connection = self.get_connection()
        connected = self._connection is not None
        self.close()
        return connected

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
                "Failed to establish a database connection using method: %s. Got return type of %s",
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
                logger.error("Failed to close the database connection: %s", e)
            self._connection = None
        if self._tunnel is not None:
            self._tunnel.close()
            self._tunnel = None

    def tool_call(self, sql: str) -> SqlToolCall:
        """
        Resolve a query into a :class:`~smarter.apps.connection.execution.SqlToolCall`, for the tool runner.

        :param sql: The final SQL.
        :returns: The call, with the database's password, and the SSH tunnel's, decrypted.
        :raises SmarterValueError: If the connection uses SSH, but has no SSH server.
        """
        password = None
        if self.password:
            password = self.password.get_secret()
        call = SqlToolCall(
            engine=self.db_engine or "",
            database=self.database,
            username=self.username,
            password=password,
            host=self.hostname,
            port=self.port or 3306,
            options=self.db_options,
            ssh=self.ssh_tunnel_settings(),
            sql=sql,
            timeout=self.timeout or self.DBMS_DEFAULT_TIMEOUT,
        )
        return call

    def execute_query(self, sql: str, limit: Optional[int] = None) -> Union[str, bool]:
        """
        Execute a SQL query and return the results as a JSON string.

        The query is resolved here, in the app, into a
        :class:`~smarter.apps.connection.execution.SqlToolCall`, with the passwords read from their
        Smarter Secrets, and executed by the tool runner (:mod:`smarter.apps.llmtool.runner`), with
        :func:`~smarter.apps.connection.execution.execute_sql_call`, through the SSH tunnel if the
        connection uses one. The signals are sent here, from its result.

        Sets :attr:`connected`, so that a caller can tell a failed connection, such as rejected
        credentials, from a failed query.

        :param sql: The SQL query to execute.
        :param limit: Optional limit on the number of rows to return.
        :return: JSON string of query results if successful, otherwise False.

        .. warning::

            This method does not perform any SQL injection protection or parameterization.
            It is the caller's responsibility to ensure that the SQL query is safe and properly formatted.

        .. warning::

            This method does not limit the number of rows returned by the query, unless the ``limit``
            parameter is provided. The connection's ``timeout`` limits how long the query runs, on
            MySQL and PostgreSQL. It is the caller's responsibility to ensure that the query is
            efficient and does not return excessive data.
        """
        if limit is not None:
            sql = sql.rstrip(";")  # Remove any trailing semicolon
            sql += f" LIMIT {limit};"
        self.connected = None
        sql_connection_attempted.send(sender=self.__class__, connection=self)
        try:
            call = self.tool_call(sql)
        except SmarterValueError as e:
            self.connected = False
            sql_connection_failed.send(sender=self.__class__, connection=self, error=str(e))
            return False
        result = get_tool_runner().run(call)
        if result.failure is not None:
            self.connected = False
            sql_connection_failed.send(sender=self.__class__, connection=self, error=result.failure)
            return False
        self.connected = True
        sql_connection_success.send(sender=self.__class__, connection=self)
        sql_connection_query_attempted.send(sender=self.__class__, connection=self, sql=sql, limit=limit)
        if result.is_error:
            sql_connection_query_failed.send(
                sender=self.__class__, connection=self, sql=sql, limit=limit, error=str(result.value)
            )
            return False
        sql_connection_query_success.send(sender=self.__class__, connection=self, sql=sql, limit=limit)
        return str(result.value)

    def test_proxy(self) -> bool:
        """
        Test the proxy connection by making a request to a known URL through the proxy.

        :return: True if the proxy connection is successful, otherwise False.
        :rtype: bool
        """
        proxy_dict: Optional[SmarterDictType] = None
        if self.proxy_protocol is not None and self.proxy_host is not None:
            # proxy_password is a Secret, whose value is the password.
            password = self.proxy_password.get_secret(update_last_accessed=False) if self.proxy_password else None
            userinfo = ""
            if self.proxy_username:
                userinfo = f"{self.proxy_username}:{password}@" if password else f"{self.proxy_username}@"
            proxy_dict = {
                self.proxy_protocol: f"{self.proxy_protocol}://{userinfo}{self.proxy_host}:{self.proxy_port}",
            }
        try:
            response = requests.get("https://www.google.com", proxies=proxy_dict, timeout=self.timeout)
            return response.status_code in [HTTPStatus.OK, HTTPStatus.PERMANENT_REDIRECT]
        except requests.exceptions.RequestException as e:
            logger.error("proxy test connection failed: %s", e)
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
        password: Optional[str]
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
            snake_case_name = to_snake_case(self.name)
            logger.warning(
                "name %s was not in snake_case. Converted to snake_case: %s",
                self.name,
                snake_case_name,
            )
            self.name = snake_case_name
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name + " - " + self.get_connection_string() if isinstance(self.name, str) else "unassigned"


__all__ = ["SqlConnection"]
