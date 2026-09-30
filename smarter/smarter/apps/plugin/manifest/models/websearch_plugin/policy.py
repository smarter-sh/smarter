"""
Domain policy for the WebsearchPlugin: which websites it may search and read.

A WebsearchPlugin manifest may restrict the plugin to an allow list of domains, e.g. a
company's own documentation, and may exclude a block list of domains. The LLM may narrow
this policy further, per tool call, but can never widen it.

A domain matches itself and all of its subdomains. For example, ``python.org`` matches
``python.org`` and ``docs.python.org``, but not ``notpython.org``.

.. code-block:: python

    policy = DomainPolicy.create(allowed=["python.org"], blocked=["wiki.python.org"])
    policy.permits_url("https://docs.python.org/3/")  # True
    policy.permits_url("https://wiki.python.org/moin/")  # False: blocked
    policy.permits_url("https://example.com/")  # False: not allowed

.. note::

    **Experimental.** The WebsearchPlugin was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

import re
from dataclasses import dataclass
from typing import Iterable, Optional
from urllib.parse import urlparse

from smarter.common.exceptions import SmarterValueError

from .const import MAX_DOMAINS

LABEL = r"(?!-)[a-z0-9-]{1,63}(?<!-)"
DOMAIN_PATTERN = re.compile(rf"^(?=.{{1,253}}$){LABEL}(\.{LABEL})*$")


class WebsearchPolicyError(SmarterValueError):
    """Raised when a domain is invalid, or a request would widen a plugin's domain policy."""


def normalize_domain(domain: str) -> str:
    """
    Normalize a domain name.

    Leading wildcards (``*.``) and dots, and trailing dots, are removed, since a domain
    always matches its subdomains. Internationalized domain names are converted to their
    ASCII (punycode) form.

    :param domain: A domain name, e.g. ``*.Example.COM.``
    :return: The normalized domain name, e.g. ``example.com``.
    :raises WebsearchPolicyError: If the value is not a domain name, e.g. a URL or an IP address with a port.
    """
    if not isinstance(domain, str):
        raise WebsearchPolicyError(f"domains must be strings: {domain!r}")
    value = domain.strip().lower()
    if value.startswith("*."):
        value = value[2:]
    value = value.strip(".")
    try:
        value = value.encode("idna").decode("ascii")
    except UnicodeError as e:
        raise WebsearchPolicyError(f"invalid domain: {domain!r}") from e
    if not DOMAIN_PATTERN.match(value):
        raise WebsearchPolicyError(
            f"invalid domain: {domain!r}. Domains are host names, e.g. example.com, without a scheme, port or path."
        )
    return value


def normalize_domains(domains: Optional[Iterable[str]]) -> tuple[str, ...]:
    """
    Normalize a list of domain names, removing duplicates while preserving order.

    :raises WebsearchPolicyError: If a domain is invalid, or there are too many.
    """
    normalized: list[str] = []
    for domain in domains or []:
        value = normalize_domain(domain)
        if value not in normalized:
            normalized.append(value)
    if len(normalized) > MAX_DOMAINS:
        raise WebsearchPolicyError(f"at most {MAX_DOMAINS} domains are permitted.")
    return tuple(normalized)


def host_matches(host: str, domain: str) -> bool:
    """Return True if a host is the domain, or one of its subdomains."""
    host = host.lower().rstrip(".")
    return host == domain or host.endswith("." + domain)


def url_host(url: str) -> Optional[str]:
    """Return the lower case host of a URL, or None if it has none."""
    try:
        host = urlparse(url).hostname
    except ValueError:
        return None
    return host.lower().rstrip(".") if host else None


@dataclass(frozen=True)
class DomainPolicy:
    """
    The domains that a WebsearchPlugin may search and read.

    :ivar allowed: If not empty, only these domains, and their subdomains, are permitted.
    :ivar blocked: These domains, and their subdomains, are never permitted. The block list
        takes precedence over the allow list.
    """

    allowed: tuple[str, ...] = ()
    blocked: tuple[str, ...] = ()

    @classmethod
    def create(cls, allowed: Optional[Iterable[str]] = None, blocked: Optional[Iterable[str]] = None) -> "DomainPolicy":
        """Create a policy from lists of domain names, which are normalized."""
        return cls(allowed=normalize_domains(allowed), blocked=normalize_domains(blocked))

    def permits_host(self, host: Optional[str]) -> bool:
        """Return True if the policy permits a host."""
        if not host:
            return False
        if any(host_matches(host, domain) for domain in self.blocked):
            return False
        return not self.allowed or any(host_matches(host, domain) for domain in self.allowed)

    def permits_url(self, url: str) -> bool:
        """Return True if the policy permits the host of a URL."""
        return self.permits_host(url_host(url))

    def narrow(
        self, allowed: Optional[Iterable[str]] = None, blocked: Optional[Iterable[str]] = None
    ) -> "DomainPolicy":
        """
        Return a policy that is at least as restrictive as this one.

        This is how the LLM restricts an individual tool call, e.g. to search only one
        website. Requested allowed domains must lie within this policy's allowed domains, if
        it has any. Requested blocked domains are added to this policy's blocked domains.

        :param allowed: Domains to restrict the tool call to.
        :param blocked: Domains to exclude from the tool call.
        :return: The narrowed policy.
        :raises WebsearchPolicyError: If a requested allowed domain is outside this policy's
            allowed domains, or is blocked by it.
        """
        requested_allowed = normalize_domains(allowed)
        for domain in requested_allowed:
            if not self.permits_host(domain):
                raise WebsearchPolicyError(f"{domain} is not permitted by this plugin's domain policy.")
        requested_blocked = normalize_domains(blocked)
        return DomainPolicy(
            allowed=requested_allowed or self.allowed,
            blocked=self.blocked + tuple(domain for domain in requested_blocked if domain not in self.blocked),
        )

    def describe(self) -> str:
        """Describe the policy in a sentence, for the LLM, or return an empty string if it is unrestricted."""
        parts = []
        if self.allowed:
            parts.append(f"restricted to {', '.join(self.allowed)}")
        if self.blocked:
            parts.append(f"excluding {', '.join(self.blocked)}")
        return f"Web access is {' and '.join(parts)}." if parts else ""
