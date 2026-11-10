"""
The operations tools of the platform's pod logs: ``list_log_sources``, ``search_logs`` and ``summarize_log_errors``.

Each tool validates its arguments, calls :mod:`smarter.apps.mcpserver.services.logs`, which reads the
last 72 hours of the app, the Celery workers, beat and MariaDB from Loki, and formats the lines as
Markdown. Each query is structured, not LogQL, so the LLM cannot inject a query of its own.

They are staff-only tools of the MCPServer, built on
:class:`~smarter.apps.mcpserver.protocol.tools.staff.StaffTool`, which records every
call in the audit trail. A result that quotes log lines starts with
:data:`~smarter.apps.mcpserver.protocol.tools.staff.UNTRUSTED_DATA_NOTICE`, because a log line
can carry text that a user wrote.

**Side effects:** each call makes one or two HTTP GETs to Loki (in the tests, to the in-memory log
service), and the audit trail's database write. Nothing is cached.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from typing import Literal, Optional, Union

from pydantic import Field

from smarter.apps.infrastructure.services.logs import LogLevel
from smarter.apps.mcpserver.protocol.tools.staff import (
    UNTRUSTED_DATA_NOTICE,
    StaffTool,
    StaffToolArguments,
)
from smarter.apps.mcpserver.services.logs import (
    MAX_MINUTES,
    SUMMARY_LINES,
    format_line,
    log_errors,
    log_sources,
    search_logs,
)

Component = Literal["smarter", "smarter-worker", "smarter-worker-infrastructure", "smarter-beat", "mariadb"]
"""
A component's name, as a tool argument: one of :data:`~smarter.apps.mcpserver.services.logs.COMPONENTS`.

A ``Literal`` puts the names in the tool's ``inputSchema`` as an ``enum``, so that the LLM sees
them, and Pydantic refuses any other.
"""


COMPONENTS_DESCRIPTION = (
    "The components to read: smarter (the web app and api), smarter-worker (Celery tasks, e.g. prompts' "
    "background work), smarter-worker-infrastructure (deploys, DNS, certificates, Kubernetes), smarter-beat "
    "(the scheduler) and mariadb (the database). Omit it to read all of them."
)
"""The description of a tool's ``components`` argument, which says what each component does, for the LLM."""


class ListLogSourcesArguments(StaffToolArguments):
    """The arguments of ``list_log_sources``: the ``ticket``, and how far back to look."""

    minutes: int = Field(default=60, ge=1, le=MAX_MINUTES, description="How far back to look, in minutes.")
    """How far back to look, in minutes, from 1 to :data:`MAX_MINUTES`.

    Defaults to an hour.
    """


class ListLogSourcesTool(StaffTool):
    """
    The ``list_log_sources`` tool: the components and pods that logged recently.

    A component that is missing from the list wrote nothing in the period, which usually means
    that its pods are down. The pods' names are what ``search_logs``' ``pod`` argument takes.
    """

    name = "list_log_sources"
    title = "List log sources"
    description = (
        "List the components and pods that wrote to the logs in the last minutes, from the log store, which "
        "keeps 72 hours. A component that is missing has written nothing, e.g. because its pods are down. "
        "Pod names change on every deploy and restart: use them with search_logs' pod argument."
    )
    arguments_model = ListLogSourcesArguments

    def run(self, arguments: ListLogSourcesArguments) -> str:  # type: ignore[override]
        """
        List the components and pods that wrote to the logs in the period.

        **Side effects:** two HTTP GETs to Loki, for the values of the ``component`` and ``pod``
        labels.

        :param arguments: The validated arguments.
        :returns: Markdown: the components, those of :data:`COMPONENTS` that wrote nothing, and the pods.
        :raises LogServiceError: If Loki could not be reached.
        :raises InfrastructureNotReadyError: If there is no log store.
        """
        sources = log_sources(arguments.minutes)

        lines = [f"## Log sources in the last {arguments.minutes} minutes", ""]
        if sources.components:
            component_list = ", ".join(sources.components)
        else:
            component_list = "none"
        lines.append("Components: " + component_list)
        if sources.missing:
            lines.append("Components that wrote nothing: " + ", ".join(sources.missing))
        lines.append("")
        lines.append("Pods:")
        if sources.pods:
            for pod in sources.pods:
                lines.append(f"- {pod}")
        else:
            lines.append("- none")
        text = "\n".join(lines)
        return text


class SearchLogsArguments(StaffToolArguments):
    """The arguments of ``search_logs``: the ``ticket``, and the filters of the search, which all apply at once."""

    components: list[Component] = Field(default_factory=list, description=COMPONENTS_DESCRIPTION)
    """The components to read, or an empty list for all of them."""

    pod: Optional[str] = Field(default=None, description="One pod's name, from list_log_sources.")
    """One pod's name, from ``list_log_sources``, or None for every pod of the components."""

    contains: list[str] = Field(
        default_factory=list,
        max_length=5,
        description="Text that every line must contain, case insensitively, e.g. ['timeout', 'openai'].",
    )
    """Up to five texts, each of which every line must contain, case insensitively."""

    pattern: Optional[str] = Field(
        default=None, description="A regular expression, in RE2 syntax, that every line must match."
    )
    """A regular expression, in RE2 syntax, that every line must match, or None."""

    min_level: Optional[LogLevel] = Field(
        default=None,
        description="The least severe level to return, e.g. 'warning' for warnings, errors and critical lines.",
    )
    """The least severe level to return, or None for lines of every level, and lines without one."""

    minutes: int = Field(default=60, ge=1, le=MAX_MINUTES, description="How far back to search, in minutes.")
    """How far back to search, in minutes, from 1 to :data:`MAX_MINUTES`.

    Defaults to an hour.
    """

    limit: int = Field(default=50, ge=1, le=200, description="The most lines to return.")
    """The most lines to return, from 1 to 200.

    Defaults to 50.
    """

    oldest_first: bool = Field(
        default=False, description="Return the oldest lines of the period first, rather than the newest."
    )
    """Whether to return the oldest lines of the period first.

    By default the newest are, like ``tail``.
    """


class SearchLogsTool(StaffTool):
    """
    The ``search_logs`` tool: the lines of the pod logs that match a set of filters.

    The filters become a :class:`~smarter.apps.infrastructure.services.logs.LogQuery`, which the log
    service turns into escaped LogQL, so the LLM's text is never run as a query.
    """

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
        """
        Search the pod logs.

        **Side effects:** one HTTP GET to Loki's ``query_range``.

        :param arguments: The validated arguments.
        :returns: Markdown: a heading with the number of lines, then the lines in a code block, after
            :data:`~smarter.apps.mcpserver.protocol.tools.staff.UNTRUSTED_DATA_NOTICE`, or a
            hint to widen the search if no line matches.
        :raises SmarterMCPServerServiceError: If the query is not valid, e.g. its pattern does not compile.
        :raises LogServiceError: If Loki could not be reached, or rejected the query.
        :raises InfrastructureNotReadyError: If there is no log store.
        """
        if arguments.oldest_first:
            order = "oldest first"
        else:
            order = "newest first"
        lines = search_logs(
            arguments.minutes,
            arguments.limit,
            components=tuple(arguments.components),
            pod=arguments.pod,
            contains=tuple(arguments.contains),
            pattern=arguments.pattern,
            min_level=arguments.min_level,
            oldest_first=arguments.oldest_first,
        )

        heading = f"## {len(lines)} log lines in the last {arguments.minutes} minutes"
        if not lines:
            return f"{heading}\n\nNo line matches. Widen the period, or remove a filter."
        if len(lines) == arguments.limit:
            heading += f" (the limit, {order}: there may be more)"
        else:
            heading += f" ({order})"
        formatted_lines = [format_line(line) for line in lines]
        body = "\n".join(formatted_lines)
        text = f"{UNTRUSTED_DATA_NOTICE}{heading}\n\n```text\n{body}\n```"
        return text


class SummarizeLogErrorsArguments(StaffToolArguments):
    """The arguments of ``summarize_log_errors``: the ``ticket``, the components, the period, the level and the number of groups."""

    components: list[Component] = Field(default_factory=list, description=COMPONENTS_DESCRIPTION)
    """The components to read, or an empty list for all of them."""

    minutes: int = Field(default=60, ge=1, le=MAX_MINUTES, description="How far back to look, in minutes.")
    """How far back to look, in minutes, from 1 to :data:`MAX_MINUTES`.

    Defaults to an hour.
    """

    min_level: Literal["warning", "error"] = Field(
        default="error", description="'error' for errors and critical lines, 'warning' to include warnings."
    )
    """``error`` for errors and critical lines, the default, or ``warning`` to include warnings."""

    groups: int = Field(default=15, ge=1, le=50, description="The most groups to return.")
    """The most groups to show, from 1 to 50.

    Defaults to 15. The result says how many more there are.
    """


class SummarizeLogErrorsTool(StaffTool):
    """
    The ``summarize_log_errors`` tool: the errors of the pod logs, grouped by their signature.

    It reads up to :data:`SUMMARY_LINES` warning and error lines, and groups them with
    :func:`~smarter.apps.mcpserver.services.logs.error_groups`, so that the LLM sees each problem
    once, with how often it happened, rather than thousands of lines.
    """

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
        """
        Group the errors, and optionally the warnings, of the period.

        **Side effects:** one HTTP GET to Loki's ``query_range``.

        :param arguments: The validated arguments.
        :returns: Markdown: a heading with the number of lines, then one section for each group, the
            most frequent first, after
            :data:`~smarter.apps.mcpserver.protocol.tools.staff.UNTRUSTED_DATA_NOTICE`, or a
            heading that says there were none.
        :raises SmarterMCPServerServiceError: If the query is not valid.
        :raises LogServiceError: If Loki could not be reached, or rejected the query.
        :raises InfrastructureNotReadyError: If there is no log store.
        """
        min_level = LogLevel(arguments.min_level)
        errors = log_errors(arguments.minutes, min_level, components=tuple(arguments.components))
        if min_level == LogLevel.ERROR:
            levels = "errors"
        else:
            levels = "warnings and errors"

        heading = f"## {errors.lines} {levels} in the last {arguments.minutes} minutes"
        if not errors.lines:
            return f"{heading}\n\nNone. The logs show no {levels} in this period."
        if errors.truncated:
            heading += f" (only the latest {SUMMARY_LINES} were grouped)"

        groups = errors.groups
        shown_groups = groups[: arguments.groups]
        out = [UNTRUSTED_DATA_NOTICE + heading, ""]
        for group in shown_groups:
            seen = f"{group.first_seen:%H:%M:%S} to {group.last_seen:%H:%M:%S} UTC"
            level: Union[LogLevel, str]
            if group.level:
                level = group.level
            else:
                level = "unknown"
            pod_count = len(group.pods)
            out.append(f"### {group.count} × {level} in {group.component} ({pod_count} pods, {seen})")
            out.append(f"Signature: `{group.signature}`")
            out.append("```text")
            out.append(group.example)
            out.append("```")
            out.append("")
        hidden_groups = len(groups) - arguments.groups
        if hidden_groups > 0:
            out.append(f"_{hidden_groups} more groups are not shown._")
        text = "\n".join(out)
        return text


__all__ = [
    "ListLogSourcesTool",
    "SearchLogsTool",
    "SummarizeLogErrorsTool",
]
