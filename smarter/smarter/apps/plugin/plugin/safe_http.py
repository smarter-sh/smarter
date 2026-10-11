"""
Safe HTTP requests to user-supplied URLs on the open web.

Plugins such as the SkillPlugin and the WebsearchPlugin make HTTP requests to URLs that
are supplied by manifest authors and, in the case of the WebsearchPlugin, by the LLM
itself. Such requests must not be able to reach the Smarter platform's own network, nor
exhaust its resources. This module provides a single, hardened request function for them.

**Protections:**

- **https only.** Plain http, and every other scheme, is rejected.
- **Public addresses only.** The host must resolve, and every address that it resolves to
  must be public. This prevents server-side request forgery (SSRF) against loopback,
  private, link-local (e.g. cloud instance metadata at 169.254.169.254), shared and
  reserved addresses.
- **Standard port only.** Only the default https port, 443, is permitted.
- **No credentials** in URLs.
- **Validated redirects.** Redirects are followed manually, up to a limit, and every hop is
  subject to the same validation, plus an optional caller-supplied policy, e.g. a domain
  allow list.
- **Bounded responses.** Responses are streamed, and abandoned once they exceed a size limit.
- **Timeouts** on every request.

.. warning::

    Host names are resolved and validated immediately before each request, which leaves a
    small window for DNS rebinding. Deployments that require stronger guarantees should
    also route plugin traffic through an egress proxy that enforces the same policy.

.. note::

    **Experimental.** This module was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

import ipaddress
import socket
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from urllib.parse import urljoin, urlparse

import requests
from pydantic import JsonValue

from smarter.common.exceptions import SmarterValueError
from smarter.lib.typing import SmarterDictType

DEFAULT_TIMEOUT = 15
"""Seconds to wait for each request."""
DEFAULT_MAX_REDIRECTS = 3
DEFAULT_MAX_BYTES = 2_000_000
"""The default maximum size of a response body, in bytes."""
DEFAULT_USER_AGENT = "Smarter/1.0 (+https://smarter.sh)"
REDIRECT_STATUS_CODES = (301, 302, 303, 307, 308)
HTTPS_PORT = 443


class SafeHttpError(SmarterValueError):
    """
    Raised when a URL is not permitted, or a request to it fails.

    :ivar status_code: The HTTP status code, if the server responded with an unexpected status.
    """

    def __init__(self, message: str = "", status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


@dataclass
class SafeResponse:
    """
    The response to a safe HTTP request.

    :ivar url: The final URL, after any redirects.
    :ivar status_code: The HTTP status code.
    :ivar headers: The response headers, with lower case names.
    :ivar content: The response body.
    :ivar redirects: The URLs that were redirected from, in order.
    """

    url: str
    status_code: int
    headers: dict[str, str]
    content: bytes
    redirects: list[str] = field(default_factory=list)

    @property
    def content_type(self) -> str:
        """The media type of the response, without parameters, e.g. ``text/html``."""
        return self.headers.get("content-type", "").split(";", 1)[0].strip().lower()

    @property
    def charset(self) -> Optional[str]:
        """The character set declared by the Content-Type header, if any."""
        for parameter in self.headers.get("content-type", "").split(";")[1:]:
            key, _, value = parameter.strip().partition("=")
            if key.lower() == "charset" and value:
                return value.strip("\"'")
        return None


def validate_public_url(url: str) -> None:
    """
    Validate that a URL is https, on the standard port, without credentials, and that every address its host resolves to is public.

    :param url: The URL to validate.
    :raises SafeHttpError: If the URL is not permitted.
    """
    try:
        parsed = urlparse(url)
        port = parsed.port
    except ValueError as e:
        raise SafeHttpError(f"invalid url: {url}") from e
    if parsed.scheme != "https" or not parsed.hostname:
        raise SafeHttpError(f"only https urls are permitted: {url}")
    if parsed.username or parsed.password:
        raise SafeHttpError("urls must not contain credentials.")
    if port not in (None, HTTPS_PORT):
        raise SafeHttpError(f"only the standard https port is permitted: {url}")
    try:
        addresses = socket.getaddrinfo(parsed.hostname, HTTPS_PORT, proto=socket.IPPROTO_TCP)
    except (socket.gaierror, UnicodeError) as e:
        raise SafeHttpError(f"host could not be resolved: {parsed.hostname}") from e
    if not addresses:
        raise SafeHttpError(f"host could not be resolved: {parsed.hostname}")
    for address in addresses:
        ip = ipaddress.ip_address(address[4][0].split("%", 1)[0])
        if not ip.is_global:
            raise SafeHttpError(f"host must have a public address: {parsed.hostname}")


# pylint: disable=too-many-arguments,too-many-locals
def fetch(
    url: str,
    *,
    method: str = "GET",
    headers: Optional[dict[str, str]] = None,
    params: Optional[SmarterDictType] = None,
    json_body: Optional[JsonValue] = None,
    timeout: float = DEFAULT_TIMEOUT,
    max_bytes: int = DEFAULT_MAX_BYTES,
    max_redirects: int = DEFAULT_MAX_REDIRECTS,
    redirect_policy: Optional[Callable[[str], None]] = None,
    accept_status: tuple[int, ...] = (200,),
) -> SafeResponse:
    """
    Make a safe HTTP request.

    :param url: The https URL to request.
    :param method: The HTTP method.
    :param headers: Additional request headers. A User-Agent is added if absent.
    :param params: URL query string parameters.
    :param json_body: A JSON request body.
    :param timeout: Seconds to wait for each request.
    :param max_bytes: The maximum size of the response body.
    :param max_redirects: The maximum number of redirects to follow.
    :param redirect_policy: Called with each redirect URL. It raises to refuse the redirect.
    :param accept_status: The HTTP status codes that constitute success.
    :return: The response.
    :raises SafeHttpError: If a URL is not permitted, a request fails or times out, the
        response status is not accepted, or the response is too large.

    **Example:**

    .. code-block:: python

        response = fetch("https://example.com/", max_bytes=100_000)
        response.content_type  # 'text/html'

    .. note::

        This function is deliberately not cached with ``@cache_results``, and must stay that
        way. Cache the expensive call that is made with it instead, in its caller, keyed on
        the caller's own parameters and with the caller's TTL, e.g.
        ``ImageSearchPlugin.brave_images()``.

        A brief experiment decorated its request with ``@cache_results(timeout=PluginCacheTtl.DEFAULT)``,
        to cache every plugin's remote calls in one place. Because this is the transport that
        every plugin shares, the cache sat beneath each plugin's own, and silently overrode it:

        - a manifest's ``cacheTtl: 0`` no longer disabled caching, and a plugin's longer or
          shorter TTL was masked by the transport's ten minutes;
        - re-applying a remote SkillPlugin served the old skill, instead of retrieving the
          latest version;
        - each hop of a redirect was replayed from the cache, so a redirect loop was no longer
          requested, and detected, as it happened;
        - HEAD requests that validate image urls were answered from the cache, instead of
          confirming that each url is still available.
    """
    request_headers = {"User-Agent": DEFAULT_USER_AGENT, **(headers or {})}

    def get_response(
        method: str,
        url: str,
        params: Optional[SmarterDictType],
        json_body: Optional[JsonValue],
        max_bytes: int,
        accept_status: tuple[int, ...],
    ) -> tuple[int, dict[str, str], bytes]:
        try:
            response = requests.request(
                method,
                url,
                headers=request_headers,
                params=params,
                json=json_body,
                timeout=timeout,
                allow_redirects=False,
                stream=True,
            )
        except requests.exceptions.RequestException as e:
            raise SafeHttpError(f"request to {urlparse(url).netloc} failed: {type(e).__name__}") from e
        try:
            response_headers = {str(key).lower(): str(value) for key, value in (response.headers or {}).items()}
            if response.status_code in REDIRECT_STATUS_CODES and response_headers.get("location"):
                return response.status_code, response_headers, b""
            if response.status_code not in accept_status:
                raise SafeHttpError(
                    f"{urlparse(url).netloc} responded with HTTP {response.status_code}",
                    status_code=response.status_code,
                )
            content = b""
            for chunk in response.iter_content(chunk_size=65536):
                content += chunk
                if len(content) > max_bytes:
                    raise SafeHttpError(f"the response from {url} exceeds the maximum size of {max_bytes} bytes.")
            return response.status_code, response_headers, content
        finally:
            response.close()

    redirects: list[str] = []
    for _ in range(max_redirects + 1):
        # validated before every request, including each redirect, since a host's addresses can change.
        validate_public_url(url)
        status_code, response_headers, content = get_response(method, url, params, json_body, max_bytes, accept_status)
        location = response_headers.get("location")
        if status_code in REDIRECT_STATUS_CODES and location:
            redirects.append(url)
            url = urljoin(url, location)
            if status_code in (301, 302, 303):
                method, json_body = "GET", None
            params = None
            if redirect_policy:
                redirect_policy(url)
            continue
        return SafeResponse(
            url=url,
            status_code=status_code,
            headers=response_headers,
            content=content,
            redirects=redirects,
        )
    raise SafeHttpError(f"{url} redirected more than {max_redirects} times.")
