"""
The tools that search, open and comment on the GitHub issues of The Smarter Project.

- ``search_issues``: the GitHub issues of the repositories, live. Anyone may call it.
- ``read_issue``: one issue and its latest comments, live. Anyone may call it.
- ``create_issue``: opens a GitHub issue in a repository, as the caller, optionally with labels.
- ``comment_on_issue``: adds a comment to an existing issue, as the caller.
- ``close_issue``: closes an issue that a merged pull request resolved, with a comment, as the caller.
- ``create_pull_request``: commits a change to a new branch, and opens a pull request, as the caller.

``create_issue``, ``comment_on_issue``, ``close_issue`` and ``create_pull_request`` are served only when the
request carries the caller's GitHub classic personal access token, and their results are never
cached. See :mod:`smarter.apps.mcpserver.github.issues` and :mod:`smarter.apps.mcpserver.github.pulls`.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from typing import Optional, cast

from pydantic import Field

from smarter.apps.mcpserver.exceptions import SmarterMCPServerToolError
from smarter.apps.mcpserver.github import issues, pulls
from smarter.apps.mcpserver.github.issues import (
    GitHubIssueComment,
    GitHubIssueHit,
    GitHubIssueThread,
    IssueState,
)
from smarter.apps.mcpserver.github.pulls import GitHubCommitAuthor, PullRequestFile
from smarter.apps.mcpserver.protocol.tools import (
    DEFAULT_SEARCH_LIMIT,
    MAX_READ_CHARACTERS,
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
# read_issue
# -----------------------------------------------------------------------------
class ReadIssueArguments(ToolArguments):
    """The arguments of read_issue."""

    issue_number: int = Field(ge=1, description="The issue's number, from search_issues.")


class ReadIssueTool(SmarterProjectTool):
    """Read a GitHub issue and its latest comments, live."""

    name = "read_issue"
    title = "Read GitHub issue"
    description = (
        "Read one GitHub issue of a repository of The Smarter Project: its state, labels and body, and its "
        "latest comments, oldest first. Call it before comment_on_issue, so that a comment adds what the "
        "issue does not already say, and to see whether a closed issue was fixed or declined."
    )
    arguments_model = ReadIssueArguments
    requires_repository = True
    open_world = True
    cache_ttl = ISSUE_SEARCH_CACHE_TTL

    def run(self, arguments: ToolArguments) -> str:
        arguments = cast(ReadIssueArguments, arguments)
        repository = cast(ProjectRepository, self.scope.resolve(arguments.repository, required=True))
        thread = issues.read_issue(repository, arguments.issue_number, self.github_token)
        return self.format_thread(repository, thread)

    @staticmethod
    def format_comment(comment: GitHubIssueComment) -> str:
        """Return one comment, as Markdown."""
        author = comment.user.login if comment.user else "unknown"
        return f"### {author}, {comment.created_at[:10]}\n\n{(comment.body or '').strip()}"

    @classmethod
    def format_thread(cls, repository: ProjectRepository, thread: GitHubIssueThread) -> str:
        """
        Return the issue and its comments, as Markdown, within :data:`MAX_READ_CHARACTERS`.

        When the result is too long, the issue's body is shortened first, and then the oldest
        comments are left out, because the latest say what is known now.
        """
        issue = thread.issue
        kind = "Pull request" if issue.pull_request is not None else "Issue"
        state = issue.state + (f" ({issue.state_reason})" if issue.state_reason else "")
        if isinstance(issue.pull_request, dict):
            merged_at = issue.pull_request.get("merged_at")
            state += f", merged {str(merged_at)[:10]}" if merged_at else ", not merged"
        closed = f", closed {issue.closed_at[:10]}" if issue.closed_at else ""
        labels = ", ".join(label.name for label in issue.labels) or "none"
        author = issue.user.login if issue.user else "unknown"
        heading = (
            f"# {kind} {repository.full_name}#{issue.number}: {issue.title}\n\n"
            f"{issue.html_url}\n{state}, opened by {author} {issue.created_at[:10]}{closed}, "
            f"updated {issue.updated_at[:10]}, labels: {labels}, {issue.comments} comments"
        )
        body = (issue.body or "").strip()
        comments = [cls.format_comment(comment) for comment in thread.comments]
        omitted = issue.comments - len(comments)
        budget = MAX_READ_CHARACTERS - len(heading) - 200
        body = body if len(body) <= budget // 2 else body[: budget // 2] + "\n\n[... the rest of the body is left out]"
        budget -= len(body)
        kept: list[str] = []
        for comment in reversed(comments):
            if len(comment) + 2 > budget:
                break
            kept.insert(0, comment)
            budget -= len(comment) + 2
        omitted += len(comments) - len(kept)
        parts = [heading, body or "(no description)"]
        if omitted:
            parts.append(f"[{omitted} earlier comments are left out]")
        parts.extend(kept)
        return "\n\n".join(parts)


# -----------------------------------------------------------------------------
# create_issue
# -----------------------------------------------------------------------------
MAX_LABELS = 10
MAX_LABEL_LENGTH = 50


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
    labels: list[str] = Field(
        default_factory=list,
        max_length=MAX_LABELS,
        description=(
            "Labels, e.g. bug or severity: high. Use the repository's existing labels where they fit. GitHub "
            "drops them if the user cannot push to the repository."
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
        labels = tuple(label.strip() for label in arguments.labels if label.strip())
        too_long = [label for label in labels if len(label) > MAX_LABEL_LENGTH]
        if too_long:
            raise SmarterMCPServerToolError(f"A label is at most {MAX_LABEL_LENGTH} characters: {too_long[0][:60]}")
        issue = issues.create_issue(
            repository, arguments.title.strip(), arguments.body.strip(), self.github_token, labels=labels
        )
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
        "Read the issue with read_issue first, and comment only to add what it does not already say. "
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


# -----------------------------------------------------------------------------
# close_issue
# -----------------------------------------------------------------------------
class CloseIssueArguments(ToolArguments):
    """The arguments of close_issue."""

    issue_number: int = Field(ge=1, description="The number of the issue to close.")
    pull_request_number: int = Field(
        ge=1, description="The number of the merged pull request, in the same repository, that resolved the issue."
    )
    comment: str = Field(
        min_length=1,
        max_length=issues.MAX_BODY_LENGTH,
        description=(
            "Why the issue is resolved, in Markdown: the pull request, what it changed, and the evidence that "
            "the problem is gone, e.g. the release that contains it."
        ),
    )


class CloseIssueTool(SmarterProjectTool):
    """Close an issue that a merged pull request resolved, as the caller."""

    name = "close_issue"
    title = "Close GitHub issue"
    description = (
        "Close an open GitHub issue of a repository of The Smarter Project, under the user's own GitHub "
        "account, when a merged pull request resolved it. It adds the comment, which says why, and closes the "
        "issue as completed, only if GitHub confirms that the pull request was merged. Read the issue and the "
        "pull request with read_issue first, and close the issue only if the pull request fixes exactly what "
        "the issue reports. It is public, and the issue's participants are notified: call it only when the "
        "user asks you to."
    )
    arguments_model = CloseIssueArguments
    requires_repository = True
    read_only = False
    requires_github_token = True
    open_world = True

    def run(self, arguments: ToolArguments) -> str:
        arguments = cast(CloseIssueArguments, arguments)
        repository = cast(ProjectRepository, self.scope.resolve(arguments.repository, required=True))
        closed = issues.close_issue(
            repository,
            arguments.issue_number,
            arguments.pull_request_number,
            arguments.comment.strip(),
            self.github_token,
        )
        author = f" by {closed.author}" if closed.author else ""
        return (
            f"Closed {repository.full_name}#{closed.number}{author}, resolved by "
            f"#{arguments.pull_request_number}.\n{closed.html_url}\nComment: {closed.comment_url}"
        )


# -----------------------------------------------------------------------------
# create_pull_request
# -----------------------------------------------------------------------------
class CreatePullRequestArguments(ToolArguments):
    """The arguments of create_pull_request."""

    branch: str = Field(
        min_length=1,
        max_length=pulls.MAX_BRANCH_LENGTH,
        description="The new branch, which must not exist, e.g. claude/fix-plugin-timeout.",
    )
    base: Optional[str] = Field(
        default=None,
        max_length=pulls.MAX_BRANCH_LENGTH,
        description="The branch to merge into, and to branch from. Omit it for the repository's default branch.",
    )
    title: str = Field(
        min_length=1, max_length=issues.MAX_TITLE_LENGTH, description="The pull request's title: one specific line."
    )
    body: str = Field(
        min_length=1,
        max_length=issues.MAX_BODY_LENGTH,
        description=(
            "The pull request's description, in Markdown: the problem, the cause, the change, how it was "
            "verified, and the issue that it fixes, e.g. Fixes #42."
        ),
    )
    commit_message: str = Field(
        min_length=1,
        max_length=pulls.MAX_COMMIT_MESSAGE_LENGTH,
        description="The commit's message: a conventional-commit subject line, a blank line, and a body.",
    )
    files: list[PullRequestFile] = Field(
        min_length=1,
        max_length=pulls.MAX_FILES,
        description=(
            "The changed files. Each is {path, content}, with the file's whole new content, not a diff, or "
            "{path, delete: true}. Read each file first, and change only what the fix needs."
        ),
    )
    author: Optional[GitHubCommitAuthor] = Field(
        default=None,
        description="The commit's author and committer, {name, email}. Omit it for the owner of the GitHub token.",
    )
    draft: bool = Field(default=False, description="Whether to open it as a draft.")


class CreatePullRequestTool(SmarterProjectTool):
    """Commit a change to a new branch, and open a pull request, as the caller."""

    name = "create_pull_request"
    title = "Create GitHub pull request"
    description = (
        "Propose a change to a repository of The Smarter Project, under the user's own GitHub account: one "
        "commit, with each changed file's whole new content, on a new branch from base, and a pull request "
        "from it. It never changes an existing branch, nor files under .github/. It is public, and maintainers "
        "are notified: call it only when the user asks you to, after showing them the files, title and "
        "description, and never twice for the same change. Read every file that you change with read_file "
        "first, from the base branch, and keep the change as small as the fix."
    )
    arguments_model = CreatePullRequestArguments
    requires_repository = True
    read_only = False
    requires_github_token = True
    open_world = True

    def run(self, arguments: ToolArguments) -> str:
        arguments = cast(CreatePullRequestArguments, arguments)
        repository = cast(ProjectRepository, self.scope.resolve(arguments.repository, required=True))
        pull_request = pulls.create_pull_request(
            repository,
            branch=arguments.branch.strip(),
            title=arguments.title.strip(),
            body=arguments.body.strip(),
            commit_message=arguments.commit_message.strip(),
            files=arguments.files,
            token=self.github_token,
            base=arguments.base.strip() if arguments.base and arguments.base.strip() else None,
            author=arguments.author,
            draft=arguments.draft,
        )
        author = f" by {pull_request.author}" if pull_request.author else ""
        draft = " draft" if pull_request.draft else ""
        return (
            f"Opened{draft} pull request #{pull_request.number} in {repository.full_name}{author}: "
            f"{pull_request.title}\n{pull_request.html_url}\n"
            f"{pull_request.branch} into {pull_request.base}, commit {pull_request.commit_sha[:12]}"
        )


__all__ = [
    "CloseIssueTool",
    "CommentOnIssueTool",
    "CreateIssueTool",
    "CreatePullRequestTool",
    "ReadIssueTool",
    "SearchIssuesTool",
]
