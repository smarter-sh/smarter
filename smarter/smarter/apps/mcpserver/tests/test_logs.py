"""Tests for smarter.apps.mcpserver.services.logs."""

from datetime import datetime, timedelta, timezone

from smarter.apps.infrastructure.services import LogLine
from smarter.apps.infrastructure.services.logs import LogLevel
from smarter.apps.mcpserver.exceptions import SmarterMCPServerServiceError
from smarter.apps.mcpserver.services.logs import (
    MAX_LINE_CHARACTERS,
    error_groups,
    format_line,
    log_errors,
    log_sources,
    search_logs,
    short,
    signature,
)
from smarter.lib.unittest.base_classes import SmarterTestBase

from .operations_base import OperationsTestBase

NOW = datetime(2026, 11, 2, 14, 0, 0, tzinfo=timezone.utc)


def line(text: str, seconds: int = 0, component: str = "smarter", pod: str = "smarter-a") -> LogLine:
    """A log line, written some seconds after NOW."""
    return LogLine(timestamp=NOW + timedelta(seconds=seconds), component=component, pod=pod, line=text)


class TestSignature(SmarterTestBase):
    """Test signature()."""

    def test_variable_parts(self):
        a = signature("[2026-11-02 13:20:00 +0000] - ERROR - MainProcess - timeout after 30s, request 1001 for 'abc'")
        b = signature("[2026-11-02 13:30:00 +0000] - ERROR - MainProcess - timeout after 31s, request 1002 for 'xyz'")
        self.assertEqual(a, b)
        self.assertEqual(a, "ERROR - MainProcess - timeout after Ns, request N for <str>")

    def test_ids_and_formats(self):
        self.assertEqual(
            signature("[2026-11-02 13:45:00,123: WARNING/ForkPoolWorker-1] task 0123456789abcdef0123 done"),
            "WARNING/ForkPoolWorker-N] task <hash> done",
        )
        self.assertEqual(
            signature("2026-11-02 13:55:00 0 [Warning] id 6f1c2b3a-1111-2222-3333-444455556666"),
            "N [Warning] id <uuid>",
        )
        self.assertEqual(len(signature("x " * 300)), 200)


class TestFormatting(SmarterTestBase):
    """Test short() and format_line()."""

    def test_short(self):
        self.assertEqual(short("abc"), "abc")
        long = "x" * (MAX_LINE_CHARACTERS + 10)
        self.assertEqual(len(short(long)), MAX_LINE_CHARACTERS)
        self.assertTrue(short(long).endswith("…"))

    def test_format_line(self):
        self.assertEqual(format_line(line("hello", pod="smarter-b")), "2026-11-02 14:00:00 smarter/smarter-b: hello")


class TestErrorGroups(SmarterTestBase):
    """Test error_groups()."""

    def test_groups(self):
        groups = error_groups(
            [
                line("- ERROR - p - timeout after 30s", seconds=1, pod="smarter-a"),
                line("- ERROR - p - timeout after 31s", seconds=3, pod="smarter-b"),
                line("- ERROR - p - timeout after 29s", seconds=2, pod="smarter-a"),
                line("- ERROR - p - timeout after 29s", seconds=4, component="smarter-worker"),
                line("- WARNING - p - slow", seconds=5),
            ]
        )
        self.assertEqual(
            [(g.component, g.count) for g in groups], [("smarter", 3), ("smarter", 1), ("smarter-worker", 1)]
        )
        first = groups[0]
        self.assertEqual(first.level, LogLevel.ERROR)
        self.assertEqual(first.pods, {"smarter-a", "smarter-b"})
        self.assertEqual(first.first_seen, NOW + timedelta(seconds=1))
        self.assertEqual(first.last_seen, NOW + timedelta(seconds=3))
        self.assertEqual(first.example, "- ERROR - p - timeout after 31s", "the latest line")
        self.assertEqual(groups[1].level, LogLevel.WARNING, "groups of one: the most recent first")

    def test_nothing(self):
        self.assertEqual(error_groups([]), [])


class TestLogReading(OperationsTestBase):
    """Test log_sources, search_logs, log_errors and log_query, with the in-memory log service."""

    def test_log_sources(self):
        """The components and pods that wrote, and the components that wrote nothing."""
        sources = log_sources(60)
        self.assertIn("smarter", sources.components)
        self.assertEqual(sources.missing, ["smarter-worker-infrastructure"])
        self.assertIn("smarter-mariadb-0", sources.pods)

    def test_search_logs(self):
        """The filters reach the query, and only lines of at least the level are kept."""
        lines = search_logs(60, 50, components=("smarter",), contains=("TIMEOUT",))
        self.assertEqual(len(lines), 3)
        self.assertEqual(self.logs.queries[-1].components, ("smarter",))
        leveled = search_logs(60, 50, min_level=LogLevel.WARNING)
        self.assertEqual(len(leveled), 6)
        search_logs(60, 5, oldest_first=True)
        self.assertEqual(self.logs.queries[-1].direction, "forward")

    def test_log_errors(self):
        """The errors are grouped by their signature."""
        errors = log_errors(60, LogLevel.ERROR)
        self.assertEqual(errors.lines, 3)
        self.assertFalse(errors.truncated)
        self.assertEqual(len(errors.groups), 1)
        self.assertEqual(errors.groups[0].count, 3)
        none = log_errors(60, LogLevel.ERROR, components=("smarter-beat",))
        self.assertEqual((none.lines, none.groups), (0, []))

    def test_invalid_query(self):
        """A query that is not valid is a service error that says why."""
        with self.assertRaisesRegex(SmarterMCPServerServiceError, "invalid log query: .*regular expression"):
            search_logs(60, 5, pattern="(")
