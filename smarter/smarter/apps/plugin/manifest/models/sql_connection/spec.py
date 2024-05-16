"""Smarter API Manifest - Plugin.spec"""

import os
from enum import Enum
from typing import ClassVar, Optional

from pydantic import Field, field_validator

from smarter.apps.plugin.manifest.models.plugin.const import MANIFEST_KIND
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.manifest.models import AbstractSAMSpecBase, SmarterBaseModel

from .enum import DbEngines


filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"
SMARTER_PLUGIN_MAX_SYSTEM_ROLE_LENGTH = 2048


class SqlConnection(SmarterBaseModel):
    """Smarter API - generic SQL Connection class."""

    class PortAssignmentDefaults(Enum):
        """SQL Port Assignments."""

        MYSQL = 3306
        POSTGRES = 5432
        SQLITE = None
        ORACLE = 1521
        MSSQL = 1433

    DEFAULT_PORT_ASSIGNMENTS: ClassVar[list] = [
        (DbEngines.MYSQL.name, PortAssignmentDefaults.MYSQL.value),
        (DbEngines.POSTGRES.name, PortAssignmentDefaults.POSTGRES.value),
        (DbEngines.ORACLE.name, PortAssignmentDefaults.ORACLE.value),
        (DbEngines.SQLITE.name, PortAssignmentDefaults.SQLITE.value),
        (DbEngines.MSSQL.name, PortAssignmentDefaults.MSSQL.value),
    ]
    PRETTY_PORT_ASSIGNMENTS: ClassVar[list] = ", ".join(
        [f"{engine}: {port}" for engine, port in DEFAULT_PORT_ASSIGNMENTS]
    )

    db_engine: str = Field(
        ...,
        description=f"a valid SQL database engine.  Common db_engines: {DbEngines.all_values()}",
    )
    hostname: str = Field(
        ...,
        description="The remote host of the SQL connection. Should be a valid internet domain name. Example: 'localhost' or 'mysql.mycompany.com' ",
    )
    port: int = Field(
        None,
        description=f"The port of the SQL connection. Default values are assigned based on the db_engine: {PRETTY_PORT_ASSIGNMENTS}.",
    )
    database: str = Field(..., description="The name of the database to connect to. Examples: 'sales' or 'mydb'")
    username: str = Field(..., description="The database username")
    password: str = Field(..., description="The password")
    proxy_host: Optional[str] = Field(
        None,
        description="The remote host of the SQL proxy connection. Should be a valid internet domain name. Example: 'mysql.mycompany.com' ",
    )
    proxy_port: Optional[int] = Field(
        None,
        description=f"The port of the SQL proxy connection. Default values are assigned based on the db_engine: {PRETTY_PORT_ASSIGNMENTS}.",
    )
    proxy_username: Optional[str] = Field(None, description="The username for the proxy connection")
    proxy_password: Optional[str] = Field(None, description="The password for the proxy connection")

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
    def validate_port(cls, v) -> int:
        if v is None:
            default_port = cls.DEFAULT_PORT_ASSIGNMENTS.get(cls.db_engine, None)
            if default_port is not None:
                return default_port
        if v < 1 or v > 65535:
            raise SAMValidationError(f"Invalid SQL connection port: {v}. Must be between 1 and 65535.")
        if not v:
            raise SAMValidationError(
                f"Invalid SQL connection. Port value is missing and no default value was found for db_engine {cls.db_engine}."
            )
        return v

    @field_validator("proxy_host")
    def validate_proxy_host(cls, v) -> str:
        if v:
            if not SmarterValidator.is_valid_domain(v):
                raise SAMValidationError(f"Invalid SQL proxy host: {v}. Must be a valid domain, IPv4, or IPv6 address.")
        return v

    @field_validator("proxy_port")
    def validate_proxy_port(cls, v) -> int:
        if v and (v < 1 or v > 65535):
            raise SAMValidationError(f"Invalid SQL proxy port: {v}. Must be between 1 and 65535.")
        return v


class SAMPluginDataSqlConnectionSpec(AbstractSAMSpecBase):
    """Smarter API Sql Connection Manifest SqlConnection.spec"""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    connection: SqlConnection = Field(
        ..., description=f"{class_identifier}.selector[obj]: the selector logic to use for the {MANIFEST_KIND}"
    )
