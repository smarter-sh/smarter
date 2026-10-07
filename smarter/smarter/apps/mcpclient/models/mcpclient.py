"""
The MCPClient model.

An MCPClient connects Smarter to a remote `Model Context Protocol <https://modelcontextprotocol.io>`_
(MCP) server, whose tools LLMClients offer to the LLM.

.. note::

    **Experimental.** The MCPClient was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

import hashlib
from typing import Optional

from django.db import models

from smarter.apps.account.models import (
    MetaDataWithOwnershipModel,
)
from smarter.apps.mcpclient.manifest.models.mcpclient.const import (
    DEFAULT_API_KEY_HEADER,
    DEFAULT_CACHE_TTL,
    DEFAULT_PRIORITY,
    DEFAULT_TIMEOUT,
)
from smarter.apps.secret.models import Secret
from smarter.lib import json, logging
from smarter.lib.django.waffle.switches import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.MCPCLIENT_LOGGING])


class MCPTransport(models.TextChoices):
    """MCP Transport choice list.

    stdio is reserved, and not supported.
    """

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
    """
    A client of a remote MCP server.

    The connection, authentication and capability scope fields are set by the MCPClient
    manifest's ``spec.config``. The status fields record the result of the last connection
    to the MCP server, and are set by :func:`smarter.apps.mcpclient.tasks.refresh_mcpclient`
    and whenever the server's catalog is fetched.
    """

    # pylint: disable=C0115
    class Meta:
        verbose_name_plural = "MCPClients"
        unique_together = ("user_profile", "name")

    # --- connection ---
    transport = models.CharField(
        max_length=16, choices=MCPTransport.choices, default=MCPTransport.HTTP, blank=True, null=True
    )
    endpoint_url = models.URLField(
        max_length=2048,
        blank=True,
        null=True,
        help_text="The https URL of the MCP server's endpoint.",
    )
    command = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Reserved for the stdio transport, which is not supported.",
    )
    headers = models.JSONField(
        default=dict,
        blank=True,
        null=True,
        help_text="Non-secret HTTP headers to send to the MCP server.",
    )
    timeout = models.PositiveSmallIntegerField(
        default=DEFAULT_TIMEOUT,
        help_text="Seconds to wait for the MCP server to connect and respond.",
    )

    # --- auth ---
    auth_type = models.CharField(max_length=16, choices=MCPAuthType.choices, default=MCPAuthType.NONE)
    credentials = models.ForeignKey(
        Secret,
        on_delete=models.SET_NULL,
        help_text="The Secret containing the credential. Required unless auth_type is none.",
        blank=True,
        null=True,
    )
    api_key_header = models.CharField(
        max_length=64,
        default=DEFAULT_API_KEY_HEADER,
        help_text="The HTTP header that carries an api_key credential.",
    )

    # --- capability scope ---
    allowed_tools = models.JSONField(
        default=list,
        blank=True,
        null=True,
        help_text="Glob patterns of the tool names to offer the LLM; empty = all tools the server advertises.",
    )
    allowed_resources = models.JSONField(
        default=list,
        blank=True,
        null=True,
        help_text="Glob patterns of the resource URIs that the LLM may read; empty = none.",
    )
    include_instructions = models.BooleanField(
        default=True,
        help_text="Add the MCP server's instructions to the system prompt.",
    )
    cache_ttl = models.PositiveIntegerField(
        default=DEFAULT_CACHE_TTL,
        help_text="Seconds to cache the MCP server's tools, instructions and capabilities. 0 disables caching.",
    )

    # --- lifecycle ---
    is_active = models.BooleanField(default=True)
    status = models.CharField(
        max_length=16,
        choices=MCPConnectionStatus.choices,
        default=MCPConnectionStatus.UNCONFIGURED,
    )
    priority = models.PositiveSmallIntegerField(
        default=DEFAULT_PRIORITY,
        help_text="The order in which an LLMClient's MCPClients are offered to the LLM; lower runs first.",
    )

    # --- last connection ---
    protocol_version = models.CharField(
        max_length=16,
        blank=True,
        null=True,
        help_text="Negotiated MCP protocol version from the last successful handshake.",
    )
    server_name = models.CharField(
        max_length=255, blank=True, null=True, help_text="The name that the MCP server reported."
    )
    server_version = models.CharField(
        max_length=64, blank=True, null=True, help_text="The version that the MCP server reported."
    )
    tools = models.JSONField(
        default=list,
        blank=True,
        null=True,
        help_text="The names of the tools offered to the LLM, as of the last successful connection.",
    )
    last_connected_at = models.DateTimeField(
        blank=True, null=True, help_text="When Smarter last connected to the MCP server."
    )
    last_error = models.TextField(blank=True, null=True, help_text="The error of the last failed connection, if any.")

    CONNECTION_FIELDS = (
        "transport",
        "endpoint_url",
        "headers",
        "timeout",
        "auth_type",
        "credentials_id",
        "api_key_header",
        "allowed_tools",
        "allowed_resources",
    )
    """The fields that determine what the MCP server returns, and so its cached catalog."""

    @property
    def fingerprint(self) -> str:
        """
        A hash of the fields that determine the MCP server's catalog.

        The cached catalog is keyed by it, so that changing any of these fields invalidates
        the cache, while recording the status of a connection does not.

        :returns: A 16-character hexadecimal hash.
        :rtype: str
        """
        data = {field: getattr(self, field, None) for field in self.CONNECTION_FIELDS}
        return hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()[:16]

    @property
    def credential_name(self) -> Optional[str]:
        """The name of the credentials Secret, if any."""
        return self.credentials.name if self.credentials else None


__all__ = ["MCPClient", "MCPTransport", "MCPAuthType", "MCPConnectionStatus"]
