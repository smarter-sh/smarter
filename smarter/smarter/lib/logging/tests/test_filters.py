"""Test :mod:`smarter.lib.logging.filters`."""

import asyncio
import logging

from smarter.lib.logging.filters import AsyncioShieldedCancelFilter, HealthCheckFilter
from smarter.lib.unittest.base_classes import SmarterTestBase


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

    def test_keeps_other_loggers(self):
        """The same message from a logger other than asyncio is emitted."""
        self.assertTrue(self.filter.filter(self.record("smarter", "CancelledError exception in shielded future")))

    def test_keeps_unformattable_record(self):
        """A record whose message can't be formatted is passed on, not swallowed."""
        self.assertTrue(self.filter.filter(self.record("asyncio", "%d", ("not a number",))))

    def test_asyncio_logger_is_configured(self):
        """Settings.LOGGING attaches the filter to the asyncio logger."""
        filters = logging.getLogger("asyncio").filters
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
