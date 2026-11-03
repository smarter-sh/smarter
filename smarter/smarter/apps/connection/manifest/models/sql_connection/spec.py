"""Smarter API Manifest - SqlConnection.spec."""

import os
from typing import ClassVar, Optional

from pydantic import Field, field_validator

from smarter.apps.connection.manifest.models.sql_connection.const import MANIFEST_KIND
from smarter.apps.connection.models import SqlConnection as SqlConnectionORM
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.manifest.models import AbstractSAMSpecBase, SmarterBasePydanticModel

from .enum import DbEngines, DBMSAuthenticationMethods

filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"


class Connection(SmarterBasePydanticModel):
    """Smarter API - generic SQL Connection class."""

    dbEngine: str = Field(
        ...,
        description=f"A valid SQL database engine. Common db_engines: {DbEngines.all()}",
    )
    hostname: str = Field(
        ...,
        description="The remote host of the SQL connection. Should be a valid internet domain name. Example: 'localhost' or 'mysql.mycompany.com'.",
    )
    port: Optional[int] = Field(
        None,
        description="The port of the SQL connection. Default values are assigned based on the dbEngine.",
    )
    database: str = Field(..., description="The name of the database to connect to. Examples: 'sales' or 'mydb'.")
    username: Optional[str] = Field(None, description="The database username.")
    password: Optional[str] = Field(None, description="The password.")
    timeout: int = Field(
        SqlConnectionORM.DBMS_DEFAULT_TIMEOUT,
        description="The timeout for the database connection in seconds. Default is 30 seconds.",
    )
    useSsl: bool = Field(
        False,
        description="Whether to use SSL/TLS for the connection.",
    )
    sslCert: Optional[str] = Field(
        None,
        description="The SSL certificate for the connection, if required.",
    )
    sslKey: Optional[str] = Field(
        None,
        description="The SSL key for the connection, if required.",
    )
    sslCa: Optional[str] = Field(
        None,
        description="The Certificate Authority (CA) certificate for verifying the server.",
    )
    proxyHost: Optional[str] = Field(
        None,
        description="The remote host of the SQL proxy connection. Should be a valid internet domain name.",
    )
    proxyPort: Optional[int] = Field(
        None,
        description="The port of the SQL proxy connection.",
    )
    proxyUsername: Optional[str] = Field(None, description="The username for the proxy connection.")
    proxyPassword: Optional[str] = Field(None, description="The password for the proxy connection.")
    sshKnownHosts: Optional[str] = Field(
        None,
        description="The known_hosts file content for verifying SSH connections.",
    )
    poolSize: int = Field(
        5,
        description="The size of the connection pool.",
    )
    maxOverflow: int = Field(
        10,
        description="The maximum number of connections to allow beyond the pool size.",
    )
    authenticationMethod: str = Field(
        DBMSAuthenticationMethods.NONE.value,
        description="The authentication method to use for the connection. Example: 'Standard TCP/IP', 'Standard TCP/IP over SSH', 'LDAP User/Password'.",
    )

    @field_validator("dbEngine")
    def validate_db_engine(cls, v) -> str:
        """
        Validate that ``dbEngine`` is one of the supported Django database backends.

        :param v: The database engine.
        :returns: The database engine, unchanged.
        :raises SAMValidationError: if it is not in ``DbEngines.all()``.
        """
        if v in DbEngines.all():
            return v
        raise SAMValidationError(f"Invalid SQL connection engine: {v}. Must be one of {DbEngines.all()}")

    @field_validator("hostname")
    def validate_host(cls, v) -> str:
        """
        Validate that ``hostname`` is a clean string.

        :param v: The database host.
        :returns: The host, unchanged.
        :raises SAMValidationError: if it is not a clean string.
        """
        if SmarterValidator.is_valid_cleanstring(v):
            return v
        raise SAMValidationError(f"Invalid SQL connection host: {v}. Must be a valid domain, IPv4, or IPv6 address.")

    @field_validator("port")
    def validate_port(cls, v, values) -> Optional[int]:
        """
        Default ``port`` from the database engine when it is missing, and validate its range.

        :param v: The port, or None.
        :param values: The values of the model's other fields, used to look up ``dbEngine``.
        :returns: The port, or the default port of the database engine when the port is None and the engine has one.
        :raises SAMValidationError: if the port is not between 1 and 65535.
        """
        if v is None:
            db_engine = values.get("dbEngine")
            default_port = None
            for engine, port in SqlConnectionORM.DBMS_CHOICES:
                if engine == db_engine:
                    default_port = port
                    break
            if default_port is not None:
                return int(default_port)
        if v and (v < 1 or v > 65535):
            raise SAMValidationError(f"Invalid SQL connection port: {v}. Must be between 1 and 65535.")
        return v

    @field_validator("database")
    def validate_database(cls, v) -> str:
        """
        Validate that ``database`` is a clean string.

        :param v: The database name.
        :returns: The database name, unchanged.
        :raises SAMValidationError: if it is not a clean string.
        """
        if SmarterValidator.is_valid_cleanstring(v):
            return v
        raise SAMValidationError(f"Invalid database name: {v}. Must be a valid string.")

    @field_validator("username")
    def validate_username(cls, v) -> Optional[str]:
        """
        Validate that ``username``, when set, is a clean string.

        :param v: The username, or None.
        :returns: The username, unchanged.
        :raises SAMValidationError: if it is not a clean string.
        """
        if v is None:
            return v
        if SmarterValidator.is_valid_cleanstring(v):
            return v
        raise SAMValidationError(f"Invalid username: {v}. Must be a valid string.")

    @field_validator("password")
    def validate_password(cls, v) -> str:
        """
        Accept ``password`` as is: it is the name of a Secret, not the password itself.

        :param v: The name of the Secret that holds the password.
        :returns: The value, unchanged.
        """
        return v

    @field_validator("timeout")
    def validate_timeout(cls, v) -> int:
        """
        Default ``timeout`` when it is missing or 0, and validate that it is positive.

        :param v: The timeout in seconds, or None.
        :returns: The timeout, or ``SqlConnection.DBMS_DEFAULT_TIMEOUT`` when it is falsy.
        :raises SAMValidationError: if the timeout is not greater than 0.
        """
        v = v or SqlConnectionORM.DBMS_DEFAULT_TIMEOUT
        if v > 0:
            return v
        raise SAMValidationError(f"Invalid timeout: {v}. Must be greater than 0.")

    @field_validator("proxyHost")
    def validate_proxy_host(cls, v) -> Optional[str]:
        """
        Validate that ``proxyHost``, when set, is a valid domain.

        :param v: The proxy host, or None.
        :returns: The proxy host, unchanged.
        :raises SAMValidationError: if it is not a valid domain.
        """
        if v is None:
            return v
        if v and not SmarterValidator.is_valid_domain(v):
            raise SAMValidationError(f"Invalid SQL proxy host: {v}. Must be a valid domain, IPv4, or IPv6 address.")
        return v

    @field_validator("proxyPort")
    def validate_proxy_port(cls, v) -> Optional[int]:
        """
        Validate that ``proxyPort``, when set, is between 1 and 65535.

        :param v: The proxy port, or None.
        :returns: The proxy port, unchanged.
        :raises SAMValidationError: if it is out of range.
        """
        if v is None:
            return v
        if v < 1 or v > 65535:
            raise SAMValidationError(f"Invalid SQL proxy port: {v}. Must be between 1 and 65535.")
        return v

    @field_validator("poolSize")
    def validate_pool_size(cls, v) -> Optional[int]:
        """
        Validate that ``poolSize``, when set, is greater than 0.

        :param v: The connection pool size, or None.
        :returns: The pool size, unchanged.
        :raises SAMValidationError: if it is not greater than 0.
        """
        if v is None:
            return v
        if v > 0:
            return v
        raise SAMValidationError(f"Invalid pool size: {v}. Must be greater than 0.")

    @field_validator("maxOverflow")
    def validate_max_overflow(cls, v) -> Optional[int]:
        """
        Validate that ``maxOverflow``, when set, is 0 or greater.

        :param v: The maximum pool overflow, or None.
        :returns: The maximum overflow, unchanged.
        :raises SAMValidationError: if it is negative.
        """
        if v is None:
            return v
        if v >= 0:
            return v
        raise SAMValidationError(f"Invalid max overflow: {v}. Must be 0 or greater.")

    @field_validator("authenticationMethod")
    def validate_authentication_method(cls, v) -> str:
        """
        Validate that ``authenticationMethod`` is one of the supported authentication methods.

        :param v: The authentication method.
        :returns: The authentication method, unchanged.
        :raises SAMValidationError: if it is not in ``DBMSAuthenticationMethods.all()``.
        """
        if v in DBMSAuthenticationMethods.all():
            return v
        raise SAMValidationError(
            f"Invalid authentication method: {v}. Must be one of {DBMSAuthenticationMethods.all()}"
        )

    @field_validator("useSsl")
    def validate_use_ssl(cls, v) -> bool:
        """
        Validate that ``useSsl`` is a boolean.

        :param v: Whether to use SSL.
        :returns: The value, unchanged.
        :raises SAMValidationError: if it is not a boolean.
        """
        if isinstance(v, bool):
            return v
        raise SAMValidationError(f"Invalid useSsl value: {v}. Must be a boolean.")

    @field_validator("sslCert", "sslKey", "sslCa")
    def validate_ssl_fields(cls, v) -> Optional[str]:
        """
        Accept ``sslCert``, ``sslKey`` and ``sslCa`` as is.

        :param v: The SSL certificate, key or CA, or None.
        :returns: The value, unchanged.
        """
        return v

    @field_validator("sshKnownHosts")
    def validate_ssh_known_hosts(cls, v) -> Optional[str]:
        """
        Accept ``sshKnownHosts`` as is.

        :param v: The SSH known hosts, or None.
        :returns: The value, unchanged.
        """
        return v


class SAMSqlConnectionSpec(AbstractSAMSpecBase):
    """Smarter API Sql Connection Manifest Connection.spec."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    connection: Connection = Field(
        ..., description=f"{class_identifier}.selector[obj]: the selector logic to use for the {MANIFEST_KIND}"
    )
