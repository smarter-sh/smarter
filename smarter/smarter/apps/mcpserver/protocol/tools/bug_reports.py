"""
The staff-only tool that opens a bug report: ``create_bug_report``.

When the platform's staff, with an AI agent such as Smarter Sysadmin, have diagnosed a bug in
Smarter itself, :class:`CreateBugReportTool` opens it as a GitHub issue in the repository of The
Smarter Project that owns it, with the platform's own GitHub token (see
:mod:`~smarter.apps.mcpserver.services.github.bug_reports`). The staff member needs no GitHub token:
they only agree to the report that the agent shows them.

It is the one staff-only tool that writes. Like every operations tool, each call takes a ``ticket``,
is recorded in the audit trail, with the report's title and body, and is never cached (see
:class:`~smarter.apps.mcpserver.protocol.tools.staff.StaffTool`).

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from typing import cast

from pydantic import Field, field_validator

from smarter.apps.mcpserver.protocol.tools.github import MAX_LABELS, clean_labels
from smarter.apps.mcpserver.protocol.tools.staff import StaffTool, StaffToolArguments
from smarter.apps.mcpserver.services.github import bug_reports, issues
from smarter.apps.mcpserver.services.repositories import (
    ProjectRepository,
    get_repository,
    repository_names,
)

DEFAULT_REPOSITORY = "smarter"
"""The repository of a bug report whose caller names none: the platform's own."""


class CreateBugReportArguments(StaffToolArguments):
    """
    The arguments of ``create_bug_report``: the ticket, the repository, the title, the body and the labels.

    The repository must be one of The Smarter Project's. The lengths are checked here, before
    anything is sent to GitHub. Personal data, private details and credentials are refused later,
    by :func:`~smarter.apps.mcpserver.services.github.bug_reports.create_bug_report`.
    """

    repository: str = Field(
        default=DEFAULT_REPOSITORY,
        description=(
            "The repository of The Smarter Project that owns the bug, e.g. smarter for the platform, or "
            "smarter-cli. Use search_code to find which one."
        ),
    )
    title: str = Field(
        min_length=1,
        max_length=issues.MAX_TITLE_LENGTH,
        description="One specific line, e.g. 'Plugin apply fails with HTTP 500 when the Secret is missing'.",
    )
    body: str = Field(
        min_length=1,
        max_length=issues.MAX_BODY_LENGTH,
        description=(
            "The report, in Markdown: what happens, what was expected, when it started and how often, the "
            "evidence (the error and the component that logged it), the cause in the code if known, with its "
            "file, and how to reproduce it. No users, email addresses, IP addresses, node names or secrets."
        ),
    )
    labels: list[str] = Field(
        default_factory=lambda: list(bug_reports.DEFAULT_LABELS),
        max_length=MAX_LABELS,
        description="Labels, bug by default. Use the repository's existing labels.",
    )

    @field_validator("repository")
    @classmethod
    def known_repository(cls, value: str) -> str:
        """
        Accept only a repository of The Smarter Project.

        :param value: The repository's name, as the LLM gave it.
        :returns: The name, stripped.
        :raises ValueError: If it is not one of the project's repositories. The error lists them.
        """
        name = value.strip()
        if get_repository(name) is None:
            choices = ", ".join(repository_names())
            raise ValueError(f"{name} is not a repository of The Smarter Project. It is one of: {choices}.")
        return name


class CreateBugReportTool(StaffTool):
    """
    The ``create_bug_report`` operations tool: open a GitHub issue for a bug that the staff diagnosed.

    **Writes:** a public GitHub issue, with the platform's GitHub token,
    ``GITHUB_TOKEN`` (see
    :func:`~smarter.apps.mcpserver.services.github.bug_reports.create_bug_report`), which notifies the
    repository's watchers.

    **Result:** a sentence with the new issue's number, repository and title, and its url.

    **Side effects:** one request to GitHub that creates the issue, and the audit trail's row, with
    the title and body. Its description tells the LLM to search for the issue first, to show the
    report to the staff member, and to call it only once they agree.
    """

    name = "create_bug_report"
    title = "Create bug report"
    description = (
        "Open a GitHub issue that reports a bug in Smarter, in the repository of The Smarter Project that owns it, "
        "with this platform's GitHub account. Use it when the evidence shows a defect in Smarter's code or "
        "configuration, not a user's mistake or an outage of a provider. It is public, and maintainers are "
        "notified: first call search_issues, if you have it, so that a bug is not reported twice, then show the "
        "staff member the repository, title and body, and call it only after they agree, once. Never include "
        "users, email addresses, IP addresses, node names or secrets."
    )
    arguments_model = CreateBugReportArguments
    read_only = False
    open_world = True

    def run(self, arguments: CreateBugReportArguments) -> str:  # type: ignore[override]
        """
        Open the bug report that the call describes.

        :param arguments: The validated arguments.
        :returns: The new issue's number, repository, title and url.
        :raises SmarterMCPServerToolError: If a label is too long.
        :raises SmarterMCPServerServiceError: If bug reports are not configured, the report contains
            personal data, private details or a credential, or GitHub did not open the issue.
        """
        repository = cast(ProjectRepository, get_repository(arguments.repository))
        labels = clean_labels(arguments.labels)
        title = arguments.title.strip()
        body = arguments.body.strip()
        issue = bug_reports.create_bug_report(repository, title, body, labels=labels)
        return f"Opened issue #{issue.number} in {repository.full_name}: {issue.title}\n{issue.html_url}"


__all__ = ["CreateBugReportTool"]
