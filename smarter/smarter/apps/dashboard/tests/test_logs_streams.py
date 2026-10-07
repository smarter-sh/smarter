"""Tests for dashboard log streaming views."""

import asyncio
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory
from redis.exceptions import RedisError

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.dashboard.views.terminal_emulator.api import streams
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
            patch.object(streams, "smarter_settings", MagicMock(enable_dashboard_server_logs=True)),
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
        fake_cache.xrevrange.side_effect = [
            [(b"1714690000000-0", {b"data": b'{"message":"before connect"}'})],
            [],
        ]

        with (
            patch.object(streams, "smarter_settings", MagicMock(enable_dashboard_server_logs=True)),
            patch.object(streams, "get_resolved_user", return_value=self.non_admin_user),
            patch.object(streams, "get_redis_connection", return_value=fake_cache),
        ):
            response = streams.stream_user_logs(request)
            chunks = asyncio.run(self._collect_stream_chunks(response, limit=2))

        self.assertEqual(chunks[0], "retry: 3000\n\n")
        self.assertEqual(chunks[1], 'event: bulk\ndata: [{"message": "before connect"}]\n\n')
        fake_cache.xrevrange.assert_any_call(
            stream_key(channel),
            max="+",
            min="-",
            count=min(streams.STREAM_REPLAY_BATCH_SIZE, streams.STREAM_REPLAY_MAX_ENTRIES),
        )

    def _stream(self, fake_cache, user=None, limit=3):
        """Call the view with a fake redis, and collect its first chunks."""
        request = RequestFactory().get("/dashboard/logs/api/stream/")
        request.user = user or self.non_admin_user
        with (
            patch.object(streams, "smarter_settings", MagicMock(enable_dashboard_server_logs=True)),
            patch.object(streams, "get_redis_connection", return_value=fake_cache),
        ):
            response = streams.stream_user_logs(request)
            if limit == 0:
                return response, []
            return response, asyncio.run(self._collect_stream_chunks(response, limit=limit))

    def test_helpers(self):
        """Test the payload decoding, SSE framing and internal log filtering helpers."""
        self.assertEqual(streams._decode_redis_payload(b"abc"), "abc")
        self.assertEqual(streams._decode_redis_payload(123), "123")
        self.assertEqual(list(streams._iter_sse_data_frames("a\nb")), ["data: a\n", "data: b\n", "\n"])
        self.assertEqual(list(streams._iter_sse_data_frames("")), ["data: \n", "\n"])

        skip = streams._should_skip_stream_internal_log
        self.assertTrue(skip(f"{streams.__name__}.stream_user_logs() called"))
        self.assertTrue(skip("2026-01-01 DEBUG something"))
        self.assertFalse(skip("plain text"))
        self.assertFalse(skip("[1, 2]"))
        self.assertTrue(skip('{"logger": "%s", "message": "x"}' % streams.__name__))
        self.assertTrue(skip('{"levelname": "debug", "message": "x"}'))
        self.assertFalse(skip('{"level": "INFO", "message": "hello"}'))

    def test_disabled(self):
        """Test that the view explains that log streaming is disabled."""
        request = RequestFactory().get("/dashboard/logs/api/stream/")
        request.user = self.non_admin_user
        with patch.object(streams, "smarter_settings", MagicMock(enable_dashboard_server_logs=False)):
            response = streams.stream_user_logs(request)
        self.assertIn(b"disabled", response.content)

    def test_redis_unavailable(self):
        """Test that the view is a 503 when redis can't be reached."""
        fake_cache = MagicMock()
        fake_cache.pubsub.side_effect = RedisError("down")
        response, _ = self._stream(fake_cache, limit=0)
        self.assertEqual(response.status_code, 503)

    def test_anonymous_user_gets_a_unique_channel(self):
        """Test that a request without a user subscribes to a channel that no logs are written to."""
        fake_cache = MagicMock()
        request = RequestFactory().get("/dashboard/logs/api/stream/")
        request.user = AnonymousUser()
        with (
            patch.object(streams, "smarter_settings", MagicMock(enable_dashboard_server_logs=True)),
            patch.object(streams, "get_redis_connection", return_value=fake_cache),
            patch.object(streams, "get_resolved_user", return_value=None),
        ):
            response = streams.stream_user_logs.__wrapped__(request)  # type: ignore[attr-defined]
        self.assertEqual(response.status_code, 200)
        channel = fake_cache.pubsub.return_value.subscribe.call_args.args[0]
        self.assertNotEqual(channel, build_channel(get_user_context(self.non_admin_user)))

    def test_replay_skips_internal_logs_and_wraps_plain_text(self):
        """Test that replayed internal logs are dropped, and plain text is wrapped in a message."""
        fake_cache = MagicMock()
        fake_cache.pubsub.return_value.get_message.return_value = None
        fake_cache.xrevrange.side_effect = [
            [
                (b"3-0", {b"data": b"plain text"}),
                (b"2-0", {b"data": b"2026-01-01 DEBUG noise"}),
                (b"1-0", {"data": '{"message": "json"}'}),
            ],
            [],
        ]
        _, chunks = self._stream(fake_cache, limit=2)
        self.assertEqual(chunks[1], 'event: bulk\ndata: [{"message": "json"}, {"message": "plain text"}]\n\n')
        self.assertEqual(fake_cache.xrevrange.call_args_list[1].kwargs["max"], "(1-0")

    def test_live_messages_and_keepalive(self):
        """Test that live messages are framed, internal ones dropped, and idle time kept alive."""
        fake_cache = MagicMock()
        fake_cache.xrevrange.side_effect = RedisError("no history")
        fake_pubsub = fake_cache.pubsub.return_value
        fake_pubsub.close.side_effect = RedisError("close failed")
        fake_pubsub.get_message.side_effect = [
            {"type": "message", "data": b"2026-01-01 DEBUG noise"},
            {"type": "message", "data": b"hello"},
            None,
        ]
        _, chunks = self._stream(fake_cache, limit=4)
        self.assertEqual(chunks, ["retry: 3000\n\n", "data: hello\n", "\n", ": keepalive\n\n"])
        fake_pubsub.close.assert_called_once()
