"""Constants for the Proxy app."""

import os

namespace = "proxy"

HERE = os.path.abspath(os.path.dirname(__file__))
BUILTIN_PROXY_PATH = os.path.join(HERE, "data", "proxy")
"""The built-in Proxy manifests, which ``manage.py add_builtin_proxies`` applies."""

DEFAULT_AUTH_HEADER = "Authorization"
DEFAULT_AUTH_SCHEME = "Bearer"
DEFAULT_TIMEOUT = 120
"""Seconds.

LLM responses, especially long completions, can be slow.
"""
MAX_TIMEOUT = 600

CREDENTIAL_HEADERS = (
    "authorization",
    "x-api-key",
    "x-goog-api-key",
    "api-key",
)
"""
The request headers in which callers may send their Smarter API key, in the order in which.

they are checked. Each is how a popular SDK sends its API key, so that callers can use the
provider's own SDK, with a Smarter API key:

- ``Authorization: Bearer <key>``: OpenAI, and OpenAI-compatible SDKs. ``Authorization: Token <key>``,
  as for the rest of the Smarter API, also works.
- ``x-api-key``: Anthropic.
- ``x-goog-api-key``: Google Gemini.
- ``api-key``: Azure OpenAI.

None of them is forwarded to the provider.
"""

HOP_BY_HOP_HEADERS = (
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "trailers",
    "transfer-encoding",
    "upgrade",
)
"""Headers that apply to one connection, and that a proxy must not forward.

See RFC 9110, section 7.6.1.
"""

DROPPED_REQUEST_HEADERS = (
    *HOP_BY_HOP_HEADERS,
    *CREDENTIAL_HEADERS,
    "host",
    "content-length",
    "cookie",
    "forwarded",
    "x-forwarded-for",
    "x-forwarded-host",
    "x-forwarded-proto",
    "x-forwarded-port",
    "x-real-ip",
    "x-csrftoken",
    "accept-encoding",
)
"""
The request headers that are not forwarded to the provider: hop-by-hop headers, the caller's.

credentials, Smarter's cookies, and the caller's address. ``accept-encoding`` is dropped so
that the provider's response is decoded before it is returned, which lets Smarter read its
token usage.
"""

DROPPED_RESPONSE_HEADERS = (
    *HOP_BY_HOP_HEADERS,
    "content-length",
    "content-encoding",
    "set-cookie",
    "alt-svc",
    "strict-transport-security",
)
"""The response headers that are not returned to the caller."""

RESERVED_HEADERS = tuple(sorted(set(DROPPED_REQUEST_HEADERS) - {"accept-encoding"}))
"""Headers that a Proxy manifest's ``spec.headers`` may not set."""

BUILTIN_ANNOTATION = "smarter.sh/proxy/builtin"
