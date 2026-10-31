"""Tests for smarter.apps.mcpserver.github.tools.

GitHub is never contacted.
"""

from unittest import mock

from pydantic import SecretStr

from smarter.apps.mcpserver.exceptions import SmarterMCPServerToolError
from smarter.apps.mcpserver.github import tools as github_tools
from smarter.apps.mcpserver.github.issues import (
    GitHubComment,
    GitHubIssue,
    GitHubIssueClosed,
    GitHubIssueComment,
    GitHubIssueDetail,
    GitHubIssueHit,
    GitHubIssueThread,
)
from smarter.apps.mcpserver.github.pulls import (
    GitHubCommitAuthor,
    GitHubPullRequest,
    PullRequestFile,
)
from smarter.apps.mcpserver.github.tools import (
    MAX_LABEL_LENGTH,
    MAX_LABELS,
    CloseIssueTool,
    CommentOnIssueTool,
    CreateIssueTool,
    CreatePullRequestTool,
    ReadIssueTool,
    SearchIssuesTool,
)
from smarter.apps.mcpserver.index.tools import (
    SearchCodeTool,
)
from smarter.apps.mcpserver.protocol.tools import MAX_READ_CHARACTERS

from .base_classes import TOKEN, MCPServerTestBase

SEARCH_ISSUES = "smarter.apps.mcpserver.github.issues.search_issues"
CREATE_ISSUE = "smarter.apps.mcpserver.github.issues.create_issue"
COMMENT_ON_ISSUE = "smarter.apps.mcpserver.github.issues.comment_on_issue"
READ_ISSUE = "smarter.apps.mcpserver.github.issues.read_issue"
CLOSE_ISSUE = "smarter.apps.mcpserver.github.issues.close_issue"
CREATE_PULL_REQUEST = "smarter.apps.mcpserver.github.pulls.create_pull_request"
GITHUB_ISSUE = GitHubIssue(
    number=42,
    title="smarter apply fails",
    html_url="https://github.com/smarter-sh/smarter-test/issues/42",
    author="octocat",
)


class TestGitHubTools(MCPServerTestBase):
    """Test search_issues, create_issue and comment_on_issue."""

    # -------------------------------------------------------------------------
    # search_issues
    # -------------------------------------------------------------------------
    def issue_hit(self, repository, number: int, body: str = "It fails.") -> GitHubIssueHit:
        return GitHubIssueHit(
            number=number,
            title=f"issue {number}",
            state="open",
            html_url=f"https://github.com/{repository.full_name}/issues/{number}",
            repository_url=f"https://api.github.com/repos/{repository.full_name}",
            comments=3,
            updated_at="2026-10-30T12:00:00Z",
            body=body,
        )

    def test_search_issues_of_all_repositories(self):
        """Without a repository, every repository is searched, with the caller's token."""
        token = SecretStr(TOKEN)
        hits = [self.issue_hit(self.code_repository, 4), self.issue_hit(self.docs_repository, 5, "")]
        with mock.patch(SEARCH_ISSUES, return_value=hits) as search:
            text = SearchIssuesTool(self.all(), github_token=token).call({"query": "all repositories", "state": "open"})
        search.assert_called_once_with(
            self.repositories, "all repositories", one=False, state="open", limit=8, token=token
        )
        self.assertIn("2 issues of The Smarter Project's repositories", text)
        self.assertIn(f"1. **issue 4** {self.code_repository.full_name}#4, open, 3 comments, updated 2026-10-30", text)
        self.assertIn("   It fails.", text)

    def test_search_issues_of_one_repository(self):
        """The server of one repository searches it, anonymously."""
        with mock.patch(SEARCH_ISSUES, return_value=[]) as search:
            text = SearchIssuesTool(self.single()).call({"query": "nothing matches"})
        self.assertEqual(search.call_args.args[0], (self.docs_repository,))
        self.assertTrue(search.call_args.kwargs["one"])
        self.assertIsNone(search.call_args.kwargs["token"])
        self.assertIn(f"No issue of {self.docs_repository.full_name} matches", text)

    def test_search_issues_is_cached_for_a_minute(self):
        """A result is cached for ISSUE_SEARCH_CACHE_TTL seconds, not an hour."""
        self.assertEqual(SearchIssuesTool.cache_ttl, github_tools.ISSUE_SEARCH_CACHE_TTL)
        with mock.patch(SEARCH_ISSUES, return_value=[]) as search:
            SearchIssuesTool(self.single()).call({"query": "cached once"})
            SearchIssuesTool(self.single()).call({"query": "cached once"})
        self.assertEqual(search.call_count, 1)
        with mock.patch("smarter.apps.mcpserver.protocol.tools.cached_tool_call") as cached:
            cached.return_value.value = "x"
            SearchIssuesTool(self.single()).call({"query": "ttl"})
        self.assertEqual(cached.call_args.args[3], github_tools.ISSUE_SEARCH_CACHE_TTL)

    def test_create_issue_is_served_only_with_a_github_token(self):
        """Create_issue is served, by every server, by every server, only to a request with a GitHub token."""
        self.assertFalse(CreateIssueTool.serves(self.single()))
        self.assertFalse(CreateIssueTool.serves(self.all()))
        self.assertTrue(CreateIssueTool.serves(self.single(), has_github_token=True))
        self.assertTrue(CreateIssueTool.serves(self.all(), has_github_token=True))
        self.assertTrue(SearchCodeTool.serves(self.single(), has_github_token=True))

    def test_create_issue_requires_a_repository(self):
        """The server of every repository must be told which repository to open the issue in."""
        tool = CreateIssueTool(self.all(), github_token=SecretStr(TOKEN))
        self.assertEqual(tool.input_schema()["required"], ["repository", "title", "body"])
        with mock.patch(CREATE_ISSUE) as create_issue:
            with self.assertRaisesRegex(SmarterMCPServerToolError, "repository is required"):
                tool.call({"title": "t", "body": "b"})
        create_issue.assert_not_called()

    def test_create_issue(self):
        """Create_issue opens the issue as the caller, and reports its url."""
        token = SecretStr(TOKEN)
        tool = CreateIssueTool(self.all(), github_token=token)
        with mock.patch(CREATE_ISSUE, return_value=GITHUB_ISSUE) as create_issue:
            text = tool.call(
                {"repository": self.code_repository.name, "title": " smarter apply fails ", "body": " It fails. "}
            )
        create_issue.assert_called_once_with(self.code_repository, "smarter apply fails", "It fails.", token, labels=())
        self.assertEqual(
            text,
            f"Opened issue #42 in {self.code_repository.full_name} by octocat: smarter apply fails\n"
            f"{GITHUB_ISSUE.html_url}",
        )

    def test_create_issue_is_never_cached(self):
        """Every call opens a new issue: the same arguments twice call GitHub twice."""
        tool = CreateIssueTool(self.single(), github_token=SecretStr(TOKEN))
        anonymous = GITHUB_ISSUE.model_copy(update={"author": None})
        with mock.patch(CREATE_ISSUE, return_value=anonymous) as create_issue:
            first = tool.call({"title": "twice", "body": "the same"})
            tool.call({"title": "twice", "body": "the same"})
        self.assertEqual(create_issue.call_count, 2)
        self.assertNotIn(" by ", first)

    def test_create_issue_limits(self):
        """Titles and bodies that are empty or too long are refused before GitHub is contacted."""
        tool = CreateIssueTool(self.single(), github_token=SecretStr(TOKEN))
        cases = [
            {"title": "", "body": "b"},
            {"title": "t", "body": ""},
            {"title": "t" * 257, "body": "b"},
            {"title": "t", "body": "b" * 20001},
            {"title": "t", "body": "b", "labels": [f"l{n}" for n in range(MAX_LABELS + 1)]},
            {"title": "t", "body": "b", "assignees": ["octocat"]},
        ]
        with mock.patch(CREATE_ISSUE) as create_issue:
            for arguments in cases:
                with self.subTest(arguments=list(arguments)):
                    with self.assertRaisesRegex(SmarterMCPServerToolError, "invalid arguments for create_issue"):
                        tool.call(arguments)
        create_issue.assert_not_called()

    def test_create_issue_with_labels(self):
        """Labels are passed on stripped, blank ones dropped, and a label that is too long is refused."""
        token = SecretStr(TOKEN)
        tool = CreateIssueTool(self.single(), github_token=token)
        with mock.patch(CREATE_ISSUE, return_value=GITHUB_ISSUE) as create_issue:
            tool.call({"title": "t", "body": "b", "labels": [" bug ", "", "severity: high"]})
            create_issue.assert_called_once_with(
                self.docs_repository, "t", "b", token, labels=("bug", "severity: high")
            )
            with self.assertRaisesRegex(SmarterMCPServerToolError, f"at most {MAX_LABEL_LENGTH} characters"):
                tool.call({"title": "t", "body": "b", "labels": ["x" * (MAX_LABEL_LENGTH + 1)]})
        self.assertEqual(create_issue.call_count, 1)

    # -------------------------------------------------------------------------
    # read_issue
    # -------------------------------------------------------------------------
    def thread(self, comments: int = 2, body: str = "It fails.", **issue) -> GitHubIssueThread:
        fields = {
            "number": 42,
            "title": "smarter apply fails",
            "state": "open",
            "html_url": "https://github.com/smarter-sh/x/issues/42",
            "user": {"login": "octocat"},
            "labels": [{"name": "bug"}, {"name": "severity: high"}],
            "comments": comments,
            "created_at": "2026-10-01T12:00:00Z",
            "updated_at": "2026-10-30T12:00:00Z",
            "body": body,
        }
        detail = GitHubIssueDetail.model_validate({**fields, **issue})
        return GitHubIssueThread(
            issue=detail,
            comments=[
                GitHubIssueComment(user={"login": f"user{n}"}, created_at="2026-10-02T12:00:00Z", body=f"comment {n}")
                for n in range(1, comments + 1)
            ],
        )

    def test_read_issue_is_served_to_everyone(self):
        """Read_issue is served without a token, is read-only, and needs a repository on the server of all of them."""
        self.assertTrue(ReadIssueTool.serves(self.single()))
        self.assertTrue(ReadIssueTool.serves(self.all()))
        self.assertTrue(ReadIssueTool.read_only)
        self.assertEqual(ReadIssueTool.cache_ttl, github_tools.ISSUE_SEARCH_CACHE_TTL)
        self.assertEqual(ReadIssueTool(self.all()).input_schema()["required"], ["repository", "issue_number"])
        with self.assertRaisesRegex(SmarterMCPServerToolError, "repository is required"):
            ReadIssueTool(self.all()).call({"issue_number": 1})

    def test_read_issue(self):
        """The issue's state, labels, body and comments are shown, oldest comment first, and cached for a minute."""
        token = SecretStr(TOKEN)
        with mock.patch(READ_ISSUE, return_value=self.thread()) as read_issue:
            text = ReadIssueTool(self.single(), github_token=token).call({"issue_number": 42})
            ReadIssueTool(self.single(), github_token=token).call({"issue_number": 42})
        read_issue.assert_called_once_with(self.docs_repository, 42, token)
        self.assertIn(f"# Issue {self.docs_repository.full_name}#42: smarter apply fails", text)
        self.assertIn(
            "open, opened by octocat 2026-10-01, updated 2026-10-30, labels: bug, severity: high, 2 comments", text
        )
        self.assertIn("It fails.", text)
        self.assertLess(text.index("### user1, 2026-10-02\n\ncomment 1"), text.index("### user2"))
        self.assertNotIn("left out", text)

    def test_read_closed_pull_request(self):
        """A pull request is named so, with why and when it was closed, and an empty body is said to be empty."""
        thread = self.thread(
            comments=0,
            body="",
            state_reason="completed",
            closed_at="2026-10-29T00:00:00Z",
            pull_request={"url": "x"},
            user=None,
            labels=[],
        )
        thread = thread.model_copy(update={"issue": thread.issue.model_copy(update={"state": "closed"})})
        text = ReadIssueTool.format_thread(self.docs_repository, thread)
        self.assertIn("# Pull request ", text)
        self.assertIn("closed (completed), not merged, opened by unknown", text)
        merged = thread.issue.model_copy(update={"pull_request": {"merged_at": "2026-10-28T09:00:00Z"}})
        merged_text = ReadIssueTool.format_thread(self.docs_repository, thread.model_copy(update={"issue": merged}))
        self.assertIn("closed (completed), merged 2026-10-28, opened by unknown", merged_text)
        self.assertIn("closed 2026-10-29", text)
        self.assertIn("labels: none", text)
        self.assertIn("(no description)", text)
        comment = GitHubIssueComment(body=None)
        self.assertEqual(ReadIssueTool.format_comment(comment), "### unknown, \n\n")

    def test_read_long_issue(self):
        """A long body is shortened, and the oldest comments are left out, to fit the result's limit."""
        thread = self.thread(comments=5, body="b" * MAX_READ_CHARACTERS)
        long_comments = [
            comment.model_copy(update={"body": f"comment {n} " + "c" * (MAX_READ_CHARACTERS // 4)})
            for n, comment in enumerate(thread.comments, start=1)
        ]
        thread = thread.model_copy(
            update={"comments": long_comments, "issue": thread.issue.model_copy(update={"comments": 105})}
        )
        text = ReadIssueTool.format_thread(self.docs_repository, thread)
        self.assertLessEqual(len(text), MAX_READ_CHARACTERS)
        self.assertIn("[... the rest of the body is left out]", text)
        self.assertIn("comment 5 ", text)
        self.assertNotIn("comment 1 ", text)
        kept = sum(f"comment {n} " in text for n in range(1, 6))
        self.assertIn(f"[{105 - kept} earlier comments are left out]", text)

    # -------------------------------------------------------------------------
    # comment_on_issue
    # -------------------------------------------------------------------------
    def test_comment_on_issue_is_served_only_with_a_github_token(self):
        """Comment_on_issue is served only to a request with a GitHub token."""
        self.assertFalse(CommentOnIssueTool.serves(self.all()))
        self.assertTrue(CommentOnIssueTool.serves(self.all(), has_github_token=True))
        self.assertEqual(
            CommentOnIssueTool(self.all()).input_schema()["required"], ["repository", "issue_number", "body"]
        )

    def test_comment_on_issue(self):
        """Comment_on_issue comments as the caller, every time, and reports the comment's url."""
        token = SecretStr(TOKEN)
        tool = CommentOnIssueTool(self.single(), github_token=token)
        comment = GitHubComment(
            id=1, html_url="https://github.com/smarter-sh/x/issues/3#issuecomment-1", author="octocat"
        )
        with mock.patch(COMMENT_ON_ISSUE, return_value=comment) as comment_on_issue:
            text = tool.call({"issue_number": 3, "body": " Me too. "})
            tool.call({"issue_number": 3, "body": " Me too. "})
        self.assertEqual(comment_on_issue.call_count, 2)
        comment_on_issue.assert_called_with(self.docs_repository, 3, "Me too.", token)
        self.assertEqual(text, f"Commented on {self.docs_repository.full_name}#3 by octocat.\n{comment.html_url}")
        with mock.patch(COMMENT_ON_ISSUE, return_value=comment.model_copy(update={"author": None})):
            self.assertNotIn(" by ", tool.call({"issue_number": 4, "body": "b"}))

    def test_comment_on_issue_limits(self):
        """An issue number below 1, or an empty body, is refused before GitHub is contacted."""
        tool = CommentOnIssueTool(self.single(), github_token=SecretStr(TOKEN))
        with mock.patch(COMMENT_ON_ISSUE) as comment_on_issue:
            for arguments in ({"issue_number": 0, "body": "b"}, {"issue_number": 1, "body": ""}):
                with self.subTest(arguments=arguments):
                    with self.assertRaisesRegex(SmarterMCPServerToolError, "invalid arguments for comment_on_issue"):
                        tool.call(arguments)
        comment_on_issue.assert_not_called()

    # -------------------------------------------------------------------------
    # close_issue
    # -------------------------------------------------------------------------
    def test_close_issue_is_served_only_with_a_github_token(self):
        """Close_issue is served only to a request with a GitHub token, writes, and needs its arguments."""
        self.assertFalse(CloseIssueTool.serves(self.all()))
        self.assertTrue(CloseIssueTool.serves(self.all(), has_github_token=True))
        self.assertFalse(CloseIssueTool.read_only)
        self.assertEqual(
            CloseIssueTool(self.all()).input_schema()["required"],
            ["repository", "issue_number", "pull_request_number", "comment"],
        )

    def test_close_issue(self):
        """Close_issue closes as the caller, every time, and reports the issue and the comment."""
        token = SecretStr(TOKEN)
        tool = CloseIssueTool(self.single(), github_token=token)
        closed = GitHubIssueClosed(
            number=3,
            html_url="https://github.com/smarter-sh/x/issues/3",
            comment_url="https://github.com/smarter-sh/x/issues/3#issuecomment-1",
            pull_request_url="https://github.com/smarter-sh/x/pull/4",
            author="octocat",
        )
        arguments = {"issue_number": 3, "pull_request_number": 4, "comment": " Fixed by #4. "}
        with mock.patch(CLOSE_ISSUE, return_value=closed) as close_issue:
            text = tool.call(arguments)
            tool.call(arguments)
        self.assertEqual(close_issue.call_count, 2)
        close_issue.assert_called_with(self.docs_repository, 3, 4, "Fixed by #4.", token)
        self.assertEqual(
            text,
            f"Closed {self.docs_repository.full_name}#3 by octocat, resolved by #4.\n{closed.html_url}\n"
            f"Comment: {closed.comment_url}",
        )
        with mock.patch(CLOSE_ISSUE, return_value=closed.model_copy(update={"author": None})):
            self.assertNotIn(" by octocat", tool.call(arguments))
        with mock.patch(CLOSE_ISSUE) as close_issue:
            with self.assertRaisesRegex(SmarterMCPServerToolError, "invalid arguments for close_issue"):
                tool.call({"issue_number": 3, "comment": "c"})
        close_issue.assert_not_called()

    # -------------------------------------------------------------------------
    # create_pull_request
    # -------------------------------------------------------------------------
    def pr_arguments(self, **overrides):
        return {
            "repository": self.code_repository.name,
            "branch": " claude/fix ",
            "base": " alpha ",
            "title": " fix: the timeout ",
            "body": " Fixes #42. ",
            "commit_message": " fix: the timeout ",
            "files": [{"path": "a.py", "content": "x = 1\n"}, {"path": "b.py", "delete": True}],
            **overrides,
        }

    def test_create_pull_request_is_served_only_with_a_github_token(self):
        """Create_pull_request is served only to a request with a GitHub token, writes, and needs its arguments."""
        self.assertFalse(CreatePullRequestTool.serves(self.all()))
        self.assertTrue(CreatePullRequestTool.serves(self.all(), has_github_token=True))
        self.assertFalse(CreatePullRequestTool.read_only)
        schema = CreatePullRequestTool(self.all()).input_schema()
        self.assertEqual(schema["required"], ["repository", "branch", "title", "body", "commit_message", "files"])

    def test_create_pull_request(self):
        """The arguments are passed on stripped, every call writes, and the result names the pull request."""
        token = SecretStr(TOKEN)
        tool = CreatePullRequestTool(self.all(), github_token=token)
        pull_request = GitHubPullRequest(
            number=7,
            title="fix: the timeout",
            html_url="https://github.com/smarter-sh/x/pull/7",
            draft=True,
            author="octocat",
            branch="claude/fix",
            base="alpha",
            commit_sha="e" * 40,
        )
        author = {"name": "Claude", "email": "noreply@anthropic.com"}
        with mock.patch(CREATE_PULL_REQUEST, return_value=pull_request) as create_pull_request:
            text = tool.call(self.pr_arguments(author=author, draft=True))
            tool.call(self.pr_arguments(author=author, draft=True))
        self.assertEqual(create_pull_request.call_count, 2)
        create_pull_request.assert_called_with(
            self.code_repository,
            branch="claude/fix",
            title="fix: the timeout",
            body="Fixes #42.",
            commit_message="fix: the timeout",
            files=[PullRequestFile(path="a.py", content="x = 1\n"), PullRequestFile(path="b.py", delete=True)],
            token=token,
            base="alpha",
            author=GitHubCommitAuthor(**author),
            draft=True,
        )
        self.assertEqual(
            text,
            f"Opened draft pull request #7 in {self.code_repository.full_name} by octocat: fix: the timeout\n"
            f"{pull_request.html_url}\nclaude/fix into alpha, commit {'e' * 12}",
        )
        plain = pull_request.model_copy(update={"draft": False, "author": None})
        with mock.patch(CREATE_PULL_REQUEST, return_value=plain) as create_pull_request:
            text = tool.call(self.pr_arguments(base="  "))
        self.assertIsNone(create_pull_request.call_args.kwargs["base"])
        self.assertIsNone(create_pull_request.call_args.kwargs["author"])
        self.assertFalse(create_pull_request.call_args.kwargs["draft"])
        self.assertTrue(text.startswith("Opened pull request #7"))
        self.assertNotIn(" by ", text)

    def test_create_pull_request_limits(self):
        """Missing files, too many files, unknown fields and a bad author are refused before GitHub is contacted."""
        tool = CreatePullRequestTool(self.all(), github_token=SecretStr(TOKEN))
        cases = [
            {"files": []},
            {"files": [{"path": f"f{n}", "content": "x"} for n in range(21)]},
            {"files": [{"path": "a", "content": "x", "mode": "100755"}]},
            {"author": {"name": "Claude", "email": "not an email"}},
            {"commit_message": ""},
        ]
        with mock.patch(CREATE_PULL_REQUEST) as create_pull_request:
            for overrides in cases:
                with self.subTest(overrides=list(overrides)):
                    with self.assertRaisesRegex(SmarterMCPServerToolError, "invalid arguments for create_pull_request"):
                        tool.call(self.pr_arguments(**overrides))
        create_pull_request.assert_not_called()
