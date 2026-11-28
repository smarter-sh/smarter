# pylint: disable=no-member,no-self-argument,unused-argument,R0801
"""The database settings, from which Django's ``DATABASES`` is built."""

from typing import Annotated, Optional, Union

from pydantic import BaseModel, Field, SecretStr, model_validator

from smarter.common.conf.const import THE_EMPTY_SET
from smarter.common.conf.credentials import DATABASE_ADMIN_POD_KINDS, HeldBy
from smarter.common.conf.env import is_missing_value
from smarter.common.conf.util import (
    before_field_validator,
    field_default,
    has_field,
    input_value,
    parse_int_setting,
    with_derived_default,
)
from smarter.common.const import SmarterEnvironments, SmarterKubernetesPodKinds
from smarter.common.exceptions import SmarterConfigurationError


class DatabaseSettings(BaseModel):
    """The platform's MySQL (MariaDB) database."""

    subsystem_sql_root_username: str = Field(
        "root",
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
    :default: ``root`` if it is not set.
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
            v = field_default(cls, "subsystem_sql_root_username")
        if not isinstance(v, str) or not v:
            raise SmarterConfigurationError(f"sql_root_username of type {type(v)} is not a non-empty string.")
        return v

    subsystem_sql_root_password: Annotated[Optional[SecretStr], HeldBy(*DATABASE_ADMIN_POD_KINDS)] = Field(
        None,
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
    :default: None if it is not set.
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
            v = field_default(cls, "subsystem_sql_root_password")
        if is_missing_value(v):
            return None
        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError(f"sql_root_password of type {type(v)} is not a SecretStr")
        return v

    subsystem_sql_backup_password: Annotated[Optional[SecretStr], HeldBy(*DATABASE_ADMIN_POD_KINDS)] = Field(
        None,
        description="The password of the read-only account that the nightly database backup dumps the database as.",
        examples=["your-backup-password"],
        title="MySQL Backup Password",
    )
    """
    The password of the database's read-only backup account, ``smarter_backup`` by default.

    Set it with ``SMARTER_SUBSYSTEM_SQL_BACKUP_PASSWORD``. The Helm chart's init Job creates the account with it,
    and its nightly backup Job dumps the database as that account; until it is set, the backup dumps as the
    administrator, :attr:`subsystem_sql_root_password`. Only the chart's shell scripts use it, not Smarter's Python
    code: it is a setting so that the credentials map (:mod:`smarter.common.conf.credentials`) says which pods hold
    it, and the chart gives it to no other pod.

    :type: Optional[SecretStr]
    :default: None if it is not set.
    :raises SmarterConfigurationError: If the value is not a SecretStr.
    """

    @before_field_validator("subsystem_sql_backup_password")
    def validate_subsystem_sql_backup_password(cls, v: Optional[SecretStr]) -> Optional[SecretStr]:
        """Validates the `sql_backup_password` field.

        Args:
            v (Optional[SecretStr]): The password to validate.
        Returns:
            Optional[SecretStr]: The validated password, or None if it is missing or a placeholder.
        """
        if v in THE_EMPTY_SET:
            v = field_default(cls, "subsystem_sql_backup_password")
        if is_missing_value(v):
            return None
        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError(f"sql_backup_password of type {type(v)} is not a SecretStr")
        return v

    subsystem_sql_host: str = Field(
        "smarter-mariadb",
        description="The host name of the platform's database server.",
        examples=["smarter-mariadb", "mysql.example.com"],
        title="MySQL Host",
    )
    """
    The host name of the platform's database server, Django's ``DATABASES["default"]["HOST"]``.

    Set it with ``SMARTER_SUBSYSTEM_SQL_HOST``.

    :type: str
    :default: ``smarter-mariadb``, the local docker-compose
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
            v = field_default(cls, "subsystem_sql_host")
        if not isinstance(v, str) or not v.strip():
            raise SmarterConfigurationError(f"sql_host of type {type(v)} is not a non-empty string.")
        return v.strip()

    subsystem_sql_port: int = Field(
        3306,
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
    :default: 3306 if it is not set.
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
            "subsystem_sql_port", v, field_default(cls, "subsystem_sql_port"), minimum=1, maximum=65535
        )

    subsystem_sql_database: str = Field(
        "smarter",
        description="The name of the platform's database.",
        examples=["smarter"],
        title="MySQL Database",
    )
    """
    The name of the platform's database, Django's ``DATABASES["default"]["NAME"]``.

    Set it with ``SMARTER_SUBSYSTEM_SQL_DATABASE``.

    :type: str
    :default: ``smarter`` if it is not set.
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
            v = field_default(cls, "subsystem_sql_database")
        if not isinstance(v, str) or not v.strip():
            raise SmarterConfigurationError(f"sql_database of type {type(v)} is not a non-empty string.")
        return v.strip()

    subsystem_sql_user: str = Field(
        "smarter",
        description="The database user that the platform connects as.",
        examples=["smarter"],
        title="MySQL User",
    )
    """
    The database user that the platform connects as, Django's ``DATABASES["default"]["USER"]``.

    Set it with ``SMARTER_SUBSYSTEM_SQL_USER``.

    :type: str
    :default: ``smarter`` if it is not set.
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
            v = field_default(cls, "subsystem_sql_user")
        if not isinstance(v, str) or not v.strip():
            raise SmarterConfigurationError(f"sql_user of type {type(v)} is not a non-empty string.")
        return v.strip()

    subsystem_sql_password: Annotated[Optional[SecretStr], HeldBy(*SmarterKubernetesPodKinds.with_database)] = Field(
        None,
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
    :default: ``"smarter"`` in the local environment, and None elsewhere. See :meth:`derive_database_defaults`.
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
            v = field_default(cls, "subsystem_sql_password")
        if isinstance(v, str):
            v = SecretStr(v)
        if is_missing_value(v):
            return None
        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError(f"sql_password of type {type(v)} is not a SecretStr")
        return v

    @model_validator(mode="before")
    @classmethod
    def derive_database_defaults(cls, data: object) -> object:
        """
        Derive the local environment's database password, unless it is set.

        In the local environment, the password is docker-compose.yml's smarter-mariadb service's,
        ``smarter``. Elsewhere there is no default.

        :param data: The values to validate: the constructor's and the environment's.
        :returns: The values, with the derived default added in the local environment.
        """
        if not has_field(cls, "environment"):
            return data
        environment = input_value(cls, data, "environment")
        if environment != SmarterEnvironments.LOCAL:
            return data
        return with_derived_default(data, "subsystem_sql_password", "smarter")

    database_read_timeout: int = Field(
        0,
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
    :default: 0 if it is not set.
    :raises SmarterConfigurationError: If the value is not a non-negative integer.
    """

    database_unavailable: bool = Field(
        False,
        description=(
            "True in a process that has no platform database: the tool worker. Waffle switches are then off, "
            "without a query."
        ),
        title="Database Unavailable",
    )
    """
    True in a process that is not given the platform's database: the tool worker, ``smarter-worker-tools``.

    The tool worker runs LLM tool calls without the database or the platform's credentials (ADR-038). Its
    network policy doesn't let it reach the database, so a query would wait for the connection to time
    out. With this setting, every waffle switch is off, and is never read from the database, so that a
    switched logger, which checks its switch on each log call, costs nothing.

    Set it with ``SMARTER_DATABASE_UNAVAILABLE``. The Helm chart sets it for the tool worker only.

    :type: bool
    :default: False
    """

    @before_field_validator("database_read_timeout")
    def parse_database_read_timeout(cls, v: Optional[Union[int, str]]) -> int:
        """Validates the 'database_read_timeout' field.

        Args:
            v (Optional[Union[int, str]]): the database_read_timeout value to validate
        Returns:
            int: The validated database_read_timeout.
        """
        return parse_int_setting("database_read_timeout", v, field_default(cls, "database_read_timeout"))


__all__ = ["DatabaseSettings"]
