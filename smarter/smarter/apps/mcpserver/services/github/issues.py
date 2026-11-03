"""
GitHub issues of The Smarter Project's repositories: searched, opened and commented on.

- :func:`search_issues` asks GitHub's issue search, ``GET /search/issues``, live, rather than
  the index: issues change by the minute, and an LLM that is about to open an issue must see
  one that was opened a minute ago. It searches one repository with ``repo:``, or all of them
  with ``org:``, and drops the results of the organization's other repositories. Issues are
  public, so the result does not depend on who asks. Without the caller's classic token the
  search is anonymous, and GitHub allows anonymous clients 10 searches a minute for each IP
  address, which the platform's users share. A token raises that to 30 for its owner.
- :func:`read_issue` reads an issue and its latest comments, with ``GET /repos/{owner}/{repo}/issues/{number}``
  and its ``/comments``, so that an LLM can see what an issue already says before it adds to it.
- :func:`create_issue` opens an issue, optionally with labels, with ``POST /repos/{owner}/{repo}/issues``.
- :func:`close_issue` closes an issue that a merged pull request resolved, with a comment that says
  why, after GitHub confirms that the pull request was merged.
- :func:`comment_on_issue` adds a comment to an existing issue, with
  ``POST /repos/{owner}/{repo}/issues/{number}/comments``.

:func:`create_issue`, :func:`comment_on_issue` and :func:`close_issue` write as the caller, with
the caller's own classic personal access token, so the issue or comment is the caller's, and
GitHub decides what the caller may do. Each appends a footer that says where the text came from.
Never cache them: every call writes. None of them writes a credential: see
:func:`~smarter.apps.mcpserver.services.github.client.refuse_secrets`. See
:mod:`smarter.apps.mcpserver.services.github.client` for how the token is checked and kept secret, and how
GitHub's errors are explained.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from typing import Literal, Optional

import requests
from pydantic import BaseModel, ConfigDict, Field, JsonValue, SecretStr, ValidationError

from smarter.apps.mcpserver.exceptions import SmarterMCPServerServiceError
from smarter.apps.mcpserver.services.repositories import (
    GITHUB_API_URL,
    ProjectRepository,
)
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.typing import SmarterDictType

from .client import (
    author_login,
    explain_failure,
    github_request,
    optional_token,
    refuse_secrets,
    validate_token,
)

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.MCPSERVER_LOGGING])
logger_prefix = logging.SmarterFormattedText.text(__name__)


IssueState = Literal["open", "closed", "all"]
"""Which issues a search asks for: ``open``, ``closed``, or ``all``, which leaves the state out of the query."""

MAX_EXCERPT_LENGTH = 300
"""The most characters of each issue's body that ``search_issues`` reports, as its excerpt."""


def _issue_not_found(repository: ProjectRepository, number: int) -> str:
    """
    Explain, for the LLM, that an issue number does not exist in a repository.

    :func:`read_issue` and :func:`comment_on_issue` pass it to
    :func:`~smarter.apps.mcpserver.services.github.client.explain_failure` as the meaning of a 404.

    :param repository: The repository.
    :param number: The issue's number.
    :returns: The explanation, which suggests finding the issue with ``search_issues``.
    """
    return f"Issue #{number} was not found in {repository.full_name}. Find it with search_issues."


class GitHubIssueHit(BaseModel):
    """
    One issue that GitHub's search found, with the fields that the ``search_issues`` tool reports.

    :func:`search_issues` builds it from an item of GitHub's ``GET /search/issues`` response.
    GitHub's response has many more fields, which are ignored. It is frozen, because it is a
    snapshot of GitHub's answer.
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    number: int = Field(description="The issue's number in its repository.")
    title: str = Field(description="The issue's title.")
    state: str = Field(description="open or closed.")
    html_url: str = Field(description="The issue's url on github.com.")
    repository_url: str = Field(description="The api url of the issue's repository.")
    comments: int = Field(default=0, description="The number of comments.")
    updated_at: str = Field(default="", description="When the issue last changed, in ISO 8601.")
    body: Optional[str] = Field(default=None, description="The issue's body, in Markdown.")

    @property
    def repository(self) -> str:
        """
        The full name of the issue's repository, e.g. ``smarter-sh/smarter``.

        GitHub's search result names the repository only by its api url, e.g.
        ``https://api.github.com/repos/smarter-sh/smarter``, so the name is that url without its prefix.
        """
        prefix = f"{GITHUB_API_URL}/repos/"
        return self.repository_url.removeprefix(prefix)

    @property
    def excerpt(self) -> str:
        """
        The start of the issue's body, on one line, at most :data:`MAX_EXCERPT_LENGTH` characters.

        Runs of whitespace, including line breaks, become one space, so that the excerpt fits on one
        line of the tool's result. A longer body is cut, and ends with ``...``. An issue without a
        body has an empty excerpt.
        """
        body = self.body or ""
        words = body.split()
        text = " ".join(words)
        if len(text) <= MAX_EXCERPT_LENGTH:
            return text
        shortened = text[: MAX_EXCERPT_LENGTH - 3]
        return shortened + "..."


class GitHubIssueSearchResult(BaseModel):
    """
    GitHub's answer to an issue search, with the fields that :func:`search_issues` reads.

    It is the whole ``GET /search/issues`` response. GitHub's response has more fields, e.g.
    ``incomplete_results``, which are ignored.
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    total_count: int = 0
    """How many issues match the query in all, which may be more than the page returned."""

    items: list[GitHubIssueHit] = Field(default_factory=list)
    """The issues of the page, best match first."""


def search_query(query: str, repositories: tuple[ProjectRepository, ...], one: bool, state: IssueState) -> str:
    """
    Return GitHub's search query: the keywords, issues only, the repositories and the state.

    One repository is searched with ``repo:owner/name``. Several are searched with
    ``org:owner``, because GitHub's search allows only a few ``repo:`` qualifiers in one query,
    and :func:`search_issues` then drops the results of the organization's other repositories.
    ``is:issue`` leaves pull requests out.

    :param query: The keywords.
    :param repositories: The repositories to search.
    :param one: Whether to search only the first repository, with ``repo:``, rather than the organization.
    :param state: ``open``, ``closed`` or ``all``.
    :returns: The query, e.g. ``guardrail apply is:issue repo:smarter-sh/smarter state:open``.
    """
    first = repositories[0]
    if one:
        where = f"repo:{first.full_name}"
    else:
        where = f"org:{first.owner}"
    keywords = query.strip()
    parts = [keywords, "is:issue", where]
    if state != "all":
        parts.append(f"state:{state}")
    return " ".join(parts)


def search_issues(
    repositories: tuple[ProjectRepository, ...],
    query: str,
    one: bool,
    state: IssueState,
    limit: int,
    token: Optional[SecretStr],
) -> list[GitHubIssueHit]:
    """
    Search the issues of the repositories, best match first.

    GitHub's issue search is asked live, rather than an index, because issues change by the
    minute (see the module's docstring). Side effects: one ``GET /search/issues`` request to
    GitHub, which counts against the caller's, or the platform's anonymous, search rate limit.
    A failure is logged.

    :param repositories: The repositories to search. They have the same owner.
    :param query: The keywords.
    :param one: Whether to search only the first repository, rather than all of them.
    :param state: ``open``, ``closed`` or ``all``.
    :param limit: The maximum number of issues.
    :param token: The caller's GitHub token, or None. Only a classic personal access token is
        sent: otherwise the search is anonymous.
    :returns: The issues of the repositories.
    :raises SmarterMCPServerServiceError: If GitHub could not be reached, or refused the search,
        e.g. its rate limit was reached.
    """
    value = optional_token(token)
    names = {repository.full_name for repository in repositories}
    if one:
        per_page = limit
    else:
        # the organization's other repositories are dropped, so ask for more than the limit.
        per_page = min(100, limit * 3)
    params = {
        "q": search_query(query, repositories, one, state),
        "per_page": str(per_page),
    }
    response = github_request("GET", "/search/issues", value, params=params)
    if response.status_code != 200:
        logger.info("%s.search_issues() GitHub did not search: HTTP %s", logger_prefix, response.status_code)
        raise SmarterMCPServerServiceError(explain_failure(response, repositories[0], "search the issues"))
    try:
        result = GitHubIssueSearchResult.model_validate(response.json())
    except (ValueError, ValidationError) as e:
        logger.warning("%s.search_issues() GitHub's response is not a search result: %s", logger_prefix, e)
        raise SmarterMCPServerServiceError("GitHub's search result could not be read. Try again later.") from e
    hits = [hit for hit in result.items if hit.repository in names]
    return hits[:limit]


COMMENTS_PER_PAGE = 100
"""The most comments that GitHub returns in one page, and that :func:`read_issue` reads."""


class GitHubUser(BaseModel):
    """
    A GitHub account, with the field that the tools report.

    GitHub nests it in an issue or a comment as its ``user``, the account that wrote it.
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    login: str = Field(description="The account's login.")


class GitHubLabel(BaseModel):
    """
    A label of an issue, with the field that the tools report.

    ``read_issue`` lists an issue's labels by name, e.g. ``bug``.
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    name: str = Field(description="The label's name.")


class GitHubIssueComment(BaseModel):
    """
    A comment on an issue, with the fields that ``read_issue`` reports.

    :func:`read_issue` builds it from an item of GitHub's
    ``GET /repos/{owner}/{repo}/issues/{number}/comments`` response. GitHub's response has many
    more fields, which are ignored.
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    user: Optional[GitHubUser] = Field(default=None, description="The comment's author.")
    created_at: str = Field(default="", description="When the comment was written, in ISO 8601.")
    html_url: str = Field(default="", description="The comment's url on github.com.")
    body: Optional[str] = Field(default=None, description="The comment, in Markdown.")


class GitHubIssueDetail(BaseModel):
    """
    One issue, as ``GET /repos/{owner}/{repo}/issues/{number}`` returns it, with the fields that ``read_issue`` reports.

    GitHub's response has many more fields, which are ignored. GitHub returns a pull request
    from this endpoint too, with a ``pull_request`` field, so ``read_issue`` can also read a pull
    request's description and conversation, e.g. before ``close_issue``.
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    number: int = Field(description="The issue's number in its repository.")
    title: str = Field(description="The issue's title.")
    state: str = Field(description="open or closed.")
    state_reason: Optional[str] = Field(default=None, description="Why it was closed, e.g. completed or not_planned.")
    html_url: str = Field(description="The issue's url on github.com.")
    user: Optional[GitHubUser] = Field(default=None, description="Who opened the issue.")
    labels: list[GitHubLabel] = Field(default_factory=list, description="The issue's labels.")
    comments: int = Field(default=0, description="The number of comments.")
    created_at: str = Field(default="", description="When the issue was opened, in ISO 8601.")
    updated_at: str = Field(default="", description="When the issue last changed, in ISO 8601.")
    closed_at: Optional[str] = Field(default=None, description="When the issue was closed, in ISO 8601.")
    body: Optional[str] = Field(default=None, description="The issue's body, in Markdown.")
    pull_request: Optional[JsonValue] = Field(default=None, description="Present if it is a pull request.")


class GitHubIssueThread(BaseModel):
    """
    An issue and its latest comments, oldest first, as :func:`read_issue` returns them.

    The ``read_issue`` tool formats it as Markdown.
    """

    model_config = ConfigDict(frozen=True)

    issue: GitHubIssueDetail
    """The issue."""

    comments: list[GitHubIssueComment] = Field(default_factory=list)
    """The issue's latest comments, at most :data:`COMMENTS_PER_PAGE`, oldest first.

    The issue's ``comments`` count says how many it has in all.
    """


def read_issue(repository: ProjectRepository, number: int, token: Optional[SecretStr]) -> GitHubIssueThread:
    """
    Read an issue of a repository, and its latest :data:`COMMENTS_PER_PAGE` comments.

    Issues are public, so the result does not depend on who asks. Without the caller's classic
    token the request is anonymous, at GitHub's anonymous rate limit.

    Side effects: one ``GET`` request to GitHub for the issue, and, if it has comments, a second
    one for the last page of its comments, which holds the latest. A failure is logged.

    :param repository: The repository.
    :param number: The issue's number.
    :param token: The caller's GitHub token, or None. Only a classic personal access token is sent.
    :returns: The issue and its latest comments, oldest first.
    :raises SmarterMCPServerServiceError: If GitHub could not be reached, the issue was not found,
        or GitHub's response could not be read.
    """
    value = optional_token(token)
    path = f"/repos/{repository.full_name}/issues/{number}"
    not_found = _issue_not_found(repository, number)
    response = github_request("GET", path, value)
    if response.status_code != 200:
        logger.info(
            "%s.read_issue() GitHub did not return %s#%s: HTTP %s",
            logger_prefix,
            repository.full_name,
            number,
            response.status_code,
        )
        reason = explain_failure(response, repository, f"read issue #{number}", not_found=not_found)
        raise SmarterMCPServerServiceError(reason)
    try:
        issue = GitHubIssueDetail.model_validate(response.json())
    except (ValueError, ValidationError) as e:
        logger.warning("%s.read_issue() GitHub's response is not an issue: %s", logger_prefix, e)
        raise SmarterMCPServerServiceError(f"GitHub's issue #{number} could not be read. Try again later.") from e
    if not issue.comments:
        return GitHubIssueThread(issue=issue)
    # the last page holds the latest comments, which say what is already known.
    last_page = (issue.comments - 1) // COMMENTS_PER_PAGE + 1
    params = {
        "per_page": str(COMMENTS_PER_PAGE),
        "page": str(last_page),
    }
    response = github_request("GET", f"{path}/comments", value, params=params)
    if response.status_code != 200:
        action = f"read the comments of issue #{number}"
        reason = explain_failure(response, repository, action, not_found=not_found)
        raise SmarterMCPServerServiceError(reason)
    try:
        data = response.json()
        comments = [GitHubIssueComment.model_validate(comment) for comment in data]
    except (ValueError, TypeError, ValidationError) as e:
        logger.warning("%s.read_issue() GitHub's response is not a list of comments: %s", logger_prefix, e)
        raise SmarterMCPServerServiceError(
            f"The comments of issue #{number} could not be read. Try again later."
        ) from e
    return GitHubIssueThread(issue=issue, comments=comments)


MAX_TITLE_LENGTH = 256
"""GitHub's maximum length of an issue's title, which the tools' arguments enforce."""

MAX_BODY_LENGTH = 20000
"""The maximum length of an issue's or comment's body, well below GitHub's limit of 65536 characters.

The tools' arguments enforce it, so that an LLM cannot paste a whole log into a public issue.
"""

ISSUE_FOOTER = "\n\n---\n_Opened with Smarter's MCPServer._"
"""Appended to every issue's body, so that maintainers can tell where it came from."""

COMMENT_FOOTER = "\n\n---\n_Written with Smarter's MCPServer._"
"""Appended to every comment's body, so that maintainers can tell where it came from."""


class GitHubIssue(BaseModel):
    """
    An issue that GitHub created, with the fields of its response that the ``create_issue`` tool reports.

    :func:`create_issue` builds it from GitHub's ``201 Created`` response, plus the ``author``
    that :func:`created` adds. GitHub's response has many more fields, which are ignored.
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    number: int = Field(description="The issue's number in its repository.")
    title: str = Field(description="The issue's title.")
    html_url: str = Field(description="The issue's url on github.com.")
    author: Optional[str] = Field(default=None, description="The GitHub login of the token's owner.")


class GitHubComment(BaseModel):
    """
    A comment that GitHub created, with the fields of its response that the ``comment_on_issue`` tool reports.

    :func:`comment_on_issue` builds it from GitHub's ``201 Created`` response, plus the
    ``author`` that :func:`created` adds. GitHub's response has many more fields, which are ignored.
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    id: int = Field(description="The comment's id.")
    html_url: str = Field(description="The comment's url on github.com.")
    author: Optional[str] = Field(default=None, description="The GitHub login of the token's owner.")


def created(response: requests.Response, repository: ProjectRepository, what: str) -> SmarterDictType:
    """
    Return GitHub's description of what it created, with its author's login as ``author``.

    GitHub names the author only as a nested ``user`` object. Copying its login to a top-level
    ``author`` lets :class:`GitHubIssue` and :class:`GitHubComment` read it as a plain field.
    By the time this runs, GitHub has already created the issue or comment, so the error says so,
    and points to where it can be found, so that the LLM does not create it again.

    :param response: GitHub's ``201 Created`` response.
    :param repository: The repository.
    :param what: What was created, e.g. ``an issue``, for the error message.
    :returns: The response's JSON object.
    :raises SmarterMCPServerServiceError: If the response is not a JSON object.
    """
    try:
        data = response.json()
        description = {**data}
        description["author"] = author_login(data)
    except (ValueError, AttributeError) as e:
        logger.warning("%s.created() GitHub's response is not JSON: %s", logger_prefix, e)
        raise SmarterMCPServerServiceError(
            f"GitHub created {what} in {repository.full_name}, but its response could not be read. "
            f"See {repository.github_url}/issues."
        ) from e
    return description


def create_issue(
    repository: ProjectRepository,
    title: str,
    body: str,
    token: Optional[SecretStr],
    labels: tuple[str, ...] = (),
) -> GitHubIssue:
    """
    Open an issue in a repository of The Smarter Project, as the owner of a GitHub token.

    The issue is written with the caller's own token, so it is theirs on GitHub, and GitHub
    decides what they may do, e.g. whether their labels are kept. Before anything is sent, the
    token is checked (:func:`~smarter.apps.mcpserver.services.github.client.validate_token`), and the
    title, body and labels are checked for credentials
    (:func:`~smarter.apps.mcpserver.services.github.client.refuse_secrets`), because the issue is public.

    Side effects: one ``POST /repos/{owner}/{repo}/issues`` request, which creates a public issue
    and notifies the repository's watchers. The result is never cached: every call writes. The
    new issue's url is logged.

    :param repository: The repository.
    :param title: The issue's title.
    :param body: The issue's body, in Markdown. :data:`ISSUE_FOOTER` is appended.
    :param token: The caller's classic personal access token.
    :param labels: The issue's labels, e.g. ``bug``. GitHub creates a label that the repository
        does not have, and silently drops the labels of a caller who cannot push to the repository.
    :returns: The new issue.
    :raises SmarterMCPServerServiceError: If the token is not a classic personal access token, the
        title or body holds a credential, or GitHub could not be reached, or did not create the issue.
    """
    value = validate_token(token)
    refuse_secrets(value, title, body, *labels)
    data: SmarterDictType = {
        "title": title,
        "body": body + ISSUE_FOOTER,
    }
    if labels:
        data["labels"] = list(labels)
    path = f"/repos/{repository.full_name}/issues"
    response = github_request("POST", path, value, json=data)
    if response.status_code != 201:
        logger.info(
            "%s.create_issue() GitHub did not open an issue in %s: HTTP %s",
            logger_prefix,
            repository.full_name,
            response.status_code,
        )
        reason = explain_failure(response, repository, "open the issue")
        raise SmarterMCPServerServiceError(reason)
    description = created(response, repository, "an issue")
    try:
        issue = GitHubIssue.model_validate(description)
    except ValidationError as e:
        logger.warning("%s.create_issue() GitHub's response is not an issue: %s", logger_prefix, e)
        raise SmarterMCPServerServiceError(
            f"GitHub opened an issue in {repository.full_name}, but its response could not be read. "
            f"See {repository.github_url}/issues."
        ) from e
    logger.info("%s.create_issue() opened %s", logger_prefix, issue.html_url)
    return issue


def comment_on_issue(
    repository: ProjectRepository, number: int, body: str, token: Optional[SecretStr]
) -> GitHubComment:
    """
    Add a comment to an issue of a repository of The Smarter Project, as the owner of a GitHub token.

    Like :func:`create_issue`, it writes with the caller's own token, after checking the token
    and the body for credentials. It also comments on a pull request, whose number GitHub shares
    with issues. :func:`close_issue` calls it to say why an issue is closed.

    Side effects: one ``POST /repos/{owner}/{repo}/issues/{number}/comments`` request, which
    creates a public comment and notifies the issue's participants. The result is never cached:
    every call writes. The new comment's url is logged.

    :param repository: The repository.
    :param number: The issue's number.
    :param body: The comment, in Markdown. :data:`COMMENT_FOOTER` is appended.
    :param token: The caller's classic personal access token.
    :returns: The new comment.
    :raises SmarterMCPServerServiceError: If the token is not a classic personal access token, the
        body holds a credential, or GitHub could not be reached, or did not create the comment,
        e.g. the issue is locked.
    """
    value = validate_token(token)
    refuse_secrets(value, body)
    path = f"/repos/{repository.full_name}/issues/{number}/comments"
    data: SmarterDictType = {"body": body + COMMENT_FOOTER}
    response = github_request("POST", path, value, json=data)
    if response.status_code != 201:
        logger.info(
            "%s.comment_on_issue() GitHub did not comment on %s#%s: HTTP %s",
            logger_prefix,
            repository.full_name,
            number,
            response.status_code,
        )
        not_found = _issue_not_found(repository, number)
        reason = explain_failure(response, repository, f"comment on issue #{number}", not_found=not_found)
        raise SmarterMCPServerServiceError(reason)
    description = created(response, repository, "a comment")
    try:
        comment = GitHubComment.model_validate(description)
    except ValidationError as e:
        logger.warning("%s.comment_on_issue() GitHub's response is not a comment: %s", logger_prefix, e)
        raise SmarterMCPServerServiceError(
            f"GitHub added a comment to {repository.full_name}#{number}, but its response could not be read. "
            f"See {repository.github_url}/issues/{number}."
        ) from e
    logger.info("%s.comment_on_issue() commented %s", logger_prefix, comment.html_url)
    return comment


class GitHubPullRequestState(BaseModel):
    """
    A pull request, as ``GET /repos/{owner}/{repo}/pulls/{number}`` returns it, with the fields that ``close_issue`` reads.

    :func:`close_issue` closes an issue only if ``merged`` is true. GitHub's response has many
    more fields, which are ignored.
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    number: int = Field(description="The pull request's number.")
    html_url: str = Field(description="The pull request's url on github.com.")
    merged: bool = Field(default=False, description="Whether it was merged.")
    merged_at: Optional[str] = Field(default=None, description="When it was merged, in ISO 8601.")


class GitHubIssueClosed(BaseModel):
    """
    An issue that :func:`close_issue` closed, with the comment that says why.

    The ``close_issue`` tool reports it. It is built from the comment that
    :func:`comment_on_issue` added and the pull request that GitHub confirmed was merged, rather
    than from GitHub's response to the closing, which the tool does not need.
    """

    model_config = ConfigDict(frozen=True)

    number: int = Field(description="The issue's number.")
    html_url: str = Field(description="The issue's url on github.com.")
    comment_url: str = Field(description="The url of the comment that says why it was closed.")
    pull_request_url: str = Field(description="The url of the merged pull request that resolved it.")
    author: Optional[str] = Field(default=None, description="The GitHub login of the token's owner.")


def close_issue(
    repository: ProjectRepository,
    number: int,
    pull_request_number: int,
    comment: str,
    token: Optional[SecretStr],
) -> GitHubIssueClosed:
    """
    Close an issue that a merged pull request resolved, with a comment that says why, as the owner of a GitHub token.

    The issue is closed only if GitHub says that the pull request was merged, so that an LLM
    cannot close an issue on its own judgment alone, nor because a log or an issue told it to.
    The comment is added first, and the issue is then closed as ``completed``, so that an issue
    is never closed without saying why.

    Side effects, in order: a ``GET`` request for the pull request; a ``POST`` that adds the
    comment (see :func:`comment_on_issue`); and a ``PATCH`` that closes the issue, which notifies
    its participants. If the closing fails after the comment was added, the error says so, so
    that the LLM does not add the comment again. Nothing is cached.

    :param repository: The repository of the issue and the pull request.
    :param number: The issue's number.
    :param pull_request_number: The number of the merged pull request that resolved the issue.
    :param comment: Why the issue is resolved, in Markdown. :data:`COMMENT_FOOTER` is appended.
    :param token: The caller's classic personal access token.
    :returns: The closed issue.
    :raises SmarterMCPServerServiceError: If the token is not a classic personal access token, the
        comment holds a credential, the pull request was not found or not merged, or GitHub could
        not be reached, or refused the comment or the closing.
    """
    value = validate_token(token)
    refuse_secrets(value, comment)
    if pull_request_number == number:
        raise SmarterMCPServerServiceError(
            "An issue cannot be resolved by itself: give the merged pull request's number."
        )
    pull_request_path = f"/repos/{repository.full_name}/pulls/{pull_request_number}"
    response = github_request("GET", pull_request_path, value)
    if response.status_code != 200:
        action = f"read pull request #{pull_request_number}"
        not_found = f"Pull request #{pull_request_number} was not found in {repository.full_name}."
        reason = explain_failure(response, repository, action, not_found=not_found)
        raise SmarterMCPServerServiceError(reason)
    try:
        pull_request = GitHubPullRequestState.model_validate(response.json())
    except (ValueError, ValidationError) as e:
        logger.warning("%s.close_issue() GitHub's response is not a pull request: %s", logger_prefix, e)
        raise SmarterMCPServerServiceError(
            f"Pull request #{pull_request_number} could not be read. Try again later."
        ) from e
    if not pull_request.merged:
        raise SmarterMCPServerServiceError(
            f"Pull request #{pull_request_number} is not merged, so issue #{number} was not closed. Close an issue "
            "only when the merged pull request that resolved it is known."
        )
    posted = comment_on_issue(repository, number, comment, token)
    issue_path = f"/repos/{repository.full_name}/issues/{number}"
    closing: SmarterDictType = {"state": "closed", "state_reason": "completed"}
    response = github_request("PATCH", issue_path, value, json=closing)
    if response.status_code != 200:
        logger.info(
            "%s.close_issue() GitHub did not close %s#%s: HTTP %s",
            logger_prefix,
            repository.full_name,
            number,
            response.status_code,
        )
        reason = explain_failure(response, repository, f"close issue #{number}")
        raise SmarterMCPServerServiceError(
            f"The comment was added, at {posted.html_url}, but the issue was not closed: {reason} "
            "Do not add the comment again."
        )
    logger.info(
        "%s.close_issue() closed %s#%s, resolved by #%s",
        logger_prefix,
        repository.full_name,
        number,
        pull_request_number,
    )
    closed = GitHubIssueClosed(
        number=number,
        html_url=f"{repository.github_url}/issues/{number}",
        comment_url=posted.html_url,
        pull_request_url=pull_request.html_url,
        author=posted.author,
    )
    return closed


__all__ = [
    "GitHubComment",
    "GitHubIssue",
    "GitHubIssueClosed",
    "GitHubIssueComment",
    "GitHubIssueDetail",
    "GitHubIssueHit",
    "GitHubIssueThread",
    "GitHubPullRequestState",
    "IssueState",
    "close_issue",
    "comment_on_issue",
    "create_issue",
    "read_issue",
    "search_issues",
]
