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
    GitHubIssueHit,
)
from smarter.apps.mcpserver.github.tools import (
    CommentOnIssueTool,
    CreateIssueTool,
    SearchIssuesTool,
)
from smarter.apps.mcpserver.index.tools import (
    SearchCodeTool,
)

from .base_classes import TOKEN, MCPServerTestBase

SEARCH_ISSUES = "smarter.apps.mcpserver.github.issues.search_issues"
CREATE_ISSUE = "smarter.apps.mcpserver.github.issues.create_issue"
COMMENT_ON_ISSUE = "smarter.apps.mcpserver.github.issues.comment_on_issue"
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
        create_issue.assert_called_once_with(self.code_repository, "smarter apply fails", "It fails.", token)
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
            {"title": "t", "body": "b", "labels": ["bug"]},
        ]
        with mock.patch(CREATE_ISSUE) as create_issue:
            for arguments in cases:
                with self.subTest(arguments=list(arguments)):
                    with self.assertRaisesRegex(SmarterMCPServerToolError, "invalid arguments for create_issue"):
                        tool.call(arguments)
        create_issue.assert_not_called()

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
