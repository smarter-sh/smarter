"""All models for the MCPClient app."""

from django.db import models

from smarter.apps.account.models import (
    MetaDataWithOwnershipModel,
)
from smarter.apps.secret.models import Secret
from smarter.lib import logging
from smarter.lib.django.waffle.switches import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.MCPCLIENT_LOGGING])


class MCPTransport(models.TextChoices):
    """MCP Transport choice list."""

    STDIO = "stdio", "Stdio (local subprocess)"
    SSE = "sse", "Server-Sent Events"
    HTTP = "http", "Streamable HTTP"


class MCPAuthType(models.TextChoices):
    """MCP Authentication Type choice list."""

    NONE = "none", "None"
    API_KEY = "api_key", "API Key"
    OAUTH2 = "oauth2", "OAuth 2.0"
    BEARER_TOKEN = "bearer_token", "Bearer Token"


class MCPConnectionStatus(models.TextChoices):
    """MCP Connection Status choice list."""

    UNCONFIGURED = "unconfigured", "Unconfigured"
    CONNECTED = "connected", "Connected"
    DISCONNECTED = "disconnected", "Disconnected"
    ERROR = "error", "Error"


class MCPClient(MetaDataWithOwnershipModel):
    """Implements the MCPClient API model."""

    # pylint: disable=C0115
    class Meta:
        verbose_name_plural = "MCPClients"
        unique_together = ("user_profile", "name")

    # --- connection ---
    transport = models.CharField(max_length=16, choices=MCPTransport.choices, blank=True, null=True)
    endpoint_url = models.URLField(
        blank=True,
        null=True,
        help_text="Required for sse/http transports; omitted for stdio.",
    )
    command = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Executable + args for stdio transport, e.g. 'npx @scope/server'.",
    )
    config = models.JSONField(
        default=dict,
        blank=True,
        null=True,
        help_text="Transport-specific params: headers, env vars, timeout_s, retry_policy, etc.",
    )

    # --- auth ---
    auth_type = models.CharField(max_length=16, choices=MCPAuthType.choices, default=MCPAuthType.NONE)
    credentials = models.ForeignKey(
        Secret, on_delete=models.deletion.CASCADE, help_text="auth credential", blank=True, null=True
    )

    # --- capability scope ---
    allowed_tools = models.JSONField(
        default=list,
        blank=True,
        null=True,
        help_text="Tool name allowlist exposed to the harness; empty = all tools the server advertises.",
    )
    allowed_resources = models.JSONField(
        default=list,
        blank=True,
        null=True,
        help_text="Resource URI patterns this client may access; empty = all.",
    )

    # --- lifecycle ---
    is_active = models.BooleanField(default=True)
    status = models.CharField(
        max_length=16,
        choices=MCPConnectionStatus.choices,
        default=MCPConnectionStatus.UNCONFIGURED,
    )
    priority = models.PositiveSmallIntegerField(
        default=100,
        help_text="Resolution order when multiple MCPClients could serve a request; lower runs first.",
    )

    # --- versioning / provenance ---
    protocol_version = models.CharField(
        max_length=16,
        blank=True,
        null=True,
        help_text="Negotiated MCP protocol version from the last successful handshake.",
    )


__all__ = ["MCPClient", "MCPTransport", "MCPAuthType", "MCPConnectionStatus"]
