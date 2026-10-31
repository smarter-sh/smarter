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
    GitHubIssueClosed,
    GitHubIssueHit,
    close_issue,
    comment_on_issue,
    create_issue,
    read_issue,
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

    def create(
        self, fake: mock.Mock, token: Optional[str] = TOKEN, body: str = "It fails.", labels: tuple[str, ...] = ()
    ) -> GitHubIssue:
        with mock.patch(REQUEST, return_value=fake) as request:
            self.request = request
            return create_issue(
                self.repository,
                "smarter apply fails",
                body,
                SecretStr(token) if token is not None else None,
                labels=labels,
            )

    def comment(self, fake: mock.Mock, body: str = "Me too.") -> GitHubComment:
        with mock.patch(REQUEST, return_value=fake) as request:
            self.request = request
            return comment_on_issue(self.repository, 42, body, SecretStr(TOKEN))

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

    def test_create_issue_with_labels(self):
        """Labels are sent only when there are some."""
        self.create(response(201, ISSUE), labels=("bug", "severity: high"))
        self.assertEqual(self.request.call_args.kwargs["json"]["labels"], ["bug", "severity: high"])
        self.create(response(201, ISSUE))
        self.assertNotIn("labels", self.request.call_args.kwargs["json"])

    def test_credentials_are_never_written(self):
        """An issue or comment that holds the caller's token or another credential is refused before GitHub is contacted."""
        api_key = "sk-" + "ant-" + "a1B2" * 8
        for body in (f"token {TOKEN}", f"key {api_key}"):
            with self.subTest(body=body[:8]):
                self.assert_fails(lambda body=body: self.create(response(201, ISSUE), body=body), "public")
                self.request.assert_not_called()
                self.assert_fails(lambda body=body: self.comment(response(201, COMMENT), body=body), "public")
                self.request.assert_not_called()
        with self.assertRaises(SmarterMCPServerToolError) as context:
            self.create(response(201, ISSUE), labels=(api_key,))
        self.assertNotIn(api_key, context.exception.message)

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


ISSUE_DETAIL: SmarterDictType = {
    "number": 42,
    "title": "smarter apply fails",
    "state": "closed",
    "state_reason": "completed",
    "html_url": "https://github.com/smarter-sh/smarter-test/issues/42",
    "user": {"login": "octocat"},
    "labels": [{"name": "bug"}],
    "comments": 0,
    "created_at": "2026-10-01T12:00:00Z",
    "updated_at": "2026-10-30T12:00:00Z",
    "closed_at": "2026-10-30T12:00:00Z",
    "body": "It fails.",
}


def comment_json(number: int) -> SmarterDictType:
    """Return one comment of GitHub's list of an issue's comments."""
    return {
        "user": {"login": f"user{number}"},
        "created_at": "2026-10-02T12:00:00Z",
        "html_url": f"https://github.com/smarter-sh/smarter-test/issues/42#issuecomment-{number}",
        "body": f"comment {number}",
    }


class TestReadIssue(SmarterTestBase):
    """Test read_issue()."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.repository = ProjectRepository(name="smarter-test", title="a test", description="A test repository.")

    def read(self, *fakes: mock.Mock, token: Optional[SecretStr] = None):
        with mock.patch(REQUEST, side_effect=list(fakes)) as request:
            self.request = request
            return read_issue(self.repository, 42, token)

    def test_issue_without_comments(self):
        """An issue without comments is read with one anonymous request."""
        thread = self.read(response(200, ISSUE_DETAIL))
        self.assertEqual(thread.issue.number, 42)
        self.assertEqual(thread.issue.state_reason, "completed")
        self.assertEqual([label.name for label in thread.issue.labels], ["bug"])
        self.assertEqual(thread.comments, [])
        self.assertEqual(self.request.call_count, 1)
        args, kwargs = self.request.call_args
        self.assertEqual(args, ("GET", "https://api.github.com/repos/smarter-sh/smarter-test/issues/42"))
        self.assertNotIn("Authorization", kwargs["headers"])

    def test_latest_comments_are_read(self):
        """The last page of comments is read, with the caller's classic token."""
        comments = [comment_json(number) for number in range(101, 151)]
        thread = self.read(
            response(200, {**ISSUE_DETAIL, "comments": 150}), response(200, comments), token=SecretStr(TOKEN)
        )
        self.assertEqual(len(thread.comments), 50)
        self.assertEqual(thread.comments[0].user.login, "user101")
        args, kwargs = self.request.call_args
        self.assertEqual(args, ("GET", "https://api.github.com/repos/smarter-sh/smarter-test/issues/42/comments"))
        self.assertEqual(kwargs["params"], {"per_page": "100", "page": "2"})
        self.assertEqual(kwargs["headers"]["Authorization"], f"Bearer {TOKEN}")

    def test_one_page_of_comments(self):
        """Up to 100 comments are on the first page."""
        self.read(response(200, {**ISSUE_DETAIL, "comments": 100}), response(200, [comment_json(1)]))
        self.assertEqual(self.request.call_args.kwargs["params"]["page"], "1")

    def test_issue_not_found(self):
        """A missing issue is explained."""
        with self.assertRaisesRegex(SmarterMCPServerToolError, "Issue #42 was not found"):
            self.read(response(404, {"message": "Not Found"}))

    def test_comments_refused(self):
        """A refusal to list the comments is explained."""
        with self.assertRaisesRegex(SmarterMCPServerToolError, "rate limit"):
            self.read(response(200, {**ISSUE_DETAIL, "comments": 1}), response(429, None))

    def test_unreadable_issue(self):
        """A response that is not an issue is an error."""
        for fake in (response(200, None), response(200, {"number": "x"})):
            with self.subTest(body=fake.json), self.assertRaisesRegex(SmarterMCPServerToolError, "could not be read"):
                self.read(fake)

    def test_unreadable_comments(self):
        """A response that is not a list of comments is an error."""
        for body in (None, {"message": "x"}, [{"user": "not a user"}]):
            with self.subTest(body=body), self.assertRaisesRegex(SmarterMCPServerToolError, "comments of issue #42"):
                self.read(response(200, {**ISSUE_DETAIL, "comments": 1}), response(200, body))


MERGED_PULL: SmarterDictType = {
    "number": 43,
    "html_url": "https://github.com/smarter-sh/smarter-test/pull/43",
    "merged": True,
    "merged_at": "2026-10-30T12:00:00Z",
}


class TestCloseIssue(SmarterTestBase):
    """Test close_issue()."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.repository = ProjectRepository(name="smarter-test", title="a test", description="A test repository.")

    def close(self, *fakes: mock.Mock, comment: str = "Fixed by #43.", pull_request_number: int = 43):
        with mock.patch(REQUEST, side_effect=list(fakes)) as request:
            self.request = request
            return close_issue(self.repository, 42, pull_request_number, comment, SecretStr(TOKEN))

    def calls(self) -> list[tuple]:
        return [call.args for call in self.request.call_args_list]

    def assert_fails(self, call, expected: str) -> str:
        with self.assertRaises(SmarterMCPServerToolError) as context:
            call()
        self.assertIn(expected, context.exception.message)
        self.assertNotIn(TOKEN, context.exception.message)
        return context.exception.message

    def test_close_issue(self):
        """The merged pull request is checked, the comment added, and the issue closed as completed."""
        closed = self.close(response(200, MERGED_PULL), response(201, COMMENT), response(200, {"state": "closed"}))
        self.assertEqual(
            closed,
            GitHubIssueClosed(
                number=42,
                html_url="https://github.com/smarter-sh/smarter-test/issues/42",
                comment_url=COMMENT["html_url"],
                pull_request_url=MERGED_PULL["html_url"],
                author="octocat",
            ),
        )
        api = "https://api.github.com/repos/smarter-sh/smarter-test"
        self.assertEqual(
            self.calls(),
            [("GET", f"{api}/pulls/43"), ("POST", f"{api}/issues/42/comments"), ("PATCH", f"{api}/issues/42")],
        )
        self.assertEqual(self.request.call_args_list[1].kwargs["json"], {"body": "Fixed by #43." + COMMENT_FOOTER})
        self.assertEqual(self.request.call_args.kwargs["json"], {"state": "closed", "state_reason": "completed"})
        for call in self.request.call_args_list:
            self.assertEqual(call.kwargs["headers"]["Authorization"], f"Bearer {TOKEN}")

    def test_unmerged_pull_request(self):
        """An open or closed but unmerged pull request closes nothing, and adds no comment."""
        for pull in ({**MERGED_PULL, "merged": False, "merged_at": None}, {"number": 43, "html_url": "x"}):
            with self.subTest(pull=pull):
                self.assert_fails(lambda pull=pull: self.close(response(200, pull)), "is not merged")
                self.assertEqual(len(self.calls()), 1)

    def test_refused_before_github_is_contacted(self):
        """A credential in the comment, a missing token or an issue that resolves itself are refused without a request."""
        self.assert_fails(lambda: self.close(response(200, MERGED_PULL), comment=f"x {TOKEN}"), "public")
        self.request.assert_not_called()
        self.assert_fails(lambda: self.close(response(200, MERGED_PULL), pull_request_number=42), "by itself")
        self.request.assert_not_called()
        with mock.patch(REQUEST) as request, self.assertRaisesRegex(SmarterMCPServerToolError, "personal access token"):
            close_issue(self.repository, 42, 43, "c", None)
        request.assert_not_called()

    def test_pull_request_not_found(self):
        """A pull request that does not exist is explained, and nothing is written."""
        self.assert_fails(lambda: self.close(response(404, {"message": "Not Found"})), "Pull request #43 was not found")
        self.assertEqual(len(self.calls()), 1)

    def test_unreadable_pull_request(self):
        """A response that is not a pull request is an error, and nothing is written."""
        for body in (None, {"number": "x"}):
            with self.subTest(body=body):
                self.assert_fails(lambda body=body: self.close(response(200, body)), "could not be read")
                self.assertEqual(len(self.calls()), 1)

    def test_comment_refused(self):
        """When the comment is refused, the issue is not closed."""
        locked = response(403, {"message": "Unable to create comment because issue is locked."})
        self.assert_fails(lambda: self.close(response(200, MERGED_PULL), locked), "issue is locked")
        self.assertNotIn("PATCH", [call[0] for call in self.calls()])

    def test_close_refused_after_the_comment(self):
        """When the issue cannot be closed, the error says that the comment was added, and not to add it again."""
        message = self.assert_fails(
            lambda: self.close(
                response(200, MERGED_PULL), response(201, COMMENT), response(403, {"message": "Must have admin rights"})
            ),
            "The comment was added",
        )
        self.assertIn(COMMENT["html_url"], message)
        self.assertIn("Must have admin rights", message)
        self.assertIn("Do not add the comment again", message)
