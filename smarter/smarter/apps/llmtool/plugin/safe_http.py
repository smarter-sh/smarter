"""
Safe HTTP requests to user-supplied URLs on the open web.

Plugins such as the SkillPlugin and the WebsearchPlugin make HTTP requests to URLs that
are supplied by manifest authors and, in the case of the WebsearchPlugin, by the LLM
itself. Such requests must not be able to reach the Smarter platform's own network, nor
exhaust its resources. This module provides a single, hardened request function for them.

**Protections:**

- **https only.** Plain http, and every other scheme, is rejected, unless the caller passes
  ``require_https=False``, as an ApiConnection does: its api may be served on plain http.
- **Public addresses only.** The host must resolve, and every address that it resolves to
  must be public. This prevents server-side request forgery (SSRF) against loopback,
  private, link-local (e.g. cloud instance metadata at 169.254.169.254), shared and
  reserved addresses. With ``permit_local_loopback``, loopback hosts are permitted in the
  local environment only (:func:`validate_destination_url`).
- **Standard port only.** Only the default https port, 443, is permitted, unless
  ``require_https=False``.
- **No credentials** in URLs.
- **Validated redirects.** Redirects are followed manually, up to a limit, and every hop is
  subject to the same validation, plus an optional caller-supplied policy, e.g. a domain
  allow list. A redirect to another origin drops ``Authorization``, ``Proxy-Authorization``
  and ``Cookie``.
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
from typing import Callable, Optional
from urllib.parse import urljoin, urlparse

import requests
from pydantic import JsonValue

from smarter.common.conf import smarter_settings
from smarter.common.const import SmarterEnvironments
from smarter.common.exceptions import SmarterValueError
from smarter.lib import json
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.typing import SmarterDictType

DEFAULT_TIMEOUT = 15
"""Seconds to wait for each request."""
DEFAULT_MAX_REDIRECTS = 3
DEFAULT_MAX_BYTES = 2_000_000
"""The default maximum size of a response body, in bytes."""
DEFAULT_USER_AGENT = "Smarter/1.0 (+https://smarter.sh)"
REDIRECT_STATUS_CODES = (301, 302, 303, 307, 308)
HTTPS_PORT = 443
HTTP_PORT = 80

CREDENTIAL_HEADERS = ("authorization", "proxy-authorization", "cookie")
"""
Request headers that are dropped when a redirect leads to another origin, as requests does for.

``Authorization``, so that a server can't redirect a caller's credentials to a host of its choosing.
"""


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

    def json(self) -> JsonValue:
        """
        The response body, parsed as JSON.

        :returns: The parsed body.
        :raises ValueError: If the body is not JSON in its declared character set, or in UTF-8.
        """
        encoding = self.charset or "utf-8"
        try:
            text = self.content.decode(encoding)
        except LookupError:
            # a charset that Python doesn't know, e.g. a typo in the server's Content-Type.
            text = self.content.decode("utf-8")
        parsed = json.loads(text)
        return parsed


def is_loopback_host(hostname: Optional[str]) -> bool:
    """
    Return whether a host name is the local machine: ``localhost``, a subdomain of it, or a loopback address.

    The local hosts are those of :attr:`SmarterValidator.LOCAL_HOSTS <smarter.lib.django.validators.SmarterValidator.LOCAL_HOSTS>`,
    any subdomain of ``localhost``, e.g. ``api.localhost``, and any loopback address, e.g.
    ``::1``. The name is not resolved, so this tells only what the name says.
    :func:`validate_public_url` refuses all of them. Callers that permit loopback hosts, e.g.
    the MCPClient in the local environment, use this to decide when to skip it.

    :param hostname: A host name or IP address, without a port, e.g. ``urlparse(url).hostname``.
    :returns: True if the host is the local machine.
    """
    if not hostname:
        return False
    host = hostname.lower().rstrip(".").strip("[]")
    local_hosts = {local_host.rsplit(":", 1)[0] for local_host in SmarterValidator.LOCAL_HOSTS}
    if host in local_hosts or host.endswith(".localhost"):
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def validate_public_url(url: str, *, require_https: bool = True) -> None:
    """
    Validate that a URL is https, on the standard port, without credentials, and that every address its host resolves to is public.

    :param url: The URL to validate.
    :param require_https: False also permits plain http, and any port. The host must still
        resolve to public addresses only. For an ApiConnection, whose api may be served on
        plain http or on its own port.
    :raises SafeHttpError: If the URL is not permitted.
    """
    hostname, port = permitted_host_and_port(url, require_https=require_https)
    require_public_addresses(hostname, port)


def permitted_host_and_port(url: str, *, require_https: bool = True) -> tuple[str, int]:
    """
    Check a URL's scheme, credentials and port, without resolving its host.

    :param url: The URL.
    :param require_https: False also permits plain http, and any port.
    :returns: The URL's host, and its port, or its scheme's default port.
    :raises SafeHttpError: If the URL is not permitted.
    """
    try:
        parsed = urlparse(url)
        port = parsed.port
    except ValueError as e:
        raise SafeHttpError(f"invalid url: {url}") from e
    if require_https:
        permitted_schemes: tuple[str, ...] = ("https",)
    else:
        permitted_schemes = ("http", "https")
    hostname = parsed.hostname
    if parsed.scheme not in permitted_schemes or not hostname:
        raise SafeHttpError(f"only {' and '.join(permitted_schemes)} urls are permitted: {url}")
    if parsed.username or parsed.password:
        raise SafeHttpError("urls must not contain credentials.")
    if require_https and port not in (None, HTTPS_PORT):
        raise SafeHttpError(f"only the standard https port is permitted: {url}")
    if port is not None:
        return hostname, port
    if parsed.scheme == "https":
        return hostname, HTTPS_PORT
    return hostname, HTTP_PORT


def require_public_addresses(hostname: str, port: int) -> None:
    """
    Resolve a host, and check that every address it resolves to is public.

    :param hostname: The host name.
    :param port: The port that will be connected to.
    :raises SafeHttpError: If the host can't be resolved, or any of its addresses is not public.
    """
    try:
        addresses = socket.getaddrinfo(hostname, port, proto=socket.IPPROTO_TCP)
    except (socket.gaierror, UnicodeError) as e:
        raise SafeHttpError(f"host could not be resolved: {hostname}") from e
    if not addresses:
        raise SafeHttpError(f"host could not be resolved: {hostname}")
    for address in addresses:
        # for IPv4 and IPv6 the sockaddr starts with the address as a str; typeshed also allows an int.
        host = str(address[4][0])
        ip = ipaddress.ip_address(host.split("%", 1)[0])
        if not ip.is_global:
            raise SafeHttpError(f"host must have a public address: {hostname}")


def validate_destination_url(url: str, *, require_https: bool = True) -> None:
    """
    Validate a URL that Smarter connects to for an account's resource, e.g. an MCPClient's server or an ApiConnection's api.

    In the local environment, a loopback host, e.g. ``http://localhost:9357/`` or
    ``https://127.0.0.1/``, is permitted, over http or https and on any port, so that a
    developer's resources can reach services that run on their machine, such as the platform's
    own api. Every other URL, and every URL in every other environment, must pass
    :func:`validate_public_url`. Loopback hosts are never permitted in a deployed environment,
    where they would let a manifest reach the services of the Smarter server itself.

    :param url: The URL.
    :param require_https: Passed to :func:`validate_public_url`.
    :raises SafeHttpError: If the URL is not permitted.
    """
    if smarter_settings.environment == SmarterEnvironments.LOCAL and is_loopback_url(url):
        return
    validate_public_url(url, require_https=require_https)


def is_loopback_url(url: str) -> bool:
    """
    Return whether a URL is http or https, to a loopback host.

    :param url: The URL.
    :returns: True if it is, False otherwise, including when it can't be parsed.
    """
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    return is_loopback_host(parsed.hostname)


def same_origin(first_url: str, second_url: str) -> bool:
    """
    Return whether two URLs have the same scheme, host and port.

    :param first_url: A URL.
    :param second_url: Another URL.
    :returns: True if a request to one could share credentials with the other.
    """
    first = urlparse(first_url)
    second = urlparse(second_url)
    same_scheme = first.scheme == second.scheme
    same_host = (first.hostname or "").lower() == (second.hostname or "").lower()
    same_port = first.port == second.port
    return same_scheme and same_host and same_port


def validate_request_url(url: str, *, require_https: bool, permit_local_loopback: bool) -> None:
    """
    Validate a URL that :func:`fetch` is about to request, the first or a redirect's.

    :param url: The URL.
    :param require_https: Passed to :func:`validate_public_url`.
    :param permit_local_loopback: True checks it with :func:`validate_destination_url`, which
        permits loopback hosts in the local environment.
    :raises SafeHttpError: If the URL is not permitted.
    """
    if permit_local_loopback:
        validate_destination_url(url, require_https=require_https)
        return
    validate_public_url(url, require_https=require_https)


def redirect_headers(headers: dict[str, str], from_url: str, to_url: str) -> dict[str, str]:
    """
    Return the headers to send to a redirect's URL.

    A redirect within an origin keeps them all. A redirect to another origin drops
    :data:`CREDENTIAL_HEADERS`, in a new dict, so the one that earlier requests were sent with is
    unchanged.

    :param headers: The headers of the request that was redirected.
    :param from_url: The URL that was redirected.
    :param to_url: The redirect's URL.
    :returns: The headers for the redirect's request.
    """
    if same_origin(from_url, to_url):
        return headers
    kept_headers: dict[str, str] = {}
    for name, value in headers.items():
        if name.lower() not in CREDENTIAL_HEADERS:
            kept_headers[name] = value
    return kept_headers


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
    require_https: bool = True,
    permit_local_loopback: bool = False,
) -> SafeResponse:
    """
    Make a safe HTTP request.

    Every URL, the first and each redirect's, is checked before it is requested, with
    :func:`validate_public_url`, or :func:`validate_destination_url` when
    ``permit_local_loopback``. A redirect to another origin (scheme, host and port) drops the
    caller's credential headers, :data:`CREDENTIAL_HEADERS`.

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
    :param require_https: False also permits plain http, and any port, to public addresses.
    :param permit_local_loopback: True permits loopback hosts in the local environment, as
        :func:`validate_destination_url` does.
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
        validate_request_url(url, require_https=require_https, permit_local_loopback=permit_local_loopback)
        status_code, response_headers, content = get_response(method, url, params, json_body, max_bytes, accept_status)
        location = response_headers.get("location")
        if status_code in REDIRECT_STATUS_CODES and location:
            redirects.append(url)
            redirect_url = urljoin(url, location)
            request_headers = redirect_headers(request_headers, url, redirect_url)
            url = redirect_url
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
