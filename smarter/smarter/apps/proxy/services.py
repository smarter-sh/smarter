# pylint: disable=R0913,R0917,R0914
"""
The Proxy passthrough: forward a caller's request to an LLM provider's API, with the provider's API key.

:func:`resolve_proxy` finds the Proxy that a caller means by its name, and :class:`ProxyForwarder`
forwards the caller's request:

1. It checks that the Proxy is active, that the path is one of its ``allowedPaths``, and that
   no budget forbids the charge.
2. It removes the caller's credentials, cookies and hop-by-hop headers, adds the Proxy's
   ``headers``, and adds the provider's API key from the Proxy's Secret.
3. It sends the request to the provider, and returns the provider's response as it is:
   status, headers and body. Server-sent event streams, e.g. ``"stream": true``, are streamed.
4. It reads the token usage from the response, and charges it to the Proxy, the caller, and the
   caller's account.

The HTTP client is `httpx <https://www.python-httpx.org/>`_. Tests replace its transport with
:func:`configure_transport`, and the forwarder refuses to call a real provider from the unit tests.

Security
--------

- The provider's API key is read from its Secret for each request, and is never logged or
  returned. The caller's Smarter API key is never forwarded.
- A Proxy's base URL may not be a private, loopback or link-local address, so that a Proxy (or
  a Provider) cannot be used to reach Smarter's internal network, e.g. a cloud metadata
  service. Only Proxies that a superuser owns may.
"""

import ipaddress
import socket
import sys
import time
from dataclasses import dataclass
from typing import Any, Callable, Iterator, Mapping, Optional

import httpx
from django.db import models
from django.http import HttpResponse, StreamingHttpResponse
from django.http.response import HttpResponseBase

from smarter.apps.account.models import UserProfile
from smarter.apps.account.models.budget import (
    SmarterChargeAuthorizationFailed,
    charge_authorization,
)
from smarter.apps.account.models.charge import ChargeTypes
from smarter.lib import json, logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .const import DROPPED_REQUEST_HEADERS, DROPPED_RESPONSE_HEADERS
from .exceptions import (
    ProxyBudgetExceeded,
    ProxyConfigurationError,
    ProxyError,
    ProxyInactive,
    ProxyNotFound,
    ProxyPathNotAllowed,
    ProxyUpstreamError,
    ProxyUpstreamTimeout,
)
from .models import Proxy
from .signals import proxy_request_completed, proxy_request_failed

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.PROXY_LOGGING])
logger_prefix = logging.formatted_text(__name__)

CONNECT_TIMEOUT = 10.0
"""Seconds to wait for a connection to the provider.

Its response may take up to the Proxy's timeout.
"""
MAX_SSE_LINE = 1024 * 1024
"""Bytes.

Longer server-sent event lines are not read for token usage.
"""
PROXY_RESPONSE_HEADER = "X-Smarter-Proxy"
"""A response header with the name of the Proxy that forwarded the request."""

_transport_factory: Optional[Callable[[], httpx.BaseTransport]] = None


def configure_transport(factory: Optional[Callable[[], httpx.BaseTransport]]) -> None:
    """
    Replace the HTTP transport to the providers, e.g. with an :class:`httpx.MockTransport` in tests.

    :param factory: Returns the transport for each request, or ``None`` to restore the default.
    """
    global _transport_factory  # pylint: disable=global-statement
    _transport_factory = factory


def get_transport() -> Optional[httpx.BaseTransport]:
    """
    The configured transport, or ``None`` for httpx's default, which calls the provider.

    :raises ProxyConfigurationError: in the unit tests, if no transport is configured, so that
        tests never call a real provider with a real API key.
    """
    if _transport_factory is not None:
        return _transport_factory()
    if "test" in sys.argv:
        raise ProxyConfigurationError(
            "Refusing to call a real LLM provider from the unit tests. Use configure_transport()."
        )
    return None


def host_addresses(host: str) -> list[str]:
    """The IP addresses of a host name.

    Tests patch it, so that they do not depend on DNS.
    """
    # sockaddr[0] is the address for AF_INET and AF_INET6, which are the only families that a host name resolves to.
    return sorted({str(info[4][0]) for info in socket.getaddrinfo(host, None)})


def is_public_address(address: str) -> bool:
    """Whether an IP address is on the public internet: not private, loopback, link-local, or reserved."""
    ip = ipaddress.ip_address(address.split("%")[0])
    return ip.is_global and not ip.is_multicast


def check_upstream_host(proxy: Proxy) -> None:
    """
    Refuse a base URL whose host is not on the public internet, unless a superuser owns the Proxy.

    :raises ProxyConfigurationError: if the host cannot be resolved, or is not public.
    """
    host = proxy.upstream_host
    if not host:
        raise ProxyConfigurationError(f"Proxy {proxy.name} has no base URL, and neither does its provider.")
    if proxy.user_profile.user.is_superuser:
        return
    try:
        addresses = host_addresses(host)
    except (socket.gaierror, UnicodeError) as e:
        raise ProxyUpstreamError(f"Proxy {proxy.name}: the provider's host {host} cannot be resolved: {e}") from e
    if not addresses or not all(is_public_address(address) for address in addresses):
        raise ProxyConfigurationError(
            f"Proxy {proxy.name}: the provider's host {host} is not on the public internet. "
            "Only a superuser's proxies may forward to private addresses."
        )


def resolve_proxy(name: str, user_profile: UserProfile) -> Proxy:
    """
    The Proxy that a caller means by ``name``: of those that the caller may read, their own, else.

    their account's, else the built-in one, which the Smarter admin owns. Ties go to the most
    recently updated.

    :raises ProxyNotFound: if the caller may read no Proxy of that name.
    """
    # pylint: disable=C0415
    from smarter.apps.account.utils import smarter_cached_objects

    matches = list(
        Proxy.objects.with_read_permission_for(user_profile.user)  # type: ignore[attr-defined]
        .filter(name=name)
        .select_related(
            "provider",
            "provider__api_key",
            "api_key_secret",
            "user_profile__user",
            "user_profile__account",
        )
    )
    if not matches:
        raise ProxyNotFound(f"Proxy {name} does not exist, or is not shared with you.")
    smarter_account_id = smarter_cached_objects.smarter_account.pk

    def precedence(proxy: Proxy) -> tuple[int, float]:
        if proxy.user_profile_id == user_profile.pk:  # type: ignore[attr-defined]
            rank = 0
        elif proxy.user_profile.account_id == user_profile.account_id:  # type: ignore[attr-defined]
            rank = 1
        elif proxy.user_profile.account_id == smarter_account_id:  # type: ignore[attr-defined]
            rank = 2
        else:
            rank = 3
        return rank, -(proxy.updated_at.timestamp() if proxy.updated_at else 0)

    return min(matches, key=precedence)


def proxies_for(user_profile: UserProfile) -> models.QuerySet[Proxy]:
    """The Proxies that a caller may read."""
    return Proxy.objects.with_read_permission_for(user_profile.user).select_related("provider")  # type: ignore[attr-defined]


###############################################################################
# Token usage
###############################################################################
@dataclass
class Usage:
    """The tokens of one request, as the provider reports them."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def merge(self, other: Optional["Usage"]) -> "Usage":
        """
        Combine the usage of two events of one stream.

        Providers report cumulative counts, e.g. Anthropic's message_start has the input
        tokens and message_delta the output tokens, and Gemini repeats its usage in every chunk,
        so the larger of each count is kept.
        """
        if other is None:
            return self
        prompt = max(self.prompt_tokens, other.prompt_tokens)
        completion = max(self.completion_tokens, other.completion_tokens)
        return Usage(prompt, completion, max(self.total_tokens, other.total_tokens, prompt + completion))

    def __bool__(self) -> bool:
        return bool(self.prompt_tokens or self.completion_tokens or self.total_tokens)


def _int(data: Mapping, *keys: str) -> int:
    """The sum of the integer values of keys of data, ignoring those that are missing or not integers."""
    return sum(value for key in keys if isinstance(value := data.get(key), int) and not isinstance(value, bool))


def _usage(data: Any) -> Optional[Usage]:
    """Usage from a usage object: OpenAI's, Anthropic's, or Cohere's."""
    if not isinstance(data, dict):
        return None
    for nested in ("billed_units", "tokens"):
        # Cohere: {"billed_units": {"input_tokens": ..., "output_tokens": ...}}
        if isinstance(data.get(nested), dict):
            return _usage(data[nested])
    prompt = _int(data, "prompt_tokens", "input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
    completion = _int(data, "completion_tokens", "output_tokens")
    total = _int(data, "total_tokens") or prompt + completion
    usage = Usage(prompt, completion, total)
    return usage if usage else None


def extract_usage(data: Any) -> Optional[Usage]:
    """
    The token usage of a response body, or of one event of a stream, as the provider reports it.

    - OpenAI, and OpenAI-compatible APIs: ``usage.prompt_tokens`` and ``usage.completion_tokens``, or, for
      the Responses API, ``usage.input_tokens`` and ``usage.output_tokens``, also in ``response.usage``.
    - Anthropic: ``usage.input_tokens`` and ``usage.output_tokens``, also in ``message.usage`` of a
      stream's message_start event.
    - Google Gemini: ``usageMetadata.promptTokenCount`` and ``usageMetadata.candidatesTokenCount``.
    - Cohere: ``meta.billed_units`` (v1), or ``usage.billed_units`` (v2).

    :returns: The usage, or ``None`` if the body reports none.
    """
    if not isinstance(data, dict):
        return None
    usage = Usage()
    for parent, key in (("", "usage"), ("message", "usage"), ("response", "usage"), ("meta", "billed_units")):
        container = data.get(parent) if parent else data
        if isinstance(container, dict):
            usage = usage.merge(_usage(container.get(key)))
    gemini = data.get("usageMetadata")
    if isinstance(gemini, dict):
        prompt = _int(gemini, "promptTokenCount")
        completion = _int(gemini, "candidatesTokenCount", "thoughtsTokenCount")
        total = _int(gemini, "totalTokenCount") or prompt + completion
        usage = usage.merge(Usage(prompt, completion, total))
    return usage if usage else None


class SSEUsageReader:
    """Reads the token usage of a server-sent event stream, as it passes through, from its ``data:`` lines."""

    def __init__(self):
        self.usage = Usage()
        self._buffer = b""

    def feed(self, chunk: bytes) -> None:
        """Read the complete lines of a chunk, and keep the rest for the next one."""
        self._buffer += chunk
        *lines, self._buffer = self._buffer.split(b"\n")
        if len(self._buffer) > MAX_SSE_LINE:
            self._buffer = b""
        for line in lines:
            self._read_line(line)

    def close(self) -> None:
        """Read the last line, if the stream did not end with a line break."""
        self._read_line(self._buffer)
        self._buffer = b""

    def _read_line(self, line: bytes) -> None:
        line = line.strip()
        if not line.startswith(b"data:"):
            return
        payload = line[5:].strip()
        if not payload or payload == b"[DONE]":
            return
        try:
            self.usage = self.usage.merge(extract_usage(json.loads(payload)))
        except (ValueError, TypeError):
            return


###############################################################################
# Charges
###############################################################################
def record_charges(proxy: Proxy, user_profile: UserProfile, usage: Usage) -> None:
    """
    Charge a request's tokens to the Proxy, the caller, and the caller's account.

    The charges are created by a Celery task. A failure is logged, and never fails the request.
    """
    # pylint: disable=C0415
    from smarter.apps.account.tasks import create_charge

    for resource_locator in (proxy.record_locator, user_profile.record_locator, user_profile.account.record_locator):
        try:
            create_charge.delay(
                resource_locator=resource_locator,
                charge_type=ChargeTypes.PROMPT_COMPLETION.value,
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                total_tokens=usage.total_tokens,
            )
        # pylint: disable=broad-except
        except Exception as e:
            logger.error("%s.record_charges() failed to charge %s: %s", logger_prefix, resource_locator, e)


def check_budget(proxy: Proxy, user_profile: UserProfile) -> None:
    """
    Refuse the request if a budget's resource lock forbids charges to the Proxy, the caller, or their account.

    :raises ProxyBudgetExceeded: if one does.
    """
    try:
        charge_authorization(
            [proxy.record_locator, user_profile.record_locator, user_profile.account.record_locator],
            ChargeTypes.PROMPT_COMPLETION.value,
        )
    except SmarterChargeAuthorizationFailed as e:
        raise ProxyBudgetExceeded(f"Proxy {proxy.name}: a budget forbids more charges. {e.message}") from e


###############################################################################
# Forwarding
###############################################################################
def forwarded_request_headers(proxy: Proxy, headers: Mapping[str, str], api_key: str) -> dict[str, str]:
    """
    The headers to send to the provider.

    The caller's, without those in :data:`~smarter.apps.proxy.const.DROPPED_REQUEST_HEADERS` and
    without the Proxy's auth header; then the Proxy's ``headers``; then the provider's API key.
    """
    replaced = {name.lower() for name in proxy.headers or {}} | {proxy.auth_header.lower()}
    retval = {
        name: value
        for name, value in headers.items()
        if name.lower() not in DROPPED_REQUEST_HEADERS and name.lower() not in replaced
    }
    retval.update(proxy.headers or {})
    retval[proxy.auth_header] = proxy.auth_header_value(api_key)
    return retval


def returned_response_headers(proxy: Proxy, headers: httpx.Headers) -> list[tuple[str, str]]:
    """The provider's response headers to return to the caller, and the name of the Proxy."""
    retval = [(name, value) for name, value in headers.multi_items() if name.lower() not in DROPPED_RESPONSE_HEADERS]
    retval.append((PROXY_RESPONSE_HEADER, proxy.name))
    return retval


def _set_headers(response: HttpResponseBase, headers: list[tuple[str, str]]) -> None:
    for name, value in headers:
        if name.lower() in response.headers:
            response.headers[name] = f"{response.headers[name]}, {value}"
        else:
            response.headers[name] = value


class ProxyForwarder:
    """
    Forward one caller's request through one Proxy.

    :param proxy: The Proxy, e.g. from :func:`resolve_proxy`.
    :param user_profile: The caller, who is charged for the request.
    """

    def __init__(self, proxy: Proxy, user_profile: UserProfile):
        self.proxy = proxy
        self.user_profile = user_profile

    def api_key(self) -> str:
        """
        The provider's API key, from the Proxy's Secret.

        :raises ProxyConfigurationError: if the Proxy has no Secret, or it is expired or empty.
        """
        secret = self.proxy.secret
        if secret is None:
            raise ProxyConfigurationError(
                f"Proxy {self.proxy.name} has no API key: set its spec.apiKey, or its provider's API key."
            )
        if not self.proxy.may_use_secret(secret):
            raise ProxyConfigurationError(
                f"Proxy {self.proxy.name} may not use the API key Secret {secret.name}, which belongs to another "
                "account. Set its spec.apiKey to a Secret of your own."
            )
        if secret.is_expired():
            raise ProxyConfigurationError(f"Proxy {self.proxy.name}: its API key Secret {secret.name} has expired.")
        try:
            value = secret.get_secret(update_last_accessed=False)
        # pylint: disable=broad-except
        except Exception as e:
            raise ProxyConfigurationError(
                f"Proxy {self.proxy.name}: its API key Secret {secret.name} cannot be read."
            ) from e
        if not value:
            raise ProxyConfigurationError(f"Proxy {self.proxy.name}: its API key Secret {secret.name} is empty.")
        return value

    def check(self, path: str) -> str:
        """
        Check that the request may be forwarded, and return the provider's URL of the path.

        :raises ProxyError: if it may not.
        """
        proxy = self.proxy
        if not proxy.is_active:
            raise ProxyInactive(f"Proxy {proxy.name} is inactive.")
        if not proxy.is_path_allowed(path):
            allowed = ", ".join(proxy.allowed_paths or [])
            raise ProxyPathNotAllowed(f"Proxy {proxy.name} does not allow the path '{path}'. Allowed: {allowed}.")
        url = proxy.upstream_url(path)
        if not url or not proxy.upstream_base_url:
            raise ProxyConfigurationError(f"Proxy {proxy.name} has no base URL, and neither does its provider.")
        check_upstream_host(proxy)
        check_budget(proxy, self.user_profile)
        return url

    def forward(
        self, method: str, path: str, query_string: str, headers: Mapping[str, str], body: bytes
    ) -> HttpResponseBase:
        """
        Forward a request to the provider, and return its response.

        :param method: e.g. POST.
        :param path: The path, relative to the Proxy's base URL, e.g. chat/completions.
        :param query_string: The request's query string, which is forwarded as it is.
        :param headers: The request's headers.
        :param body: The request's body, which is forwarded as it is.
        :raises ProxyError: if the request is refused, or the provider cannot be reached. A
            provider's error response is not an exception: it is returned as it is.
        """
        started = time.monotonic()
        try:
            url = self.check(path)
            if query_string:
                url = f"{url}?{query_string}"
            request_headers = forwarded_request_headers(self.proxy, headers, self.api_key())
            client = httpx.Client(
                transport=get_transport(),
                timeout=httpx.Timeout(float(self.proxy.timeout), connect=CONNECT_TIMEOUT),
                follow_redirects=False,
            )
        except ProxyError as e:
            self._failed(method, path, e, started)
            raise
        try:
            upstream = client.send(
                client.build_request(method, url, headers=request_headers, content=body or None), stream=True
            )
        except httpx.TimeoutException as e:
            client.close()
            error = ProxyUpstreamTimeout(f"Proxy {self.proxy.name}: the provider did not respond in time: {e}")
            self._failed(method, path, error, started)
            raise error from e
        except httpx.HTTPError as e:
            client.close()
            error = ProxyUpstreamError(f"Proxy {self.proxy.name}: the provider cannot be reached: {e}")
            self._failed(method, path, error, started)
            raise error from e

        headers_out = returned_response_headers(self.proxy, upstream.headers)
        if upstream.headers.get("content-type", "").startswith("text/event-stream"):
            response: HttpResponseBase = StreamingHttpResponse(
                self._stream(client, upstream, method, path, started), status=upstream.status_code
            )
        else:
            try:
                content = upstream.read()
            except httpx.HTTPError as e:
                error = ProxyUpstreamError(f"Proxy {self.proxy.name}: the provider's response was interrupted: {e}")
                self._failed(method, path, error, started)
                raise error from e
            finally:
                upstream.close()
                client.close()
            usage = None
            if "json" in upstream.headers.get("content-type", ""):
                try:
                    usage = extract_usage(json.loads(content))
                except (ValueError, TypeError):
                    usage = None
            self._completed(method, path, upstream.status_code, usage, started)
            response = HttpResponse(content, status=upstream.status_code)
        # Django's default content type is replaced by the provider's.
        del response.headers["Content-Type"]
        _set_headers(response, headers_out)
        return response

    def _stream(
        self, client: httpx.Client, upstream: httpx.Response, method: str, path: str, started: float
    ) -> Iterator[bytes]:
        """Return the provider's event stream as it arrives, and charge its usage when it ends."""
        reader = SSEUsageReader()
        try:
            for chunk in upstream.iter_bytes():
                reader.feed(chunk)
                yield chunk
        except httpx.HTTPError as e:
            logger.warning("%s Proxy %s: the provider's stream was interrupted: %s", logger_prefix, self.proxy.name, e)
        finally:
            upstream.close()
            client.close()
            reader.close()
            self._completed(method, path, upstream.status_code, reader.usage or None, started)

    def _completed(self, method: str, path: str, status: int, usage: Optional[Usage], started: float) -> None:
        elapsed = time.monotonic() - started
        logger.info(
            "%s Proxy %s: %s %s -> %s in %.2fs, usage %s, for %s",
            logger_prefix,
            self.proxy.name,
            method,
            path,
            status,
            elapsed,
            usage,
            self.user_profile,
        )
        if usage:
            record_charges(self.proxy, self.user_profile, usage)
        proxy_request_completed.send(
            sender=self.__class__,
            proxy=self.proxy,
            user_profile=self.user_profile,
            method=method,
            path=path,
            status=status,
            usage=usage,
            elapsed=elapsed,
        )

    def _failed(self, method: str, path: str, error: ProxyError, started: float) -> None:
        logger.warning(
            "%s Proxy %s: %s %s refused: %s (%s)", logger_prefix, self.proxy.name, method, path, error.code, error
        )
        proxy_request_failed.send(
            sender=self.__class__,
            proxy=self.proxy,
            user_profile=self.user_profile,
            method=method,
            path=path,
            error=error,
            elapsed=time.monotonic() - started,
        )


__all__ = [
    "ProxyForwarder",
    "SSEUsageReader",
    "Usage",
    "check_budget",
    "check_upstream_host",
    "configure_transport",
    "extract_usage",
    "forwarded_request_headers",
    "get_transport",
    "host_addresses",
    "is_public_address",
    "proxies_for",
    "record_charges",
    "resolve_proxy",
    "returned_response_headers",
]
