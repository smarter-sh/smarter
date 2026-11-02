"""
Log lines, as the operations tools show them to an LLM, and errors grouped by their signature.

A signature is a line's message with what varies between occurrences removed: its timestamp,
numbers, ids, hashes and quoted values. Lines with the same signature are the same problem, so
:func:`error_groups` counts them, and keeps one example of each.

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
"""The most characters of one log line that a tool shows.

Longer lines are cut.
"""

TIMESTAMP_PREFIX = re.compile(r"^\[?\d{4}-\d{2}-\d{2}[T ][\d:.,]+(?:\s?[+-]\d{4}|Z)?\]?\s*(?:-\s*)?")
"""A timestamp at the start of a line, in the platform's, Celery's or MariaDB's format."""

VARIABLE_PARTS: tuple[tuple[re.Pattern, str], ...] = (
    (re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.IGNORECASE), "<uuid>"),
    (re.compile(r"\b[0-9a-f]{16,}\b", re.IGNORECASE), "<hash>"),
    (re.compile(r"'[^']*'|\"[^\"]*\""), "<str>"),
    # every number, also one that a unit follows, e.g. 30s or 512MB.
    (re.compile(r"\d+(\.\d+)?"), "N"),
    (re.compile(r"\s+"), " "),
)
"""What varies between occurrences of the same message, and what it becomes in a signature."""


def short(line: str, limit: int = MAX_LINE_CHARACTERS) -> str:
    """Return a line, cut to a limit."""
    return line if len(line) <= limit else line[: limit - 1] + "…"


def format_line(line: LogLine) -> str:
    """
    Return a log line as a tool shows it: when, where, and its text.

    :param line: The line.
    :returns: e.g. ``2026-11-02 14:00:01 smarter-worker/smarter-worker-6f9c-x2: <text>``.
    """
    return f"{line.timestamp:%Y-%m-%d %H:%M:%S} {line.component}/{line.pod}: {short(line.line)}"


def signature(text: str) -> str:
    """
    Return a log line's signature: its message, without what varies between occurrences.

    :param text: The line.
    :returns: The signature, at most 200 characters.
    """
    text = TIMESTAMP_PREFIX.sub("", text.strip())
    for pattern, replacement in VARIABLE_PARTS:
        text = pattern.sub(replacement, text)
    return text.strip()[:200]


@dataclass
class ErrorGroup:
    """The lines of one component that have the same level and signature."""

    component: str
    level: Optional[LogLevel]
    signature: str
    count: int = 0
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    example: str = ""
    pods: set[str] = field(default_factory=set)

    def add(self, line: LogLine) -> None:
        """Count a line in the group."""
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

    :param lines: The lines, e.g. the warnings and errors of the last hour.
    :returns: The groups, the most frequent first, then the most recent.
    """
    groups: dict[tuple[str, Optional[LogLevel], str], ErrorGroup] = {}
    for line in lines:
        level = line.level
        key = (line.component, level, signature(line.line))
        group = groups.get(key)
        if group is None:
            group = groups[key] = ErrorGroup(component=line.component, level=level, signature=key[2])
        group.add(line)
    return sorted(
        groups.values(),
        key=lambda group: (-group.count, -(group.last_seen.timestamp() if group.last_seen else 0)),
    )


__all__ = [
    "MAX_LINE_CHARACTERS",
    "ErrorGroup",
    "error_groups",
    "format_line",
    "short",
    "signature",
]
