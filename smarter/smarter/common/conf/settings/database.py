# pylint: disable=no-member,no-self-argument,unused-argument,R0801
"""The database settings, from which Django's ``DATABASES`` is built."""

from typing import Optional, Union

from pydantic import BaseModel, Field, SecretStr

from smarter.common.conf.const import THE_EMPTY_SET
from smarter.common.conf.defaults import settings_defaults
from smarter.common.conf.env import is_missing_value
from smarter.common.conf.util import before_field_validator, parse_int_setting
from smarter.common.exceptions import SmarterConfigurationError


class DatabaseSettings(BaseModel):
    """The platform's MySQL (MariaDB) database."""

    subsystem_sql_root_username: str = Field(
        settings_defaults.SUBSYSTEM_SQL_ROOT_USERNAME,
        description="The database server's administrator, whom manage.py load_from_github --run_scripts passes to a repository's scripts.",
        examples=["root"],
        title="MySQL Root Username",
    )
    """
    The database server's administrator.

    ``manage.py load_from_github --run_scripts`` passes it to a repository's scripts, in
    ``SMARTER_DATABASE_ADMIN_USERNAME``, e.g. to the Stackademy script that creates its course database
    and its users, so it needs a user that may.
    Set it with ``SMARTER_SUBSYSTEM_SQL_ROOT_USERNAME``.

    :type: str
    :default: Value from ``settings_defaults.SUBSYSTEM_SQL_ROOT_USERNAME``, ``root`` if it is not set.
    :raises SmarterConfigurationError: If the value is not a non-empty string.
    """

    @before_field_validator("subsystem_sql_root_username")
    def validate_subsystem_sql_root_username(cls, v: Optional[str]) -> str:
        """Validates the `sql_root_username` field.

        Args:
            v (Optional[str]): The username to validate.
        Returns:
            str: The validated username.
        """
        if v in THE_EMPTY_SET:
            v = settings_defaults.SUBSYSTEM_SQL_ROOT_USERNAME
        if not isinstance(v, str) or not v:
            raise SmarterConfigurationError(f"sql_root_username of type {type(v)} is not a non-empty string.")
        return v

    subsystem_sql_root_password: Optional[SecretStr] = Field(
        settings_defaults.SUBSYSTEM_SQL_ROOT_PASSWORD,
        description="The password of the database server's administrator, sql_root_username.",
        examples=["your-root-password"],
        title="MySQL Root Password",
    )
    """
    The password of the database server's administrator, :attr:`sql_root_username`.

    Set it with ``SMARTER_SUBSYSTEM_SQL_ROOT_PASSWORD``. ``manage.py load_from_github --run_scripts`` passes it
    to a repository's scripts in the ``MYSQL_PWD`` environment variable, where the MariaDB and MySQL
    clients read it, which keeps it off the command line. Without it, the scripts don't receive it.

    :type: Optional[SecretStr]
    :default: Value from ``settings_defaults.SUBSYSTEM_SQL_ROOT_PASSWORD``, None if it is not set.
    :raises SmarterConfigurationError: If the value is not a SecretStr.
    """

    @before_field_validator("subsystem_sql_root_password")
    def validate_subsystem_sql_root_password(cls, v: Optional[SecretStr]) -> Optional[SecretStr]:
        """Validates the `sql_root_password` field.

        Args:
            v (Optional[SecretStr]): The password to validate.
        Returns:
            Optional[SecretStr]: The validated password, or None if it is missing or a placeholder.
        """
        if v in THE_EMPTY_SET:
            v = settings_defaults.SUBSYSTEM_SQL_ROOT_PASSWORD
        if is_missing_value(v):
            return None
        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError(f"sql_root_password of type {type(v)} is not a SecretStr")
        return v

    subsystem_sql_host: str = Field(
        settings_defaults.SUBSYSTEM_SQL_HOST,
        description="The host name of the platform's database server.",
        examples=["smarter-mariadb", "mysql.example.com"],
        title="MySQL Host",
    )
    """
    The host name of the platform's database server, Django's ``DATABASES["default"]["HOST"]``.

    Set it with ``SMARTER_SUBSYSTEM_SQL_HOST``.

    :type: str
    :default: Value from ``settings_defaults.SUBSYSTEM_SQL_HOST``, ``smarter-mariadb``, the local docker-compose
        service, if it is not set.
    :raises SmarterConfigurationError: If the value is not a non-empty string.
    """

    @before_field_validator("subsystem_sql_host")
    def validate_subsystem_sql_host(cls, v: Optional[str]) -> str:
        """Validates the `sql_host` field.

        Args:
            v (Optional[str]): The host name to validate.
        Returns:
            str: The validated host name.
        """
        if v in THE_EMPTY_SET or is_missing_value(v):
            v = settings_defaults.SUBSYSTEM_SQL_HOST
        if not isinstance(v, str) or not v.strip():
            raise SmarterConfigurationError(f"sql_host of type {type(v)} is not a non-empty string.")
        return v.strip()

    subsystem_sql_port: int = Field(
        settings_defaults.SUBSYSTEM_SQL_PORT,
        ge=1,
        le=65535,
        description="The TCP port of the platform's database server.",
        examples=[3306],
        title="MySQL Port",
    )
    """
    The TCP port of the platform's database server, Django's ``DATABASES["default"]["PORT"]``.

    Set it with ``SMARTER_SUBSYSTEM_SQL_PORT``.

    :type: int
    :default: Value from ``settings_defaults.SUBSYSTEM_SQL_PORT``, 3306 if it is not set.
    :raises SmarterConfigurationError: If the value is not a port number, 1 to 65535.
    """

    @before_field_validator("subsystem_sql_port")
    def validate_subsystem_sql_port(cls, v: Optional[Union[int, str]]) -> int:
        """Validates the `sql_port` field.

        Args:
            v (Optional[Union[int, str]]): The port to validate, e.g. ``"3306"`` from an environment variable.
        Returns:
            int: The validated port.
        """
        return parse_int_setting(
            "subsystem_sql_port", v, settings_defaults.SUBSYSTEM_SQL_PORT, minimum=1, maximum=65535
        )

    subsystem_sql_database: str = Field(
        settings_defaults.SUBSYSTEM_SQL_DATABASE,
        description="The name of the platform's database.",
        examples=["smarter"],
        title="MySQL Database",
    )
    """
    The name of the platform's database, Django's ``DATABASES["default"]["NAME"]``.

    Set it with ``SMARTER_SUBSYSTEM_SQL_DATABASE``.

    :type: str
    :default: Value from ``settings_defaults.SUBSYSTEM_SQL_DATABASE``, ``smarter`` if it is not set.
    :raises SmarterConfigurationError: If the value is not a non-empty string.
    """

    @before_field_validator("subsystem_sql_database")
    def validate_subsystem_sql_database(cls, v: Optional[str]) -> str:
        """Validates the `sql_database` field.

        Args:
            v (Optional[str]): The database name to validate.
        Returns:
            str: The validated database name.
        """
        if v in THE_EMPTY_SET or is_missing_value(v):
            v = settings_defaults.SUBSYSTEM_SQL_DATABASE
        if not isinstance(v, str) or not v.strip():
            raise SmarterConfigurationError(f"sql_database of type {type(v)} is not a non-empty string.")
        return v.strip()

    subsystem_sql_user: str = Field(
        settings_defaults.SUBSYSTEM_SQL_USER,
        description="The database user that the platform connects as.",
        examples=["smarter"],
        title="MySQL User",
    )
    """
    The database user that the platform connects as, Django's ``DATABASES["default"]["USER"]``.

    Set it with ``SMARTER_SUBSYSTEM_SQL_USER``.

    :type: str
    :default: Value from ``settings_defaults.SUBSYSTEM_SQL_USER``, ``smarter`` if it is not set.
    :raises SmarterConfigurationError: If the value is not a non-empty string.
    """

    @before_field_validator("subsystem_sql_user")
    def validate_subsystem_sql_user(cls, v: Optional[str]) -> str:
        """Validates the `sql_user` field.

        Args:
            v (Optional[str]): The user name to validate.
        Returns:
            str: The validated user name.
        """
        if v in THE_EMPTY_SET or is_missing_value(v):
            v = settings_defaults.SUBSYSTEM_SQL_USER
        if not isinstance(v, str) or not v.strip():
            raise SmarterConfigurationError(f"sql_user of type {type(v)} is not a non-empty string.")
        return v.strip()

    subsystem_sql_password: Optional[SecretStr] = Field(
        settings_defaults.SUBSYSTEM_SQL_PASSWORD,
        description="The password of sql_user, the database user that the platform connects as.",
        examples=["your-database-password"],
        title="MySQL Password",
    )
    """
    The password of :attr:`sql_user`, Django's ``DATABASES["default"]["PASSWORD"]``.

    Set it with ``SMARTER_SUBSYSTEM_SQL_PASSWORD``. In the local environment it defaults to the password of
    docker-compose.yml's smarter-mariadb service. Elsewhere there is no default: a missing password, or
    a placeholder such as ``SET-ME-PLEASE``, is None, and the platform can't connect to its database.

    :type: Optional[SecretStr]
    :default: Value from ``settings_defaults.SUBSYSTEM_SQL_PASSWORD``.
    :raises SmarterConfigurationError: If the value is not a SecretStr.
    """

    @before_field_validator("subsystem_sql_password")
    def validate_subsystem_sql_password(cls, v: Optional[Union[SecretStr, str]]) -> Optional[SecretStr]:
        """Validates the `sql_password` field.

        Args:
            v (Optional[Union[SecretStr, str]]): The password to validate.
        Returns:
            Optional[SecretStr]: The validated password, or None if it is missing or a placeholder.
        """
        if v in THE_EMPTY_SET:
            v = settings_defaults.SUBSYSTEM_SQL_PASSWORD
        if isinstance(v, str):
            v = SecretStr(v)
        if is_missing_value(v):
            return None
        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError(f"sql_password of type {type(v)} is not a SecretStr")
        return v

    database_read_timeout: int = Field(
        settings_defaults.DATABASE_READ_TIMEOUT,
        ge=0,
        description=(
            "The seconds that a query of the platform's database may wait for the server's reply before it fails. "
            "0 for no timeout."
        ),
        title="Database Read Timeout",
    )
    """
    The seconds that a query of the platform's database may wait for the server's reply, and a write may.

    wait to be sent, before it fails. 0, the default, is no timeout.

    Without a timeout, a request whose query the database never answers holds its thread forever. The
    Helm chart sets it for the web server's pods only: migrations and other management commands can
    legitimately run longer, and keep the default. Connecting always times out after
    :data:`smarter.settings.base.DATABASE_CONNECT_TIMEOUT` seconds.

    Set it with ``SMARTER_DATABASE_READ_TIMEOUT``.

    :type: int
    :default: Value from ``settings_defaults.DATABASE_READ_TIMEOUT``, 0 if it is not set.
    :raises SmarterConfigurationError: If the value is not a non-negative integer.
    """

    @before_field_validator("database_read_timeout")
    def parse_database_read_timeout(cls, v: Optional[Union[int, str]]) -> int:
        """Validates the 'database_read_timeout' field.

        Args:
            v (Optional[Union[int, str]]): the database_read_timeout value to validate
        Returns:
            int: The validated database_read_timeout.
        """
        return parse_int_setting("database_read_timeout", v, settings_defaults.DATABASE_READ_TIMEOUT)


__all__ = ["DatabaseSettings"]
