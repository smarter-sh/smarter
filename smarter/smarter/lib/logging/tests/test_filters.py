"""Test :mod:`smarter.lib.logging.filters`."""

import asyncio

from smarter.common.utils import mask_identifier
from smarter.lib import logging
from smarter.lib.logging.filters import (
    AccessLogQueryFilter,
    AsyncioShieldedCancelFilter,
    HealthCheckFilter,
)
from smarter.lib.unittest.base_classes import SmarterTestBase

SESSION_KEY = "0123456789abcdef" * 4
"""A made-up 64-character session key."""

ACCESS_LOG_FORMAT = '%s - "%s %s HTTP/%s" %d'
"""The message of uvicorn's access log records."""


class TestAccessLogQueryFilter(SmarterTestBase):
    """Test AccessLogQueryFilter.filter(), and its configuration in settings.LOGGING (issue #1000)."""

    def setUp(self):
        super().setUp()
        self.filter = AccessLogQueryFilter()

    def record(self, name: str, args) -> logging.LogRecord:
        """Build a uvicorn access log record."""
        return logging.makeLogRecord({"name": name, "msg": ACCESS_LOG_FORMAT, "args": args})

    def test_masks_the_session_key(self):
        """The session_key in the path's query is masked, and the record is still emitted."""
        path = f"/api/v1/llm-clients/abc/config/?session_key={SESSION_KEY}"
        record = self.record("uvicorn.access", ("127.0.0.1:1", "POST", path, "1.1", 200))
        self.assertTrue(self.filter.filter(record))
        message = record.getMessage()
        self.assertNotIn(SESSION_KEY, message)
        self.assertIn(f"?session_key={mask_identifier(SESSION_KEY)}", message)
        self.assertIn("POST /api/v1/llm-clients/abc/config/", message)
        self.assertIn("200", message)

    def test_keeps_other_paths_unchanged(self):
        """A path without a sensitive parameter keeps the very same args."""
        args = ("127.0.0.1:1", "GET", "/api/v1/search/?q=hello%20world", "1.1", 200)
        record = self.record("uvicorn.access", args)
        self.assertTrue(self.filter.filter(record))
        self.assertIs(record.args, args)

    def test_keeps_other_loggers_and_malformed_records(self):
        """Other loggers, and records without a readable path, are emitted unchanged."""
        path = f"/config/?session_key={SESSION_KEY}"
        other_logger_args = ("127.0.0.1:1", "POST", path, "1.1", 200)
        other_logger_record = self.record("smarter", other_logger_args)
        self.assertTrue(self.filter.filter(other_logger_record))
        self.assertIs(other_logger_record.args, other_logger_args)

        no_args_record = logging.makeLogRecord({"name": "uvicorn.access", "args": None})
        self.assertTrue(self.filter.filter(no_args_record))
        short_record = self.record("uvicorn.access", ("127.0.0.1:1", "POST"))
        self.assertTrue(self.filter.filter(short_record))
        not_a_string_record = self.record("uvicorn.access", ("127.0.0.1:1", "POST", 5, "1.1", 200))
        self.assertTrue(self.filter.filter(not_a_string_record))

    def test_uvicorn_access_logger_is_configured(self):
        """Settings.LOGGING attaches the filter to the uvicorn.access logger itself."""
        filters = logging.getSmarterLogger("uvicorn.access").filters
        self.assertTrue(any(isinstance(f, AccessLogQueryFilter) for f in filters))

    def test_uvicorn_access_log_line_is_masked(self):
        """A record logged the way uvicorn logs it reaches the handlers with the key masked."""
        access_logger = logging.getSmarterLogger("uvicorn.access")
        path = f"/config/?session_key={SESSION_KEY}"
        with self.assertLogs("uvicorn.access", level="INFO") as captured:
            access_logger.info(ACCESS_LOG_FORMAT, "127.0.0.1:1", "POST", path, "1.1", 200)
        output = "\n".join(captured.output)
        self.assertNotIn(SESSION_KEY, output)
        self.assertIn(mask_identifier(SESSION_KEY), output)


class TestAsyncioShieldedCancelFilter(SmarterTestBase):
    """Test AsyncioShieldedCancelFilter.filter(), and its configuration in settings.LOGGING."""

    def setUp(self):
        super().setUp()
        self.filter = AsyncioShieldedCancelFilter()

    def record(self, name: str, msg: str, args=None) -> logging.LogRecord:
        """Build a log record."""
        return logging.makeLogRecord({"name": name, "msg": msg, "args": args})

    def test_suppresses_shielded_cancelled_error(self):
        """Asyncio's shielded-future CancelledError is dropped."""
        record = self.record(
            "asyncio",
            "CancelledError exception in shielded future\nfuture: <Future finished exception=CancelledError()>",
        )
        self.assertFalse(self.filter.filter(record))

    def test_keeps_other_asyncio_errors(self):
        """Any other asyncio error is still emitted, including other shielded-future exceptions."""
        self.assertTrue(self.filter.filter(self.record("asyncio", "Task exception was never retrieved")))
        self.assertTrue(self.filter.filter(self.record("asyncio", "ValueError exception in shielded future")))

    def test_suppresses_never_retrieved_cancelled_error(self):
        """Some Python builds log the shielded CancelledError as a never-retrieved future instead."""
        error = asyncio.CancelledError()
        record = self.record("asyncio", "Future exception was never retrieved")
        record.exc_info = (type(error), error, None)
        self.assertFalse(self.filter.filter(record))

    def test_keeps_never_retrieved_other_errors(self):
        """A never-retrieved future with any other exception, or none attached, is still emitted."""
        error = ValueError("boom")
        record = self.record("asyncio", "Future exception was never retrieved")
        record.exc_info = (type(error), error, None)
        self.assertTrue(self.filter.filter(record))
        self.assertTrue(self.filter.filter(self.record("asyncio", "Future exception was never retrieved")))

    def test_keeps_other_loggers(self):
        """The same message from a logger other than asyncio is emitted."""
        self.assertTrue(self.filter.filter(self.record("smarter", "CancelledError exception in shielded future")))

    def test_keeps_unformattable_record(self):
        """A record whose message can't be formatted is passed on, not swallowed."""
        self.assertTrue(self.filter.filter(self.record("asyncio", "%d", ("not a number",))))

    def test_asyncio_logger_is_configured(self):
        """Settings.LOGGING attaches the filter to the asyncio logger."""
        filters = logging.getSmarterLogger("asyncio").filters
        self.assertTrue(any(isinstance(f, AsyncioShieldedCancelFilter) for f in filters))

    def test_real_shielded_cancel_is_not_logged(self):
        """Reproduce asgiref's case: the outer task is cancelled, then the shielded future fails with CancelledError."""

        async def scenario():
            loop = asyncio.get_running_loop()
            inner = loop.create_future()

            async def outer():
                await asyncio.shield(inner)

            task = asyncio.ensure_future(outer())
            await asyncio.sleep(0)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            inner.set_exception(asyncio.CancelledError())
            await asyncio.sleep(0)

        with self.assertNoLogs("asyncio", level="ERROR"):
            asyncio.run(scenario())


class TestHealthCheckFilter(SmarterTestBase):
    """Test HealthCheckFilter.filter()."""

    def setUp(self):
        super().setUp()
        self.filter = HealthCheckFilter()

    def record(self, name: str, args) -> logging.LogRecord:
        """Build a log record."""
        return logging.makeLogRecord({"name": name, "msg": "%s - %s %s HTTP/%s %d", "args": args})

    def test_suppresses_health_check(self):
        """A uvicorn access log for a health check url is dropped."""
        path = f"/{self.filter.health_check_urls[0]}/"
        self.assertFalse(self.filter.filter(self.record("uvicorn.access", ("127.0.0.1:1", "GET", path, "1.1", 200))))

    def test_keeps_other_paths_and_loggers(self):
        """Other paths, other loggers and malformed args are emitted."""
        self.assertTrue(
            self.filter.filter(self.record("uvicorn.access", ("127.0.0.1:1", "GET", "/api/v1/", "1.1", 200)))
        )
        self.assertTrue(self.filter.filter(self.record("smarter", ("127.0.0.1:1", "GET", "/healthz/", "1.1", 200))))
        self.assertTrue(self.filter.filter(logging.makeLogRecord({"name": "uvicorn.access", "args": None})))
        self.assertTrue(self.filter.filter(self.record("uvicorn.access", ("127.0.0.1:1", "GET"))))
        self.assertTrue(self.filter.filter(self.record("uvicorn.access", ("127.0.0.1:1", "GET", 5, "1.1", 200))))
