"""
Smarter API Manifest - Proxy.spec.

A Proxy forwards requests, as they are, to an LLM provider's native API, and adds the
provider's API key, which Smarter keeps in a Secret. Callers authenticate with a Smarter
API key instead, and so never see the provider's.

.. code-block:: yaml

    spec:
      provider: anthropic                 # the name of a Provider
      apiKey: anthropic_api_key           # the name of a Secret. Optional: defaults to the Provider's.
      baseUrl: https://api.anthropic.com/v1/   # Optional: defaults to the Provider's.
      auth:
        header: x-api-key                 # where the provider expects its API key
        scheme: ""                        # its prefix, e.g. Bearer. Empty for none.
      headers:
        anthropic-version: "2023-06-01"   # added to every request
      allowedPaths:                       # glob patterns. Empty allows every path.
        - messages
        - messages/count_tokens
        - models
        - models/*
      timeout: 120                        # seconds
      isActive: true

A request to ``/api/v1/proxy/<name>/messages`` is forwarded to
``https://api.anthropic.com/v1/messages``.
"""

import os
import re
from typing import ClassVar, Optional
from urllib.parse import urlparse

from pydantic import ConfigDict, Field, field_validator

from smarter.apps.proxy.const import (
    DEFAULT_AUTH_HEADER,
    DEFAULT_AUTH_SCHEME,
    DEFAULT_TIMEOUT,
    HOP_BY_HOP_HEADERS,
    MAX_TIMEOUT,
    RESERVED_HEADERS,
)
from smarter.apps.proxy.manifest.models.proxy.const import MANIFEST_KIND
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.manifest.models import AbstractSAMSpecBase

filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"

HEADER_NAME = re.compile(r"^[!#$%&'*+\-.^_`|~0-9A-Za-z]+$")
"""An HTTP header name: an RFC 9110 token."""
RESOURCE_NAME = re.compile(r"^[A-Za-z0-9_\-]+$")
"""The name of a Provider or Secret."""
PATH_PATTERN = re.compile(r"^[A-Za-z0-9_\-.:/*?\[\]{}]+$")


class ProxyBaseModel(AbstractSAMSpecBase):
    """Base class of the Proxy spec's blocks.

    Unknown fields are rejected, to catch typos.
    """

    model_config = ConfigDict(extra="forbid")


def validate_header_name(name: str, field: str) -> str:
    name = str(name).strip()
    if not HEADER_NAME.match(name):
        raise SAMValidationError(f"{field}: '{name}' is not a valid HTTP header name.")
    return name


def validate_header_value(value: str, field: str) -> str:
    value = str(value)
    if "\r" in value or "\n" in value:
        raise SAMValidationError(f"{field}: header values may not contain line breaks.")
    return value


class SAMProxySpecAuth(ProxyBaseModel):
    """Spec.auth: how the provider expects its API key."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER + ".auth"

    header: str = Field(
        default=DEFAULT_AUTH_HEADER,
        description=(
            f"{class_identifier}.header[str]: the HTTP header in which the provider expects its API key, "
            "e.g. Authorization (OpenAI), x-api-key (Anthropic) or x-goog-api-key (Google Gemini)."
        ),
    )
    scheme: Optional[str] = Field(
        default=DEFAULT_AUTH_SCHEME,
        description=(
            f"{class_identifier}.scheme[str]: the prefix of the API key in the header, e.g. Bearer. "
            "Empty or null for none, e.g. for x-api-key."
        ),
    )

    @field_validator("header")
    @classmethod
    def validate_header(cls, v: str) -> str:
        v = validate_header_name(v, "auth.header")
        if v.lower() in HOP_BY_HOP_HEADERS or v.lower() in ("host", "content-length", "content-type", "cookie"):
            raise SAMValidationError(f"auth.header: '{v}' cannot carry an API key.")
        return v

    @field_validator("scheme")
    @classmethod
    def validate_scheme(cls, v: Optional[str]) -> str:
        v = str(v or "").strip()
        if v and not HEADER_NAME.match(v):
            raise SAMValidationError(f"auth.scheme: '{v}' must be a single word, e.g. Bearer, or empty.")
        return v


class SAMProxySpec(ProxyBaseModel):
    """Smarter API Proxy Manifest Proxy.spec."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    provider: str = Field(
        ...,
        description=(
            f"{class_identifier}.provider[str]: the name of the Provider whose API the {MANIFEST_KIND} forwards "
            "to, e.g. openai. It must belong to, or be shared with, the manifest's owner."
        ),
    )
    apiKey: Optional[str] = Field(
        default=None,
        description=(
            f"{class_identifier}.apiKey[str]: the name of the Secret that contains the provider's API key. It "
            "must belong to, or be shared with, the manifest's owner. Defaults to the Provider's API key."
        ),
    )
    baseUrl: Optional[str] = Field(
        default=None,
        description=(
            f"{class_identifier}.baseUrl[str]: the base URL of the provider's API, e.g. https://api.openai.com/v1/. "
            "Defaults to the Provider's base URL."
        ),
    )
    auth: SAMProxySpecAuth = Field(
        default_factory=SAMProxySpecAuth,
        description=f"{class_identifier}.auth[object]: how the provider expects its API key. Defaults to Authorization: Bearer.",
    )
    headers: dict[str, str] = Field(
        default_factory=dict,
        description=(
            f"{class_identifier}.headers[dict]: other HTTP headers that are added to every request, e.g. "
            "anthropic-version. They replace the caller's headers of the same name."
        ),
    )
    allowedPaths: list[str] = Field(
        default_factory=list,
        description=(
            f"{class_identifier}.allowedPaths[list]: glob patterns of the paths, relative to baseUrl, that callers "
            "may use, e.g. chat/completions or models/*. Empty allows every path."
        ),
    )
    timeout: int = Field(
        default=DEFAULT_TIMEOUT,
        ge=1,
        le=MAX_TIMEOUT,
        description=f"{class_identifier}.timeout[int]: the most seconds to wait for the provider's response.",
    )
    isActive: bool = Field(
        default=True,
        description=f"{class_identifier}.isActive[bool]: inactive {MANIFEST_KIND} refuse every request.",
    )

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        v = str(v or "").strip()
        if not RESOURCE_NAME.match(v):
            raise SAMValidationError(f"provider: '{v}' is not a valid Provider name.")
        return v

    @field_validator("apiKey")
    @classmethod
    def validate_api_key(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = str(v).strip()
        if not RESOURCE_NAME.match(v):
            raise SAMValidationError(
                f"apiKey: '{v}' is not a valid Secret name. It is the name of a Secret, not the API key itself."
            )
        return v

    @field_validator("baseUrl")
    @classmethod
    def validate_base_url(cls, v: Optional[str]) -> Optional[str]:
        if v is None or not str(v).strip():
            return None
        v = str(v).strip()
        url = urlparse(v)
        if url.scheme not in ("http", "https") or not url.hostname:
            raise SAMValidationError(f"baseUrl: '{v}' must be an http(s) URL.")
        if url.username or url.password:
            raise SAMValidationError("baseUrl: may not contain credentials. Use apiKey.")
        if url.query or url.fragment:
            raise SAMValidationError(f"baseUrl: '{v}' may not contain a query or fragment.")
        return v if v.endswith("/") else v + "/"

    @field_validator("headers")
    @classmethod
    def validate_headers(cls, v: dict[str, str]) -> dict[str, str]:
        retval = {}
        for name, value in (v or {}).items():
            name = validate_header_name(name, "headers")
            if name.lower() in RESERVED_HEADERS:
                raise SAMValidationError(
                    f"headers: '{name}' is reserved. Use auth for the provider's API key, which Smarter adds."
                )
            retval[name] = validate_header_value(value, f"headers.{name}")
        return retval

    @field_validator("allowedPaths")
    @classmethod
    def validate_allowed_paths(cls, v: list[str]) -> list[str]:
        retval = []
        for pattern in v or []:
            pattern = str(pattern).strip().strip("/")
            segments = pattern.split("/")
            if (
                not pattern
                or not PATH_PATTERN.match(pattern)
                or "://" in pattern
                or any(segment in ("", ".", "..") for segment in segments)
            ):
                raise SAMValidationError(
                    f"allowedPaths: '{pattern}' is not a path pattern, e.g. chat/completions or models/*."
                )
            retval.append(pattern)
        return retval


__all__ = [
    "SAMProxySpec",
    "SAMProxySpecAuth",
]
