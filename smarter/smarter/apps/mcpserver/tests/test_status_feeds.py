"""Test smarter.apps.mcpserver.services.status.feeds, with the safe HTTP client faked: nothing reaches the internet."""

from datetime import datetime, timezone
from unittest import mock

from smarter.apps.llmtool.plugin.safe_http import SafeHttpError
from smarter.apps.mcpserver.services.status import feeds
from smarter.apps.mcpserver.services.status.feeds import (
    STATUS_PAGES,
    ProviderStatus,
    aws_service_events,
    fetch_aws_feed,
    fetch_statuspage,
    provider_statuses,
    published_time,
)
from smarter.lib.unittest.base_classes import SmarterTestBase

FETCH = "smarter.apps.mcpserver.services.status.feeds.fetch"
NOW = datetime(2026, 11, 2, 21, 0, 0, tzinfo=timezone.utc)


def response(content: str) -> mock.Mock:
    """A fake SafeResponse with a body."""
    return mock.Mock(content=content.encode("utf-8"))


def rss(*items: tuple[str, str]) -> str:
    """An AWS status RSS feed, with items of (pubDate, title)."""
    entries = "".join(
        f"<item><title>{title}</title><pubDate>{published}</pubDate><description>details</description></item>"
        for published, title in items
    )
    return f'<?xml version="1.0"?><rss version="2.0"><channel><title>EKS</title>{entries}</channel></rss>'


class TestProviderStatuses(SmarterTestBase):
    """Test provider_statuses()."""

    def setUp(self):
        super().setUp()
        for url in [url for _, url in STATUS_PAGES]:
            fetch_statuspage.invalidate(url)

    def test_statuses(self):
        def fetch(url, **kwargs):
            if "openai" in url:
                return response(
                    '{"page": {"name": "OpenAI"}, "status": {"indicator": "major", "description": "Major Outage"}}'
                )
            if "claude" in url:
                return response('{"status": {"indicator": "none", "description": "All Systems Operational"}}')
            raise SafeHttpError("timed out")

        with mock.patch(FETCH, side_effect=fetch):
            statuses = {status.name: status for status in provider_statuses()}
        self.assertEqual(statuses["OpenAI"].indicator, "major")
        self.assertFalse(statuses["OpenAI"].operational)
        self.assertEqual(statuses["OpenAI"].url, "https://status.openai.com/")
        self.assertTrue(statuses["Anthropic"].operational)
        self.assertEqual(statuses["Mistral"].indicator, "unknown", "a page that cannot be read is unknown")
        self.assertFalse(statuses["Mistral"].operational)

    def test_not_a_status_page(self):
        with mock.patch(FETCH, return_value=response('{"something": "else"}')):
            statuses = provider_statuses()
        self.assertEqual({status.indicator for status in statuses}, {"unknown"})
        with mock.patch(FETCH, return_value=response("<html>")):
            self.assertEqual(provider_statuses()[0].indicator, "unknown")

    def test_failures_are_not_cached(self):
        url = STATUS_PAGES[0][1]
        with mock.patch(FETCH, side_effect=SafeHttpError("down")):
            provider_statuses()
        with mock.patch(FETCH, return_value=response('{"status": {"indicator": "none"}}')) as fetch:
            self.assertTrue(provider_statuses()[0].operational)
            fetch_statuspage(url)
        self.assertEqual(fetch.call_count, len(STATUS_PAGES), "the second call is cached")

    def test_operational(self):
        self.assertTrue(ProviderStatus(name="x", url="u", indicator="none").operational)
        self.assertFalse(ProviderStatus(name="x", url="u").operational)


class TestAwsServiceEvents(SmarterTestBase):
    """Test aws_service_events()."""

    def setUp(self):
        super().setUp()
        for service, _ in feeds.AWS_SERVICES:
            fetch_aws_feed.invalidate(service, "test-region-1")

    def test_events(self):
        def fetch(url, **kwargs):
            if "/eks-test-region-1.rss" in url:
                return response(
                    rss(
                        ("Mon, 02 Nov 2026 12:00:00 PST", "Increased API error rates"),
                        ("Mon, 19 Oct 2026 12:00:00 PST", "An old event"),
                        ("not a date", "An event without a date"),
                    )
                )
            return response(rss())

        with mock.patch(FETCH, side_effect=fetch):
            events, unread = aws_service_events("test-region-1", now=NOW)
        self.assertEqual(unread, [])
        titles = [event.title for event in events]
        self.assertEqual(
            titles,
            ["An event without a date", "Increased API error rates"],
            "older than 3 days is left out, and an undated event is listed first, as if it were current",
        )
        dated = events[1]
        self.assertEqual(dated.service, "EKS")
        self.assertEqual(dated.published, datetime(2026, 11, 2, 20, 0, 0, tzinfo=timezone.utc))
        self.assertEqual(dated.description, "details")

    def test_unreadable_feeds(self):
        def fetch(url, **kwargs):
            if "eks" in url:
                raise SafeHttpError("down")
            return response("not xml <")

        with mock.patch(FETCH, side_effect=fetch):
            events, unread = aws_service_events("test-region-1", now=NOW)
        self.assertEqual(events, [])
        self.assertEqual(unread, ["EKS", "EC2"])

    def test_entities_are_refused(self):
        """A feed that declares entities, e.g. a billion laughs, is refused by defusedxml."""
        bomb = '<?xml version="1.0"?><!DOCTYPE r [<!ENTITY a "aaaa">]><rss><channel><item><title>&a;</title></item></channel></rss>'
        with mock.patch(FETCH, return_value=response(bomb)):
            events, unread = aws_service_events("test-region-1", now=NOW)
        self.assertEqual(unread, ["EKS", "EC2"])

    def test_published_time(self):
        self.assertEqual(published_time("Mon, 02 Nov 2026 12:47:37 PST").hour, 20)
        self.assertIsNone(published_time(""))
