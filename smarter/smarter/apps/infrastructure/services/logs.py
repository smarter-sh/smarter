"""
The log service: the platform's pod logs, from the log store.

The Helm chart keeps the last 72 hours of the logs of the app, the Celery workers, beat and
MariaDB in `Loki <https://grafana.com/oss/loki/>`__, which `Grafana Alloy
<https://grafana.com/docs/alloy/latest/>`__ fills. Alloy labels each line with its
``component`` (the pod's ``app.kubernetes.io/name``, e.g. ``smarter-worker``), ``pod`` and
``container``, and redacts email addresses, IP addresses, tokens, api keys and passwords
before it is stored. See ``helm/charts/smarter/values.yaml``.

Loki does not depend on a cloud, so :class:`LogService` is implemented by
:class:`LokiLogService`, at ``smarter_settings.loki_url``, for every cloud provider. Tests and
local development use :class:`InMemoryLogService`, installed with :func:`configure_logs`.

.. code-block:: python

    from datetime import timedelta

    from smarter.apps.infrastructure.services import infrastructure
    from smarter.apps.infrastructure.services.logs import LogQuery

    lines = infrastructure.logs.query(
        LogQuery.last(timedelta(hours=1), components=("smarter-worker",), contains=("ERROR",))
    )

A :class:`LogQuery` is structured, not LogQL: the service builds the query itself, and escapes
every value, so that a caller, e.g. an LLM's tool call, cannot inject LogQL.
"""

import re
from abc import abstractmethod
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from typing import Callable, Literal, Optional, Union

import requests
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from smarter.apps.infrastructure.const import InfrastructureServiceNames
from smarter.apps.infrastructure.exceptions import LogServiceError
from smarter.apps.infrastructure.services.base import (
    InfrastructureService,
    refuse_in_unit_tests,
)
from smarter.common.conf import smarter_settings
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.unittest import running_unit_tests

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.INFRASTRUCTURE_LOGGING])

LOG_RETENTION = timedelta(hours=72)
"""How long the log store keeps a line: ``limits_config.retention_period`` in the Helm chart's Loki."""

MAX_QUERY_LINES = 5000
"""The most lines that one query returns: Loki's default ``max_entries_limit_per_query``."""

REQUEST_TIMEOUT = 30
"""Seconds to wait for Loki to answer a query."""

LABEL_VALUE = re.compile(r"^[a-z0-9]([a-z0-9.-]{0,251}[a-z0-9])?$")
"""A Kubernetes name: what a ``component`` or ``pod`` label may be."""

RE2_SPECIAL = frozenset("\\.+*?()|[]{}^$-")
"""The characters that RE2, the regular expressions of LogQL, gives a meaning, and that :func:`re2_escape` escapes."""


class LogLevel(StrEnum):
    """The level of a log line, as :func:`parse_level` reads it from the line's text."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


LOG_LEVEL_PATTERNS: tuple[tuple[LogLevel, re.Pattern], ...] = (
    # the platform's formats, "- ERROR -" and "] ERROR ", Celery's "ERROR/MainProcess", and MariaDB's "[ERROR]".
    (LogLevel.CRITICAL, re.compile(r"\b(CRITICAL|FATAL)\b")),
    (LogLevel.ERROR, re.compile(r"\bERROR\b|\[ERROR\]")),
    (LogLevel.WARNING, re.compile(r"\bWARNING\b|\[Warning\]")),
    (LogLevel.INFO, re.compile(r"\bINFO\b|\[Note\]")),
    (LogLevel.DEBUG, re.compile(r"\bDEBUG\b")),
)


LOG_LEVEL_ORDER: tuple[LogLevel, ...] = (
    LogLevel.DEBUG,
    LogLevel.INFO,
    LogLevel.WARNING,
    LogLevel.ERROR,
    LogLevel.CRITICAL,
)
"""The levels, least severe first."""

LOG_LEVEL_RE2: dict[LogLevel, str] = {
    LogLevel.DEBUG: r"\bDEBUG\b",
    LogLevel.INFO: r"\bINFO\b|\[Note\]",
    LogLevel.WARNING: r"\bWARNING\b|\[Warning\]",
    LogLevel.ERROR: r"\bERROR\b|\[ERROR\]",
    LogLevel.CRITICAL: r"\bCRITICAL\b|\bFATAL\b",
}
"""Each level as an RE2 regular expression, for Loki to filter by, as :data:`LOG_LEVEL_PATTERNS` reads it."""


def at_least(level: Optional[LogLevel], minimum: LogLevel) -> bool:
    """Whether a level is at least as severe as a minimum.

    A line without a level is not.
    """
    return level is not None and LOG_LEVEL_ORDER.index(level) >= LOG_LEVEL_ORDER.index(minimum)


def parse_level(line: str) -> Optional[LogLevel]:
    """
    Return the level of a log line, from its text.

    The platform's lines put their level near the start, so only the first 120 characters are
    read, which keeps a message that mentions "ERROR" from making an INFO line an error.

    :param line: The line.
    :returns: The level, or None if the line names none, e.g. a traceback's continuation.
    """
    head = line[:120]
    for level, pattern in LOG_LEVEL_PATTERNS:
        if pattern.search(head):
            return level
    return None


class LogLine(BaseModel):
    """One line of a pod's log."""

    model_config = ConfigDict(frozen=True)

    timestamp: datetime
    """When the line was written, in UTC."""

    component: str = ""
    """The pod's ``app.kubernetes.io/name``, e.g. ``smarter``, ``smarter-worker`` or ``mariadb``."""

    pod: str = ""
    """The pod's name."""

    container: str = ""
    """The container's name."""

    line: str
    """The line's text, as stored: already redacted."""

    @property
    def level(self) -> Optional[LogLevel]:
        """The line's level, from its text."""
        return parse_level(self.line)


class LogQuery(BaseModel):
    """
    A query of the pod logs.

    Every value is validated, and the service escapes it, so a query cannot carry LogQL of its own.

    :param start: The earliest time, in UTC. It may not be earlier than :data:`LOG_RETENTION` ago.
    :param end: The latest time, in UTC.
    :param components: The components to read, e.g. ``("smarter", "smarter-worker")``, or all of them.
    :param pod: One pod's name, or every pod of the components.
    :param contains: Text that every line must contain, case insensitively.
    :param pattern: A regular expression (RE2 syntax) that every line must match.
    :param min_level: The least severe level to return, e.g. ``warning`` for warnings, errors and
        critical lines. Lines without a level, e.g. a traceback's continuation, are then left out.
    :param limit: The most lines to return.
    :param direction: ``backward`` returns the latest lines first, ``forward`` the earliest.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    start: datetime
    end: datetime
    components: tuple[str, ...] = ()
    pod: Optional[str] = None
    contains: tuple[str, ...] = ()
    pattern: Optional[str] = None
    min_level: Optional[LogLevel] = None
    limit: int = Field(default=200, ge=1, le=MAX_QUERY_LINES)
    direction: Literal["backward", "forward"] = "backward"

    @classmethod
    def last(cls, period: timedelta, **kwargs) -> "LogQuery":
        """
        Return a query of the most recent period, e.g. the last hour.

        :param period: How far back to read, at most :data:`LOG_RETENTION`.
        :param kwargs: The query's other fields.
        """
        end = datetime.now(timezone.utc)
        return cls(start=end - min(period, LOG_RETENTION), end=end, **kwargs)

    @field_validator("start", "end")
    @classmethod
    def utc(cls, value: datetime) -> datetime:
        """A time without a time zone is UTC."""
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)

    @field_validator("components")
    @classmethod
    def valid_components(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        """Each component is a Kubernetes name."""
        for component in value:
            if not LABEL_VALUE.match(component):
                raise ValueError(f"{component!r} is not a component name")
        return value

    @field_validator("pod")
    @classmethod
    def valid_pod(cls, value: Optional[str]) -> Optional[str]:
        """The pod is a Kubernetes name."""
        if value is not None and not LABEL_VALUE.match(value):
            raise ValueError(f"{value!r} is not a pod name")
        return value

    @field_validator("contains")
    @classmethod
    def valid_contains(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        """Each text is a single line, of at most 200 characters."""
        for text in value:
            if not text or len(text) > 200 or "\n" in text:
                raise ValueError("each text must be one line of 1 to 200 characters")
        return value

    @field_validator("pattern")
    @classmethod
    def valid_pattern(cls, value: Optional[str]) -> Optional[str]:
        """The pattern compiles, and is at most 200 characters."""
        if value is None:
            return None
        if len(value) > 200:
            raise ValueError("the pattern must be at most 200 characters")
        try:
            re.compile(value)
        except re.error as e:
            raise ValueError(f"the pattern is not a valid regular expression: {e}") from e
        return value

    @model_validator(mode="after")
    def valid_period(self) -> "LogQuery":
        """The period ends after it starts, and starts within the retention period."""
        if self.end <= self.start:
            raise ValueError("end must be later than start")
        earliest = datetime.now(timezone.utc) - LOG_RETENTION - timedelta(minutes=5)
        if self.start < earliest:
            raise ValueError(f"start must be within the last {int(LOG_RETENTION.total_seconds() // 3600)} hours")
        return self

    def logql(self) -> str:
        """
        Return the query as LogQL, with every value escaped.

        :returns: e.g. ``{component=~"smarter|smarter-worker"} |~ "(?i)timeout"``.
        """
        if self.components:
            selector = f'component=~"{logql_string("|".join(re2_escape(c) for c in self.components))}"'
        else:
            selector = 'component=~".+"'
        if self.pod:
            selector += f', pod="{logql_string(self.pod)}"'
        query = "{" + selector + "}"
        for text in self.contains:
            query += f' |~ "{logql_string("(?i)" + re2_escape(text))}"'
        if self.pattern:
            query += f' |~ "{logql_string(self.pattern)}"'
        if self.min_level:
            levels = LOG_LEVEL_ORDER[LOG_LEVEL_ORDER.index(self.min_level) :]
            query += f' |~ "{logql_string("|".join(LOG_LEVEL_RE2[level] for level in levels))}"'
        return query


def re2_escape(text: str) -> str:
    """
    Escape text so that an RE2 regular expression matches it literally.

    Unlike :func:`re.escape`, it escapes only :data:`RE2_SPECIAL`: RE2 rejects an escaped space or
    letter, which :func:`re.escape` can produce.

    :param text: The text.
    :returns: The text, with each special character escaped with a backslash.
    """
    return "".join(f"\\{character}" if character in RE2_SPECIAL else character for character in text)


def logql_string(value: str) -> str:
    """
    Escape a value for a LogQL double-quoted string, whose escapes are Go's.

    :param value: The value.
    :returns: The value with backslashes and double quotes escaped.
    """
    return value.replace("\\", "\\\\").replace('"', '\\"')


class LogService(InfrastructureService):
    """The platform's pod logs, from the log store."""

    service_name = InfrastructureServiceNames.LOGS
    error_class = LogServiceError

    @abstractmethod
    def query(self, query: LogQuery) -> list[LogLine]:
        """
        Return the lines that match a query.

        :param query: The query.
        :returns: At most ``query.limit`` lines, latest first if ``query.direction`` is ``backward``.
        :raises LogServiceError: If the store could not be reached, or rejected the query.
        :raises InfrastructureNotReadyError: If there is no log store.
        """

    @abstractmethod
    def label_values(self, label: Literal["component", "pod"], start: datetime, end: datetime) -> list[str]:
        """
        Return the values of a label in a period, e.g. the pods that logged in the last hour.

        :param label: ``component`` or ``pod``.
        :param start: The earliest time, in UTC.
        :param end: The latest time, in UTC.
        :returns: The values, sorted.
        :raises LogServiceError: If the store could not be reached.
        :raises InfrastructureNotReadyError: If there is no log store.
        """


class LokiResultStream(BaseModel):
    """
    One stream of a Loki ``query_range`` result: its labels, and its lines.

    Each line is ``[nanoseconds, text]``, or ``[nanoseconds, text, metadata]`` when the line has
    structured metadata.
    """

    model_config = ConfigDict(extra="allow")

    stream: dict[str, str] = {}
    values: list[list[Union[str, dict[str, str]]]] = []


class LokiQueryData(BaseModel):
    """The ``data`` of a Loki ``query_range`` response, for a log query."""

    model_config = ConfigDict(extra="allow")

    resultType: str = "streams"  # noqa: N815 (Loki's name)
    result: list[LokiResultStream] = []


class LokiResponse(BaseModel):
    """The fields of a Loki api response that the service reads.

    Loki adds others, which are ignored.
    """

    model_config = ConfigDict(extra="allow")

    status: str = ""
    data: Optional[LokiQueryData] = None


class LokiLabelsResponse(BaseModel):
    """A Loki ``label/<name>/values`` response."""

    model_config = ConfigDict(extra="allow")

    status: str = ""
    data: list[str] = []


def nanoseconds(value: datetime) -> str:
    """Return a time as Unix nanoseconds, as Loki's api takes and returns it."""
    return str(int(value.timestamp() * 1_000_000_000))


def from_nanoseconds(value: str) -> datetime:
    """Return a Unix nanoseconds timestamp, from Loki's api, as a UTC time."""
    return datetime.fromtimestamp(int(value) / 1_000_000_000, tz=timezone.utc)


class LokiLogService(LogService):
    """
    The pod logs, in Loki at ``smarter_settings.loki_url``.

    It is ready when the url is set. In the unit tests, it refuses to query, unless ``allow_in_tests``
    is True, e.g. with ``requests`` mocked. Loki is in the platform's namespace, so the url is a
    private, in-cluster address, and redirects are not followed.

    :param allow_in_tests: Query in the unit tests.
    """

    def __init__(self, allow_in_tests: bool = False, **kwargs):
        super().__init__(provider_name="loki", **kwargs)
        self.allow_in_tests = allow_in_tests

    @property
    def ready(self) -> bool:
        if running_unit_tests() and not self.allow_in_tests:
            return False
        return bool(smarter_settings.loki_url)

    def _get(self, path: str, params: dict[str, str]) -> requests.Response:
        """
        Send a GET to Loki's api.

        :param path: The api path, e.g. ``/loki/api/v1/query_range``.
        :param params: The query string.
        :returns: The response, which is 200.
        :raises LogServiceError: If Loki could not be reached, or did not answer 200.
        """
        refuse_in_unit_tests("Loki", self.allow_in_tests)
        self.require_ready()
        try:
            response = requests.get(
                f"{smarter_settings.loki_url}{path}", params=params, timeout=REQUEST_TIMEOUT, allow_redirects=False
            )
        except requests.exceptions.RequestException as e:
            self.connection_state(False, type(e).__name__)
            raise LogServiceError(f"Loki could not be reached: {type(e).__name__}") from e
        self.connection_state(True)
        if response.status_code != 200:
            # Loki explains a rejected query in plain text, e.g. a bad regular expression.
            raise LogServiceError(f"Loki answered HTTP {response.status_code}: {response.text[:300].strip()}")
        return response

    def query(self, query: LogQuery) -> list[LogLine]:
        response = self._get(
            "/loki/api/v1/query_range",
            {
                "query": query.logql(),
                "start": nanoseconds(query.start),
                "end": nanoseconds(query.end),
                "limit": str(query.limit),
                "direction": query.direction,
            },
        )
        try:
            body = LokiResponse.model_validate(response.json())
        except ValueError as e:
            raise LogServiceError("Loki's response is not a query response") from e
        lines = [
            LogLine(
                timestamp=from_nanoseconds(str(value[0])),
                component=stream.stream.get("component", ""),
                pod=stream.stream.get("pod", ""),
                container=stream.stream.get("container", ""),
                line=str(value[1]),
            )
            for stream in (body.data.result if body.data else [])
            for value in stream.values
            if len(value) >= 2
        ]
        # Loki limits each query, but orders lines only within a stream.
        lines.sort(key=lambda line: line.timestamp, reverse=query.direction == "backward")
        logger.debug("%s.query() %s returned %s lines", self.formatted_class_name, query.logql(), len(lines))
        return lines[: query.limit]

    def label_values(self, label: Literal["component", "pod"], start: datetime, end: datetime) -> list[str]:
        response = self._get(
            f"/loki/api/v1/label/{label}/values", {"start": nanoseconds(start), "end": nanoseconds(end)}
        )
        try:
            return sorted(LokiLabelsResponse.model_validate(response.json()).data)
        except ValueError as e:
            raise LogServiceError("Loki's response is not a label values response") from e


class InMemoryLogService(LogService):
    """
    Pod logs in memory, for tests and local development: add lines to :attr:`lines`.

    Queries are answered in Python: ``contains`` case insensitively, and ``pattern`` with
    :mod:`re`, which accepts the RE2 syntax that Loki uses for the patterns that matter here.

    :param ready: Whether the service is ready.
    """

    def __init__(self, ready: bool = True, **kwargs):
        super().__init__(provider_name="memory", **kwargs)
        self._ready = ready
        self.lines: list[LogLine] = []
        self.queries: list[LogQuery] = []
        """Every query, in order, for tests to inspect."""

    @property
    def ready(self) -> bool:
        return self._ready

    def matches(self, query: LogQuery, line: LogLine) -> bool:
        """Whether a line matches a query."""
        if not query.start <= line.timestamp <= query.end:
            return False
        if query.components and line.component not in query.components:
            return False
        if query.pod and line.pod != query.pod:
            return False
        if any(text.lower() not in line.line.lower() for text in query.contains):
            return False
        if query.min_level and not at_least(line.level, query.min_level):
            return False
        return not (query.pattern and not re.search(query.pattern, line.line))

    def query(self, query: LogQuery) -> list[LogLine]:
        self.require_ready()
        self.queries.append(query)
        lines = sorted(
            (line for line in self.lines if self.matches(query, line)),
            key=lambda line: line.timestamp,
            reverse=query.direction == "backward",
        )
        return lines[: query.limit]

    def label_values(self, label: Literal["component", "pod"], start: datetime, end: datetime) -> list[str]:
        self.require_ready()
        return sorted({getattr(line, label) for line in self.lines if start <= line.timestamp <= end})


_logs_factory: Optional[Callable[[], LogService]] = None
_logs: Optional[LogService] = None


def configure_logs(factory: Optional[Callable[[], LogService]]) -> None:
    """
    Set the factory of the log service that :func:`get_logs` returns.

    :param factory: Returns the service, or None to restore the default, :class:`LokiLogService`.
    """
    global _logs_factory, _logs  # pylint: disable=global-statement
    _logs_factory = factory
    _logs = None


def get_logs() -> LogService:
    """Return the log service, which is created once."""
    global _logs  # pylint: disable=global-statement
    if _logs is None:
        _logs = _logs_factory() if _logs_factory is not None else LokiLogService()
    return _logs


__all__ = [
    "LOG_LEVEL_ORDER",
    "LOG_RETENTION",
    "MAX_QUERY_LINES",
    "InMemoryLogService",
    "LogLevel",
    "LogLine",
    "LogQuery",
    "LogService",
    "LokiLogService",
    "at_least",
    "configure_logs",
    "get_logs",
    "logql_string",
    "parse_level",
    "re2_escape",
]
