"""
Test :mod:`smarter.apps.infrastructure.services.logs`.

Nothing reaches Loki: the Loki service's ``requests.get`` is a fake, and the other tests use the
in-memory log service.
"""

import re
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import requests
from pydantic import ValidationError

from smarter.apps.infrastructure.exceptions import (
    InfrastructureConfigurationError,
    InfrastructureNotReadyError,
    LogServiceError,
)
from smarter.apps.infrastructure.services import (
    InMemoryLogService,
    LogLine,
    LogQuery,
    LokiLogService,
    configure_logs,
    get_logs,
    infrastructure,
)
from smarter.apps.infrastructure.services.logs import (
    LOG_RETENTION,
    LogLevel,
    at_least,
    from_nanoseconds,
    logql_string,
    nanoseconds,
    parse_level,
    re2_escape,
)

from .base import InfrastructureTestBase

MODULE = "smarter.apps.infrastructure.services.logs"
LOKI_URL = "http://loki.test:3100"
NOW = datetime.now(timezone.utc)


def line(text: str, minutes_ago: int = 1, component: str = "smarter", pod: str = "smarter-abc") -> LogLine:
    """A log line, written some minutes ago."""
    return LogLine(
        timestamp=NOW - timedelta(minutes=minutes_ago), component=component, pod=pod, container=component, line=text
    )


def response(body=None, status_code: int = 200, text: str = "") -> MagicMock:
    """A fake requests.Response, whose json() is ``body``."""
    fake = MagicMock(status_code=status_code, text=text)
    if isinstance(body, Exception):
        fake.json.side_effect = body
    else:
        fake.json.return_value = body
    return fake


class TestParseLevel(InfrastructureTestBase):
    """Test parse_level() on each format that the platform's pods write."""

    def test_formats(self):
        cases = {
            "[2026-11-02 14:00:00 +0000] - ERROR - MainProcess - smarter.x boom": LogLevel.ERROR,
            "[2026-11-02 14:00:00] INFO 10.0.0.1 GET /": LogLevel.INFO,
            "[2026-11-02 14:00:00,123: WARNING/ForkPoolWorker-1] retrying": LogLevel.WARNING,
            "2026-11-02 14:00:00 0 [ERROR] InnoDB: something": LogLevel.ERROR,
            "2026-11-02 14:00:00 0 [Warning] Aborted connection": LogLevel.WARNING,
            "2026-11-02 14:00:00 0 [Note] mariadbd: ready": LogLevel.INFO,
            "[x] - CRITICAL - MainProcess - down": LogLevel.CRITICAL,
            "[x] - DEBUG - MainProcess - detail": LogLevel.DEBUG,
            '  File "/x.py", line 1, in <module>': None,
        }
        for text, level in cases.items():
            self.assertEqual(parse_level(text), level, text)

    def test_only_the_head_is_read(self):
        """A message that mentions ERROR late in an INFO line is INFO."""
        self.assertEqual(parse_level("[x] - INFO - p - " + "x" * 200 + " ERROR"), LogLevel.INFO)
        self.assertEqual(line("[x] - ERROR - p - boom").level, LogLevel.ERROR)


class TestEscaping(InfrastructureTestBase):
    """Test re2_escape() and logql_string()."""

    def test_re2_escape(self):
        self.assertEqual(re2_escape("a.b (c) d-e"), r"a\.b \(c\) d\-e")
        self.assertEqual(re2_escape("plain text 123"), "plain text 123", "spaces and letters are never escaped")
        escaped = re2_escape("x.*+?|[]{}^$\\")
        self.assertTrue(re.fullmatch(escaped, "x.*+?|[]{}^$\\"))

    def test_logql_string(self):
        self.assertEqual(logql_string('a"b\\c'), 'a\\"b\\\\c')


class TestLogQuery(InfrastructureTestBase):
    """Test LogQuery's validation and its LogQL."""

    def test_last(self):
        query = LogQuery.last(timedelta(hours=1))
        self.assertAlmostEqual((query.end - query.start).total_seconds(), 3600, delta=1)
        capped = LogQuery.last(timedelta(days=30))
        self.assertLessEqual(capped.end - capped.start, LOG_RETENTION)

    def test_naive_times_are_utc(self):
        query = LogQuery(start=(NOW - timedelta(hours=1)).replace(tzinfo=None), end=NOW.replace(tzinfo=None))
        self.assertEqual(query.start.tzinfo, timezone.utc)

    def test_logql(self):
        query = LogQuery.last(
            timedelta(hours=1),
            components=("smarter", "smarter-worker"),
            pod="smarter-worker-abc",
            contains=('say "hi" (now)',),
            pattern=r"took \d+s",
        )
        self.assertEqual(
            query.logql(),
            '{component=~"smarter|smarter\\\\-worker", pod="smarter-worker-abc"}'
            ' |~ "(?i)say \\"hi\\" \\\\(now\\\\)"'
            ' |~ "took \\\\d+s"',
        )

    def test_logql_of_min_level(self):
        query = LogQuery.last(timedelta(hours=1), min_level=LogLevel.ERROR)
        self.assertEqual(
            query.logql(),
            '{component=~".+"} |~ "\\\\bERROR\\\\b|\\\\[ERROR\\\\]|\\\\bCRITICAL\\\\b|\\\\bFATAL\\\\b"',
        )

    def test_logql_of_every_component(self):
        self.assertEqual(LogQuery.last(timedelta(hours=1)).logql(), '{component=~".+"}')

    def test_invalid(self):
        hour = timedelta(hours=1)
        invalid = [
            {"components": ('smarter"}|',)},
            {"pod": "Pod With Spaces"},
            {"contains": ("",)},
            {"contains": ("a\nb",)},
            {"contains": ("x" * 201,)},
            {"pattern": "("},
            {"pattern": "x" * 201},
            {"limit": 0},
            {"limit": 5001},
            {"direction": "sideways"},
        ]
        for kwargs in invalid:
            with self.assertRaises(ValidationError, msg=str(kwargs)):
                LogQuery.last(hour, **kwargs)
        with self.assertRaises(ValidationError):
            LogQuery(start=NOW, end=NOW - hour)
        with self.assertRaises(ValidationError):
            LogQuery(start=NOW - timedelta(days=4), end=NOW)
        self.assertIsNone(LogQuery.last(hour, pattern=None).pattern)


class TestConfigureLogs(InfrastructureTestBase):
    """Test configure_logs(), get_logs() and infrastructure.logs."""

    def test_default_is_loki(self):
        configure_logs(None)
        self.assertIsInstance(get_logs(), LokiLogService)
        self.assertIs(get_logs(), get_logs())

    def test_configured(self):
        logs = InMemoryLogService()
        configure_logs(lambda: logs)
        self.assertIs(infrastructure.logs, logs)


class TestInMemoryLogService(InfrastructureTestBase):
    """Test InMemoryLogService."""

    def setUp(self):
        super().setUp()
        self.logs = InMemoryLogService()
        self.logs.lines = [
            line("[x] - ERROR - p - Timeout talking to OpenAI", minutes_ago=5),
            line("[x] - INFO - p - all good", minutes_ago=4),
            line(
                "[x] - ERROR - p - timeout in task", minutes_ago=3, component="smarter-worker", pod="smarter-worker-1"
            ),
            line("[x] - INFO - p - old", minutes_ago=600),
        ]

    def test_query(self):
        lines = self.logs.query(LogQuery.last(timedelta(hours=1), contains=("TIMEOUT",)))
        self.assertEqual([x.line for x in lines], [self.logs.lines[2].line, self.logs.lines[0].line])
        forward = self.logs.query(LogQuery.last(timedelta(hours=1), contains=("timeout",), direction="forward"))
        self.assertEqual(forward[0].line, self.logs.lines[0].line)
        self.assertEqual(len(self.logs.queries), 2)

    def test_filters(self):
        hour = timedelta(hours=1)
        self.assertEqual(len(self.logs.query(LogQuery.last(hour, components=("smarter-worker",)))), 1)
        self.assertEqual(len(self.logs.query(LogQuery.last(hour, pod="smarter-worker-1"))), 1)
        self.assertEqual(len(self.logs.query(LogQuery.last(hour, pattern=r"all \w+"))), 1)
        self.assertEqual(len(self.logs.query(LogQuery.last(hour, limit=1))), 1)
        self.assertEqual(len(self.logs.query(LogQuery.last(timedelta(hours=24)))), 4)

    def test_min_level(self):
        lines = self.logs.query(LogQuery.last(timedelta(hours=24), min_level=LogLevel.WARNING))
        self.assertEqual(len(lines), 2)
        self.assertTrue(at_least(LogLevel.CRITICAL, LogLevel.ERROR))
        self.assertFalse(at_least(LogLevel.INFO, LogLevel.WARNING))
        self.assertFalse(at_least(None, LogLevel.DEBUG))

    def test_label_values(self):
        self.assertEqual(
            self.logs.label_values("component", NOW - timedelta(hours=1), NOW), ["smarter", "smarter-worker"]
        )
        self.assertEqual(
            self.logs.label_values("pod", NOW - timedelta(hours=1), NOW), ["smarter-abc", "smarter-worker-1"]
        )

    def test_not_ready(self):
        logs = InMemoryLogService(ready=False)
        with self.assertRaises(InfrastructureNotReadyError):
            logs.query(LogQuery.last(timedelta(hours=1)))
        with self.assertRaises(InfrastructureNotReadyError):
            logs.label_values("pod", NOW - timedelta(hours=1), NOW)


class TestLokiLogService(InfrastructureTestBase):
    """Test LokiLogService, with requests.get faked."""

    def setUp(self):
        super().setUp()
        self.loki = LokiLogService(allow_in_tests=True)
        settings = patch(f"{MODULE}.smarter_settings", MagicMock(loki_url=LOKI_URL))
        settings.start()
        self.addCleanup(settings.stop)
        get = patch(f"{MODULE}.requests.get")
        self.get = get.start()
        self.addCleanup(get.stop)

    def test_ready(self):
        self.assertTrue(self.loki.ready)
        self.assertFalse(LokiLogService().ready, "never ready in the unit tests")
        with patch(f"{MODULE}.smarter_settings", MagicMock(loki_url="")):
            self.assertFalse(self.loki.ready)

    def test_refuses_in_unit_tests(self):
        with self.assertRaises(InfrastructureConfigurationError):
            LokiLogService().query(LogQuery.last(timedelta(hours=1)))
        self.get.assert_not_called()

    def test_query(self):
        older, newer = NOW - timedelta(minutes=2), NOW - timedelta(minutes=1)
        self.get.return_value = response(
            {
                "status": "success",
                "data": {
                    "resultType": "streams",
                    "result": [
                        {
                            "stream": {"component": "smarter", "pod": "smarter-a", "container": "smarter"},
                            "values": [[nanoseconds(older), "first"]],
                        },
                        {
                            "stream": {"component": "smarter-worker", "pod": "smarter-worker-a"},
                            "values": [[nanoseconds(newer), "second", {"trace_id": "x"}], ["1"]],
                        },
                    ],
                },
            }
        )
        query = LogQuery.last(timedelta(hours=1), contains=("x",), limit=10)
        lines = self.loki.query(query)
        self.assertEqual([x.line for x in lines], ["second", "first"], "latest first, across streams")
        self.assertEqual(lines[0].component, "smarter-worker")
        self.assertEqual(lines[1].container, "smarter")
        args, kwargs = self.get.call_args
        self.assertEqual(args[0], f"{LOKI_URL}/loki/api/v1/query_range")
        self.assertEqual(kwargs["params"]["query"], query.logql())
        self.assertEqual(kwargs["params"]["limit"], "10")
        self.assertEqual(kwargs["params"]["direction"], "backward")
        self.assertFalse(kwargs["allow_redirects"])

    def test_query_limit_and_empty(self):
        self.get.return_value = response({"status": "success", "data": None})
        self.assertEqual(self.loki.query(LogQuery.last(timedelta(hours=1))), [])

    def test_label_values(self):
        self.get.return_value = response({"status": "success", "data": ["smarter-worker", "smarter"]})
        self.assertEqual(
            self.loki.label_values("component", NOW - timedelta(hours=1), NOW), ["smarter", "smarter-worker"]
        )
        self.assertEqual(self.get.call_args.args[0], f"{LOKI_URL}/loki/api/v1/label/component/values")

    def test_failures(self):
        query = LogQuery.last(timedelta(hours=1))
        self.get.side_effect = requests.exceptions.ConnectionError("down")
        with self.assertRaisesRegex(LogServiceError, "could not be reached: ConnectionError"):
            self.loki.query(query)
        self.get.side_effect = None
        self.get.return_value = response(status_code=400, text="parse error: invalid regex")
        with self.assertRaisesRegex(LogServiceError, "HTTP 400: parse error"):
            self.loki.query(query)
        self.get.return_value = response(ValueError("not json"))
        with self.assertRaisesRegex(LogServiceError, "not a query response"):
            self.loki.query(query)
        with self.assertRaisesRegex(LogServiceError, "not a label values response"):
            self.loki.label_values("pod", NOW - timedelta(hours=1), NOW)

    def test_not_configured(self):
        with patch(f"{MODULE}.smarter_settings", MagicMock(loki_url="")):
            with self.assertRaises(InfrastructureNotReadyError):
                self.loki.query(LogQuery.last(timedelta(hours=1)))


class TestNanoseconds(InfrastructureTestBase):
    """Test the conversions to and from Loki's timestamps."""

    def test_round_trip(self):
        when = datetime(2026, 11, 2, 14, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(nanoseconds(when), "1793628000000000000")
        self.assertEqual(from_nanoseconds(nanoseconds(when)), when)
