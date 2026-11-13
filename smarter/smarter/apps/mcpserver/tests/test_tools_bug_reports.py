"""Tests for smarter.apps.mcpserver.protocol.tools.bug_reports: create_bug_report.

GitHub is never contacted: the service's create_bug_report is replaced.
"""

from unittest import mock

from smarter.apps.mcpserver.exceptions import (
    SmarterMCPServerServiceError,
    SmarterMCPServerToolError,
)
from smarter.apps.mcpserver.protocol.tools.bug_reports import (
    DEFAULT_REPOSITORY,
    CreateBugReportTool,
)
from smarter.apps.mcpserver.protocol.tools.github import MAX_LABEL_LENGTH
from smarter.apps.mcpserver.services.github.issues import GitHubIssue
from smarter.lib.typing import required

from .operations_base import TICKET, OperationsTestBase

CREATE_BUG_REPORT = "smarter.apps.mcpserver.services.github.bug_reports.create_bug_report"
ISSUE = GitHubIssue(
    number=7,
    title="Workers stop consuming after a Redis restart",
    html_url="https://github.com/smarter-sh/smarter/issues/7",
    author="smarter-bot",
)
BODY = "After Redis restarted, no Celery worker ran a task."


class TestCreateBugReportTool(OperationsTestBase):
    """Test create_bug_report."""

    def report(self, **arguments) -> str:
        tool = CreateBugReportTool(self.admin_user)
        return tool.call({"ticket": TICKET, "title": ISSUE.title, "body": BODY, **arguments})

    def test_annotations(self):
        """It is the staff-only tool that writes, and says so."""
        definition = CreateBugReportTool(self.admin_user).definition()
        annotations = required(definition.annotations, "definition.annotations")
        self.assertFalse(annotations.read_only_hint)
        self.assertTrue(annotations.open_world_hint)

    def test_create_bug_report(self):
        with mock.patch(CREATE_BUG_REPORT, return_value=ISSUE) as create_bug_report:
            text = self.report(labels=[" bug ", "", "severity: high"])
        repository, title, body = create_bug_report.call_args.args
        self.assertEqual(repository.name, DEFAULT_REPOSITORY)
        self.assertEqual(title, ISSUE.title)
        self.assertEqual(body, BODY)
        self.assertEqual(create_bug_report.call_args.kwargs["labels"], ("bug", "severity: high"))
        self.assertIn(f"Opened issue #7 in smarter-sh/{DEFAULT_REPOSITORY}", text)
        self.assertIn(ISSUE.html_url, text)
        row = self.audit_rows().first()
        self.assertEqual(row.tool, "create_bug_report")
        self.assertEqual(row.arguments["title"], ISSUE.title, "the report is audited")
        self.assertFalse(row.is_error)

    def test_default_label(self):
        with mock.patch(CREATE_BUG_REPORT, return_value=ISSUE) as create_bug_report:
            self.report()
        self.assertEqual(create_bug_report.call_args.kwargs["labels"], ("bug",))

    def test_other_repository(self):
        with mock.patch(CREATE_BUG_REPORT, return_value=ISSUE) as create_bug_report:
            self.report(repository="smarter-cli")
        self.assertEqual(create_bug_report.call_args.args[0].name, "smarter-cli")

    def test_unknown_repository(self):
        with mock.patch(CREATE_BUG_REPORT) as create_bug_report:
            with self.assertRaisesRegex(SmarterMCPServerToolError, "not a repository of The Smarter Project"):
                self.report(repository="not-a-repository")
        create_bug_report.assert_not_called()

    def test_label_too_long(self):
        with mock.patch(CREATE_BUG_REPORT) as create_bug_report:
            with self.assertRaisesRegex(SmarterMCPServerToolError, "A label is at most"):
                self.report(labels=["x" * (MAX_LABEL_LENGTH + 1)])
        create_bug_report.assert_not_called()
        self.assertTrue(self.audit_rows().first().is_error)

    def test_service_error(self):
        """A refusal of the service reaches the LLM, and the call is audited as an error."""
        error = SmarterMCPServerServiceError("Bug reports are not configured on this platform.")
        with mock.patch(CREATE_BUG_REPORT, side_effect=error):
            with self.assertRaisesRegex(SmarterMCPServerToolError, "not configured"):
                self.report()
        self.assertTrue(self.audit_rows().first().is_error)

    def test_requires_a_staff_user(self):
        with self.assertRaisesRegex(SmarterMCPServerToolError, "requires a staff user"):
            CreateBugReportTool(None).call({"ticket": TICKET, "title": ISSUE.title, "body": BODY})
