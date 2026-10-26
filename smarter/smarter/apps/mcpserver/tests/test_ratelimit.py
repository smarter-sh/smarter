"""Tests for smarter.apps.mcpserver.ratelimit, and the rate limit of the MCP server's view."""

import json
from unittest import mock

from cache_results import lazy_cache
from django.test import Client, RequestFactory
from django.urls import reverse

from smarter.apps.mcpserver import ratelimit
from smarter.apps.mcpserver.ratelimit import (
    RATE_LIMITED,
    WINDOW_SECONDS,
    client_ip,
    is_rate_limited,
    rate_limit_key,
    retry_after,
)
from smarter.apps.mcpserver.urls import MCPServerReverseNames

from .base_classes import MCPServerTestBase

SETTINGS_PATCH = "smarter.apps.mcpserver.ratelimit.smarter_settings"


class TestRateLimit(MCPServerTestBase):
    """Test the per-IP rate limit.

    Each test uses its own client address, so that the counts do not mix.
    """

    def setUp(self):
        super().setUp()
        self.ip = (
            f"9.{int(self.hash_suffix[:4], 16) % 250}.{len(self._testMethodName)}.{hash(self._testMethodName) % 250}"
        )
        self.addCleanup(lazy_cache.delete, rate_limit_key(self.ip, ratelimit.current_window()))
        patcher = mock.patch(SETTINGS_PATCH)
        self.settings = patcher.start()
        self.addCleanup(patcher.stop)
        self.settings.mcpserver_rate_limit = 3

    def test_limit(self):
        """A client may send the limit's number of requests in a window, and no more."""
        self.assertEqual([is_rate_limited(self.ip) for _ in range(5)], [False, False, False, True, True])

    def test_limit_of_one(self):
        """With a limit of 1, only the first request of a window is allowed."""
        self.settings.mcpserver_rate_limit = 1
        self.assertEqual([is_rate_limited(self.ip) for _ in range(2)], [False, True])

    def test_disabled(self):
        """A limit of 0 disables the rate limit, and an unknown address is never limited."""
        self.settings.mcpserver_rate_limit = 0
        self.assertFalse(any(is_rate_limited(self.ip) for _ in range(10)))
        self.settings.mcpserver_rate_limit = 1
        self.assertFalse(any(is_rate_limited(None) for _ in range(10)))

    def test_windows(self):
        """Each window starts a new count."""
        with mock.patch.object(ratelimit, "current_window", return_value=1):
            self.assertEqual([is_rate_limited(self.ip) for _ in range(4)], [False, False, False, True])
        with mock.patch.object(ratelimit, "current_window", return_value=2):
            self.addCleanup(lazy_cache.delete, rate_limit_key(self.ip, 2))
            self.assertFalse(is_rate_limited(self.ip))
        lazy_cache.delete(rate_limit_key(self.ip, 1))

    def test_expired_between_add_and_incr(self):
        """A count that expires between add() and incr() starts again."""
        with (
            mock.patch.object(ratelimit.lazy_cache, "add", return_value=False),
            mock.patch.object(ratelimit.lazy_cache, "incr", side_effect=ValueError("no such key")),
            mock.patch.object(ratelimit.lazy_cache, "set") as cache_set,
        ):
            self.assertFalse(is_rate_limited(self.ip))
        cache_set.assert_called_once()

    def test_retry_after(self):
        """Retry-After is the rest of the window, at least one second."""
        self.assertTrue(1 <= retry_after() <= WINDOW_SECONDS)
        with mock.patch.object(ratelimit.time, "time", return_value=WINDOW_SECONDS * 100 + 59.5):
            self.assertEqual(retry_after(), 1)

    def test_client_ip(self):
        """The client's public address comes from the proxies' headers, and a private address is unknown."""
        factory = RequestFactory()
        self.assertEqual(client_ip(factory.post("/", HTTP_X_FORWARDED_FOR=f"{self.ip}, 10.0.0.1")), self.ip)
        self.assertEqual(client_ip(factory.post("/", REMOTE_ADDR=self.ip)), self.ip)
        self.assertIsNone(client_ip(factory.post("/", REMOTE_ADDR="10.0.0.1")))

    def test_view(self):
        """A client over the limit is answered 429, with Retry-After and a JSON-RPC error."""
        url = reverse(f"{MCPServerReverseNames.namespace}:{MCPServerReverseNames.smarter_project}")
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"})
        client = Client()
        statuses = [
            client.post(url, data=body, content_type="application/json", HTTP_X_FORWARDED_FOR=self.ip).status_code
            for _ in range(3)
        ]
        self.assertEqual(statuses, [200, 200, 200])
        response = client.post(url, data=body, content_type="application/json", HTTP_X_FORWARDED_FOR=self.ip)
        self.assertEqual(response.status_code, 429)
        self.assertTrue(1 <= int(response["Retry-After"]) <= WINDOW_SECONDS)
        self.assertEqual(response.json()["error"]["code"], RATE_LIMITED)
        self.assertIsNone(response.json()["id"])
        other = client.post(url, data=body, content_type="application/json", REMOTE_ADDR="10.0.0.1")
        self.assertEqual(other.status_code, 200)
