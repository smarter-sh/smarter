"""Smarter API MCPClient Manifest Constants."""

from smarter_types import SAMKinds

MANIFEST_KIND = SAMKinds.MCP_CLIENT.value

DEFAULT_TIMEOUT = 30
"""Default seconds to wait for an MCP server to connect and respond."""
MAX_TIMEOUT = 120
"""Maximum seconds to wait for an MCP server to connect and respond."""

DEFAULT_CACHE_TTL = 3600
"""Default seconds to cache an MCP server's catalog: its tools, instructions and capabilities.

One hour.
"""
MAX_CACHE_TTL = 86400
"""Maximum seconds to cache an MCP server's catalog."""

DEFAULT_PRIORITY = 100
"""Default resolution order of an MCPClient.

Lower runs first.
"""

DEFAULT_API_KEY_HEADER = "X-API-Key"
"""Default HTTP header that carries the credential of an MCPClient whose authType is api_key."""

MAX_HEADERS = 20
"""Maximum number of custom HTTP headers."""
MAX_HEADER_VALUE_LENGTH = 1024
"""Maximum length of a custom HTTP header value."""

RESERVED_HEADERS = frozenset(
    {
        "authorization",
        "connection",
        "content-length",
        "content-type",
        "cookie",
        "host",
        "keep-alive",
        "proxy-authorization",
        "te",
        "trailer",
        "transfer-encoding",
        "upgrade",
    }
)
"""
Headers that a manifest may not set.

Credentials belong in a Smarter Secret, via
credentials, and the rest are managed by the HTTP client and the MCP transport, as
are all headers that begin with ``mcp-``.
"""
