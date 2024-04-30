"""Pydantic models for Smarter API Manifests."""

import re
from enum import Enum
from typing import ClassVar, List, Optional

import validators
from pydantic import BaseModel, Field, field_validator

from smarter.lib.django.validators import SmarterValidator

from .enum import DbEngine, SAMKinds
from .exceptions import SAMValidationError
from .version import SMARTER_API_VERSION


class SmarterBaseModel(BaseModel):
    """Smarter API V0 Base Pydantic Model."""


class HttpRequest(SmarterBaseModel):
    """Smarter API V0 Manifest generic HTTP request model."""

    DEFAULT_PORT: ClassVar[int] = 80
    DEFAULT_METHOD: ClassVar[str] = "GET"

    host: str = Field(..., description="a valid internet domain name")
    port: int = Field(
        DEFAULT_PORT,
        gt=0,
        lt=65535,
        description=f"a valid http port number: 0 thru 65,535. Default is {DEFAULT_PORT}",
    )
    endpoint: str = Field(..., description="a valid http url")
    method: str = Field(
        DEFAULT_METHOD,
        description=f"any valid http method: GET, POST, PUT, DELETE. Default is '{DEFAULT_METHOD}'",
    )
    headers: Optional[dict] = Field(None, description="a valid http header dict")
    body: Optional[dict] = Field(None, description="The http request body")

    @field_validator("host")
    def validate_host(cls, v) -> str:
        if validators.domain(v) or validators.ipv4(v) or validators.ipv6(v):
            return v
        raise SAMValidationError(f"Invalid API host: {v}. Must be a valid domain, IPv4, or IPv6 address.")

    @field_validator("endpoint")
    def validate_endpoint(cls, v) -> str:
        if re.match(SmarterValidator.VALID_URL_PATTERN, v):
            return v
        raise SAMValidationError(
            f"Invalid characters found in API endpoint: {v}. Ensure that you do not include characters that are not URL friendly."
        )

    @field_validator("method")
    def validate_method(cls, v) -> str:
        if isinstance(v, str):
            v = v.upper()
            if v in ["GET", "PATCH", "POST", "PUT", "DELETE"]:
                return v
            raise SAMValidationError(
                f"Invalid API method: {v}. Must be one of ['GET', 'PATCH', 'POST', 'PUT', 'DELETE']"
            )
        return v


class SqlConnection(SmarterBaseModel):
    """Smarter API V0 - generic SQL Connection class."""

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
        if validators.domain(v) or validators.ipv4(v) or validators.ipv6(v):
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


class SAMMetadataBase(SmarterBaseModel):
    """Pydantic Metadata base class. Expected to be subclassed by specific manifest classes."""

    name: str = Field(..., description="The name of the manifest")
    description: str = Field(..., description="The description of the manifest")
    version: str = Field(..., description="The version of the manifest")
    tags: Optional[List[str]] = Field(None, description="The tags of the manifest")
    annotations: Optional[List[str]] = Field(None, description="The annotations of the manifest")

    @field_validator("name")
    def validate_name(cls, v) -> str:
        if v in [None, ""]:
            raise SAMValidationError("Missing required key name")
        if len(v) > 50:
            raise SAMValidationError("Name must be less than 50 characters")
        if not re.match(SmarterValidator.VALID_CLEAN_STRING, v):
            raise SAMValidationError(
                f"Invalid name: {v}. Ensure that you do not include characters that are not URL friendly."
            )
        return v

    @field_validator("description")
    def validate_description(cls, v) -> str:
        if v in [None, ""]:
            raise SAMValidationError("Missing required key description")
        return v

    @field_validator("version")
    def validate_version(cls, v) -> str:
        if v in [None, ""]:
            raise SAMValidationError("Missing required key version")
        if not re.match(SmarterValidator.VALID_SEMANTIC_VERSION, v):
            raise SAMValidationError(
                f"Invalid semantic version. Expected semantic version (ie '1.0.0-alpha') but got {v}"
            )
        return v

    @field_validator("tags")
    def validate_tags(cls, v) -> List[str]:
        if isinstance(v, list):
            for tag in v:
                if not re.match(SmarterValidator.VALID_CLEAN_STRING, tag):
                    raise SAMValidationError(
                        f"Invalid tag: {tag}. Ensure that you do not include characters that are not URL friendly."
                    )
        return v

    @field_validator("annotations")
    def validate_annotations(cls, v) -> List[str]:
        if isinstance(v, list):
            for annotation in v:
                if not re.match(SmarterValidator.VALID_CLEAN_STRING, annotation):
                    raise SAMValidationError(
                        f"Invalid annotation: {annotation}. Ensure that you do not include characters that are not URL friendly."
                    )
        return v


class SAMSpecBase(SmarterBaseModel):
    """Pydantic Spec base class. Expected to be subclassed by specific manifest classes."""


class SAMStatusBase(SmarterBaseModel):
    """Pydantic Status base class. Expected to be subclassed by specific manifest classes."""


class SAM(SmarterBaseModel):
    """
    Pydantic Smarter API Manifest ("SAM") base class.

    The SAM class is a base class for all Smarter API manifests. It provides
    methods for validating the manifest data against a strongly-typed specification,
    and for accessing the manifest data in a structured way.

    The SAM class is designed to be subclassed by specific manifest classes
    that implement the specific manifest data and methods for that manifest.


    """

    apiVersion: str = Field(
        ..., description=f"apiVersion[String]: Required. The API version of the SAM. Set this to {SMARTER_API_VERSION}"
    )
    kind: str = Field(
        ...,
        description=f"kind[String]: Required. The kind of resource described by the manifest. Must be one of {SAMKinds.all_values()}",
    )
    metadata: SAMMetadataBase = Field(..., description="metadata[obj]: Required. The manifest metadata.")
    spec: SAMSpecBase = Field(..., description="spec[obj]: Required. The manifest specification.")
    status: Optional[SAMStatusBase] = Field(
        None,
        description="status[obj]: Optional. Read-only. The run-time state of the resource described by the manifest.",
    )

    @field_validator("apiVersion")
    def validate_apiVersion(cls, v) -> str:
        """Validate apiVersion"""
        if v in [None, ""]:
            raise SAMValidationError("Missing required manifest key: apiVersion")
        if v != SMARTER_API_VERSION:
            raise SAMValidationError(f"Invalid apiVersion. Expected {SMARTER_API_VERSION} but got {v}")
        return v

    @field_validator("kind")
    def validate_kind(cls, v) -> str:
        """Validate kind"""
        if v in [None, ""]:
            raise SAMValidationError("Missing required manifest key: kind")
        if v not in SAMKinds.all_values():
            raise SAMValidationError(f"Invalid kind. Must be one of {SAMKinds.all_values()} but got {v}")
        return v
