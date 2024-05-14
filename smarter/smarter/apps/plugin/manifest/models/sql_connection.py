"""Smarter API - SQL Connection model."""

import re
from enum import Enum
from typing import ClassVar

from pydantic import Field, field_validator

from smarter.lib.django.validators import SmarterValidator
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.manifest.models import SmarterBaseModel

from .enum import DbEngine


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
        (DbEngine.MYSQL.name, PortAssignmentDefaults.MYSQL.value),
        (DbEngine.POSTGRES.name, PortAssignmentDefaults.POSTGRES.value),
        (DbEngine.ORACLE.name, PortAssignmentDefaults.ORACLE.value),
        (DbEngine.SQLITE.name, PortAssignmentDefaults.SQLITE.value),
        (DbEngine.MSSQL.name, PortAssignmentDefaults.MSSQL.value),
    ]
    PRETTY_PORT_ASSIGNMENTS: ClassVar[list] = ", ".join(
        [f"{engine}: {port}" for engine, port in DEFAULT_PORT_ASSIGNMENTS]
    )

    db_engine: str = Field(
        ...,
        description=f"a valid SQL database engine.  Common db_engines: {DbEngine.all_values()}",
    )
    host: str = Field(
        ...,
        description="The remote host of the SQL connection. Should be a valid internet domain name. Example: 'localhost' or 'mysql.mycompany.com' ",
    )
    port: int = Field(
        None,
        description=f"The port of the SQL connection. Default values are assigned based on the db_engine: {PRETTY_PORT_ASSIGNMENTS}.",
    )
    database: str = Field(..., description="The name of the database to connect to. Examples: 'sales' or 'mydb'")
    user: str = Field(..., description="The database username")
    password: str = Field(..., description="The password")

    @field_validator("db_engine")
    def validate_db_engine(cls, v) -> str:
        if v in DbEngine.all_values():
            return v
        raise SAMValidationError(f"Invalid SQL connection engine: {v}. Must be one of {DbEngine.all_values()}")

    @field_validator("host")
    def validate_host(cls, v) -> str:
        if SmarterValidator.is_valid_domain(v):
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

    @field_validator("database")
    def validate_database(cls, v) -> str:
        if re.match(SmarterValidator.VALID_CLEAN_STRING, v):
            return v
        raise SAMValidationError(
            f"Invalid characters found in SQL connection database: {v}. Ensure that you do not include characters that are not URL friendly."
        )

    @field_validator("user")
    def validate_user(cls, v) -> str:
        if re.match(SmarterValidator.VALID_CLEAN_STRING, v):
            return v
        raise SAMValidationError(f"Invalid characters found in SQL connection user: {v}")

    @field_validator("password")
    def validate_password(cls, v) -> str:
        return v
