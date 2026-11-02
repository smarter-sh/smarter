"""
Log lines, as the operations tools show them to an LLM, and errors grouped by their signature.

The pod log tools of :mod:`smarter.apps.mcpserver.logs.tools` show log lines with
:func:`format_line`, which puts the time, component and pod before each line, and cuts a long line
with :func:`short`, so that one stack trace cannot fill the LLM's context.

``summarize_log_errors`` groups the warnings and errors of a period with :func:`error_groups`. A
signature is a line's message with what varies between occurrences removed: its timestamp,
numbers, ids, hashes and quoted values. Lines with the same signature are the same problem, so
:func:`error_groups` counts them, and keeps one example of each. A thousand timeouts of one
provider then read as one group, with a count, rather than a thousand lines.

Everything here is plain Python over :class:`~smarter.apps.infrastructure.services.logs.LogLine`
objects that the caller has already read: nothing is queried, cached or written.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from smarter.apps.infrastructure.services.logs import LogLevel, LogLine

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


__all__ = [
    "MAX_LINE_CHARACTERS",
    "ErrorGroup",
    "error_groups",
    "format_line",
    "short",
    "signature",
]
