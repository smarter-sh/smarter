"""
GitHub issues of The Smarter Project's repositories: searched, opened and commented on.

- :func:`search_issues` asks GitHub's issue search, ``GET /search/issues``, live, rather than
  the index: issues change by the minute, and an LLM that is about to open an issue must see
  one that was opened a minute ago. It searches one repository with ``repo:``, or all of them
  with ``org:``, and drops the results of the organization's other repositories. Issues are
  public, so the result does not depend on who asks. Without the caller's classic token the
  search is anonymous, and GitHub allows anonymous clients 10 searches a minute for each IP
  address, which the platform's users share. A token raises that to 30 for its owner.
- :func:`create_issue` opens an issue, with ``POST /repos/{owner}/{repo}/issues``.
- :func:`comment_on_issue` adds a comment to an existing issue, with
  ``POST /repos/{owner}/{repo}/issues/{number}/comments``.

:func:`create_issue` and :func:`comment_on_issue` write as the caller, with the caller's own
classic personal access token, so the issue or comment is the caller's, and GitHub decides
what the caller may do. Both append a footer that says where the text came from. Never cache
them: every call writes. See :mod:`smarter.apps.mcpserver.github.client` for how the token is
checked and kept secret, and how GitHub's errors are explained.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from typing import Literal, Optional

import requests
from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError

from smarter.apps.mcpserver.exceptions import SmarterMCPServerToolError
from smarter.apps.mcpserver.github.client import (
    explain_failure,
    github_request,
    optional_token,
    validate_token,
)
from smarter.apps.mcpserver.repositories import GITHUB_API_URL, ProjectRepository
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.typing import SmarterDictType

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.MCPSERVER_LOGGING])
logger_prefix = logging.SmarterFormattedText.text(__name__)


IssueState = Literal["open", "closed", "all"]
MAX_EXCERPT_LENGTH = 300
"""The length of each issue's body excerpt in the result."""


class GitHubIssueHit(BaseModel):
    """
    One issue that GitHub's search found, with the fields that the tool reports.

    GitHub's response has many more fields, which are ignored.
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
        """The repository's full name, e.g. ``smarter-sh/smarter``."""
        return self.repository_url.removeprefix(f"{GITHUB_API_URL}/repos/")

    @property
    def excerpt(self) -> str:
        """The start of the issue's body, on one line."""
        text = " ".join((self.body or "").split())
        return text if len(text) <= MAX_EXCERPT_LENGTH else text[: MAX_EXCERPT_LENGTH - 3] + "..."


class GitHubIssueSearchResult(BaseModel):
    """GitHub's answer to an issue search, with the fields that the tool reads."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    total_count: int = 0
    items: list[GitHubIssueHit] = Field(default_factory=list)


def search_query(query: str, repositories: tuple[ProjectRepository, ...], one: bool, state: IssueState) -> str:
    """
    Return GitHub's search query: the keywords, issues only, the repositories and the state.

    :param query: The keywords.
    :param repositories: The repositories to search.
    :param one: Whether to search only the first repository, with ``repo:``, rather than the organization.
    :param state: ``open``, ``closed`` or ``all``.
    :returns: The query, e.g. ``guardrail apply is:issue repo:smarter-sh/smarter state:open``.
    """
    where = f"repo:{repositories[0].full_name}" if one else f"org:{repositories[0].owner}"
    parts = [query.strip(), "is:issue", where]
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

    :param repositories: The repositories to search. They have the same owner.
    :param query: The keywords.
    :param one: Whether to search only the first repository, rather than all of them.
    :param state: ``open``, ``closed`` or ``all``.
    :param limit: The maximum number of issues.
    :param token: The caller's GitHub token, or None. Only a classic personal access token is
        sent: otherwise the search is anonymous.
    :returns: The issues of the repositories.
    :raises SmarterMCPServerToolError: If GitHub could not be reached, or refused the search,
        e.g. its rate limit was reached.
    """
    value = optional_token(token)
    names = {repository.full_name for repository in repositories}
    # the organization's other repositories are dropped, so ask for more than the limit.
    per_page = limit if one else min(100, limit * 3)
    response = github_request(
        "GET",
        "/search/issues",
        value,
        params={"q": search_query(query, repositories, one, state), "per_page": str(per_page)},
    )
    if response.status_code != 200:
        logger.info("%s.search_issues() GitHub did not search: HTTP %s", logger_prefix, response.status_code)
        raise SmarterMCPServerToolError(explain_failure(response, repositories[0], "search the issues"))
    try:
        result = GitHubIssueSearchResult.model_validate(response.json())
    except (ValueError, ValidationError) as e:
        logger.warning("%s.search_issues() GitHub's response is not a search result: %s", logger_prefix, e)
        raise SmarterMCPServerToolError("GitHub's search result could not be read. Try again later.") from e
    return [hit for hit in result.items if hit.repository in names][:limit]


MAX_TITLE_LENGTH = 256
"""GitHub's maximum length of an issue's title."""
MAX_BODY_LENGTH = 20000
"""The maximum length of an issue's or comment's body, well below GitHub's limit of 65536 characters."""
ISSUE_FOOTER = "\n\n---\n_Opened with the Smarter Project MCP server._"
"""Appended to every issue's body, so that maintainers can tell where it came from."""
COMMENT_FOOTER = "\n\n---\n_Written with the Smarter Project MCP server._"
"""Appended to every comment's body."""


class GitHubIssue(BaseModel):
    """
    An issue that GitHub created, with the fields of its response that the tool reports.

    GitHub's response has many more fields, which are ignored.
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    number: int = Field(description="The issue's number in its repository.")
    title: str = Field(description="The issue's title.")
    html_url: str = Field(description="The issue's url on github.com.")
    author: Optional[str] = Field(default=None, description="The GitHub login of the token's owner.")


class GitHubComment(BaseModel):
    """
    A comment that GitHub created, with the fields of its response that the tool reports.

    GitHub's response has many more fields, which are ignored.
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    id: int = Field(description="The comment's id.")
    html_url: str = Field(description="The comment's url on github.com.")
    author: Optional[str] = Field(default=None, description="The GitHub login of the token's owner.")


def created(response: requests.Response, repository: ProjectRepository, what: str) -> SmarterDictType:
    """
    Return GitHub's description of what it created, with its author's login as ``author``.

    :param response: GitHub's ``201 Created`` response.
    :param repository: The repository.
    :param what: What was created, e.g. ``an issue``, for the error message.
    :returns: The response's JSON object.
    :raises SmarterMCPServerToolError: If the response is not a JSON object.
    """
    try:
        data = response.json()
        return {**data, "author": (data.get("user") or {}).get("login")}
    except (ValueError, AttributeError) as e:
        logger.warning("%s.created() GitHub's response is not JSON: %s", logger_prefix, e)
        raise SmarterMCPServerToolError(
            f"GitHub created {what} in {repository.full_name}, but its response could not be read. "
            f"See {repository.github_url}/issues."
        ) from e


def create_issue(repository: ProjectRepository, title: str, body: str, token: Optional[SecretStr]) -> GitHubIssue:
    """
    Open an issue in a repository of The Smarter Project, as the owner of a GitHub token.

    :param repository: The repository.
    :param title: The issue's title.
    :param body: The issue's body, in Markdown. :data:`ISSUE_FOOTER` is appended.
    :param token: The caller's classic personal access token.
    :returns: The new issue.
    :raises SmarterMCPServerToolError: If the token is not a classic personal access token, or
        GitHub could not be reached, or did not create the issue.
    """
    value = validate_token(token)
    response = github_request(
        "POST", f"/repos/{repository.full_name}/issues", value, json={"title": title, "body": body + ISSUE_FOOTER}
    )
    if response.status_code != 201:
        logger.info(
            "%s.create_issue() GitHub did not open an issue in %s: HTTP %s",
            logger_prefix,
            repository.full_name,
            response.status_code,
        )
        raise SmarterMCPServerToolError(explain_failure(response, repository, "open the issue"))
    try:
        issue = GitHubIssue.model_validate(created(response, repository, "an issue"))
    except ValidationError as e:
        logger.warning("%s.create_issue() GitHub's response is not an issue: %s", logger_prefix, e)
        raise SmarterMCPServerToolError(
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

    :param repository: The repository.
    :param number: The issue's number.
    :param body: The comment, in Markdown. :data:`COMMENT_FOOTER` is appended.
    :param token: The caller's classic personal access token.
    :returns: The new comment.
    :raises SmarterMCPServerToolError: If the token is not a classic personal access token, or
        GitHub could not be reached, or did not create the comment, e.g. the issue is locked.
    """
    value = validate_token(token)
    response = github_request(
        "POST",
        f"/repos/{repository.full_name}/issues/{number}/comments",
        value,
        json={"body": body + COMMENT_FOOTER},
    )
    if response.status_code != 201:
        logger.info(
            "%s.comment_on_issue() GitHub did not comment on %s#%s: HTTP %s",
            logger_prefix,
            repository.full_name,
            number,
            response.status_code,
        )
        raise SmarterMCPServerToolError(
            explain_failure(
                response,
                repository,
                f"comment on issue #{number}",
                not_found=f"Issue #{number} was not found in {repository.full_name}. Find it with search_issues.",
            )
        )
    try:
        comment = GitHubComment.model_validate(created(response, repository, "a comment"))
    except ValidationError as e:
        logger.warning("%s.comment_on_issue() GitHub's response is not a comment: %s", logger_prefix, e)
        raise SmarterMCPServerToolError(
            f"GitHub added a comment to {repository.full_name}#{number}, but its response could not be read. "
            f"See {repository.github_url}/issues/{number}."
        ) from e
    logger.info("%s.comment_on_issue() commented %s", logger_prefix, comment.html_url)
    return comment


__all__ = [
    "GitHubComment",
    "GitHubIssue",
    "GitHubIssueHit",
    "IssueState",
    "comment_on_issue",
    "create_issue",
    "search_issues",
]
