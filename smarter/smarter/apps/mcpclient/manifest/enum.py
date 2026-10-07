"""Smarter API MCPClient Manifest - enumerated datatypes."""

from smarter.lib.manifest.enum import SmarterEnumAbstract


class SAMMCPClientTransport(SmarterEnumAbstract):
    """
    The transport with which an MCPClient reaches its MCP server.

    - ``http``: Streamable HTTP, the MCP transport for remote servers.
    - ``sse``: the legacy HTTP+SSE transport, which some remote servers still use.
    - ``stdio``: a local subprocess. Reserved. Smarter does not run MCP servers as
      subprocesses, so manifests with this transport are rejected.
    """

    HTTP = "http"
    SSE = "sse"
    STDIO = "stdio"

    @classmethod
    def supported(cls) -> list[str]:
        """Return the transports that Smarter supports."""
        return [cls.HTTP.value, cls.SSE.value]


class SAMMCPClientAuthType(SmarterEnumAbstract):
    """
    How an MCPClient authenticates with its MCP server.

    - ``none``: no authentication.
    - ``api_key``: the credential is sent in the ``apiKeyHeader`` HTTP header.
    - ``bearer_token``: the credential is sent as ``Authorization: Bearer <credential>``.
    - ``oauth2``: an OAuth access token, sent as ``Authorization: Bearer <token>``.
      Smarter does not yet perform the OAuth authorization flow, nor refresh tokens,
      so the token must be obtained elsewhere and stored in a Smarter Secret.
    """

    NONE = "none"
    API_KEY = "api_key"
    BEARER_TOKEN = "bearer_token"
    OAUTH2 = "oauth2"
