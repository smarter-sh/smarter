"""Pydantic models for Smarter API Manifests."""

import re
from typing import List, Optional

import validators
from pydantic import BaseModel, Field, field_validator

from smarter.lib.django.validators import SmarterValidator

from .enum import SAMKinds
from .exceptions import SAMValidationError
from .version import SMARTER_API_VERSION


class HttpRequest(BaseModel):
    """Smarter API V0 Manifest generic HTTP request model."""

    host: str = Field(..., description="Plugin.spec.data.api_data.host: a valid internet domain name")
    port: int = Field(
        ..., gt=0, lt=65535, description="Plugin.spec.data.api_data.port: a valid http port number: 0 thru 65,535"
    )
    endpoint: str = Field(..., description="Plugin.spec.data.api_data.endPoint: a valid http url")
    method: str = Field(
        ..., description="Plugin.spec.data.api_data.method: a valid http method: GET, POST, PUT, DELETE"
    )
    headers: Optional[dict] = Field(None, description="Plugin.spec.data.api_data.headers: a valid http header dict")
    body: Optional[dict] = Field(None, description="Plugin.spec.data.api_data.body: The body of the API connection")

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


class SqlConnection(BaseModel):
    """Smarter API V0 Plugin Manifest - Spec - Data - SQL - Connection class."""

    host: str = Field(..., description="The host of the SQL connection")
    port: int = Field(..., description="The port of the SQL connection")
    database: str = Field(..., description="The database of the SQL connection")
    user: str = Field(..., description="The user of the SQL connection")
    password: str = Field(..., description="The password of the SQL connection")

    @field_validator("host")
    def validate_host(cls, v) -> str:
        if validators.domain(v) or validators.ipv4(v) or validators.ipv6(v):
            return v
        raise SAMValidationError(f"Invalid SQL connection host: {v}. Must be a valid domain, IPv4, or IPv6 address.")

    @field_validator("port")
    def validate_port(cls, v) -> int:
        if v < 1 or v > 65535:
            raise SAMValidationError(f"Invalid SQL connection port: {v}. Must be between 1 and 65535.")
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


class SAMMetadataBase(BaseModel):
    """Pydantic Metadata base class. Expected to be subclassed by specific manifest classes."""

    name: str = Field(..., description="The name of the SAM")
    description: str = Field(..., description="The description of the SAM")
    version: str = Field(..., description="The version of the SAM")
    tags: Optional[List[str]] = Field(None, description="The tags of the SAM")
    annotations: Optional[List[str]] = Field(None, description="The annotations of the SAM")

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


class SAMSpecBase(BaseModel):
    """Pydantic Spec base class. Expected to be subclassed by specific manifest classes."""


class SAMStatusBase(BaseModel):
    """Pydantic Status base class. Expected to be subclassed by specific manifest classes."""


class SAM(BaseModel):
    """
    Pydantic Smarter API Manifest ("SAM") base class.

    The SAM class is a base class for all Smarter API manifests. It provides
    methods for validating the manifest data against a strongly-typed specification,
    and for accessing the manifest data in a structured way.

    The SAM class is designed to be subclassed by specific manifest classes
    that implement the specific manifest data and methods for that manifest.


    """

    apiVersion: str = Field(..., description="The API version of the SAM")
    kind: str = Field(..., description="The kind of SAM")
    metadata: SAMMetadataBase
    spec: SAMSpecBase
    status: SAMStatusBase

    @field_validator("apiVersion")
    def validate_apiVersion(cls, v) -> str:
        """Validate apiVersion"""
        if v in [None, ""]:
            raise SAMValidationError("Missing required key apiVersion")
        if v != SMARTER_API_VERSION:
            raise SAMValidationError(f"Invalid apiVersion. Expected {SMARTER_API_VERSION} but got {v}")
        return v

    @field_validator("kind")
    def validate_kind(cls, v) -> str:
        """Validate kind"""
        if v in [None, ""]:
            raise SAMValidationError("Missing required key kind")
        if v not in SAMKinds.all_values():
            raise SAMValidationError(f"Invalid kind. Expected one of {SAMKinds.all_values()} but got {v}")
        return v
