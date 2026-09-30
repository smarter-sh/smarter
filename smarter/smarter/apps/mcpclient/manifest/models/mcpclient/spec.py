"""
Smarter API Manifest - MCPClient.spec.

An MCPClient connects Smarter to a remote `Model Context Protocol <https://modelcontextprotocol.io>`_
(MCP) server. When an LLMClient lists the MCPClient in its ``spec.mcpClients``, the server's
tools are offered to the LLM on each prompt, alongside the LLMClient's Plugins and Functions,
and the server's instructions are added to the system prompt.

.. code-block:: yaml

    spec:
      config:
        transport: http              # http (Streamable HTTP) or sse (legacy HTTP+SSE)
        endpointUrl: https://mcp.example.com/mcp
        headers: {}                  # optional, non-secret HTTP headers
        timeout: 30                  # seconds
        authType: bearer_token       # none, api_key, bearer_token or oauth2
        credentials: example_token   # the name of a Smarter Secret containing the credential
        apiKeyHeader: X-API-Key      # the header that carries an api_key credential
        allowedTools: []             # glob patterns. Empty means all of the server's tools
        allowedResources: []         # glob patterns of resource URIs the LLM may read
        includeInstructions: true    # add the server's instructions to the system prompt
        cacheTtl: 300                # seconds to cache the server's tools and instructions
        isActive: true
        priority: 100                # lower runs first

.. note::

    **Experimental.** The MCPClient was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

import os
import re
from typing import ClassVar, Optional
from urllib.parse import urlparse

from pydantic import Field, field_validator, model_validator

from smarter.apps.mcpclient.manifest.enum import (
    SAMMCPClientAuthType,
    SAMMCPClientTransport,
)
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.manifest.models import AbstractSAMSpecBase

from .const import (
    DEFAULT_API_KEY_HEADER,
    DEFAULT_CACHE_TTL,
    DEFAULT_PRIORITY,
    DEFAULT_TIMEOUT,
    MANIFEST_KIND,
    MAX_CACHE_TTL,
    MAX_HEADER_VALUE_LENGTH,
    MAX_HEADERS,
    MAX_TIMEOUT,
    RESERVED_HEADERS,
)

filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"

HEADER_NAME_PATTERN = re.compile(r"^[A-Za-z0-9!#$%&'*+.^_`|~-]{1,64}$")
"""An HTTP header name: an RFC 9110 token, of at most 64 characters."""


def validate_header_name(name: str, field: str) -> str:
    """
    Validate an HTTP header name that a manifest may set.

    :param name: The header name.
    :param field: The manifest field, for the error message.
    :returns: The header name.
    :raises SAMValidationError: If the name is not a valid header name, or is reserved.
    """
    if not HEADER_NAME_PATTERN.match(name):
        raise SAMValidationError(f"{field}: '{name}' is not a valid HTTP header name.")
    lower = name.lower()
    if lower in RESERVED_HEADERS or lower.startswith("mcp-"):
        raise SAMValidationError(
            f"{field}: the '{name}' header is reserved. Credentials belong in a Smarter Secret, via credentials."
        )
    return name


def validate_endpoint_url(url: str) -> str:
    """
    Validate an MCP server's endpoint URL.

    The URL must be https, on the standard port, without credentials or a fragment.
    Whether its host has a public address is verified each time Smarter connects.

    :param url: The URL.
    :returns: The URL.
    :raises SAMValidationError: If the URL is not permitted.
    """
    try:
        parsed = urlparse(url)
        port = parsed.port
    except ValueError as e:
        raise SAMValidationError(f"endpointUrl: '{url}' is not a valid URL.") from e
    if parsed.scheme != "https" or not parsed.hostname:
        raise SAMValidationError(f"endpointUrl: '{url}' must be an https URL.")
    if parsed.username or parsed.password:
        raise SAMValidationError("endpointUrl: must not contain credentials. Use credentials instead.")
    if port not in (None, 443):
        raise SAMValidationError(f"endpointUrl: '{url}' must use the standard https port.")
    if parsed.fragment:
        raise SAMValidationError(f"endpointUrl: '{url}' must not contain a fragment.")
    return url


class SAMMCPClientSpecConfig(AbstractSAMSpecBase):
    """Smarter API MCPClient Manifest MCPClient.spec.config."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER + ".config"

    # --- connection ---
    transport: str = Field(
        default=SAMMCPClientTransport.HTTP.value,
        description=(
            f"{class_identifier}.transport[str]: the MCP transport. One of: "
            f"{SAMMCPClientTransport.supported()}. http is Streamable HTTP, and sse is the legacy "
            "HTTP+SSE transport."
        ),
    )
    endpointUrl: str = Field(
        ...,
        description=f"{class_identifier}.endpointUrl[str]: the https URL of the MCP server's endpoint.",
    )
    headers: Optional[dict[str, str]] = Field(
        default_factory=dict,
        description=(
            f"{class_identifier}.headers[dict]: optional, non-secret HTTP headers to send to the MCP "
            "server. Credentials belong in a Smarter Secret, via credentials."
        ),
    )
    timeout: int = Field(
        default=DEFAULT_TIMEOUT,
        ge=1,
        le=MAX_TIMEOUT,
        description=f"{class_identifier}.timeout[int]: seconds to wait for the MCP server to connect and respond.",
    )

    # --- auth ---
    authType: str = Field(
        default=SAMMCPClientAuthType.NONE.value,
        description=(
            f"{class_identifier}.authType[str]: how to authenticate with the MCP server. One of: "
            f"{SAMMCPClientAuthType.all()}. oauth2 sends an OAuth access token, obtained elsewhere, as a "
            "bearer token."
        ),
    )
    credentials: Optional[str] = Field(
        default=None,
        description=(
            f"{class_identifier}.credentials[str]: the name of the Smarter Secret containing the credential. "
            "Required unless authType is none."
        ),
    )
    apiKeyHeader: Optional[str] = Field(
        default=DEFAULT_API_KEY_HEADER,
        description=f"{class_identifier}.apiKeyHeader[str]: the HTTP header that carries an api_key credential.",
    )

    # --- capability scope ---
    allowedTools: Optional[list[str]] = Field(
        default_factory=list,
        description=(
            f"{class_identifier}.allowedTools[list]: glob patterns of the tool names to offer the LLM, "
            "e.g. search_* . Empty means all of the tools that the server advertises."
        ),
    )
    allowedResources: Optional[list[str]] = Field(
        default_factory=list,
        description=(
            f"{class_identifier}.allowedResources[list]: glob patterns of the resource URIs that the LLM "
            "may read, e.g. docs://example.com/* . Empty means none."
        ),
    )
    includeInstructions: bool = Field(
        default=True,
        description=f"{class_identifier}.includeInstructions[bool]: add the MCP server's instructions to the system prompt.",
    )
    cacheTtl: int = Field(
        default=DEFAULT_CACHE_TTL,
        ge=0,
        le=MAX_CACHE_TTL,
        description=(
            f"{class_identifier}.cacheTtl[int]: seconds to cache the MCP server's tools, instructions and "
            "capabilities. 0 disables caching."
        ),
    )

    # --- lifecycle ---
    isActive: bool = Field(
        default=True,
        description=f"{class_identifier}.isActive[bool]: whether LLMClients use this {MANIFEST_KIND}.",
    )
    priority: int = Field(
        default=DEFAULT_PRIORITY,
        ge=0,
        description=(
            f"{class_identifier}.priority[int]: the order in which an LLMClient's {MANIFEST_KIND}s are "
            "offered to the LLM. Lower runs first."
        ),
    )

    @field_validator("transport")
    @classmethod
    def validate_transport(cls, v: str) -> str:
        """Validate the transport.

        stdio is reserved, and not supported.
        """
        v = (v or "").lower()
        if v == SAMMCPClientTransport.STDIO.value:
            raise SAMValidationError(
                "transport: stdio is not supported. Smarter connects only to remote MCP servers, via http or sse."
            )
        if v not in SAMMCPClientTransport.supported():
            raise SAMValidationError(f"transport: must be one of {SAMMCPClientTransport.supported()}, not '{v}'.")
        return v

    @field_validator("endpointUrl")
    @classmethod
    def validate_endpoint_url(cls, v: str) -> str:
        """Validate the endpoint URL."""
        return validate_endpoint_url(v)

    @field_validator("headers")
    @classmethod
    def validate_headers(cls, v: Optional[dict[str, str]]) -> dict[str, str]:
        """Validate the custom HTTP headers."""
        v = v or {}
        if len(v) > MAX_HEADERS:
            raise SAMValidationError(f"headers: at most {MAX_HEADERS} headers are permitted.")
        for name, value in v.items():
            validate_header_name(name, "headers")
            if not isinstance(value, str) or len(value) > MAX_HEADER_VALUE_LENGTH or "\n" in value or "\r" in value:
                raise SAMValidationError(
                    f"headers: the value of '{name}' must be a single line of at most {MAX_HEADER_VALUE_LENGTH} characters."
                )
        return v

    @field_validator("authType")
    @classmethod
    def validate_auth_type(cls, v: str) -> str:
        """Validate the authentication type."""
        v = (v or SAMMCPClientAuthType.NONE.value).lower()
        if v not in SAMMCPClientAuthType.all():
            raise SAMValidationError(f"authType: must be one of {SAMMCPClientAuthType.all()}, not '{v}'.")
        return v

    @field_validator("apiKeyHeader")
    @classmethod
    def validate_api_key_header(cls, v: Optional[str]) -> str:
        """Validate the api key header name."""
        return validate_header_name(v or DEFAULT_API_KEY_HEADER, "apiKeyHeader")

    @field_validator("allowedTools", "allowedResources")
    @classmethod
    def validate_patterns(cls, v: Optional[list[str]]) -> list[str]:
        """Validate the glob patterns: non-empty strings, without duplicates."""
        patterns = []
        for pattern in v or []:
            if not isinstance(pattern, str) or not pattern.strip():
                raise SAMValidationError("allowedTools and allowedResources must contain non-empty strings.")
            if pattern.strip() not in patterns:
                patterns.append(pattern.strip())
        return patterns

    @model_validator(mode="after")
    def validate_credentials(self) -> "SAMMCPClientSpecConfig":
        """Require credentials unless authType is none, and forbid them if it is."""
        if self.authType == SAMMCPClientAuthType.NONE.value and self.credentials:
            raise SAMValidationError("credentials: must be empty when authType is none.")
        if self.authType != SAMMCPClientAuthType.NONE.value and not self.credentials:
            raise SAMValidationError(
                f"credentials: the name of a Smarter Secret is required when authType is {self.authType}."
            )
        return self


class SAMMCPClientSpec(AbstractSAMSpecBase):
    """Smarter API MCPClient Manifest MCPClient.spec."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    config: SAMMCPClientSpecConfig = Field(
        ..., description=f"{class_identifier}.config[object]. The configuration for the {MANIFEST_KIND}."
    )
