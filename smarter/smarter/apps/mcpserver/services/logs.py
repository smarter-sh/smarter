"""
The platform's pod logs: reading them, formatting their lines for an LLM, and grouping errors by their signature.

The logs come from :data:`smarter.apps.infrastructure.services.infrastructure` ``.logs``: the last
72 hours of the app (``smarter``), the Celery workers (``smarter-worker``,
``smarter-worker-infrastructure``), beat (``smarter-beat``) and MariaDB (``mariadb``), kept in Loki.
Every query is built from structured filters (:func:`log_query`), never from LogQL that a caller
wrote, so an LLM cannot inject a query of its own.

- :func:`log_sources`: the components and pods that wrote to the logs in a period.
- :func:`search_logs`: the lines that match a set of filters.
- :func:`log_errors`: the errors, or warnings and errors, of a period, grouped by their signature.

The MCPServer's staff-only log tools (:mod:`smarter.apps.mcpserver.protocol.tools.logs`) call them,
and show log lines with :func:`format_line`, which puts the time, component and pod before each
line, and cuts a long line with :func:`short`, so that one stack trace cannot fill the LLM's context.

:func:`log_errors` groups lines with :func:`error_groups`. A signature is a line's message with
what varies between occurrences removed: its timestamp, numbers, ids, hashes and quoted values.
Lines with the same signature are the same problem, so :func:`error_groups` counts them, and keeps
one example of each. A thousand timeouts of one provider then read as one group, with a count,
rather than a thousand lines.

**Side effects:** :func:`log_sources`, :func:`search_logs` and :func:`log_errors` make one or two
HTTP GETs to Loki (in the tests, to the in-memory log service). Nothing is cached or written.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

from pydantic import ValidationError

from smarter.apps.infrastructure.services import infrastructure
from smarter.apps.infrastructure.services.logs import (
    LOG_RETENTION,
    LogLevel,
    LogLine,
    LogQuery,
    at_least,
)
from smarter.apps.mcpserver.exceptions import SmarterMCPServerServiceError

COMPONENTS = ("smarter", "smarter-worker", "smarter-worker-infrastructure", "smarter-beat", "mariadb")
"""The components whose logs are kept: the ``app.kubernetes.io/name`` of their pods."""

MAX_MINUTES = int(LOG_RETENTION.total_seconds() // 60)
"""The longest period that can be read: the log store's retention."""

SUMMARY_LINES = 5000
"""The most warning and error lines that :func:`log_errors` groups."""

MAX_LINE_CHARACTERS = 500
"""
The most characters of one log line that a tool shows.

Longer lines are cut by :func:`short`, and end with an ellipsis.
"""

TIMESTAMP_PREFIX = re.compile(r"^\[?\d{4}-\d{2}-\d{2}[T ][\d:.,]+(?:\s?[+-]\d{4}|Z)?\]?\s*(?:-\s*)?")
"""
A timestamp at the start of a line, in the platform's, Celery's or MariaDB's format.

E.g. ``2026-11-02 14:00:01,123 - ``, ``[2026-11-02 14:00:01,123: `` or ``2026-11-02T14:00:01Z``.
:func:`signature` removes it, since every occurrence of a message has its own.
"""

VARIABLE_PARTS: tuple[tuple[re.Pattern, str], ...] = (
    (re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.IGNORECASE), "<uuid>"),
    (re.compile(r"\b[0-9a-f]{16,}\b", re.IGNORECASE), "<hash>"),
    (re.compile(r"'[^']*'|\"[^\"]*\""), "<str>"),
    # every number, also one that a unit follows, e.g. 30s or 512MB.
    (re.compile(r"\d+(\.\d+)?"), "N"),
    (re.compile(r"\s+"), " "),
)
"""
What varies between occurrences of the same message, and what it becomes in a signature.

Each pattern is applied in order: uuids before hashes, since a uuid's parts are hex, and quoted
values before numbers, so that a quoted number becomes ``<str>``. The last pattern collapses runs
of whitespace, which the earlier replacements can leave.
"""


def short(line: str, limit: int = MAX_LINE_CHARACTERS) -> str:
    """
    Return a line, cut to a limit.

    :param line: The line's text.
    :param limit: The most characters to return.
    :returns: The line, if it is no longer than the limit, and otherwise its first ``limit - 1``
        characters followed by ``…``, which is ``limit`` characters in all.
    """
    if len(line) <= limit:
        return line
    head = line[: limit - 1]
    return head + "…"


def format_line(line: LogLine) -> str:
    """
    Return a log line as a tool shows it: when, where, and its text.

    The time is UTC, to the second, and the text is cut with :func:`short`.

    :param line: The line.
    :returns: e.g. ``2026-11-02 14:00:01 smarter-worker/smarter-worker-6f9c-x2: <text>``.
    """
    text = short(line.line)
    formatted = f"{line.timestamp:%Y-%m-%d %H:%M:%S} {line.component}/{line.pod}: {text}"
    return formatted


def signature(text: str) -> str:
    """
    Return a log line's signature: its message, without what varies between occurrences.

    The leading timestamp is removed with :data:`TIMESTAMP_PREFIX`, then each of
    :data:`VARIABLE_PARTS` is replaced with its placeholder, e.g.
    ``2026-11-02 14:00:01 - ERROR - timeout after 30s for 'gpt-4o'`` becomes
    ``ERROR - timeout after Ns for <str>``.

    :param text: The line.
    :returns: The signature, at most 200 characters.
    """
    stripped = text.strip()
    message = TIMESTAMP_PREFIX.sub("", stripped)
    for pattern, replacement in VARIABLE_PARTS:
        message = pattern.sub(replacement, message)
    message = message.strip()
    return message[:200]


@dataclass
class ErrorGroup:
    """
    The lines of one component that have the same level and signature: one problem, and how often it happened.

    :func:`error_groups` creates the groups, and calls :meth:`add` for each line.
    ``summarize_log_errors`` shows each group as a heading, its signature and its example.
    """

    component: str
    """The component that wrote the lines, e.g. ``smarter-worker``."""

    level: Optional[LogLevel]
    """The lines' level, or None if they name none."""

    signature: str
    """The lines' :func:`signature`."""

    count: int = 0
    """How many lines the group has."""

    first_seen: Optional[datetime] = None
    """When the earliest line was written, in UTC, or None before the first :meth:`add`."""

    last_seen: Optional[datetime] = None
    """When the latest line was written, in UTC, or None before the first :meth:`add`."""

    example: str = ""
    """The latest line's text, cut with :func:`short`."""

    pods: set[str] = field(default_factory=set)
    """The names of the pods that wrote the lines."""

    def add(self, line: LogLine) -> None:
        """
        Count a line in the group.

        The line's time widens :attr:`first_seen` and :attr:`last_seen`, and the latest line is kept
        as the :attr:`example`. A line as late as the current example replaces it.

        :param line: A line with the group's component, level and signature.
        """
        self.count += 1
        self.pods.add(line.pod)
        if self.first_seen is None or line.timestamp < self.first_seen:
            self.first_seen = line.timestamp
        if self.last_seen is None or line.timestamp >= self.last_seen:
            self.last_seen = line.timestamp
            self.example = short(line.line)


def error_groups(lines: list[LogLine]) -> list[ErrorGroup]:
    """
    Group log lines by component, level and signature.

    The same message from two components is two groups, since it is usually two problems.

    :param lines: The lines, e.g. the warnings and errors of the last hour.
    :returns: The groups, the most frequent first, then the most recent.
    """
    groups: dict[tuple[str, Optional[LogLevel], str], ErrorGroup] = {}
    for line in lines:
        level = line.level
        line_signature = signature(line.line)
        key = (line.component, level, line_signature)
        group = groups.get(key)
        if group is None:
            group = ErrorGroup(component=line.component, level=level, signature=line_signature)
            groups[key] = group
        group.add(line)
    ordered = sorted(groups.values(), key=_group_order)
    return ordered


def _group_order(group: ErrorGroup) -> tuple[int, float]:
    """
    Return the sort key of a group: the most frequent first, then the most recent.

    Both numbers are negated, because :func:`sorted` puts the smallest first.

    :param group: The group.
    :returns: The negated count, and the negated Unix time of the latest line, or 0 if it has none.
    """
    if group.last_seen:
        last_seen = group.last_seen.timestamp()
    else:
        last_seen = 0
    return (-group.count, -last_seen)


def log_query(**kwargs) -> LogQuery:
    """
    Return a query of the most recent period, with a validation error that the caller can correct.

    :class:`~smarter.apps.infrastructure.services.logs.LogQuery` validates what a caller's
    arguments may not, e.g. that a ``pattern`` compiles, or that a ``pod`` is a Kubernetes name.

    :param kwargs: The query's fields, for
        :meth:`~smarter.apps.infrastructure.services.logs.LogQuery.last`, starting with ``period``.
    :returns: The query, of the most recent period.
    :raises SmarterMCPServerServiceError: If the query is not valid.
    """
    try:
        query = LogQuery.last(**kwargs)
    except ValidationError as e:
        messages = [str(problem["msg"]) for problem in e.errors()]
        problems = "; ".join(messages)
        raise SmarterMCPServerServiceError(f"invalid log query: {problems}") from e
    return query


@dataclass(frozen=True)
class LogSources:
    """The components and pods that wrote to the logs in a period, as :func:`log_sources` returns them."""

    components: list[str]
    """The components that wrote to the logs."""

    missing: list[str]
    """The components of :data:`COMPONENTS` that wrote nothing, e.g. because they are down."""

    pods: list[str]
    """The pods that wrote to the logs."""


def log_sources(minutes: int) -> LogSources:
    """
    Return the components and pods that wrote to the logs in the last minutes.

    **Side effects:** two HTTP GETs to Loki, for the values of the ``component`` and ``pod`` labels.

    :param minutes: The period, in minutes, up to now.
    :returns: The components, the components that wrote nothing, and the pods.
    :raises LogServiceError: If Loki could not be reached.
    :raises InfrastructureNotReadyError: If there is no log store.
    """
    end = datetime.now(timezone.utc)
    start = end - timedelta(minutes=minutes)
    components = infrastructure.logs.label_values("component", start, end)
    pods = infrastructure.logs.label_values("pod", start, end)
    missing = []
    for component in COMPONENTS:
        if component not in components:
            missing.append(component)
    sources = LogSources(components=list(components), missing=missing, pods=list(pods))
    return sources


def search_logs(
    minutes: int,
    limit: int,
    components: tuple[str, ...] = (),
    pod: Optional[str] = None,
    contains: tuple[str, ...] = (),
    pattern: Optional[str] = None,
    min_level: Optional[LogLevel] = None,
    oldest_first: bool = False,
) -> list[LogLine]:
    """
    Return the lines of the last minutes that match every filter.

    **Side effects:** one HTTP GET to Loki's ``query_range``.

    :param minutes: The period, in minutes, up to now.
    :param limit: The most lines to return.
    :param components: The components to read, or an empty tuple for all of them.
    :param pod: One pod's name, or None for every pod of the components.
    :param contains: Texts that every line must contain, case insensitively.
    :param pattern: A regular expression, in RE2 syntax, that every line must match, or None.
    :param min_level: The least severe level to return, or None for lines of every level.
    :param oldest_first: Whether to return the oldest lines of the period first, rather than the newest.
    :returns: The lines, newest first unless ``oldest_first``.
    :raises SmarterMCPServerServiceError: If the query is not valid, e.g. its pattern does not compile.
    :raises LogServiceError: If Loki could not be reached, or rejected the query.
    :raises InfrastructureNotReadyError: If there is no log store.
    """
    if oldest_first:
        direction = "forward"
    else:
        direction = "backward"
    query = log_query(
        period=timedelta(minutes=minutes),
        components=components,
        pod=pod,
        contains=contains,
        pattern=pattern,
        min_level=min_level,
        limit=limit,
        direction=direction,
    )
    lines = infrastructure.logs.query(query)
    if not min_level:
        return lines
    # Loki matches the level anywhere in the line; keep the lines whose own level it is.
    leveled_lines = [line for line in lines if at_least(line.level, min_level)]
    return leveled_lines


@dataclass(frozen=True)
class LogErrors:
    """The errors of a period, grouped by their signature, as :func:`log_errors` returns them."""

    lines: int
    """The number of lines that were grouped."""

    truncated: bool
    """Whether there were more lines than :data:`SUMMARY_LINES`, of which only the latest were grouped."""

    groups: list["ErrorGroup"]
    """The groups, the most frequent first."""


def log_errors(minutes: int, min_level: LogLevel, components: tuple[str, ...] = ()) -> LogErrors:
    """
    Return the errors, or the warnings and errors, of the last minutes, grouped by their signature.

    **Side effects:** one HTTP GET to Loki's ``query_range``.

    :param minutes: The period, in minutes, up to now.
    :param min_level: ``LogLevel.ERROR`` for errors and critical lines, or ``LogLevel.WARNING`` to
        include warnings.
    :param components: The components to read, or an empty tuple for all of them.
    :returns: The number of lines, whether they were cut at :data:`SUMMARY_LINES`, and the groups.
    :raises SmarterMCPServerServiceError: If the query is not valid.
    :raises LogServiceError: If Loki could not be reached, or rejected the query.
    :raises InfrastructureNotReadyError: If there is no log store.
    """
    query = log_query(
        period=timedelta(minutes=minutes),
        components=components,
        min_level=min_level,
        limit=SUMMARY_LINES,
    )
    matching_lines = infrastructure.logs.query(query)
    # Loki matches the level anywhere in the line; keep the lines whose own level it is.
    lines = [line for line in matching_lines if at_least(line.level, min_level)]
    truncated = len(lines) >= SUMMARY_LINES
    groups = error_groups(lines)
    errors = LogErrors(lines=len(lines), truncated=truncated, groups=groups)
    return errors


__all__ = [
    "COMPONENTS",
    "MAX_LINE_CHARACTERS",
    "MAX_MINUTES",
    "SUMMARY_LINES",
    "ErrorGroup",
    "LogErrors",
    "LogSources",
    "error_groups",
    "format_line",
    "log_errors",
    "log_query",
    "log_sources",
    "search_logs",
    "short",
    "signature",
]
