"""
The tools that search, open and comment on the GitHub issues of The Smarter Project.

- ``search_issues``: the GitHub issues of the repositories, live. Anyone may call it.
- ``read_issue``: one issue and its latest comments, live. Anyone may call it.
- ``create_issue``: opens a GitHub issue in a repository, as the caller, optionally with labels.
- ``comment_on_issue``: adds a comment to an existing issue, as the caller.
- ``close_issue``: closes an issue that a merged pull request resolved, with a comment, as the caller.
- ``create_pull_request``: commits a change to a new branch, and opens a pull request, as the caller.

Each tool class validates its arguments with a Pydantic model, calls GitHub through
:mod:`smarter.apps.mcpserver.github.issues` or :mod:`smarter.apps.mcpserver.github.pulls`, and
formats the answer as Markdown for the LLM. The GitHub work, the checks for credentials and the
explanations of GitHub's errors are in those modules: this one only turns arguments into a call,
and a result into text.

``search_issues`` and ``read_issue`` are read-only, and their results are cached for
:data:`ISSUE_SEARCH_CACHE_TTL` seconds. ``create_issue``, ``comment_on_issue``, ``close_issue``
and ``create_pull_request`` write to GitHub, as the caller: they are served only when the request
carries the caller's GitHub classic personal access token, and their results are never cached.

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
    GitHubIssueDetail,
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


def _by(author: Optional[str]) -> str:
    """
    Return the words that say who wrote something on GitHub, for a tool's result.

    :param author: The GitHub login of the token's owner, or None if GitHub did not say.
    :returns: e.g. `` by octocat``, with its leading space, or an empty string.
    """
    if not author:
        return ""
    return f" by {author}"


def _day(timestamp: str) -> str:
    """
    Return the date of an ISO 8601 timestamp, e.g. ``2026-11-02`` of ``2026-11-02T14:05:00Z``.

    :param timestamp: The timestamp, as GitHub gives it.
    :returns: Its first ten characters, the date.
    """
    return timestamp[:10]


# -----------------------------------------------------------------------------
# search_issues
# -----------------------------------------------------------------------------
ISSUE_SEARCH_CACHE_TTL = 60
"""Seconds that ``search_issues`` and ``read_issue`` cache a result: issues change by the minute."""


class SearchIssuesArguments(ToolArguments):
    """
    The arguments of ``search_issues``: the keywords, the state, and the most issues to return.

    The inherited ``repository`` argument narrows the search to one repository. Without it, the
    MCP server of all of the repositories searches them all.
    """

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
    """
    The ``search_issues`` tool: search the repositories' GitHub issues, live.

    **Reads:** GitHub's issue search (see :func:`~smarter.apps.mcpserver.github.issues.search_issues`),
    with the caller's GitHub token if it is a classic token, or anonymously.

    **Result:** Markdown: one numbered entry per issue, best match first, with its title,
    repository and number, state, number of comments, last update, url and an excerpt of its body.

    **Side effects:** one request to GitHub. The result is cached for
    :data:`ISSUE_SEARCH_CACHE_TTL` seconds, because issues are public, so the result does not
    depend on who asks.
    """

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
        """
        Search the issues of the repository that the call names, or of every repository of the scope.

        :param arguments: The validated :class:`SearchIssuesArguments`.
        :returns: The matching issues, as Markdown, or a sentence that says none matched.
        :raises SmarterMCPServerToolError: If the repository is unknown, or GitHub could not be
            reached or refused the search, e.g. its rate limit was reached.
        """
        arguments = cast(SearchIssuesArguments, arguments)
        repository = self.scope.resolve(arguments.repository, required=False)
        if repository:
            repositories = (repository,)
            where = repository.full_name
        else:
            repositories = self.scope.repositories
            where = "The Smarter Project's repositories"
        hits = issues.search_issues(
            repositories,
            arguments.query,
            one=repository is not None,
            state=arguments.state,
            limit=arguments.limit,
            token=self.github_token,
        )
        if not hits:
            return f'No issue of {where} matches "{arguments.query}". Try other keywords.'
        entries: list[str] = []
        for number, hit in enumerate(hits, start=1):
            entries.append(self.format_hit(number, hit))
        results = "\n\n".join(entries)
        return f'{len(hits)} issues of {where}, for "{arguments.query}", best first.\n\n{results}'

    @staticmethod
    def format_hit(number: int, hit: GitHubIssueHit) -> str:
        """
        Return one issue of the search result, as a numbered Markdown list item.

        :param number: The issue's position in the result, from 1.
        :param hit: The issue.
        :returns: Its title, repository and number, state, number of comments, last update and url,
            and, on a third line, the excerpt of its body, if it has one.
        """
        heading = (
            f"{number}. **{hit.title}** {hit.repository}#{hit.number}, {hit.state}, "
            f"{hit.comments} comments, updated {_day(hit.updated_at)}\n   {hit.html_url}"
        )
        if not hit.excerpt:
            return heading
        return f"{heading}\n   {hit.excerpt}"


# -----------------------------------------------------------------------------
# read_issue
# -----------------------------------------------------------------------------
THREAD_OVERHEAD = 200
"""Characters of ``read_issue``'s result kept back for the notice of left-out comments and the separators."""


class ReadIssueArguments(ToolArguments):
    """
    The arguments of ``read_issue``: the repository, which it requires, and the issue's number.

    A pull request's number is accepted too, because GitHub numbers issues and pull requests
    together.
    """

    issue_number: int = Field(ge=1, description="The issue's number, from search_issues.")


class ReadIssueTool(SmarterProjectTool):
    """
    The ``read_issue`` tool: read a GitHub issue and its latest comments, live.

    **Reads:** the issue and the last page of its comments, from GitHub (see
    :func:`~smarter.apps.mcpserver.github.issues.read_issue`), with the caller's GitHub token if
    it is a classic token, or anonymously.

    **Result:** Markdown: a heading with the issue's state, author, dates and labels, its body,
    and its latest comments, oldest first, within :data:`MAX_READ_CHARACTERS`.

    **Side effects:** one or two requests to GitHub. The result is cached for
    :data:`ISSUE_SEARCH_CACHE_TTL` seconds.
    """

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
        """
        Read the issue that the call names, with its latest comments.

        :param arguments: The validated :class:`ReadIssueArguments`.
        :returns: The issue and its comments, as Markdown (see :meth:`format_thread`).
        :raises SmarterMCPServerToolError: If the repository is unknown, the issue was not found,
            or GitHub could not be reached, or refused the request.
        """
        arguments = cast(ReadIssueArguments, arguments)
        repository = cast(ProjectRepository, self.scope.resolve(arguments.repository, required=True))
        thread = issues.read_issue(repository, arguments.issue_number, self.github_token)
        return self.format_thread(repository, thread)

    @staticmethod
    def format_comment(comment: GitHubIssueComment) -> str:
        """
        Return one comment, as Markdown: a heading with its author and date, then its text.

        :param comment: The comment.
        :returns: The comment, e.g. ``### octocat, 2026-11-02`` and its body. A comment whose
            author's account was deleted is by ``unknown``.
        """
        author = "unknown"
        if comment.user:
            author = comment.user.login
        body = comment.body or ""
        text = body.strip()
        return f"### {author}, {_day(comment.created_at)}\n\n{text}"

    @staticmethod
    def _state(issue: GitHubIssueDetail) -> str:
        """
        Describe an issue's state, e.g. ``closed (completed)``, or ``open, not merged`` for a pull request.

        :param issue: The issue, or pull request.
        :returns: Its state, why it was closed if GitHub says, and, for a pull request, whether and
            when it was merged.
        """
        state = issue.state
        if issue.state_reason:
            state += f" ({issue.state_reason})"
        if isinstance(issue.pull_request, dict):
            merged_at = issue.pull_request.get("merged_at")
            if merged_at:
                state += f", merged {_day(str(merged_at))}"
            else:
                state += ", not merged"
        return state

    @classmethod
    def _heading(cls, repository: ProjectRepository, issue: GitHubIssueDetail) -> str:
        """
        Return the heading of ``read_issue``'s result: what the issue is, its url, and its facts.

        :param repository: The issue's repository.
        :param issue: The issue, or pull request.
        :returns: A Markdown title, the url, and a line with the state, author, dates, labels and
            number of comments.
        """
        kind = "Issue"
        if issue.pull_request is not None:
            kind = "Pull request"
        state = cls._state(issue)
        closed = ""
        if issue.closed_at:
            closed = f", closed {_day(issue.closed_at)}"
        label_names = [label.name for label in issue.labels]
        labels = ", ".join(label_names)
        if not labels:
            labels = "none"
        author = "unknown"
        if issue.user:
            author = issue.user.login
        heading = (
            f"# {kind} {repository.full_name}#{issue.number}: {issue.title}\n\n"
            f"{issue.html_url}\n{state}, opened by {author} {_day(issue.created_at)}{closed}, "
            f"updated {_day(issue.updated_at)}, labels: {labels}, {issue.comments} comments"
        )
        return heading

    @classmethod
    def format_thread(cls, repository: ProjectRepository, thread: GitHubIssueThread) -> str:
        """
        Return the issue and its comments, as Markdown, within :data:`MAX_READ_CHARACTERS`.

        When the result is too long, the issue's body is shortened first, to at most half of what
        is left after the heading, and then the oldest comments are left out, because the latest
        say what is known now. A notice says how many earlier comments are not shown, counting
        those that GitHub was not asked for.

        :param repository: The issue's repository.
        :param thread: The issue and its latest comments.
        :returns: The heading, the body, the notice of left-out comments, if any, and the comments
            that fit, oldest first, separated by blank lines.
        """
        issue = thread.issue
        heading = cls._heading(repository, issue)
        body = issue.body or ""
        body = body.strip()
        comments = [cls.format_comment(comment) for comment in thread.comments]
        # the comments that GitHub was not asked for, i.e. those before the last page.
        omitted = issue.comments - len(comments)

        budget = MAX_READ_CHARACTERS - len(heading) - THREAD_OVERHEAD
        body_budget = budget // 2
        if len(body) > body_budget:
            body = body[:body_budget] + "\n\n[... the rest of the body is left out]"
        budget -= len(body)

        # keep the latest comments that fit, each with its blank-line separator.
        kept: list[str] = []
        for comment in reversed(comments):
            size = len(comment) + 2
            if size > budget:
                break
            kept.insert(0, comment)
            budget -= size
        omitted += len(comments) - len(kept)

        parts = [heading]
        if body:
            parts.append(body)
        else:
            parts.append("(no description)")
        if omitted:
            parts.append(f"[{omitted} earlier comments are left out]")
        parts.extend(kept)
        result = "\n\n".join(parts)
        return result


# -----------------------------------------------------------------------------
# create_issue
# -----------------------------------------------------------------------------
MAX_LABELS = 10
"""The most labels that ``create_issue`` accepts for one issue."""

MAX_LABEL_LENGTH = 50
"""The longest label, in characters, that ``create_issue`` accepts, which is GitHub's limit."""


class CreateIssueArguments(ToolArguments):
    """
    The arguments of ``create_issue``: the repository, which it requires, the title, the body and the labels.

    The lengths are checked here, before anything is sent to GitHub. Credentials are refused later,
    by :func:`~smarter.apps.mcpserver.github.client.refuse_secrets`.
    """

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
    """
    The ``create_issue`` tool: open a GitHub issue in a repository, as the caller.

    **Writes:** a public issue, with the caller's own GitHub token (see
    :func:`~smarter.apps.mcpserver.github.issues.create_issue`), which notifies the repository's
    watchers.

    **Result:** a sentence with the new issue's number, repository, author and title, and its url.

    **Side effects:** one request to GitHub that creates the issue. The tool is served only to a
    request that carries the caller's GitHub token, and its result is never cached: every call
    writes. Its description tells the LLM to search first, and to call it only when the user asks.
    """

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
        """
        Open the issue that the call describes.

        Labels are stripped of surrounding whitespace, and blank ones are dropped.

        :param arguments: The validated :class:`CreateIssueArguments`.
        :returns: The new issue's number, repository, author, title and url.
        :raises SmarterMCPServerToolError: If the repository is unknown, a label is longer than
            :data:`MAX_LABEL_LENGTH`, the token is not a classic personal access token, the text
            holds a credential, or GitHub could not be reached, or did not create the issue.
        """
        arguments = cast(CreateIssueArguments, arguments)
        repository = cast(ProjectRepository, self.scope.resolve(arguments.repository, required=True))
        label_list: list[str] = []
        for label in arguments.labels:
            name = label.strip()
            if name:
                label_list.append(name)
        labels = tuple(label_list)
        too_long = [label for label in labels if len(label) > MAX_LABEL_LENGTH]
        if too_long:
            first = too_long[0]
            raise SmarterMCPServerToolError(f"A label is at most {MAX_LABEL_LENGTH} characters: {first[:60]}")
        title = arguments.title.strip()
        body = arguments.body.strip()
        issue = issues.create_issue(repository, title, body, self.github_token, labels=labels)
        author = _by(issue.author)
        return f"Opened issue #{issue.number} in {repository.full_name}{author}: {issue.title}\n{issue.html_url}"


# -----------------------------------------------------------------------------
# comment_on_issue
# -----------------------------------------------------------------------------
class CommentOnIssueArguments(ToolArguments):
    """The arguments of ``comment_on_issue``: the repository, which it requires, the issue's number and the comment."""

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
    """
    The ``comment_on_issue`` tool: add a comment to a GitHub issue, as the caller.

    **Writes:** a public comment, with the caller's own GitHub token (see
    :func:`~smarter.apps.mcpserver.github.issues.comment_on_issue`), which notifies the issue's
    participants.

    **Result:** a sentence with the issue, the author, and the comment's url.

    **Side effects:** one request to GitHub that creates the comment. The tool is served only to
    a request that carries the caller's GitHub token, and its result is never cached: every call
    writes.
    """

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
        """
        Add the comment that the call gives to the issue that it names.

        :param arguments: The validated :class:`CommentOnIssueArguments`.
        :returns: The issue, the author, and the new comment's url.
        :raises SmarterMCPServerToolError: If the repository is unknown, the token is not a classic
            personal access token, the comment holds a credential, or GitHub could not be reached,
            or did not create the comment, e.g. the issue is locked.
        """
        arguments = cast(CommentOnIssueArguments, arguments)
        repository = cast(ProjectRepository, self.scope.resolve(arguments.repository, required=True))
        body = arguments.body.strip()
        comment = issues.comment_on_issue(repository, arguments.issue_number, body, self.github_token)
        author = _by(comment.author)
        return f"Commented on {repository.full_name}#{arguments.issue_number}{author}.\n{comment.html_url}"


# -----------------------------------------------------------------------------
# close_issue
# -----------------------------------------------------------------------------
class CloseIssueArguments(ToolArguments):
    """
    The arguments of ``close_issue``: the repository, which it requires, the issue, the merged pull request and the comment.

    The pull request must be in the same repository as the issue.
    """

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
    """
    The ``close_issue`` tool: close an issue that a merged pull request resolved, as the caller.

    **Reads:** the pull request, from GitHub, to confirm that it was merged.

    **Writes:** a public comment that says why the issue is resolved, then the issue's state,
    closed as ``completed``, with the caller's own GitHub token (see
    :func:`~smarter.apps.mcpserver.github.issues.close_issue`). Both notify the issue's
    participants.

    **Result:** a sentence with the issue, the author and the pull request, the issue's url, and
    the comment's url.

    **Side effects:** three requests to GitHub. The tool is served only to a request that carries
    the caller's GitHub token, and its result is never cached: every call writes.
    """

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
        """
        Close the issue that the call names, if its pull request was merged, with the comment.

        :param arguments: The validated :class:`CloseIssueArguments`.
        :returns: The closed issue, the author, the pull request, and the urls of the issue and
            the comment.
        :raises SmarterMCPServerToolError: If the repository is unknown, the token is not a classic
            personal access token, the comment holds a credential, the pull request was not found
            or not merged, or GitHub could not be reached, or refused the comment or the closing.
        """
        arguments = cast(CloseIssueArguments, arguments)
        repository = cast(ProjectRepository, self.scope.resolve(arguments.repository, required=True))
        comment = arguments.comment.strip()
        closed = issues.close_issue(
            repository,
            arguments.issue_number,
            arguments.pull_request_number,
            comment,
            self.github_token,
        )
        author = _by(closed.author)
        return (
            f"Closed {repository.full_name}#{closed.number}{author}, resolved by "
            f"#{arguments.pull_request_number}.\n{closed.html_url}\nComment: {closed.comment_url}"
        )


# -----------------------------------------------------------------------------
# create_pull_request
# -----------------------------------------------------------------------------
class CreatePullRequestArguments(ToolArguments):
    """
    The arguments of ``create_pull_request``: the repository, which it requires, the branches, the text, the files, the author and whether it is a draft.

    The lengths are checked here. The branch names and the files' paths are checked by
    :func:`~smarter.apps.mcpserver.github.pulls.validate_branch` and
    :func:`~smarter.apps.mcpserver.github.pulls.validate_files`, and credentials are refused by
    :func:`~smarter.apps.mcpserver.github.client.refuse_secrets`, before anything is sent to GitHub.
    """

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
    """
    The ``create_pull_request`` tool: commit a change to a new branch, and open a pull request, as the caller.

    **Reads:** the base branch, its commit, and the folders of the changed files, from GitHub.

    **Writes:** a tree, a commit, a new branch and a public pull request, with the caller's own
    GitHub token (see :func:`~smarter.apps.mcpserver.github.pulls.create_pull_request`). It never
    changes an existing branch, nor a file under ``.github/``.

    **Result:** a sentence with the new pull request's number, repository, author and title, its
    url, its branches, and its commit.

    **Side effects:** several requests to GitHub. The tool is served only to a request that
    carries the caller's GitHub token, and its result is never cached: every call writes.
    """

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
        """
        Open the pull request that the call describes.

        The branch names and the text are stripped of surrounding whitespace. A blank ``base``
        means the repository's default branch.

        :param arguments: The validated :class:`CreatePullRequestArguments`.
        :returns: The new pull request's number, repository, author, title, url, branches and
            commit.
        :raises SmarterMCPServerToolError: If the repository is unknown, the token is not a classic
            personal access token, a branch name or a file is not valid, the change holds a
            credential, or GitHub could not be reached, or refused a step, e.g. because the branch
            exists.
        """
        arguments = cast(CreatePullRequestArguments, arguments)
        repository = cast(ProjectRepository, self.scope.resolve(arguments.repository, required=True))
        base = None
        if arguments.base:
            stripped_base = arguments.base.strip()
            if stripped_base:
                base = stripped_base
        pull_request = pulls.create_pull_request(
            repository,
            branch=arguments.branch.strip(),
            title=arguments.title.strip(),
            body=arguments.body.strip(),
            commit_message=arguments.commit_message.strip(),
            files=arguments.files,
            token=self.github_token,
            base=base,
            author=arguments.author,
            draft=arguments.draft,
        )
        author = _by(pull_request.author)
        draft = ""
        if pull_request.draft:
            draft = " draft"
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
