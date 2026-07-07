"""Smarter API Manifest - MCPClient.spec."""

import os
from typing import ClassVar, Optional

from pydantic import Field, model_validator

from smarter.apps.mcpclient.manifest.models.mcpclient.const import MANIFEST_KIND
from smarter.apps.mcpclient.models import (
    MCPAuthType,
    MCPTransport,
)
from smarter.lib.manifest.models import AbstractSAMSpecBase

filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"
SMARTER_PLUGIN_MAX_SYSTEM_ROLE_LENGTH = 2048


class SAMMCPClientSpecConfig(AbstractSAMSpecBase):
    """Smarter API MCPClient Manifest MCPClient.spec.config."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER + ".configuration"

    # --- connection ---
    transport: MCPTransport = Field(
        ...,
        description="Transport mechanism used to reach the MCP server.",
    )
    endpoint_url: Optional[str] = Field(
        default="",
        description="Required for sse/http transports; omitted for stdio.",
    )
    command: Optional[str] = Field(
        default="",
        description="Executable + args for stdio transport, e.g. 'npx @scope/server'.",
    )
    config: Optional[dict] = Field(
        default_factory=dict,
        description="Transport-specific parameters: headers, env vars, timeout_s, retry_policy, etc.",
    )

    # --- auth ---
    auth_type: MCPAuthType = Field(
        default=MCPAuthType.NONE,
        description="Authentication mechanism used to connect to the MCP server.",
    )
    credentials: str = Field(
        ...,
        description=(
            f"{class_identifier}.credentials[str]. Name/slug of the Secret "
            "resource holding this client's auth credential."
        ),
    )

    # --- capability scope ---
    allowed_tools: Optional[list[str]] = Field(
        default_factory=list,
        description="Tool name allowlist exposed to the harness; empty = all tools the server advertises.",
    )
    allowed_resources: Optional[list[str]] = Field(
        default_factory=list,
        description="Resource URI patterns this client may access; empty = all.",
    )

    # --- lifecycle ---
    is_active: bool = Field(
        default=True,
        description="Whether this MCPClient should be considered for use.",
    )
    priority: int = Field(
        default=100,
        ge=0,
        description="Resolution order when multiple MCPClients could serve a request; lower runs first.",
    )

    # --- cross-field validation, mirrors the Django model's intended clean() logic ---
    @model_validator(mode="after")
    def validate_transport_target(self) -> "SAMMCPClientSpecConfig":
        if self.transport == MCPTransport.STDIO and not self.command:
            raise ValueError("command is required when transport=stdio")
        if self.transport in (MCPTransport.SSE, MCPTransport.HTTP) and not self.endpoint_url:
            raise ValueError(f"endpoint_url is required when transport={self.transport}")
        return self

    @model_validator(mode="after")
    def validate_credentials_required_for_auth(self) -> "SAMMCPClientSpecConfig":
        if self.auth_type == MCPAuthType.NONE and self.credentials:
            raise ValueError("credentials must be empty when auth_type=none")
        return self


class SAMMCPClientSpec(AbstractSAMSpecBase):
    """Smarter API MCPClient Manifest MCPClient.spec."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    config: SAMMCPClientSpecConfig = Field(
        ..., description=f"{class_identifier}.config[object]. The configuration for the {MANIFEST_KIND}."
    )
