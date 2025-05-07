"""Smarter API Manifest - Plugin.spec"""

import os
from typing import ClassVar, Optional

from pydantic import Field, field_validator

from smarter.apps.plugin.manifest.models.plugin.const import MANIFEST_KIND
from smarter.apps.plugin.models import SqlConnection as SqlConnectionORM
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.manifest.models import AbstractSAMSpecBase, SmarterBaseModel

from .enum import DbEngines


filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"
SMARTER_PLUGIN_MAX_SYSTEM_ROLE_LENGTH = 2048


class SqlConnection(SmarterBaseModel):
    """Smarter API - generic SQL Connection class."""

    db_engine: str = Field(
        ...,
        description=f"A valid SQL database engine. Common db_engines: {DbEngines.all_values()}",
    )
    hostname: str = Field(
        ...,
        description="The remote host of the SQL connection. Should be a valid internet domain name. Example: 'localhost' or 'mysql.mycompany.com'.",
    )
    port: Optional[int] = Field(
        None,
        description="The port of the SQL connection. Default values are assigned based on the db_engine.",
    )
    database: str = Field(..., description="The name of the database to connect to. Examples: 'sales' or 'mydb'.")
    username: Optional[str] = Field(False, description="The database username.")
    password: Optional[str] = Field(False, description="The password.")
    timeout: int = Field(
        SqlConnectionORM.DBMS_DEFAULT_TIMEOUT,
        description="The timeout for the database connection in seconds. Default is 30 seconds.",
    )
    use_ssl: bool = Field(
        False,
        description="Whether to use SSL/TLS for the connection.",
    )
    ssl_cert: Optional[str] = Field(
        None,
        description="The SSL certificate for the connection, if required.",
    )
    ssl_key: Optional[str] = Field(
        None,
        description="The SSL key for the connection, if required.",
    )
    ssl_ca: Optional[str] = Field(
        None,
        description="The Certificate Authority (CA) certificate for verifying the server.",
    )
    proxy_host: Optional[str] = Field(
        None,
        description="The remote host of the SQL proxy connection. Should be a valid internet domain name.",
    )
    proxy_port: Optional[int] = Field(
        None,
        description="The port of the SQL proxy connection.",
    )
    proxy_username: Optional[str] = Field(None, description="The username for the proxy connection.")
    proxy_password: Optional[str] = Field(None, description="The password for the proxy connection.")
    ssh_known_hosts: Optional[str] = Field(
        None,
        description="The known_hosts file content for verifying SSH connections.",
    )
    pool_size: int = Field(
        None,
        description="The size of the connection pool.",
    )
    max_overflow: int = Field(
        None,
        description="The maximum number of connections to allow beyond the pool size.",
    )
    authentication_method: str = Field(
        SqlConnectionORM.DBMSAuthenticationMethods.NONE.value,
        description="The authentication method to use for the connection. Example: 'Standard TCP/IP', 'Standard TCP/IP over SSH', 'LDAP User/Password'.",
    )

    @field_validator("db_engine")
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
                (port for engine, port in SqlConnectionORM.DBMS_CHOICES if engine == values.get("db_engine")), None
            )
            if default_port is not None:
                return default_port
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

    @field_validator("proxy_host")
    def validate_proxy_host(cls, v) -> str:
        if v is None:
            return v
        if v and not SmarterValidator.is_valid_domain(v):
            raise SAMValidationError(f"Invalid SQL proxy host: {v}. Must be a valid domain, IPv4, or IPv6 address.")
        return v

    @field_validator("proxy_port")
    def validate_proxy_port(cls, v) -> int:
        if v is None:
            return v
        if v < 1 or v > 65535:
            raise SAMValidationError(f"Invalid SQL proxy port: {v}. Must be between 1 and 65535.")
        return v

    @field_validator("pool_size")
    def validate_pool_size(cls, v) -> int:
        if v is None:
            return v
        if v > 0:
            return v
        raise SAMValidationError(f"Invalid pool size: {v}. Must be greater than 0.")

    @field_validator("max_overflow")
    def validate_max_overflow(cls, v) -> int:
        if v is None:
            return v
        if v >= 0:
            return v
        raise SAMValidationError(f"Invalid max overflow: {v}. Must be 0 or greater.")

    @field_validator("authentication_method")
    def validate_authentication_method(cls, v) -> str:
        if v in SqlConnectionORM.DBMSAuthenticationMethods.choices():
            return v
        raise SAMValidationError(
            f"Invalid authentication method: {v}. Must be one of {SqlConnectionORM.DBMSAuthenticationMethods.choices()}"
        )

    @field_validator("use_ssl")
    def validate_use_ssl(cls, v) -> bool:
        if isinstance(v, bool):
            return v
        raise SAMValidationError(f"Invalid use_ssl value: {v}. Must be a boolean.")

    @field_validator("ssl_cert", "ssl_key", "ssl_ca")
    def validate_ssl_fields(cls, v) -> Optional[str]:
        return v

    @field_validator("ssh_known_hosts")
    def validate_ssh_known_hosts(cls, v) -> Optional[str]:
        return v


class SAMPluginDataSqlConnectionSpec(AbstractSAMSpecBase):
    """Smarter API Sql Connection Manifest SqlConnection.spec"""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    connection: SqlConnection = Field(
        ..., description=f"{class_identifier}.selector[obj]: the selector logic to use for the {MANIFEST_KIND}"
    )
