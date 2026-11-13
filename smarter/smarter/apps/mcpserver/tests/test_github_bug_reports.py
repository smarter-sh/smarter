"""Tests for smarter.apps.mcpserver.services.github.bug_reports.

GitHub is never contacted: create_issue is replaced.
"""

from unittest import mock

from pydantic import SecretStr

from smarter.apps.mcpserver.exceptions import SmarterMCPServerServiceError
from smarter.apps.mcpserver.services.github.bug_reports import (
    DEFAULT_LABELS,
    NOT_CONFIGURED,
    bug_report_footer,
    create_bug_report,
    public_text_findings,
    refuse_private_data,
)
from smarter.apps.mcpserver.services.github.issues import GitHubIssue
from smarter.apps.mcpserver.services.repositories import ProjectRepository
from smarter.lib.unittest.base_classes import SmarterTestBase

from .base_classes import TOKEN

SETTINGS = "smarter.apps.mcpserver.services.github.bug_reports.smarter_settings"
CREATE_ISSUE = "smarter.apps.mcpserver.services.github.issues.create_issue"
ISSUE = GitHubIssue(
    number=7,
    title="Workers stop consuming after a Redis restart",
    html_url="https://github.com/smarter-sh/smarter-test/issues/7",
    author="smarter-bot",
)
BODY = "After Redis restarted, no Celery worker ran a task. The beat pod sent 13 due tasks."


class TestBugReports(SmarterTestBase):
    """Test create_bug_report() and its checks."""

    repository: ProjectRepository

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.repository = ProjectRepository(name="smarter-test", title="a test", description="A test repository.")

    def settings(self, token=TOKEN, environment="prod") -> mock.Mock:
        fake = mock.Mock()
        fake.github_token = SecretStr(token) if token else None
        fake.environment = environment
        return fake

    def test_create_bug_report(self):
        """The report is opened with the platform's token, the default label and the footer."""
        settings = self.settings()
        with mock.patch(SETTINGS, settings), mock.patch(CREATE_ISSUE, return_value=ISSUE) as create_issue:
            issue = create_bug_report(self.repository, ISSUE.title, BODY)
        self.assertEqual(issue, ISSUE)
        repository, title, body, token = create_issue.call_args.args
        self.assertEqual(repository, self.repository)
        self.assertEqual(title, ISSUE.title)
        self.assertTrue(body.startswith(BODY))
        self.assertIn("Reported by the staff of the prod Smarter platform, with Smarter Sysadmin.", body)
        self.assertIs(token, settings.github_token)
        self.assertEqual(create_issue.call_args.kwargs["labels"], DEFAULT_LABELS)

    def test_not_configured(self):
        """Without a token, nothing is sent, and the error says what the operator must set."""
        with mock.patch(SETTINGS, self.settings(token=None)), mock.patch(CREATE_ISSUE) as create_issue:
            with self.assertRaisesRegex(SmarterMCPServerServiceError, "GITHUB_TOKEN"):
                create_bug_report(self.repository, ISSUE.title, BODY)
        create_issue.assert_not_called()
        self.assertIn("Give the staff member the title and body", NOT_CONFIGURED)

    def test_private_data_is_refused(self):
        """Personal data and node names are refused before GitHub is called, and each is named."""
        body = "It fails for jane.doe@example.com on ip-192-168-10-152.ca-central-1.compute.internal."
        with mock.patch(SETTINGS, self.settings()), mock.patch(CREATE_ISSUE) as create_issue:
            with self.assertRaises(SmarterMCPServerServiceError) as context:
                create_bug_report(self.repository, ISSUE.title, body)
        create_issue.assert_not_called()
        message = str(context.exception)
        self.assertIn("email", message)
        self.assertIn("node_name", message)
        self.assertIn("try again", message)

    def test_what_a_report_may_contain(self):
        """Versions, pod names and exception names help a maintainer, and are allowed."""
        text = "smarter-worker-5b7f794fb-dw7mx raised ConnectionError on v0.42.9, in lib/celery_conf/__init__.py."
        self.assertEqual(public_text_findings(text), [])
        refuse_private_data(ISSUE.title, text)

    def test_account_id_is_refused(self):
        findings = public_text_findings("The role in account 123456789012 is missing.")
        self.assertEqual([finding.rule for finding in findings], ["account_id"])

    def test_footer_without_environment(self):
        with mock.patch(SETTINGS, self.settings(environment="")):
            self.assertIn("staff of a Smarter platform", bug_report_footer())
