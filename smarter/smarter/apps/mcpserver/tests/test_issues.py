"""Tests for smarter.apps.mcpserver.github.issues.

GitHub is never contacted: requests.request is replaced.
"""

from typing import Optional
from unittest import mock

from pydantic import SecretStr

from smarter.apps.mcpserver.exceptions import SmarterMCPServerToolError
from smarter.apps.mcpserver.github import issues
from smarter.apps.mcpserver.github.issues import (
    COMMENT_FOOTER,
    ISSUE_FOOTER,
    MAX_EXCERPT_LENGTH,
    GitHubComment,
    GitHubIssue,
    GitHubIssueHit,
    comment_on_issue,
    create_issue,
    search_issues,
    search_query,
)
from smarter.apps.mcpserver.repositories import ProjectRepository
from smarter.lib.typing import SmarterDictType
from smarter.lib.unittest.base_classes import SmarterTestBase

from .base_classes import TOKEN
from .test_github_client import REQUEST, response

ISSUE: SmarterDictType = {
    "number": 42,
    "title": "smarter apply fails",
    "html_url": "https://github.com/smarter-sh/smarter-test/issues/42",
    "user": {"login": "octocat"},
    "state": "open",
}
COMMENT: SmarterDictType = {
    "id": 7,
    "html_url": "https://github.com/smarter-sh/smarter-test/issues/42#issuecomment-7",
    "user": {"login": "octocat"},
}


class TestIssues(SmarterTestBase):
    """Test create_issue() and comment_on_issue()."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.repository = ProjectRepository(name="smarter-test", title="a test", description="A test repository.")

    def create(self, fake: mock.Mock, token: Optional[str] = TOKEN) -> GitHubIssue:
        with mock.patch(REQUEST, return_value=fake) as request:
            self.request = request
            return create_issue(
                self.repository, "smarter apply fails", "It fails.", SecretStr(token) if token is not None else None
            )

    def comment(self, fake: mock.Mock) -> GitHubComment:
        with mock.patch(REQUEST, return_value=fake) as request:
            self.request = request
            return comment_on_issue(self.repository, 42, "Me too.", SecretStr(TOKEN))

    def assert_fails(self, call, expected: str) -> None:
        with self.assertRaises(SmarterMCPServerToolError) as context:
            call()
        self.assertIn(expected, context.exception.message)
        self.assertNotIn(TOKEN, context.exception.message)

    # -------------------------------------------------------------------------
    # create_issue
    # -------------------------------------------------------------------------
    def test_create_issue(self):
        """The issue is opened with the caller's token, with its footer."""
        issue = self.create(response(201, ISSUE))
        self.assertEqual(
            issue, GitHubIssue(number=42, title=ISSUE["title"], html_url=ISSUE["html_url"], author="octocat")
        )
        args, kwargs = self.request.call_args
        self.assertEqual(args, ("POST", "https://api.github.com/repos/smarter-sh/smarter-test/issues"))
        self.assertEqual(kwargs["headers"]["Authorization"], f"Bearer {TOKEN}")
        self.assertEqual(kwargs["json"], {"title": "smarter apply fails", "body": "It fails." + ISSUE_FOOTER})

    def test_create_issue_requires_a_classic_token(self):
        """Without a classic token, GitHub is never contacted."""
        for token in (None, "not-a-token"):
            with self.subTest(token=token):
                self.assert_fails(lambda token=token: self.create(response(201, ISSUE), token), "personal access token")
                self.request.assert_not_called()

    def test_issue_without_a_user(self):
        """An issue whose response has no user has no author."""
        self.assertIsNone(self.create(response(201, {**ISSUE, "user": None})).author)

    def test_unreadable_issue(self):
        """A 201 whose body is not an issue points to the repository's issues."""
        self.assert_fails(lambda: self.create(response(201, None)), "github.com/smarter-sh/smarter-test/issues")
        self.assert_fails(lambda: self.create(response(201, {"number": "not a number"})), "could not be read")

    def test_create_issue_refused(self):
        """GitHub's refusal is explained."""
        self.assert_fails(lambda: self.create(response(401, {"message": "Bad credentials"})), "revoked")
        self.assert_fails(lambda: self.create(response(422, {"message": "Validation Failed"})), "open the issue")

    # -------------------------------------------------------------------------
    # comment_on_issue
    # -------------------------------------------------------------------------
    def test_comment_on_issue(self):
        """The comment is added with the caller's token, with its footer."""
        comment = self.comment(response(201, COMMENT))
        self.assertEqual(comment, GitHubComment(id=7, html_url=COMMENT["html_url"], author="octocat"))
        args, kwargs = self.request.call_args
        self.assertEqual(args, ("POST", "https://api.github.com/repos/smarter-sh/smarter-test/issues/42/comments"))
        self.assertEqual(kwargs["json"], {"body": "Me too." + COMMENT_FOOTER})

    def test_comment_on_a_missing_issue(self):
        """A 404 means that the issue was not found."""
        self.assert_fails(lambda: self.comment(response(404, {"message": "Not Found"})), "Issue #42 was not found")

    def test_comment_on_a_locked_issue(self):
        """GitHub's reason for refusing a comment is passed on."""
        locked = response(403, {"message": "Unable to create comment because issue is locked."})
        self.assert_fails(lambda: self.comment(locked), "issue is locked")

    def test_unreadable_comment(self):
        """A 201 whose body is not a comment points to the issue."""
        self.assert_fails(lambda: self.comment(response(201, {"id": "x"})), "smarter-test/issues/42")

    def test_the_token_is_never_logged(self):
        """Neither success nor failure logs the token."""
        for fake in (response(201, ISSUE), response(401, {"message": "Bad credentials"})):
            with self.subTest(status=fake.status_code), mock.patch.object(issues, "logger") as logger:
                try:
                    self.create(fake)
                except SmarterMCPServerToolError:
                    pass
                self.assertNotIn(TOKEN, str(logger.method_calls))


def hit(repository: str, number: int, body: str = "It fails.") -> SmarterDictType:
    """Return one issue of GitHub's search result."""
    return {
        "number": number,
        "title": f"issue {number}",
        "state": "open",
        "html_url": f"https://github.com/smarter-sh/{repository}/issues/{number}",
        "repository_url": f"https://api.github.com/repos/smarter-sh/{repository}",
        "comments": 2,
        "updated_at": "2026-10-30T12:00:00Z",
        "body": body,
    }


class TestIssueSearch(SmarterTestBase):
    """Test search_issues() and its query."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cli = ProjectRepository(name="smarter-cli", title="the cli", description="The cli.")
        cls.docs = ProjectRepository(name="smarter", title="the platform", description="The platform.")

    def search(self, fake, repositories=None, one=False, state="all", limit=8, token=None):
        with mock.patch(REQUEST, return_value=fake) as request:
            self.request = request
            return search_issues(repositories or (self.cli, self.docs), "apply fails", one, state, limit, token)

    def test_search_query(self):
        """One repository is searched with repo:, all of them with org:, and a state narrows the search."""
        self.assertEqual(
            search_query("apply fails ", (self.cli,), True, "open"),
            "apply fails is:issue repo:smarter-sh/smarter-cli state:open",
        )
        self.assertEqual(search_query("apply", (self.cli, self.docs), False, "all"), "apply is:issue org:smarter-sh")

    def test_search_all_repositories(self):
        """The organization's other repositories are dropped, and the limit is applied after."""
        items = [hit("smarter-cli", 1), hit("website", 2), hit("smarter", 3), hit("smarter", 4)]
        hits = self.search(response(200, {"total_count": 4, "items": items}), limit=2)
        self.assertEqual(
            [(h.repository, h.number) for h in hits], [("smarter-sh/smarter-cli", 1), ("smarter-sh/smarter", 3)]
        )
        params = self.request.call_args.kwargs["params"]
        self.assertEqual(params["per_page"], "6")
        self.assertNotIn("Authorization", self.request.call_args.kwargs["headers"])

    def test_search_one_repository_with_a_token(self):
        """A classic token is sent, and one repository is searched."""
        self.search(
            response(200, {"items": [hit("smarter-cli", 1)]}), (self.cli,), one=True, limit=3, token=SecretStr(TOKEN)
        )
        kwargs = self.request.call_args.kwargs
        self.assertEqual(kwargs["headers"]["Authorization"], f"Bearer {TOKEN}")
        self.assertEqual(kwargs["params"]["per_page"], "3")
        self.assertIn("repo:smarter-sh/smarter-cli", kwargs["params"]["q"])

    def test_other_tokens_are_not_sent(self):
        """A token that is not a classic GitHub token is not sent to GitHub."""
        self.search(response(200, {"items": []}), token=SecretStr("smarter-api-key"))
        self.assertNotIn("Authorization", self.request.call_args.kwargs["headers"])

    def test_refused(self):
        """GitHub's refusal, e.g. its rate limit, is explained."""
        with self.assertRaisesRegex(SmarterMCPServerToolError, "rate limit"):
            self.search(response(403, {"message": "API rate limit exceeded"}))
        with self.assertRaisesRegex(SmarterMCPServerToolError, "search the issues"):
            self.search(response(422, {"message": "Validation Failed"}))

    def test_unreadable_result(self):
        """A result that is not a search result is an error."""
        for fake in (response(200, None), response(200, {"items": [{"number": "x"}]})):
            with self.subTest(body=fake.json), self.assertRaisesRegex(SmarterMCPServerToolError, "could not be read"):
                self.search(fake)

    def test_excerpt(self):
        """An issue's body is shown on one line, shortened."""
        self.assertEqual(GitHubIssueHit.model_validate(hit("x", 1, "a\n\n b")).excerpt, "a b")
        long = GitHubIssueHit.model_validate(hit("x", 1, "word " * 200)).excerpt
        self.assertEqual(len(long), MAX_EXCERPT_LENGTH)
        self.assertTrue(long.endswith("..."))
        self.assertEqual(GitHubIssueHit.model_validate({**hit("x", 1), "body": None}).excerpt, "")
