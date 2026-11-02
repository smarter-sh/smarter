"""
The operations tools of the platform's pod logs: ``list_log_sources``, ``search_logs`` and ``summarize_log_errors``.

They read :data:`smarter.apps.infrastructure.services.infrastructure` ``.logs``: the last 72 hours
of the app (``smarter``), the Celery workers (``smarter-worker``, ``smarter-worker-infrastructure``),
beat (``smarter-beat``) and MariaDB (``mariadb``). Each query is structured, not LogQL, so the LLM
cannot inject a query of its own.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from datetime import datetime, timedelta, timezone
from typing import Literal, Optional

from pydantic import Field, ValidationError

from smarter.apps.infrastructure.services import infrastructure
from smarter.apps.infrastructure.services.logs import (
    LOG_RETENTION,
    LogLevel,
    LogQuery,
    at_least,
)
from smarter.apps.mcpserver.exceptions import SmarterMCPServerToolError
from smarter.apps.mcpserver.logs.summary import error_groups, format_line
from smarter.apps.mcpserver.protocol.operations_tools import (
    UNTRUSTED_DATA_NOTICE,
    OperationsToolArguments,
    SmarterOperationsTool,
)

COMPONENTS = ("smarter", "smarter-worker", "smarter-worker-infrastructure", "smarter-beat", "mariadb")
"""The components whose logs are kept: the ``app.kubernetes.io/name`` of their pods."""

Component = Literal["smarter", "smarter-worker", "smarter-worker-infrastructure", "smarter-beat", "mariadb"]

MAX_MINUTES = int(LOG_RETENTION.total_seconds() // 60)
"""The longest period that a tool reads: the log store's retention."""

SUMMARY_LINES = 5000
"""The most warning and error lines that ``summarize_log_errors`` groups."""

COMPONENTS_DESCRIPTION = (
    "The components to read: smarter (the web app and api), smarter-worker (Celery tasks, e.g. prompts' "
    "background work), smarter-worker-infrastructure (deploys, DNS, certificates, Kubernetes), smarter-beat "
    "(the scheduler) and mariadb (the database). Omit it to read all of them."
)


def log_query(**kwargs) -> LogQuery:
    """
    Return a log query, with a validation error as a tool error that the LLM can correct.

    :param kwargs: The query's fields.
    :raises SmarterMCPServerToolError: If the query is not valid.
    """
    try:
        return LogQuery.last(**kwargs)
    except ValidationError as e:
        problems = "; ".join(str(problem["msg"]) for problem in e.errors())
        raise SmarterMCPServerToolError(f"invalid log query: {problems}") from e


class ListLogSourcesArguments(OperationsToolArguments):
    """The arguments of ``list_log_sources``."""

    minutes: int = Field(default=60, ge=1, le=MAX_MINUTES, description="How far back to look, in minutes.")


class ListLogSourcesTool(SmarterOperationsTool):
    """The components and pods that logged recently."""

    name = "list_log_sources"
    title = "List log sources"
    description = (
        "List the components and pods that wrote to the logs in the last minutes, from the log store, which "
        "keeps 72 hours. A component that is missing has written nothing, e.g. because its pods are down. "
        "Pod names change on every deploy and restart: use them with search_logs' pod argument."
    )
    arguments_model = ListLogSourcesArguments

    def run(self, arguments: ListLogSourcesArguments) -> str:  # type: ignore[override]
        end = datetime.now(timezone.utc)
        start = end - timedelta(minutes=arguments.minutes)
        components = infrastructure.logs.label_values("component", start, end)
        pods = infrastructure.logs.label_values("pod", start, end)
        missing = [component for component in COMPONENTS if component not in components]
        lines = [f"## Log sources in the last {arguments.minutes} minutes", ""]
        lines.append("Components: " + (", ".join(components) or "none"))
        if missing:
            lines.append("Components that wrote nothing: " + ", ".join(missing))
        lines += ["", "Pods:"]
        lines += [f"- {pod}" for pod in pods] or ["- none"]
        return "\n".join(lines)


class SearchLogsArguments(OperationsToolArguments):
    """The arguments of ``search_logs``."""

    components: list[Component] = Field(default_factory=list, description=COMPONENTS_DESCRIPTION)
    pod: Optional[str] = Field(default=None, description="One pod's name, from list_log_sources.")
    contains: list[str] = Field(
        default_factory=list,
        max_length=5,
        description="Text that every line must contain, case insensitively, e.g. ['timeout', 'openai'].",
    )
    pattern: Optional[str] = Field(
        default=None, description="A regular expression, in RE2 syntax, that every line must match."
    )
    min_level: Optional[LogLevel] = Field(
        default=None,
        description="The least severe level to return, e.g. 'warning' for warnings, errors and critical lines.",
    )
    minutes: int = Field(default=60, ge=1, le=MAX_MINUTES, description="How far back to search, in minutes.")
    limit: int = Field(default=50, ge=1, le=200, description="The most lines to return.")
    oldest_first: bool = Field(
        default=False, description="Return the oldest lines of the period first, rather than the newest."
    )


class SearchLogsTool(SmarterOperationsTool):
    """Search the pod logs."""

    name = "search_logs"
    title = "Search pod logs"
    description = (
        "Search the logs of the platform's pods, from the log store, which keeps 72 hours. Filter by component, "
        "pod, text, a regular expression and the least severe level. Returns the newest matching lines first, "
        "each with its time (UTC), component and pod. With no filters, it returns the latest lines, like tail. "
        "To find what went wrong, start with summarize_log_errors, then search for a signature it returns."
    )
    arguments_model = SearchLogsArguments

    def run(self, arguments: SearchLogsArguments) -> str:  # type: ignore[override]
        query = log_query(
            period=timedelta(minutes=arguments.minutes),
            components=tuple(arguments.components),
            pod=arguments.pod,
            contains=tuple(arguments.contains),
            pattern=arguments.pattern,
            min_level=arguments.min_level,
            limit=arguments.limit,
            direction="forward" if arguments.oldest_first else "backward",
        )
        lines = infrastructure.logs.query(query)
        if arguments.min_level:
            # Loki matches the level anywhere in the line; keep the lines whose own level it is.
            lines = [line for line in lines if at_least(line.level, arguments.min_level)]
        heading = f"## {len(lines)} log lines in the last {arguments.minutes} minutes"
        if not lines:
            return f"{heading}\n\nNo line matches. Widen the period, or remove a filter."
        order = "oldest first" if arguments.oldest_first else "newest first"
        if len(lines) == arguments.limit:
            heading += f" (the limit, {order}: there may be more)"
        else:
            heading += f" ({order})"
        body = "\n".join(format_line(line) for line in lines)
        return f"{UNTRUSTED_DATA_NOTICE}{heading}\n\n```text\n{body}\n```"


class SummarizeLogErrorsArguments(OperationsToolArguments):
    """The arguments of ``summarize_log_errors``."""

    components: list[Component] = Field(default_factory=list, description=COMPONENTS_DESCRIPTION)
    minutes: int = Field(default=60, ge=1, le=MAX_MINUTES, description="How far back to look, in minutes.")
    min_level: Literal["warning", "error"] = Field(
        default="error", description="'error' for errors and critical lines, 'warning' to include warnings."
    )
    groups: int = Field(default=15, ge=1, le=50, description="The most groups to return.")


class SummarizeLogErrorsTool(SmarterOperationsTool):
    """The errors of the pod logs, grouped by their signature."""

    name = "summarize_log_errors"
    title = "Summarize log errors"
    description = (
        "Summarize the errors, and optionally the warnings, in the platform's pod logs over the last minutes: "
        "the lines are grouped by component, level and signature (the message without its numbers, ids and "
        "quoted values), and each group has its count, its pods, when it was first and last seen, and its "
        "latest line. Call it first when a user reports errors, slowness or an outage, then use search_logs "
        "for the lines around a group."
    )
    arguments_model = SummarizeLogErrorsArguments

    def run(self, arguments: SummarizeLogErrorsArguments) -> str:  # type: ignore[override]
        min_level = LogLevel(arguments.min_level)
        query = log_query(
            period=timedelta(minutes=arguments.minutes),
            components=tuple(arguments.components),
            min_level=min_level,
            limit=SUMMARY_LINES,
        )
        lines = [line for line in infrastructure.logs.query(query) if at_least(line.level, min_level)]
        levels = "errors" if min_level == LogLevel.ERROR else "warnings and errors"
        heading = f"## {len(lines)} {levels} in the last {arguments.minutes} minutes"
        if not lines:
            return f"{heading}\n\nNone. The logs show no {levels} in this period."
        if len(lines) >= SUMMARY_LINES:
            heading += f" (only the latest {SUMMARY_LINES} were grouped)"
        groups = error_groups(lines)
        out = [UNTRUSTED_DATA_NOTICE + heading, ""]
        for group in groups[: arguments.groups]:
            seen = f"{group.first_seen:%H:%M:%S} to {group.last_seen:%H:%M:%S} UTC"
            out += [
                f"### {group.count} × {group.level or 'unknown'} in {group.component} ({len(group.pods)} pods, {seen})",
                f"Signature: `{group.signature}`",
                "```text",
                group.example,
                "```",
                "",
            ]
        if len(groups) > arguments.groups:
            out.append(f"_{len(groups) - arguments.groups} more groups are not shown._")
        return "\n".join(out)


__all__ = [
    "COMPONENTS",
    "ListLogSourcesTool",
    "SearchLogsTool",
    "SummarizeLogErrorsTool",
]
