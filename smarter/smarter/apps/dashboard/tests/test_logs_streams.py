"""Tests for dashboard log streaming views."""

import asyncio
import logging
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

    def _stream(self, fake_cache, user=None, limit=3, query=None, log_level=logging.DEBUG):
        """Call the view with a fake redis, and collect its first chunks."""
        request = RequestFactory().get("/dashboard/logs/api/stream/", query or {})
        request.user = user or self.non_admin_user
        with (
            patch.object(
                streams, "smarter_settings", MagicMock(enable_dashboard_server_logs=True, log_level=log_level)
            ),
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
        self.assertFalse(skip("2026-01-01 DEBUG something"))
        self.assertFalse(skip("plain text"))
        self.assertFalse(skip("[1, 2]"))
        self.assertTrue(skip('{"logger": "%s", "message": "x"}' % streams.__name__))
        self.assertFalse(skip('{"levelname": "debug", "message": "x"}'))
        self.assertFalse(skip('{"level": "DEBUG", "logger": "smarter.apps.prompt", "message": "x"}'))
        self.assertTrue(skip('{"level": "DEBUG", "logger": "redis.connection", "message": "x"}'))
        self.assertTrue(skip('{"level": "DEBUG", "logger": "asyncio", "message": "x"}'))
        self.assertFalse(skip('{"level": "INFO", "logger": "asyncio", "message": "x"}'))
        self.assertFalse(skip('{"level": "DEBUG", "logger": "redistribution", "message": "x"}'))
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
                (b"2-0", {b"data": ('{"logger": "%s", "message": "noise"}' % streams.__name__).encode()}),
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
            {"type": "message", "data": f"{streams.__name__}.stream_user_logs() noise".encode()},
            {"type": "message", "data": b"hello"},
            None,
        ]
        _, chunks = self._stream(fake_cache, limit=4)
        self.assertEqual(chunks, ["retry: 3000\n\n", "data: hello\n", "\n", ": keepalive\n\n"])
        fake_pubsub.close.assert_called_once()

    def test_min_log_level(self):
        """Test that the minimum log level is the level query parameter, or else the server's log level."""
        factory = RequestFactory()
        with patch.object(streams, "smarter_settings", MagicMock(log_level=logging.INFO)):
            self.assertEqual(streams._min_log_level(factory.get("/", {"level": "DEBUG"})), logging.DEBUG)
            self.assertEqual(streams._min_log_level(factory.get("/", {"level": " warning "})), logging.WARNING)
            self.assertEqual(streams._min_log_level(factory.get("/")), logging.INFO)
            self.assertEqual(streams._min_log_level(factory.get("/", {"level": "LOUD"})), logging.INFO)

    def test_is_below_level(self):
        """Test that only log records below the minimum level are dropped."""
        below = streams._is_below_level
        self.assertTrue(below('{"level": "DEBUG", "message": "x"}', logging.INFO))
        self.assertTrue(below('{"levelname": "info", "message": "x"}', logging.WARNING))
        self.assertFalse(below('{"level": "INFO", "message": "x"}', logging.INFO))
        self.assertFalse(below('{"level": "DEBUG", "message": "x"}', logging.DEBUG))
        self.assertFalse(below('{"level": "LOUD", "message": "x"}', logging.INFO))
        self.assertFalse(below('{"message": "x"}', logging.INFO))
        self.assertFalse(below("plain text", logging.INFO))
        self.assertFalse(below("[1, 2]", logging.INFO))

    def test_stream_filters_by_level(self):
        """Test that replayed and live records below the stream's level are dropped."""
        debug = b'{"level": "DEBUG", "message": "debug"}'
        info = b'{"level": "INFO", "message": "info"}'

        def fake_cache():
            cache = MagicMock()
            cache.xrevrange.side_effect = [[(b"2-0", {b"data": info}), (b"1-0", {b"data": debug})], []]
            cache.pubsub.return_value.get_message.side_effect = [
                {"type": "message", "data": debug},
                {"type": "message", "data": info},
                None,
            ]
            return cache

        # production mode: the server's log level.
        _, chunks = self._stream(fake_cache(), limit=4, log_level=logging.INFO)
        self.assertEqual(chunks[1], 'event: bulk\ndata: [{"level": "INFO", "message": "info"}]\n\n')
        self.assertEqual(chunks[2:], [f"data: {info.decode()}\n", "\n"])

        # sandbox mode: DEBUG.
        _, chunks = self._stream(fake_cache(), limit=5, query={"level": "DEBUG"}, log_level=logging.INFO)
        self.assertIn('"message": "debug"', chunks[1])
        self.assertIn('"message": "info"', chunks[1])
        self.assertEqual(chunks[2:], [f"data: {debug.decode()}\n", "\n", f"data: {info.decode()}\n"])

    def test_request_id(self):
        """Test that the request id is the request_id query parameter, if it is a valid request id."""
        factory = RequestFactory()
        self.assertEqual(streams._request_id(factory.get("/", {"request_id": "abc123"})), "abc123")
        self.assertIsNone(streams._request_id(factory.get("/", {"request_id": "not valid"})))
        self.assertIsNone(streams._request_id(factory.get("/")))

    def test_is_other_request(self):
        """Test that, for one request's stream, only that request's records are kept."""
        other = streams._is_other_request
        self.assertFalse(other('{"request_id": "abc", "message": "x"}', "abc"))
        self.assertTrue(other('{"request_id": "xyz", "message": "x"}', "abc"))
        self.assertTrue(other('{"message": "x"}', "abc"))
        self.assertTrue(other("plain text", "abc"))
        self.assertTrue(other("[1, 2]", "abc"))
        self.assertFalse(other('{"message": "x"}', None))
        self.assertFalse(other("plain text", None))

    def test_one_requests_records(self):
        """Test that a stream with a request_id replays, and sends live, only that request's records."""
        fake_cache = MagicMock()
        fake_cache.xrevrange.side_effect = [
            [
                (b"2-0", {b"data": b'{"message": "other", "request_id": "xyz"}'}),
                (b"1-0", {b"data": b'{"message": "mine", "request_id": "abc"}'}),
            ],
            [],
        ]
        fake_cache.pubsub.return_value.get_message.side_effect = [
            {"type": "message", "data": b'{"message": "live other", "request_id": "xyz"}'},
            {"type": "message", "data": b'{"message": "live mine", "request_id": "abc"}'},
        ]
        _, chunks = self._stream(fake_cache, limit=3, query={"request_id": "abc"})
        self.assertEqual(chunks[1], 'event: bulk\ndata: [{"message": "mine", "request_id": "abc"}]\n\n')
        self.assertEqual(chunks[2], 'data: {"message": "live mine", "request_id": "abc"}\n')

    def test_session_key(self):
        """Test that the session key is the session_key query parameter, if it is a valid chat session key."""
        factory = RequestFactory()
        session_key = "a" * 64
        self.assertEqual(streams._session_key(factory.get("/", {"session_key": session_key})), session_key)
        self.assertIsNone(streams._session_key(factory.get("/", {"session_key": "abc123"})))
        self.assertIsNone(streams._session_key(factory.get("/")))

    def test_is_other_session(self):
        """Test that, for one chat's stream, only that chat's records are kept."""
        other = streams._is_other_session
        self.assertFalse(other('{"session_key": "abc", "message": "x"}', "abc"))
        self.assertTrue(other('{"session_key": "xyz", "message": "x"}', "abc"))
        self.assertTrue(other('{"message": "x"}', "abc"))
        self.assertTrue(other("plain text", "abc"))
        self.assertTrue(other("[1, 2]", "abc"))
        self.assertFalse(other('{"message": "x"}', None))
        self.assertFalse(other("plain text", None))

    def test_one_chats_records(self):
        """Test that a stream with a session_key replays, and sends live, only that chat's records."""
        mine = "a" * 64
        other = "b" * 64
        fake_cache = MagicMock()
        fake_cache.xrevrange.side_effect = [
            [
                (b"2-0", {b"data": f'{{"message": "other", "session_key": "{other}"}}'.encode()}),
                (b"1-0", {b"data": f'{{"message": "mine", "session_key": "{mine}"}}'.encode()}),
            ],
            [],
        ]
        fake_cache.pubsub.return_value.get_message.side_effect = [
            {"type": "message", "data": f'{{"message": "live other", "session_key": "{other}"}}'.encode()},
            {"type": "message", "data": f'{{"message": "live mine", "session_key": "{mine}"}}'.encode()},
        ]
        _, chunks = self._stream(fake_cache, limit=3, query={"session_key": mine})
        self.assertEqual(chunks[1], f'event: bulk\ndata: [{{"message": "mine", "session_key": "{mine}"}}]\n\n')
        self.assertEqual(chunks[2], f'data: {{"message": "live mine", "session_key": "{mine}"}}\n')
