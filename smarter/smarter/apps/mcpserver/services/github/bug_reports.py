"""
Bug reports that the platform's staff open in The Smarter Project's repositories.

When a staff member and their AI agent, e.g. Smarter Sysadmin, have diagnosed a bug in Smarter
itself, rather than a user's mistake or an outage of a provider, :func:`create_bug_report` opens it
as a GitHub issue, with :func:`~smarter.apps.mcpserver.services.github.issues.create_issue`.

Unlike the public ``create_issue`` tool, which writes with the caller's own GitHub token, a bug
report is written with the platform's token, ``smarter_settings.github_token``
(``GITHUB_TOKEN``), so that a staff member who chats with Smarter Sysadmin needs no
GitHub token of their own. The staff-only endpoint has already verified who they are, and the
staff-only tool records the call, under their name, in the audit trail.

A bug report is public, and it is written from material that is not: the platform's logs and its
users' accounts. So, before anything is sent to GitHub, :func:`public_text_findings` looks for
personal data, with the same Guardrail detectors as ``check_reply``, and for the rules of
:data:`BUG_REPORT_RULES`, e.g. node names, which contain private IP addresses. A report with a
finding is refused, with the findings, so that the agent can remove them and try again.
:func:`~smarter.apps.mcpserver.services.github.client.refuse_secrets` then refuses credentials.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from smarter.apps.mcpserver.exceptions import SmarterMCPServerServiceError
from smarter.apps.mcpserver.services.github import issues
from smarter.apps.mcpserver.services.github.issues import GitHubIssue
from smarter.apps.mcpserver.services.helpdesk.replies import (
    REPLY_RULES,
    ReplyFinding,
    detector_findings,
)
from smarter.apps.mcpserver.services.repositories import ProjectRepository
from smarter.common.conf import smarter_settings
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.MCPSERVER_LOGGING])
logger_prefix = logging.SmarterFormattedText.text(__name__)

BUG_REPORT_RULE_NAMES = ("node_name", "account_id")
"""The rules of :data:`~smarter.apps.mcpserver.services.helpdesk.replies.REPLY_RULES` that a bug report must follow too.

A bug report may quote an error, an exception's name, a version or a pod's name, which help a
maintainer find the bug. It must not name a node, whose name contains a private IP address, nor a
cloud account id.
"""

BUG_REPORT_RULES = tuple(rule for rule in REPLY_RULES if rule.name in BUG_REPORT_RULE_NAMES)
"""The rules that :func:`public_text_findings` applies, beyond the Guardrail detectors."""

DEFAULT_LABELS = ("bug",)
"""The labels of a bug report whose caller gives none."""

NOT_CONFIGURED = (
    "Bug reports are not configured on this platform: its operator must set GITHUB_TOKEN to a "
    "GitHub classic personal access token with the public_repo scope. Give the staff member the title and body "
    "instead, so that they can open the issue themselves."
)
"""The error of :func:`create_bug_report` when the platform has no GitHub token for bug reports."""


def bug_report_footer() -> str:
    """
    Return the line that :func:`create_bug_report` appends to every bug report's body.

    It says where the report came from, so that maintainers can tell it from a user's issue. It
    names the platform's environment, e.g. ``prod``, but never the staff member, whose name is in
    the audit trail rather than in a public issue.

    :returns: The footer, which starts with a blank line.
    """
    environment = smarter_settings.environment
    where = "a Smarter platform"
    if environment:
        where = f"the {environment} Smarter platform"
    return f"\n\n_Reported by the staff of {where}, with Smarter Sysadmin._"


def public_text_findings(text: str) -> list[ReplyFinding]:
    """
    Find personal data, and the platform's private details, in the text of a bug report.

    :param text: The title, or the body.
    :returns: Each match of the Guardrail detectors of
        :data:`~smarter.apps.mcpserver.services.helpdesk.replies.DETECTOR_REASONS`, then of
        :data:`BUG_REPORT_RULES`, in that order, or an empty list.
    """
    findings = detector_findings(text, None)
    for rule in BUG_REPORT_RULES:
        for match in rule.pattern.finditer(text):
            finding = ReplyFinding(rule=rule.name, text=match.group(0), why=rule.why)
            findings.append(finding)
    return findings


def refuse_private_data(*texts: str) -> None:
    """
    Refuse to publish a bug report that contains personal data, or the platform's private details.

    :param texts: The title and the body.
    :raises SmarterMCPServerServiceError: If a text has a finding of :func:`public_text_findings`.
        The error lists each one, its rule and why, so that the agent can remove it.
    """
    findings: list[ReplyFinding] = []
    for text in texts:
        findings += public_text_findings(text)
    if not findings:
        return
    lines = ["The bug report was not opened: it is public, and it contains what must not be published."]
    for finding in findings:
        lines.append(f"- {finding.rule}: `{finding.text}`. {finding.why}")
    lines.append("Remove or generalize them, e.g. 'a user' rather than an address, and try again.")
    message = "\n".join(lines)
    raise SmarterMCPServerServiceError(message)


def create_bug_report(
    repository: ProjectRepository,
    title: str,
    body: str,
    labels: tuple[str, ...] = DEFAULT_LABELS,
) -> GitHubIssue:
    """
    Open a bug report in a repository of The Smarter Project, with the platform's GitHub token.

    The title and body are checked for personal data and private details first
    (:func:`refuse_private_data`), then :func:`~smarter.apps.mcpserver.services.github.issues.create_issue`
    checks the token and refuses credentials, and opens the issue, with :func:`bug_report_footer`
    appended to the body.

    Side effects: one ``POST /repos/{owner}/{repo}/issues`` request to GitHub, which creates a
    public issue and notifies the repository's watchers. Nothing is cached. The new issue's url is
    logged.

    :param repository: The repository that owns the bug.
    :param title: The issue's title.
    :param body: The issue's body, in Markdown.
    :param labels: The issue's labels, :data:`DEFAULT_LABELS` by default.
    :returns: The new issue.
    :raises SmarterMCPServerServiceError: If the platform has no token for bug reports, the text
        contains personal data, private details or a credential, or GitHub did not open the issue.
    """
    token = smarter_settings.github_token
    if token is None:
        logger.info("%s.create_bug_report() GITHUB_TOKEN is not set", logger_prefix)
        raise SmarterMCPServerServiceError(NOT_CONFIGURED)
    refuse_private_data(title, body)
    body_with_footer = body + bug_report_footer()
    issue = issues.create_issue(repository, title, body_with_footer, token, labels=labels)
    logger.info("%s.create_bug_report() opened %s", logger_prefix, issue.html_url)
    return issue


__all__ = [
    "BUG_REPORT_RULES",
    "DEFAULT_LABELS",
    "NOT_CONFIGURED",
    "bug_report_footer",
    "create_bug_report",
    "public_text_findings",
    "refuse_private_data",
]
