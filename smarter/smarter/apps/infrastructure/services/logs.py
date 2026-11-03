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

The MCPServer's staff-only log tools (:mod:`smarter.apps.mcpserver.protocol.tools.logs`), through
:mod:`smarter.apps.mcpserver.services.logs`, and its
help desk snapshot (:mod:`smarter.apps.mcpserver.services.helpdesk.users`) are the service's callers. The
service only reads: nothing is written to Loki, and nothing is cached.
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
"""Seconds to wait for Loki to answer a query, before :class:`LokiLogService` gives up with a :class:`~smarter.apps.infrastructure.exceptions.LogServiceError`."""

LABEL_VALUE = re.compile(r"^[a-z0-9]([a-z0-9.-]{0,251}[a-z0-9])?$")
"""
A Kubernetes name: what a ``component`` or ``pod`` label may be.

Lower-case letters, digits, dots and hyphens, starting and ending with a letter or digit, at most
253 characters. :class:`LogQuery` refuses any other component or pod, before it reaches LogQL.
"""

RE2_SPECIAL = frozenset("\\.+*?()|[]{}^$-")
"""The characters that RE2, the regular expressions of LogQL, gives a meaning, and that :func:`re2_escape` escapes."""


class LogLevel(StrEnum):
    """
    The level of a log line, as :func:`parse_level` reads it from the line's text.

    Loki stores lines as text, without a level, so the level is read from the words that the
    platform's, Celery's and MariaDB's formats put near the start of each line. The values are
    lower case, as an LLM writes them in a tool call, e.g. ``warning``.
    """

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
"""
How each level appears in a line's text, the most severe first.

:func:`parse_level` tries them in this order, so that a line that names two levels, e.g.
``ERROR ... WARNING``, takes the more severe one.
"""


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
"""
Each level as an RE2 regular expression, for Loki to filter by, as :data:`LOG_LEVEL_PATTERNS` reads it.

Loki matches the expression anywhere in the line, not only near its start, so a filtered query can
return a line whose own level is lower. Callers filter the result again with :func:`at_least`.
"""


def at_least(level: Optional[LogLevel], minimum: LogLevel) -> bool:
    """
    Return whether a level is at least as severe as a minimum.

    A line without a level, e.g. a traceback's continuation, is not.

    :param level: The line's level, or None.
    :param minimum: The least severe level, e.g. ``LogLevel.WARNING``.
    :returns: True if the level is the minimum, or more severe, by :data:`LOG_LEVEL_ORDER`.
    """
    if level is None:
        return False
    level_rank = LOG_LEVEL_ORDER.index(level)
    minimum_rank = LOG_LEVEL_ORDER.index(minimum)
    return level_rank >= minimum_rank


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
    """
    One line of a pod's log, with the labels that Alloy gave it.

    It is frozen: a line is read, never changed.
    """

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
        """The line's level, read from its text by :func:`parse_level`, or None if it names none."""
        return parse_level(self.line)


class LogQuery(BaseModel):
    """
    A query of the pod logs.

    Every value is validated, and the service escapes it, so a query cannot carry LogQL of its own.
    It is frozen, and refuses fields that it does not define. Build one with :meth:`last`, for the
    most recent period, or with ``start`` and ``end``. :meth:`logql` turns it into LogQL.

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
    """The earliest time, in UTC, within :data:`LOG_RETENTION` of now."""

    end: datetime
    """The latest time, in UTC, later than :attr:`start`."""

    components: tuple[str, ...] = ()
    """The components to read, each a Kubernetes name, or empty for all of them."""

    pod: Optional[str] = None
    """One pod's name, or None for every pod of the components."""

    contains: tuple[str, ...] = ()
    """Texts that every line must contain, case insensitively, each one line of 1 to 200 characters."""

    pattern: Optional[str] = None
    """A regular expression (RE2 syntax) of at most 200 characters, that every line must match, or None."""

    min_level: Optional[LogLevel] = None
    """The least severe level to return, or None for every line."""

    limit: int = Field(default=200, ge=1, le=MAX_QUERY_LINES)
    """The most lines to return, from 1 to :data:`MAX_QUERY_LINES`."""

    direction: Literal["backward", "forward"] = "backward"
    """``backward`` for the latest lines first, ``forward`` for the earliest."""

    @classmethod
    def last(cls, period: timedelta, **kwargs) -> "LogQuery":
        """
        Return a query of the most recent period, e.g. the last hour.

        A period longer than :data:`LOG_RETENTION` is shortened to it, since Loki keeps nothing older.

        :param period: How far back to read, at most :data:`LOG_RETENTION`.
        :param kwargs: The query's other fields.
        :returns: The query, from ``period`` ago until now.
        :raises pydantic.ValidationError: If a field is not valid.
        """
        end = datetime.now(timezone.utc)
        read_period = min(period, LOG_RETENTION)
        start = end - read_period
        query = cls(start=start, end=end, **kwargs)
        return query

    @field_validator("start", "end")
    @classmethod
    def utc(cls, value: datetime) -> datetime:
        """
        Return a time in UTC: a time without a time zone is taken to be UTC, and any other is converted.

        :param value: The ``start`` or ``end``.
        :returns: The time, with the UTC time zone.
        """
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @field_validator("components")
    @classmethod
    def valid_components(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        """
        Check that each component is a Kubernetes name, which cannot carry LogQL.

        :param value: The components.
        :returns: The components, unchanged.
        :raises ValueError: If a component is not a Kubernetes name.
        """
        for component in value:
            if not LABEL_VALUE.match(component):
                raise ValueError(f"{component!r} is not a component name")
        return value

    @field_validator("pod")
    @classmethod
    def valid_pod(cls, value: Optional[str]) -> Optional[str]:
        """
        Check that the pod is a Kubernetes name, which cannot carry LogQL.

        :param value: The pod's name, or None.
        :returns: The name, unchanged.
        :raises ValueError: If the name is not a Kubernetes name.
        """
        if value is None:
            return None
        if not LABEL_VALUE.match(value):
            raise ValueError(f"{value!r} is not a pod name")
        return value

    @field_validator("contains")
    @classmethod
    def valid_contains(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        """
        Check that each text is a single line, of 1 to 200 characters.

        :param value: The texts.
        :returns: The texts, unchanged.
        :raises ValueError: If a text is empty, too long, or has a line break.
        """
        for text in value:
            if not text:
                raise ValueError("each text must be one line of 1 to 200 characters")
            if len(text) > 200:
                raise ValueError("each text must be one line of 1 to 200 characters")
            if "\n" in text:
                raise ValueError("each text must be one line of 1 to 200 characters")
        return value

    @field_validator("pattern")
    @classmethod
    def valid_pattern(cls, value: Optional[str]) -> Optional[str]:
        """
        Check that the pattern is at most 200 characters, and compiles.

        It is compiled with Python's :mod:`re`, which accepts nearly all of RE2's syntax. A pattern
        that RE2 rejects anyway is reported by Loki, as a :class:`LogServiceError`.

        :param value: The pattern, or None.
        :returns: The pattern, unchanged.
        :raises ValueError: If the pattern is too long, or does not compile.
        """
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
        """
        Check that the period ends after it starts, and starts within the retention period.

        Five minutes of grace allow for the time between :meth:`last` and this check.

        :returns: The query, unchanged.
        :raises ValueError: If the period is empty, or starts too long ago.
        """
        if self.end <= self.start:
            raise ValueError("end must be later than start")
        now = datetime.now(timezone.utc)
        earliest = now - LOG_RETENTION - timedelta(minutes=5)
        if self.start < earliest:
            retention_hours = int(LOG_RETENTION.total_seconds() // 3600)
            raise ValueError(f"start must be within the last {retention_hours} hours")
        return self

    def logql(self) -> str:
        """
        Return the query as LogQL, with every value escaped.

        The stream selector picks the components, as an alternation of their escaped names, or
        every component, and the pod. Each filter is then a line filter, ``|~``: each ``contains``
        text, escaped and case insensitive, the ``pattern``, and the levels from ``min_level`` up,
        as :data:`LOG_LEVEL_RE2`. Every value is escaped for RE2 with :func:`re2_escape`, where it
        is taken literally, and for a LogQL string with :func:`logql_string`.

        :returns: e.g. ``{component=~"smarter|smarter-worker"} |~ "(?i)timeout"``.
        """
        if self.components:
            escaped_components = [re2_escape(component) for component in self.components]
            components_regex = "|".join(escaped_components)
            selector = f'component=~"{logql_string(components_regex)}"'
        else:
            selector = 'component=~".+"'
        if self.pod:
            selector += f', pod="{logql_string(self.pod)}"'
        query = "{" + selector + "}"
        for text in self.contains:
            text_regex = "(?i)" + re2_escape(text)
            query += f' |~ "{logql_string(text_regex)}"'
        if self.pattern:
            query += f' |~ "{logql_string(self.pattern)}"'
        if self.min_level:
            min_level_index = LOG_LEVEL_ORDER.index(self.min_level)
            levels = LOG_LEVEL_ORDER[min_level_index:]
            level_regexes = [LOG_LEVEL_RE2[level] for level in levels]
            levels_regex = "|".join(level_regexes)
            query += f' |~ "{logql_string(levels_regex)}"'
        return query


def re2_escape(text: str) -> str:
    """
    Escape text so that an RE2 regular expression matches it literally.

    Unlike :func:`re.escape`, it escapes only :data:`RE2_SPECIAL`: RE2 rejects an escaped space or
    letter, which :func:`re.escape` can produce.

    :param text: The text.
    :returns: The text, with each special character escaped with a backslash.
    """
    escaped_characters = []
    for character in text:
        if character in RE2_SPECIAL:
            escaped_characters.append("\\" + character)
        else:
            escaped_characters.append(character)
    escaped = "".join(escaped_characters)
    return escaped


def logql_string(value: str) -> str:
    """
    Escape a value for a LogQL double-quoted string, whose escapes are Go's.

    :param value: The value.
    :returns: The value with backslashes and double quotes escaped.
    """
    # backslashes first, so that the backslashes added before double quotes are not doubled.
    escaped = value.replace("\\", "\\\\")
    escaped = escaped.replace('"', '\\"')
    return escaped


class LogService(InfrastructureService):
    """
    The platform's pod logs, from the log store: the interface of the facade's ``.logs``.

    :class:`LokiLogService` implements it for every platform, and :class:`InMemoryLogService` for
    tests and local development. Callers reach it as
    :data:`smarter.apps.infrastructure.services.infrastructure` ``.logs``, never directly.
    """

    service_name = InfrastructureServiceNames.LOGS
    """The service's name in the infrastructure facade, and in its signals."""

    error_class = LogServiceError
    """The exception that the service raises when its backend fails."""

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
    """The stream's labels, e.g. ``{"component": "smarter", "pod": "smarter-6f9c-x2", "container": "smarter"}``."""

    values: list[list[Union[str, dict[str, str]]]] = []
    """The stream's lines, each ``[nanoseconds, text]`` or ``[nanoseconds, text, metadata]``."""


class LokiQueryData(BaseModel):
    """The ``data`` of a Loki ``query_range`` response, for a log query."""

    model_config = ConfigDict(extra="allow")

    resultType: str = "streams"  # noqa: N815 (Loki's name)
    """The kind of result: ``streams`` for a log query.

    Loki's name, in camelCase.
    """

    result: list[LokiResultStream] = []
    """The streams that have matching lines, one for each set of labels."""


class LokiResponse(BaseModel):
    """
    The fields of a Loki api response that the service reads.

    Loki adds others, e.g. query statistics, which are ignored.
    """

    model_config = ConfigDict(extra="allow")

    status: str = ""
    """``success``, for a query that Loki answered."""

    data: Optional[LokiQueryData] = None
    """The query's result, or None if Loki sent none."""


class LokiLabelsResponse(BaseModel):
    """A Loki ``label/<name>/values`` response: the values of one label, e.g. the pods' names."""

    model_config = ConfigDict(extra="allow")

    status: str = ""
    """``success``, for a request that Loki answered."""

    data: list[str] = []
    """The label's values in the period, in Loki's order."""


def nanoseconds(value: datetime) -> str:
    """
    Return a time as Unix nanoseconds, as Loki's api takes and returns it.

    :param value: The time, with a time zone.
    :returns: The nanoseconds since the Unix epoch, as a string of digits.
    """
    seconds = value.timestamp()
    nanoseconds_since_epoch = int(seconds * 1_000_000_000)
    return str(nanoseconds_since_epoch)


def from_nanoseconds(value: str) -> datetime:
    """
    Return a Unix nanoseconds timestamp, from Loki's api, as a UTC time.

    :param value: The nanoseconds since the Unix epoch, as a string of digits.
    :returns: The time, in UTC, to the microsecond.
    """
    seconds = int(value) / 1_000_000_000
    return datetime.fromtimestamp(seconds, tz=timezone.utc)


def _line_time(line: LogLine) -> datetime:
    """
    Return a line's time, the key that the services sort their lines by.

    :param line: The line.
    :returns: When the line was written.
    """
    return line.timestamp


class LokiLogService(LogService):
    """
    The pod logs, in Loki at ``smarter_settings.loki_url``.

    It is ready when the url is set. In the unit tests, it refuses to query, unless ``allow_in_tests``
    is True, e.g. with ``requests`` mocked. Loki is in the platform's namespace, so the url is a
    private, in-cluster address, and redirects are not followed.

    **Side effects:** every query is an HTTP GET to Loki, and the first success or failure after a
    change of state sends the infrastructure service's connection signal (see
    :meth:`~smarter.apps.infrastructure.services.base.InfrastructureService.connection_state`).

    :param allow_in_tests: Query in the unit tests.
    """

    def __init__(self, allow_in_tests: bool = False, **kwargs):
        """
        Create the service.

        :param allow_in_tests: Query in the unit tests, e.g. with ``requests`` mocked.
        :param kwargs: Passed to :class:`~smarter.apps.infrastructure.services.base.InfrastructureService`.
        """
        super().__init__(provider_name="loki", **kwargs)
        self.allow_in_tests = allow_in_tests

    @property
    def ready(self) -> bool:
        """Whether the service can query: ``smarter_settings.loki_url`` is set, and it is not a unit test, unless ``allow_in_tests``."""
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
        :raises InfrastructureNotReadyError: If ``smarter_settings.loki_url`` is not set.
        :raises InfrastructureConfigurationError: In the unit tests, unless ``allow_in_tests``.
        """
        refuse_in_unit_tests("Loki", self.allow_in_tests)
        self.require_ready()
        url = f"{smarter_settings.loki_url}{path}"
        try:
            response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT, allow_redirects=False)
        except requests.exceptions.RequestException as e:
            self.connection_state(False, type(e).__name__)
            raise LogServiceError(f"Loki could not be reached: {type(e).__name__}") from e
        self.connection_state(True)
        if response.status_code != 200:
            # Loki explains a rejected query in plain text, e.g. a bad regular expression.
            explanation = response.text[:300].strip()
            raise LogServiceError(f"Loki answered HTTP {response.status_code}: {explanation}")
        return response

    def query(self, query: LogQuery) -> list[LogLine]:
        """
        Return the lines that match a query, from Loki's ``query_range`` api.

        Loki returns one stream for each set of labels, each ordered on its own, so the lines of
        every stream are merged, and sorted by time, in the query's direction.

        **Side effects:** one HTTP GET to Loki, and a DEBUG log of the LogQL and the number of lines.

        :param query: The query.
        :returns: At most ``query.limit`` lines, latest first if ``query.direction`` is ``backward``.
        :raises LogServiceError: If Loki could not be reached, rejected the query, or answered with
            something other than a query response.
        :raises InfrastructureNotReadyError: If there is no log store.
        """
        params = {
            "query": query.logql(),
            "start": nanoseconds(query.start),
            "end": nanoseconds(query.end),
            "limit": str(query.limit),
            "direction": query.direction,
        }
        response = self._get("/loki/api/v1/query_range", params)
        try:
            response_json = response.json()
            body = LokiResponse.model_validate(response_json)
        except ValueError as e:
            raise LogServiceError("Loki's response is not a query response") from e

        streams: list[LokiResultStream] = []
        if body.data:
            streams = body.data.result
        lines: list[LogLine] = []
        for stream in streams:
            labels = stream.stream
            for value in stream.values:
                # a value is [nanoseconds, text], or [nanoseconds, text, metadata].
                if len(value) < 2:
                    continue
                line = LogLine(
                    timestamp=from_nanoseconds(str(value[0])),
                    component=labels.get("component", ""),
                    pod=labels.get("pod", ""),
                    container=labels.get("container", ""),
                    line=str(value[1]),
                )
                lines.append(line)

        # Loki limits each query, but orders lines only within a stream.
        latest_first = query.direction == "backward"
        lines.sort(key=_line_time, reverse=latest_first)
        logger.debug("%s.query() %s returned %s lines", self.formatted_class_name, query.logql(), len(lines))
        limited_lines = lines[: query.limit]
        return limited_lines

    def label_values(self, label: Literal["component", "pod"], start: datetime, end: datetime) -> list[str]:
        """
        Return the values of a label in a period, from Loki's ``label/<name>/values`` api.

        **Side effects:** one HTTP GET to Loki.

        :param label: ``component`` or ``pod``.
        :param start: The earliest time, in UTC.
        :param end: The latest time, in UTC.
        :returns: The values, sorted.
        :raises LogServiceError: If Loki could not be reached, or answered with something other than
            a label values response.
        :raises InfrastructureNotReadyError: If there is no log store.
        """
        path = f"/loki/api/v1/label/{label}/values"
        params = {"start": nanoseconds(start), "end": nanoseconds(end)}
        response = self._get(path, params)
        try:
            response_json = response.json()
            body = LokiLabelsResponse.model_validate(response_json)
        except ValueError as e:
            raise LogServiceError("Loki's response is not a label values response") from e
        values = sorted(body.data)
        return values


class InMemoryLogService(LogService):
    """
    Pod logs in memory, for tests and local development: add lines to :attr:`lines`.

    Queries are answered in Python: ``contains`` case insensitively, and ``pattern`` with
    :mod:`re`, which accepts the RE2 syntax that Loki uses for the patterns that matter here.

    Unlike Loki, a ``min_level`` query keeps only the lines whose own level is at least the
    minimum, which is what callers filter Loki's result down to.

    :param ready: Whether the service is ready.
    """

    def __init__(self, ready: bool = True, **kwargs):
        """
        Create the service, with no lines.

        :param ready: Whether the service is ready. False makes every call raise
            :class:`~smarter.apps.infrastructure.exceptions.InfrastructureNotReadyError`, like a
            platform without a log store.
        :param kwargs: Passed to :class:`~smarter.apps.infrastructure.services.base.InfrastructureService`.
        """
        super().__init__(provider_name="memory", **kwargs)
        self._ready = ready
        self.lines: list[LogLine] = []
        """The log, in any order: tests add lines here."""
        self.queries: list[LogQuery] = []
        """Every query, in order, for tests to inspect."""

    @property
    def ready(self) -> bool:
        """Whether the service is ready, as the constructor set it."""
        return self._ready

    def matches(self, query: LogQuery, line: LogLine) -> bool:
        """
        Return whether a line matches every filter of a query.

        :param query: The query.
        :param line: The line.
        :returns: True if the line is in the query's period, components and pod, contains each text,
            has at least the minimum level, and matches the pattern.
        """
        if line.timestamp < query.start:
            return False
        if line.timestamp > query.end:
            return False
        if query.components and line.component not in query.components:
            return False
        if query.pod and line.pod != query.pod:
            return False
        lower_line = line.line.lower()
        for text in query.contains:
            if text.lower() not in lower_line:
                return False
        if query.min_level and not at_least(line.level, query.min_level):
            return False
        if query.pattern and not re.search(query.pattern, line.line):
            return False
        return True

    def query(self, query: LogQuery) -> list[LogLine]:
        """
        Return the lines of :attr:`lines` that match a query, and record the query in :attr:`queries`.

        :param query: The query.
        :returns: At most ``query.limit`` lines, latest first if ``query.direction`` is ``backward``.
        :raises InfrastructureNotReadyError: If the service is not ready.
        """
        self.require_ready()
        self.queries.append(query)
        matching_lines = [line for line in self.lines if self.matches(query, line)]
        latest_first = query.direction == "backward"
        matching_lines.sort(key=_line_time, reverse=latest_first)
        limited_lines = matching_lines[: query.limit]
        return limited_lines

    def label_values(self, label: Literal["component", "pod"], start: datetime, end: datetime) -> list[str]:
        """
        Return the values of a label among the lines of :attr:`lines` in a period.

        :param label: ``component`` or ``pod``.
        :param start: The earliest time, in UTC.
        :param end: The latest time, in UTC.
        :returns: The distinct values, sorted.
        :raises InfrastructureNotReadyError: If the service is not ready.
        """
        self.require_ready()
        values = set()
        for line in self.lines:
            if start <= line.timestamp <= end:
                values.add(getattr(line, label))
        sorted_values = sorted(values)
        return sorted_values


_logs_factory: Optional[Callable[[], LogService]] = None
"""The factory that :func:`configure_logs` set, or None for :class:`LokiLogService`."""

_logs: Optional[LogService] = None
"""The log service that :func:`get_logs` created, or None until it is first called."""


def configure_logs(factory: Optional[Callable[[], LogService]]) -> None:
    """
    Set the factory of the log service that :func:`get_logs` returns.

    The current service is dropped, so that the next :func:`get_logs` creates one with the new
    factory. Tests install an :class:`InMemoryLogService` this way, and restore the default after.

    :param factory: Returns the service, or None to restore the default, :class:`LokiLogService`.
    """
    global _logs_factory, _logs  # pylint: disable=global-statement
    _logs_factory = factory
    _logs = None


def get_logs() -> LogService:
    """
    Return the log service, which is created once, by the factory of :func:`configure_logs`.

    :returns: The service: the factory's, or a :class:`LokiLogService` by default.
    """
    global _logs  # pylint: disable=global-statement
    if _logs is None:
        if _logs_factory is not None:
            _logs = _logs_factory()
        else:
            _logs = LokiLogService()
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
