"""
The public status of the services that the platform depends on: the AI providers, and AWS in the platform's region.

Many problems that users report start upstream: an AI provider that is slow or down makes prompts fail,
and an AWS outage in the platform's region can stop its nodes or its cluster. The Smarter Operations MCP
server's ``platform_status`` and ``eks_status`` tools
(:mod:`smarter.apps.mcpserver.status.tools`) use this module to check the providers' own public status
pages, so that a help desk answer can say "the problem is upstream" with evidence. It reads:

- **the AI providers' status pages** of :data:`STATUS_PAGES`. Each is an `Atlassian Statuspage
  <https://developer.statuspage.io/>`__, whose ``/api/v2/status.json`` gives an overall indicator,
  ``none``, ``minor``, ``major`` or ``critical``, and a description, e.g. "All Systems Operational".
  :func:`provider_statuses` reads them.
- **the AWS service status feeds** of :data:`AWS_SERVICES` in the platform's region, e.g. EKS in
  ``ca-central-1``. Each is an RSS feed at ``https://status.aws.amazon.com/rss/<service>-<region>.rss``,
  whose items are the service's recent events. :func:`aws_service_events` reads them. They need no AWS
  account, unlike the AWS Health api, which requires a paid support plan, and they cost nothing.

Every feed is fetched with :func:`smarter.apps.llmtool.plugin.safe_http.fetch`, the platform's guarded
HTTP client, which refuses private addresses and limits the size of a response. A feed is cached for
:data:`FEED_CACHE_TTL` seconds, so that several tool calls in a row fetch it once. A feed that cannot be
read is reported as unknown, never as healthy, and the failure is not cached.

The text of a feed is written by its provider, and is passed to an LLM: the tools mark their results as
data, not instructions.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Optional

from cache_results import cache_results
from defusedxml import DefusedXmlException, ElementTree
from pydantic import BaseModel, ConfigDict, ValidationError

from smarter.apps.llmtool.plugin.safe_http import SafeHttpError, fetch
from smarter.lib import json, logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.MCPSERVER_LOGGING])
logger_prefix = logging.SmarterFormattedText.text(__name__)

FEED_CACHE_TTL = 60
"""Seconds that a status feed is cached: long enough for one help desk conversation's tool calls, short enough to stay current."""

FEED_TIMEOUT = 5
"""Seconds to wait for a status feed, so that a slow status page never makes ``platform_status`` slow."""

FEED_MAX_BYTES = 500_000
"""The largest status feed that is read.

A real one is a few kilobytes.
"""

AWS_EVENT_PERIOD = timedelta(days=3)
"""How far back the AWS events that are reported go.

An AWS feed keeps older events, which are history, not news.
"""

STATUS_PAGES: tuple[tuple[str, str], ...] = (
    ("OpenAI", "https://status.openai.com/api/v2/status.json"),
    ("Anthropic", "https://status.claude.com/api/v2/status.json"),
    ("Mistral", "https://status.mistral.ai/api/v2/status.json"),
)
"""
The AI providers whose status page is an Atlassian Statuspage: each one's name, and the url of its status.

Add a provider here when its status page offers ``/api/v2/status.json``. Google's status page does not:
it publishes its incidents in another format, so Gemini is not checked.
"""

AWS_SERVICES: tuple[tuple[str, str], ...] = (("eks", "EKS"), ("ec2", "EC2"))
"""
The AWS services whose status feeds are read: each one's name in its feed's url, and its name for people.

EKS runs the cluster's control plane, and EC2 runs its nodes.
"""


class StatuspageIndicator(BaseModel):
    """
    The ``status`` object of an Atlassian Statuspage ``status.json``: the page's overall status.

    Statuspage adds other fields, which are allowed, and ignored.
    """

    model_config = ConfigDict(extra="allow")

    indicator: str = "unknown"
    """``none`` when everything works, then ``minor``, ``major`` or ``critical``."""

    description: str = ""
    """The status in words, e.g. "All Systems Operational" or "Partial System Outage"."""


class StatuspageStatus(BaseModel):
    """
    An Atlassian Statuspage ``/api/v2/status.json``, with the one field that is read.

    The page also describes itself, in ``page``, which is allowed, and ignored.
    """

    model_config = ConfigDict(extra="allow")

    status: StatuspageIndicator
    """The page's overall status."""


@dataclass
class ProviderStatus:
    """
    An AI provider's status, as its status page reports it, for ``platform_status``.

    :func:`provider_statuses` builds it. A page that cannot be read keeps the ``unknown`` indicator, so
    that it is never mistaken for a provider that works.
    """

    name: str
    """The provider's name, e.g. ``OpenAI``."""

    url: str
    """The status page that people can open, e.g. ``https://status.openai.com/``."""

    indicator: str = "unknown"
    """``none``, ``minor``, ``major`` or ``critical``, from the page, or ``unknown`` if it could not be read."""

    description: str = "the status page could not be read"
    """The status in words, from the page, or why it is unknown."""

    @property
    def operational(self) -> bool:
        """
        Whether the provider reports that everything works.

        :returns: True only for the indicator ``none``. A page that could not be read is not operational.
        """
        return self.indicator == "none"


@dataclass
class AwsEvent:
    """An event of an AWS service in the platform's region, e.g. "Increased API error rates", from its RSS feed."""

    service: str
    """The service's name for people, e.g. ``EKS``."""

    published: Optional[datetime]
    """When AWS posted the event, in UTC, or None if the feed did not say."""

    title: str
    """The event's title, as AWS wrote it."""

    description: str
    """The event's details, as AWS wrote them."""


@cache_results(timeout=FEED_CACHE_TTL)
def fetch_statuspage(url: str) -> StatuspageStatus:
    """
    Fetch and parse a Statuspage ``status.json``.

    It is cached for :data:`FEED_CACHE_TTL` seconds. A failure raises, rather than returning a value,
    so that the cache never keeps it.

    Side effects: one HTTPS GET, through :func:`~smarter.apps.llmtool.plugin.safe_http.fetch`, unless the
    page is cached.

    :param url: The url of the ``status.json``.
    :returns: The page's status.
    :raises SafeHttpError: If the page cannot be fetched, e.g. it times out or answers an error.
    :raises ValueError: If the page is not JSON.
    :raises ValidationError: If the JSON is not a Statuspage status.
    """
    response = fetch(url, timeout=FEED_TIMEOUT, max_bytes=FEED_MAX_BYTES, headers={"Accept": "application/json"})
    body = json.loads(response.content)
    return StatuspageStatus.model_validate(body)


def provider_statuses() -> list[ProviderStatus]:
    """
    Read the status of each AI provider of :data:`STATUS_PAGES`.

    It never raises: a page that cannot be read is reported as ``unknown``, and logged.

    Side effects: one HTTPS GET per provider, unless its page is cached (see :func:`fetch_statuspage`).

    :returns: Each provider's status, in the order of :data:`STATUS_PAGES`.
    """
    statuses = []
    for name, url in STATUS_PAGES:
        page_url = url.removesuffix("api/v2/status.json")
        status = ProviderStatus(name=name, url=page_url)
        try:
            page = fetch_statuspage(url)
        except (SafeHttpError, ValidationError, ValueError) as e:
            logger.warning("%s.provider_statuses() could not read %s: %s", logger_prefix, url, e)
            statuses.append(status)
            continue
        status.indicator = page.status.indicator
        status.description = page.status.description
        statuses.append(status)
    return statuses


@cache_results(timeout=FEED_CACHE_TTL)
def fetch_aws_feed(service: str, region: str) -> list[tuple[str, str, str]]:
    """
    Fetch and parse the RSS status feed of an AWS service in a region.

    The feed is parsed with ``defusedxml``, which refuses XML entities, so that a malicious feed cannot
    expand into a huge document or read local files. It is cached for :data:`FEED_CACHE_TTL` seconds. A
    failure raises, rather than returning a value, so that the cache never keeps it.

    Side effects: one HTTPS GET, through :func:`~smarter.apps.llmtool.plugin.safe_http.fetch`, unless the
    feed is cached.

    :param service: The service's name in its feed's url, e.g. ``eks``.
    :param region: The AWS region, e.g. ``ca-central-1``.
    :returns: Each item of the feed, as its ``(pubDate, title, description)``, in the feed's order.
    :raises SafeHttpError: If the feed cannot be fetched.
    :raises ElementTree.ParseError: If the feed is not XML.
    :raises DefusedXmlException: If the feed declares entities, which are refused.
    """
    url = f"https://status.aws.amazon.com/rss/{service}-{region}.rss"
    response = fetch(url, timeout=FEED_TIMEOUT, max_bytes=FEED_MAX_BYTES)
    root = ElementTree.fromstring(response.content)
    items = []
    for item in root.iter("item"):
        published = (item.findtext("pubDate") or "").strip()
        title = (item.findtext("title") or "").strip()
        description = (item.findtext("description") or "").strip()
        items.append((published, title, description))
    return items


def published_time(value: str) -> Optional[datetime]:
    """
    Convert an RSS ``pubDate`` into a time in UTC.

    :param value: The date, in RFC 2822 format, as AWS writes it, e.g. ``Mon, 02 Nov 2026 12:47:37 PST``.
    :returns: The time, in UTC, or None if the value is missing or is not a date.
    """
    try:
        when = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    return when.astimezone(timezone.utc)


def aws_service_events(region: str, now: Optional[datetime] = None) -> tuple[list[AwsEvent], list[str]]:
    """
    Read the recent events of the AWS services of :data:`AWS_SERVICES` in a region.

    An event older than :data:`AWS_EVENT_PERIOD` is left out. An event without a date is kept, rather
    than hidden, and is listed first, as if it were current, because it may be. It never raises: a feed
    that cannot be read is named in the second list, and logged.

    Side effects: one HTTPS GET per service, unless its feed is cached (see :func:`fetch_aws_feed`).

    :param region: The AWS region, e.g. ``smarter_settings.aws_region``.
    :param now: The current time, which tests set. By default, the current time in UTC.
    :returns: The recent events of every service, newest first, and the names of the services whose
        feed could not be read, e.g. ``["EC2"]``. An empty first list means that AWS reports no events.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    events: list[AwsEvent] = []
    unread: list[str] = []
    for service, name in AWS_SERVICES:
        try:
            items = fetch_aws_feed(service, region)
        except (SafeHttpError, ElementTree.ParseError, DefusedXmlException) as e:
            logger.warning("%s.aws_service_events() could not read %s in %s: %s", logger_prefix, name, region, e)
            unread.append(name)
            continue
        for published, title, description in items:
            when = published_time(published)
            if when is not None and now - when > AWS_EVENT_PERIOD:
                continue
            event = AwsEvent(service=name, published=when, title=title, description=description)
            events.append(event)
    events.sort(key=lambda event: event.published or now, reverse=True)
    return events, unread


__all__ = [
    "AWS_SERVICES",
    "STATUS_PAGES",
    "AwsEvent",
    "ProviderStatus",
    "aws_service_events",
    "provider_statuses",
]
