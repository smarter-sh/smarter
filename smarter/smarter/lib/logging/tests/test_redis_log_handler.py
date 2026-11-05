"""
Test :mod:`smarter.lib.logging.redis_log_handler`.

Redis is faked, and the module's log_queue is replaced with a new queue in each
test, so that the running worker thread and the real Redis are never touched.
"""

import json
import logging
import queue
from unittest.mock import MagicMock, patch

from django.core.exceptions import ImproperlyConfigured

from smarter.lib.logging import redis_log_handler as handler
from smarter.lib.unittest.base_classes import SmarterTestBase

MODULE = "smarter.lib.logging.redis_log_handler"
GET_REDIS_CACHE = handler.get_redis_cache


class TestRedisLogHandler(SmarterTestBase):
    """Test flush(), purge_log_context(), the redis helpers, and RedisLogHandler.emit()."""

    def setUp(self):
        super().setUp()
        self.queue = queue.Queue(maxsize=3)
        patcher = patch(f"{MODULE}.log_queue", self.queue)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.redis = MagicMock()
        patcher = patch(f"{MODULE}.get_redis_cache", return_value=self.redis)
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = patch.dict(handler._publish_state, {"failing": False})  # pylint: disable=protected-access
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = patch.object(handler.RedisLogHandler, "publishing_enabled", True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def queued(self, *payloads):
        """Queue and dequeue payloads, as the worker does, so that flush() can mark them done."""
        for payload in payloads:
            self.queue.put_nowait(payload)
        return [self.queue.get_nowait() for _ in payloads]

    def test_flush(self):
        """Test that each payload is published, added to its stream, and given its stream's ttl."""
        buffer = self.queued(
            {"channel": handler.build_channel("user.a"), "data": "one"},
            {"channel": handler.build_channel(handler.GLOBAL_LOG_CHANNEL), "data": "two"},
        )
        handler.flush(buffer)
        pipe = self.redis.pipeline.return_value
        self.assertEqual(pipe.publish.call_count, 2)
        self.assertEqual(pipe.xadd.call_count, 2)
        pipe.execute.assert_called_once()
        self.assertEqual(self.queue.unfinished_tasks, 0)

    def test_flush_sets_each_streams_ttl_once(self):
        """Test that a batch of records for one stream sets its ttl once, not once per record."""
        channel = handler.build_channel("user.a")
        buffer = self.queued(
            {"channel": channel, "data": "one"},
            {"channel": channel, "data": "two"},
            {"channel": channel, "data": "three"},
        )
        handler.flush(buffer)
        pipe = self.redis.pipeline.return_value
        self.assertEqual(pipe.xadd.call_count, 3)
        pipe.expire.assert_called_once_with(handler.stream_key(channel), handler.USER_STREAM_TTL_SECONDS)

    def test_flush_does_not_ping(self):
        """Test that flush() publishes without a round trip to check that Redis is up."""
        handler.flush(self.queued({"channel": "logs:a", "data": "one"}))
        self.redis.ping.assert_not_called()

    def test_flush_redis_not_configured(self):
        with patch(f"{MODULE}.get_redis_cache", return_value=None):
            handler.flush(self.queued({"channel": "logs:a", "data": "one"}))
        self.redis.pipeline.assert_not_called()
        self.assertEqual(self.queue.unfinished_tasks, 0)

    def test_flush_pipeline_error(self):
        """Test that a Redis outage is logged once, not once per batch, and that recovery is logged."""
        execute = self.redis.pipeline.return_value.execute
        execute.side_effect = Exception("pipeline failed")
        with patch(f"{MODULE}.logger") as logger:
            handler.flush(self.queued({"channel": "logs:a", "data": "one"}))
            handler.flush(self.queued({"channel": "logs:a", "data": "two"}))
            logger.warning.assert_called_once()
            logger.exception.assert_not_called()
            self.assertEqual(str(logger.warning.call_args.args[-1]), "pipeline failed")
            self.assertEqual(self.queue.unfinished_tasks, 0)

            execute.side_effect = None
            handler.flush(self.queued({"channel": "logs:a", "data": "three"}))
            handler.flush(self.queued({"channel": "logs:a", "data": "four"}))
            logger.info.assert_called_once()

    def test_next_batch(self):
        """Test that a batch takes everything that is queued, without waiting for more."""
        self.queue.put_nowait({"channel": "logs:a", "data": "one"})
        self.queue.put_nowait({"channel": "logs:a", "data": "two"})
        buffer, stop = handler.next_batch(timeout=0.01)
        self.assertEqual([payload["data"] for payload in buffer], ["one", "two"])
        self.assertFalse(stop)
        self.assertEqual(handler.next_batch(timeout=0.01), ([], False))

    def test_next_batch_max_batch(self):
        self.queue = queue.Queue()
        with patch(f"{MODULE}.log_queue", self.queue), patch(f"{MODULE}.MAX_BATCH", 2):
            for data in ("one", "two", "three"):
                self.queue.put_nowait({"channel": "logs:a", "data": data})
            buffer, stop = handler.next_batch(timeout=0.01)
        self.assertEqual(len(buffer), 2)
        self.assertFalse(stop)
        self.assertEqual(self.queue.qsize(), 1)

    def test_next_batch_shutdown(self):
        """Test that the shutdown sentinel ends the batch, and the entries before it are kept."""
        self.queue.put_nowait({"channel": "logs:a", "data": "one"})
        self.queue.put_nowait(None)
        buffer, stop = handler.next_batch(timeout=0.01)
        self.assertEqual(len(buffer), 1)
        self.assertTrue(stop)
        self.assertEqual(handler.next_batch(timeout=0.01), ([], False))

    def test_redis_is_ready(self):
        self.assertTrue(handler.redis_is_ready())
        self.redis.ping.side_effect = Exception("down")
        self.assertFalse(handler.redis_is_ready())
        with patch(f"{MODULE}.get_redis_cache", return_value=None):
            self.assertFalse(handler.redis_is_ready())
            with self.assertRaises(RuntimeError):
                handler.purge_log_context("user.a")

    def test_purge_log_context(self):
        handler.purge_log_context("user.a")
        self.redis.delete.assert_called_once_with(handler.stream_key(handler.build_channel("user.a")))

    def test_get_redis_cache_not_configured(self):
        """Test the real get_redis_cache(), which setUp() replaced, when Redis isn't configured."""
        with (
            patch.object(handler, "_redis_client", None),
            patch.object(handler, "_redis_unconfigured_logged", False),
            patch(f"{MODULE}.get_redis_connection", side_effect=ImproperlyConfigured("no redis")) as connect,
            patch(f"{MODULE}.logger") as logger,
        ):
            self.assertIsNone(GET_REDIS_CACHE())
            self.assertIsNone(GET_REDIS_CACHE())
            # it tries again on each call, but says so once.
            self.assertEqual(connect.call_count, 2)
            logger.warning.assert_called_once()

    def test_get_redis_cache_connects_once(self):
        """Test the real get_redis_cache() opens the connection on first use, then reuses it."""
        client = MagicMock()
        with (
            patch.object(handler, "_redis_client", None),
            patch(f"{MODULE}.get_redis_connection", return_value=client) as connect,
        ):
            self.assertIs(GET_REDIS_CACHE(), client)
            self.assertIs(GET_REDIS_CACHE(), client)
            connect.assert_called_once_with("default")

    def test_get_user_context(self):
        user = MagicMock(username="ada")
        self.assertEqual(handler.get_user_context(user), "MagicMock.ada")
        self.assertEqual(handler.get_user_context("job-1"), "str.job-1")

    def test_emit_queue_full(self):
        """Test that a log record is dropped, and counted, when the queue is full."""
        record = logging.LogRecord("test", logging.INFO, __file__, 1, "a message", None, None)
        log_handler = handler.RedisLogHandler()
        dropped = handler.RedisLogHandler.dropped_logs
        token = handler.user_id_context.set("User.a")
        try:
            log_handler.emit(record)  # 2 payloads: the user's channel and the global channel.
            with patch(f"{MODULE}.sys.stderr"):
                log_handler.emit(record)  # the queue is full after one more payload.
        finally:
            handler.user_id_context.reset(token)
        self.assertEqual(self.queue.qsize(), 3)
        self.assertEqual(handler.RedisLogHandler.dropped_logs, dropped + 1)

    def test_emit_without_a_user_goes_to_the_global_channel_only(self):
        """A record outside any user's context gets no channel of its own, which no one could subscribe to."""
        record = logging.LogRecord("test", logging.INFO, __file__, 1, "a message", None, None)
        handler.RedisLogHandler().emit(record)
        self.assertEqual(self.queue.qsize(), 1)
        self.assertEqual(self.queue.get_nowait()["channel"], handler.GLOBAL_CHANNEL)

    def test_emit_with_a_user_goes_to_the_users_channel_too(self):
        record = logging.LogRecord("test", logging.INFO, __file__, 1, "a message", None, None)
        token = handler.user_id_context.set("User.a")
        try:
            handler.RedisLogHandler().emit(record)
        finally:
            handler.user_id_context.reset(token)
        channels = [self.queue.get_nowait()["channel"] for _ in range(2)]
        self.assertEqual(channels, [handler.build_channel("User.a"), handler.GLOBAL_CHANNEL])

    def test_emit_publishes_nothing_when_disabled(self):
        """When the dashboard's server logs are off, no record is queued."""
        record = logging.LogRecord("test", logging.INFO, __file__, 1, "a message", None, None)
        with patch.object(handler.RedisLogHandler, "publishing_enabled", False):
            handler.RedisLogHandler().emit(record)
        self.assertEqual(self.queue.qsize(), 0)

    def test_is_publishing_enabled_reads_the_setting_once(self):
        with (
            patch.object(handler.RedisLogHandler, "publishing_enabled", None),
            patch("smarter.common.conf.smarter_settings") as settings,
        ):
            settings.enable_dashboard_server_logs = False
            log_handler = handler.RedisLogHandler()
            self.assertFalse(log_handler.is_publishing_enabled())
            settings.enable_dashboard_server_logs = True
            self.assertFalse(log_handler.is_publishing_enabled())

    def test_emit_failure_is_reported_by_handle_error(self):
        """A failure is reported by handleError(), not logged, which would feed the handler its own record."""
        record = logging.LogRecord("test", logging.INFO, __file__, 1, "a message", None, None)
        log_handler = handler.RedisLogHandler()
        with (
            patch.object(log_handler, "format", side_effect=RuntimeError("boom")),
            patch.object(log_handler, "handleError") as handle_error,
        ):
            log_handler.emit(record)
        handle_error.assert_called_once_with(record)

    def test_get_user_channel(self):
        token = handler.user_id_context.set("User.a")
        try:
            self.assertEqual(handler.get_user_channel(), "User.a")
        finally:
            handler.user_id_context.reset(token)
        self.assertTrue(handler.get_user_channel().startswith("job_"))

    def test_valid_request_id(self):
        """Test that a request id from the browser is used only if it has the form of one."""
        self.assertEqual(handler.valid_request_id(" 0123abcdef_-XYZ "), "0123abcdef_-XYZ")
        self.assertEqual(handler.valid_request_id("a" * 64), "a" * 64)
        for invalid in (None, "", "a" * 65, "has space", "line\nbreak", "<script>", "a/b"):
            self.assertIsNone(handler.valid_request_id(invalid), msg=f"request_id={invalid!r}")

    def test_emit_tags_the_record_with_the_request_id(self):
        """Test that a record carries the request id while one is set, and not otherwise."""
        self.queue = queue.Queue(maxsize=10)
        record = logging.LogRecord("test", logging.INFO, __file__, 1, "a message", None, None)
        log_handler = handler.RedisLogHandler()
        with patch(f"{MODULE}.log_queue", self.queue):
            token = handler.request_id_context.set("abc123")
            try:
                log_handler.emit(record)
            finally:
                handler.request_id_context.reset(token)
            log_handler.emit(record)
        payloads = [json.loads(self.queue.get_nowait()["data"]) for _ in range(2)]
        self.assertEqual([payload.get("request_id") for payload in payloads], ["abc123", None])

    def test_bind_log_context(self):
        """Test that a bound function runs in the log context of its binding, and restores the caller's."""
        user_token = handler.user_id_context.set("User.a")
        request_token = handler.request_id_context.set("abc123")
        try:
            bound = handler.bind_log_context(
                lambda value: (handler.user_id_context.get(), handler.request_id_context.get(), value)
            )
        finally:
            handler.request_id_context.reset(request_token)
            handler.user_id_context.reset(user_token)

        # e.g. a streaming response's generator, after the middleware reset the request's log context.
        self.assertEqual(bound("x"), ("User.a", "abc123", "x"))
        self.assertIsNone(handler.user_id_context.get())
        self.assertIsNone(handler.request_id_context.get())

        failing = handler.bind_log_context(lambda: 1 / 0)
        with self.assertRaises(ZeroDivisionError):
            failing()
        self.assertIsNone(handler.request_id_context.get())

    def test_valid_session_key(self):
        """Test that a chat session key is used only if it has the form of one."""
        session_key = "0123456789abcdef" * 4
        self.assertEqual(handler.valid_session_key(f" {session_key} "), session_key)
        for invalid in (None, "", "a" * 63, "a" * 65, "g" * 64, "abc123"):
            self.assertIsNone(handler.valid_session_key(invalid), msg=f"session_key={invalid!r}")

    def test_emit_tags_the_record_with_the_session_key(self):
        """Test that a record carries the chat session key while one is set, and not otherwise."""
        self.queue = queue.Queue(maxsize=10)
        record = logging.LogRecord("test", logging.INFO, __file__, 1, "a message", None, None)
        log_handler = handler.RedisLogHandler()
        session_key = "a" * 64
        with patch(f"{MODULE}.log_queue", self.queue):
            token = handler.session_key_context.set(session_key)
            try:
                log_handler.emit(record)
            finally:
                handler.session_key_context.reset(token)
            log_handler.emit(record)
        payloads = [json.loads(self.queue.get_nowait()["data"]) for _ in range(2)]
        self.assertEqual([payload.get("session_key") for payload in payloads], [session_key, None])

    def test_bind_log_context_with_a_session_key(self):
        """Test that a bound function runs with the chat session key of its binding."""
        token = handler.session_key_context.set("a" * 64)
        try:
            bound = handler.bind_log_context(handler.session_key_context.get)
        finally:
            handler.session_key_context.reset(token)
        self.assertEqual(bound(), "a" * 64)
        self.assertIsNone(handler.session_key_context.get())
