"""
The tools that search, open and comment on the GitHub issues of The Smarter Project.

- ``search_issues``: the GitHub issues of the repositories, live. Anyone may call it.
- ``create_issue``: opens a GitHub issue in a repository, as the caller.
- ``comment_on_issue``: adds a comment to an existing issue, as the caller.

``create_issue`` and ``comment_on_issue`` are served only when the request carries the
caller's GitHub classic personal access token, and their results are never cached. See
:mod:`smarter.apps.mcpserver.github.issues`.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from typing import cast

from pydantic import Field

from smarter.apps.mcpserver.github import issues
from smarter.apps.mcpserver.github.issues import GitHubIssueHit, IssueState
from smarter.apps.mcpserver.protocol.tools import (
    DEFAULT_SEARCH_LIMIT,
    MAX_SEARCH_LIMIT,
    SmarterProjectTool,
    ToolArguments,
)
from smarter.apps.mcpserver.repositories import ProjectRepository

# -----------------------------------------------------------------------------
# search_issues
# -----------------------------------------------------------------------------
ISSUE_SEARCH_CACHE_TTL = 60
"""Seconds that search_issues caches a result: issues change by the minute."""


class SearchIssuesArguments(ToolArguments):
    """The arguments of search_issues."""

    query: str = Field(
        min_length=1,
        max_length=200,
        description="Keywords, e.g. guardrail apply error. GitHub's qualifiers, e.g. label:bug, are allowed.",
    )
    state: IssueState = Field(default="all", description="open, closed, or all.")
    limit: int = Field(
        default=DEFAULT_SEARCH_LIMIT, ge=1, le=MAX_SEARCH_LIMIT, description="The maximum number of issues."
    )


class SearchIssuesTool(SmarterProjectTool):
    """Search the repositories' GitHub issues, live."""

    name = "search_issues"
    title = "Search GitHub issues"
    description = (
        "Search the GitHub issues of The Smarter Project's repositories: known bugs, feature requests, "
        "and whether they are fixed. Returns the best matches, with their state, number of comments, "
        "and url. Use it when a user reports a problem, and always before create_issue, so that an issue "
        "is not opened twice: comment on an existing one instead."
    )
    arguments_model = SearchIssuesArguments
    open_world = True
    cache_ttl = ISSUE_SEARCH_CACHE_TTL

    def run(self, arguments: ToolArguments) -> str:
        arguments = cast(SearchIssuesArguments, arguments)
        repository = self.scope.resolve(arguments.repository, required=False)
        repositories = (repository,) if repository else self.scope.repositories
        hits = issues.search_issues(
            repositories,
            arguments.query,
            one=repository is not None,
            state=arguments.state,
            limit=arguments.limit,
            token=self.github_token,
        )
        where = repository.full_name if repository else "The Smarter Project's repositories"
        if not hits:
            return f'No issue of {where} matches "{arguments.query}". Try other keywords.'
        results = "\n\n".join(self.format_hit(number, hit) for number, hit in enumerate(hits, start=1))
        return f'{len(hits)} issues of {where}, for "{arguments.query}", best first.\n\n{results}'

    @staticmethod
    def format_hit(number: int, hit: GitHubIssueHit) -> str:
        """Return one issue, as Markdown."""
        heading = (
            f"{number}. **{hit.title}** {hit.repository}#{hit.number}, {hit.state}, "
            f"{hit.comments} comments, updated {hit.updated_at[:10]}\n   {hit.html_url}"
        )
        return f"{heading}\n   {hit.excerpt}" if hit.excerpt else heading


# -----------------------------------------------------------------------------
# create_issue
# -----------------------------------------------------------------------------
class CreateIssueArguments(ToolArguments):
    """The arguments of create_issue."""

    title: str = Field(
        min_length=1,
        max_length=issues.MAX_TITLE_LENGTH,
        description="The issue's title: one specific line, e.g. smarter apply fails on a Guardrail with no rules.",
    )
    body: str = Field(
        min_length=1,
        max_length=issues.MAX_BODY_LENGTH,
        description=(
            "The issue's body, in Markdown: what happened, what was expected, how to reproduce it, and the "
            "versions involved, or for a feature request, the problem that it solves."
        ),
    )


class CreateIssueTool(SmarterProjectTool):
    """Open a GitHub issue in a repository, as the caller."""

    name = "create_issue"
    title = "Create GitHub issue"
    description = (
        "Open a GitHub issue in a repository of The Smarter Project, under the user's own GitHub account, "
        "to report a bug or request a feature. It creates a public issue that maintainers are notified of: "
        "call it only when the user asks you to, after showing them the repository, title and body, and "
        "never more than once for the same issue. Search the code and documentation first, so that the "
        "issue is specific, choose the repository that owns the problem, and call search_issues first: "
        "if the issue already exists, use comment_on_issue instead."
    )
    arguments_model = CreateIssueArguments
    requires_repository = True
    read_only = False
    requires_github_token = True
    open_world = True

    def run(self, arguments: ToolArguments) -> str:
        arguments = cast(CreateIssueArguments, arguments)
        repository = cast(ProjectRepository, self.scope.resolve(arguments.repository, required=True))
        issue = issues.create_issue(repository, arguments.title.strip(), arguments.body.strip(), self.github_token)
        author = f" by {issue.author}" if issue.author else ""
        return f"Opened issue #{issue.number} in {repository.full_name}{author}: {issue.title}\n{issue.html_url}"


# -----------------------------------------------------------------------------
# comment_on_issue
# -----------------------------------------------------------------------------
class CommentOnIssueArguments(ToolArguments):
    """The arguments of comment_on_issue."""

    issue_number: int = Field(ge=1, description="The issue's number, from search_issues.")
    body: str = Field(
        min_length=1,
        max_length=issues.MAX_BODY_LENGTH,
        description=(
            "The comment, in Markdown: what it adds to the issue, e.g. another way to reproduce it, a "
            "version that is affected, or a workaround."
        ),
    )


class CommentOnIssueTool(SmarterProjectTool):
    """Add a comment to a GitHub issue, as the caller."""

    name = "comment_on_issue"
    title = "Comment on GitHub issue"
    description = (
        "Add a comment to an existing GitHub issue of a repository of The Smarter Project, under the user's "
        "own GitHub account, e.g. to confirm a bug that search_issues found, rather than open it again. "
        "It is public, and the issue's participants are notified: call it only when the user asks you to, "
        "after showing them the issue and the comment, and never more than once for the same comment."
    )
    arguments_model = CommentOnIssueArguments
    requires_repository = True
    read_only = False
    requires_github_token = True
    open_world = True

    def run(self, arguments: ToolArguments) -> str:
        arguments = cast(CommentOnIssueArguments, arguments)
        repository = cast(ProjectRepository, self.scope.resolve(arguments.repository, required=True))
        comment = issues.comment_on_issue(repository, arguments.issue_number, arguments.body.strip(), self.github_token)
        author = f" by {comment.author}" if comment.author else ""
        return f"Commented on {repository.full_name}#{arguments.issue_number}{author}.\n{comment.html_url}"


__all__ = ["CommentOnIssueTool", "CreateIssueTool", "SearchIssuesTool"]
