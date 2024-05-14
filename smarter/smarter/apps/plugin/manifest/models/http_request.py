"""Pydantic model for the Smarter API Manifest HTTP request."""

import re
from typing import ClassVar, Optional

from pydantic import Field, field_validator

from smarter.lib.django.validators import SmarterValidator
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.manifest.models import SmarterBaseModel


class HttpRequest(SmarterBaseModel):
    """Smarter API Manifest generic HTTP request model."""

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
        if SmarterValidator.is_valid_domain(v):
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
