"""Tests for dashboard log streaming views."""

import asyncio
from unittest.mock import MagicMock, patch

from django.test import RequestFactory

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.dashboard.views.logs import streams
from smarter.lib.logging.redis_log_handler import (
    build_channel,
    get_user_context,
    stream_key,
)


class TestLogStreams(TestAccountMixin):
    """Regression tests for Redis-backed log streaming."""

    @staticmethod
    async def _collect_stream_chunks(response, limit=3):
        chunks = []
        async for chunk in response.streaming_content:
            chunks.append(chunk.decode() if isinstance(chunk, (bytes, bytearray)) else chunk)
            if len(chunks) >= limit:
                break
        return chunks

    def test_stream_user_logs_subscribes_to_resolved_user_channel(self):
        """The SSE stream should use the same user context as the logging middleware."""
        request = RequestFactory().get("/dashboard/logs/api/stream/")
        request.user = self.non_admin_user

        fake_pubsub = MagicMock()
        fake_cache = MagicMock()
        fake_cache.pubsub.return_value = fake_pubsub

        with (
            patch.object(streams.smarter_settings, "enable_dashboard_server_logs", True),
            patch.object(streams, "get_resolved_user", return_value=self.non_admin_user),
            patch.object(streams, "get_redis_connection", return_value=fake_cache),
        ):
            response = streams.stream_user_logs(request)

        self.assertEqual(response.status_code, 200)
        fake_pubsub.subscribe.assert_called_once_with(build_channel(get_user_context(self.non_admin_user)))

    def test_stream_user_logs_replays_stream_history_before_live_messages(self):
        """Historical Redis stream entries should be emitted as the first log events."""
        request = RequestFactory().get("/dashboard/logs/api/stream/")
        request.user = self.non_admin_user
        channel = build_channel(get_user_context(self.non_admin_user))

        fake_pubsub = MagicMock()
        fake_pubsub.get_message.return_value = None
        fake_cache = MagicMock()
        fake_cache.pubsub.return_value = fake_pubsub
        fake_cache.xrange.side_effect = [
            [(b"1714690000000-0", {b"data": b'{"message":"before connect"}'})],
            [],
        ]

        with (
            patch.object(streams.smarter_settings, "enable_dashboard_server_logs", True),
            patch.object(streams, "get_resolved_user", return_value=self.non_admin_user),
            patch.object(streams, "get_redis_connection", return_value=fake_cache),
        ):
            response = streams.stream_user_logs(request)
            chunks = asyncio.run(self._collect_stream_chunks(response))

        self.assertEqual(chunks[0], "retry: 3000\n\n")
        self.assertEqual(chunks[1], 'data: {"message":"before connect"}\n')
        self.assertEqual(chunks[2], "\n")
        fake_cache.xrange.assert_any_call(
            stream_key(channel),
            min="-",
            max="+",
            count=streams.STREAM_REPLAY_BATCH_SIZE,
        )
