"""
Test :mod:`smarter.lib.logging.redis_log_handler`.

Redis is faked, and the module's log_queue is replaced with a new queue in each
test, so that the running worker thread and the real Redis are never touched.
"""

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

    def test_flush_redis_not_ready(self):
        self.redis.ping.side_effect = ConnectionError("down")
        buffer = self.queued({"channel": "logs:a", "data": "one"})
        handler.flush(buffer)
        self.redis.pipeline.assert_not_called()
        self.assertEqual(self.queue.unfinished_tasks, 0)

    def test_flush_pipeline_error(self):
        self.redis.pipeline.return_value.execute.side_effect = Exception("pipeline failed")
        with patch(f"{MODULE}.logger") as logger:
            handler.flush(self.queued({"channel": "logs:a", "data": "one"}))
        logger.exception.assert_called_once()

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
            patch.dict(handler._redis_cache_holder, {"client": None}),  # pylint: disable=protected-access
            patch(f"{MODULE}.get_redis_connection", side_effect=ImproperlyConfigured("no redis")),
        ):
            self.assertIsNone(GET_REDIS_CACHE())

    def test_get_user_context(self):
        user = MagicMock(username="ada")
        self.assertEqual(handler.get_user_context(user), "MagicMock.ada")
        self.assertEqual(handler.get_user_context("job-1"), "str.job-1")

    def test_emit_queue_full(self):
        """Test that a log record is dropped, and counted, when the queue is full."""
        record = logging.LogRecord("test", logging.INFO, __file__, 1, "a message", None, None)
        log_handler = handler.RedisLogHandler()
        dropped = handler.RedisLogHandler.dropped_logs
        log_handler.emit(record)  # 2 payloads: the user's channel and the global channel.
        log_handler.emit(record)  # the queue is full after one more payload.
        self.assertEqual(self.queue.qsize(), 3)
        self.assertEqual(handler.RedisLogHandler.dropped_logs, dropped + 1)
