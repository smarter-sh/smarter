"""Smarter API Manifest - Plugin.spec"""

import os
from typing import ClassVar, Optional

from pydantic import Field, field_validator

from smarter.apps.plugin.manifest.models.sql_connection.const import MANIFEST_KIND
from smarter.apps.plugin.models import SqlConnection as SqlConnectionORM
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.manifest.models import AbstractSAMSpecBase, SmarterBasePydanticModel

from .enum import DbEngines, DBMSAuthenticationMethods


filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"
SMARTER_PLUGIN_MAX_SYSTEM_ROLE_LENGTH = 2048


class SqlConnection(SmarterBasePydanticModel):
    """Smarter API - generic SQL Connection class."""

    dbEngine: str = Field(
        ...,
        description=f"A valid SQL database engine. Common db_engines: {DbEngines.all_values()}",
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
    username: Optional[str] = Field(False, description="The database username.")
    password: Optional[str] = Field(False, description="The password.")
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
        if v in DbEngines.all_values():
            return v
        raise SAMValidationError(f"Invalid SQL connection engine: {v}. Must be one of {DbEngines.all_values()}")

    @field_validator("hostname")
    def validate_host(cls, v) -> str:
        if SmarterValidator.is_valid_cleanstring(v):
            return v
        raise SAMValidationError(f"Invalid SQL connection host: {v}. Must be a valid domain, IPv4, or IPv6 address.")

    @field_validator("port")
    def validate_port(cls, v, values) -> int:
        if v is None:
            default_port = next(
                (port for engine, port in SqlConnectionORM.DBMS_CHOICES if engine == values.get("dbEngine")), None
            )
            if default_port is not None:
                return int(default_port)
        if v and (v < 1 or v > 65535):
            raise SAMValidationError(f"Invalid SQL connection port: {v}. Must be between 1 and 65535.")
        return v

    @field_validator("database")
    def validate_database(cls, v) -> str:
        if SmarterValidator.is_valid_cleanstring(v):
            return v
        raise SAMValidationError(f"Invalid database name: {v}. Must be a valid string.")

    @field_validator("username")
    def validate_username(cls, v) -> str:
        if v is None:
            return v
        if SmarterValidator.is_valid_cleanstring(v):
            return v
        raise SAMValidationError(f"Invalid username: {v}. Must be a valid string.")

    @field_validator("password")
    def validate_password(cls, v) -> str:
        return v

    @field_validator("timeout")
    def validate_timeout(cls, v) -> int:
        v = v or SqlConnectionORM.DBMS_DEFAULT_TIMEOUT
        if v > 0:
            return v
        raise SAMValidationError(f"Invalid timeout: {v}. Must be greater than 0.")

    @field_validator("proxyHost")
    def validate_proxy_host(cls, v) -> str:
        if v is None:
            return v
        if v and not SmarterValidator.is_valid_domain(v):
            raise SAMValidationError(f"Invalid SQL proxy host: {v}. Must be a valid domain, IPv4, or IPv6 address.")
        return v

    @field_validator("proxyPort")
    def validate_proxy_port(cls, v) -> int:
        if v is None:
            return v
        if v < 1 or v > 65535:
            raise SAMValidationError(f"Invalid SQL proxy port: {v}. Must be between 1 and 65535.")
        return v

    @field_validator("poolSize")
    def validate_pool_size(cls, v) -> int:
        if v is None:
            return v
        if v > 0:
            return v
        raise SAMValidationError(f"Invalid pool size: {v}. Must be greater than 0.")

    @field_validator("maxOverflow")
    def validate_max_overflow(cls, v) -> int:
        if v is None:
            return v
        if v >= 0:
            return v
        raise SAMValidationError(f"Invalid max overflow: {v}. Must be 0 or greater.")

    @field_validator("authenticationMethod")
    def validate_authentication_method(cls, v) -> str:
        if v in DBMSAuthenticationMethods.all_values():
            return v
        raise SAMValidationError(
            f"Invalid authentication method: {v}. Must be one of {DBMSAuthenticationMethods.all_values()}"
        )

    @field_validator("useSsl")
    def validate_use_ssl(cls, v) -> bool:
        if isinstance(v, bool):
            return v
        raise SAMValidationError(f"Invalid useSsl value: {v}. Must be a boolean.")

    @field_validator("sslCert", "sslKey", "sslCa")
    def validate_ssl_fields(cls, v) -> Optional[str]:
        return v

    @field_validator("sshKnownHosts")
    def validate_ssh_known_hosts(cls, v) -> Optional[str]:
        return v


class SAMSqlConnectionSpec(AbstractSAMSpecBase):
    """Smarter API Sql Connection Manifest SqlConnection.spec"""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    connection: SqlConnection = Field(
        ..., description=f"{class_identifier}.selector[obj]: the selector logic to use for the {MANIFEST_KIND}"
    )
