"""
Pull requests to The Smarter Project's repositories, opened as the caller.

:func:`create_pull_request` writes a change as one commit on a new branch, and opens a pull
request from it, with GitHub's REST api alone, without a clone:

1. ``GET /repos/{owner}/{repo}/git/ref/heads/{base}``: the base branch's latest commit.
2. ``GET /repos/{owner}/{repo}/git/trees/{sha}``: the trees of the folders of the changed
   files, so that an executable file stays executable, and a symbolic link or a folder is
   never overwritten by a file.
3. ``POST /repos/{owner}/{repo}/git/trees``: the base commit's tree, with the changes.
4. ``POST /repos/{owner}/{repo}/git/commits``: the commit, optionally with its author.
5. ``POST /repos/{owner}/{repo}/git/refs``: the new branch. GitHub refuses a branch that
   exists, so the tool never changes an existing branch, e.g. ``main``, nor anyone's work.
6. ``POST /repos/{owner}/{repo}/pulls``: the pull request.

Like :func:`~smarter.apps.mcpserver.github.issues.create_issue`, it writes as the caller,
with the caller's own classic personal access token, which needs the ``public_repo`` scope,
and never writes a credential (see :func:`~smarter.apps.mcpserver.github.client.refuse_secrets`).
It never changes a file under ``.github/``: GitHub would refuse it without the ``workflow``
scope, and a workflow that a pull request changes may run with the repository's secrets.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

import posixpath
import re
from typing import Optional, TypeVar

import requests
from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError

from smarter.apps.mcpserver.exceptions import SmarterMCPServerToolError
from smarter.apps.mcpserver.repositories import ProjectRepository
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.typing import SmarterDictType

from .client import (
    explain_failure,
    github_request,
    refuse_secrets,
    validate_token,
)

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.MCPSERVER_LOGGING])
logger_prefix = logging.SmarterFormattedText.text(__name__)

PULL_REQUEST_FOOTER = "\n\n---\n_Opened with the Smarter Project MCP server._"
"""Appended to every pull request's body, so that maintainers can tell where it came from."""
MAX_BRANCH_LENGTH = 100
MAX_PATH_LENGTH = 300
MAX_FILES = 20
"""The most files that one pull request may change."""
MAX_FILE_LENGTH = 200000
"""The longest file, in characters, that a pull request may write."""
MAX_COMMIT_MESSAGE_LENGTH = 10000
BRANCH_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")
"""A branch name: letters, digits, ``.``, ``_``, ``-`` and ``/``, starting with a letter or digit."""
PROTECTED_FOLDERS = (".github/", ".git/")
"""Folders whose files a pull request never changes."""
FILE_MODE = "100644"
EXECUTABLE_MODE = "100755"
SYMLINK_MODE = "120000"


class GitHubCommitAuthor(BaseModel):
    """The author of a commit, as git records it."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(min_length=1, max_length=100, description="The author's name, e.g. Claude.")
    email: str = Field(
        min_length=3,
        max_length=254,
        pattern=r"^[^@\s]+@[^@\s]+$",
        description="The author's email address, e.g. noreply@anthropic.com.",
    )


class PullRequestFile(BaseModel):
    """One file that a pull request changes: its whole new content, or its deletion."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    path: str = Field(
        min_length=1,
        max_length=MAX_PATH_LENGTH,
        description="The file's path in the repository, e.g. smarter/smarter/apps/plugin/models.py.",
    )
    content: Optional[str] = Field(
        default=None,
        max_length=MAX_FILE_LENGTH,
        description="The file's whole new content, as UTF-8 text. Omit it to delete the file.",
    )
    delete: bool = Field(default=False, description="True to delete the file.")


class GitTreeEntry(BaseModel):
    """One entry of a git tree, with the fields that :func:`create_pull_request` reads."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    path: str
    mode: str
    type: str
    sha: Optional[str] = None


class GitTree(BaseModel):
    """A git tree, as ``GET /repos/{owner}/{repo}/git/trees/{sha}`` returns it."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    sha: str
    tree: list[GitTreeEntry] = Field(default_factory=list)


class GitObject(BaseModel):
    """A git object that GitHub returns: a ref's target, a commit or a tree, by its sha."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    sha: str


class GitRef(BaseModel):
    """A branch, as ``GET /repos/{owner}/{repo}/git/ref/heads/{branch}`` returns it."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    object: GitObject


class GitCommit(BaseModel):
    """A commit, as ``GET /repos/{owner}/{repo}/git/commits/{sha}`` returns it."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    sha: str
    tree: GitObject


class GitHubRepositoryInfo(BaseModel):
    """A repository, as ``GET /repos/{owner}/{repo}`` returns it, with the field that is read."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    default_branch: str


class GitHubPullRequest(BaseModel):
    """
    A pull request that GitHub created, with the fields that the tool reports.

    GitHub's response has many more fields, which are ignored.
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    number: int = Field(description="The pull request's number in its repository.")
    title: str = Field(description="The pull request's title.")
    html_url: str = Field(description="The pull request's url on github.com.")
    draft: bool = Field(default=False, description="Whether it is a draft.")
    author: Optional[str] = Field(default=None, description="The GitHub login of the token's owner.")
    branch: str = Field(default="", description="The new branch.")
    base: str = Field(default="", description="The branch that it would merge into.")
    commit_sha: str = Field(default="", description="The commit on the new branch.")


Model = TypeVar("Model", bound=BaseModel)


def validate_branch(name: str) -> str:
    """
    Return a branch name, if git and GitHub accept it.

    :param name: The branch name, e.g. ``claude/fix-plugin-timeout``.
    :returns: The name.
    :raises SmarterMCPServerToolError: If git would refuse the name.
    """
    if (
        len(name) > MAX_BRANCH_LENGTH
        or not BRANCH_PATTERN.match(name)
        or ".." in name
        or "//" in name
        or name.endswith(("/", ".", ".lock"))
        or "/." in name
    ):
        raise SmarterMCPServerToolError(
            f"{name!r} is not a valid branch name. Use letters, digits, '-', '_', '.' and '/', "
            f"e.g. claude/fix-plugin-timeout, at most {MAX_BRANCH_LENGTH} characters."
        )
    return name


def validate_files(files: list[PullRequestFile]) -> list[PullRequestFile]:
    """
    Return a pull request's files, if they are a change that the tool may write.

    :param files: The files.
    :returns: The files.
    :raises SmarterMCPServerToolError: If there are none or too many, a path is not a plain
        relative path, is under ``.github/``, or appears twice, or a file has both or neither
        of content and ``delete``.
    """
    if not files:
        raise SmarterMCPServerToolError("A pull request must change at least one file.")
    if len(files) > MAX_FILES:
        raise SmarterMCPServerToolError(f"A pull request may change at most {MAX_FILES} files.")
    seen: set[str] = set()
    for file in files:
        path = file.path
        parts = path.split("/")
        if path.startswith("/") or "\\" in path or any(part in ("", ".", "..") for part in parts):
            raise SmarterMCPServerToolError(
                f"{path!r} is not a path in the repository. Use a relative path, e.g. docs/source/index.rst."
            )
        if path.startswith(PROTECTED_FOLDERS):
            raise SmarterMCPServerToolError(
                f"{path} is under {path.split('/')[0]}/, which this tool never changes: describe the change in the "
                "pull request instead."
            )
        if path in seen:
            raise SmarterMCPServerToolError(f"{path} is listed twice.")
        seen.add(path)
        if file.delete == (file.content is not None):
            raise SmarterMCPServerToolError(f"{path}: give either its whole new content, or delete: true.")
    return files


def parse(response: requests.Response, model: type[Model], what: str) -> Model:
    """
    Return GitHub's JSON response as a model.

    :param response: GitHub's successful response.
    :param model: The model of the response.
    :param what: What the response is, for the error message, e.g. ``the base branch``.
    :returns: The model.
    :raises SmarterMCPServerToolError: If the response is not what was expected.
    """
    try:
        return model.model_validate(response.json())
    except (ValueError, ValidationError) as e:
        logger.warning("%s.parse() GitHub's response for %s could not be read: %s", logger_prefix, what, e)
        raise SmarterMCPServerToolError(f"GitHub's response for {what} could not be read. Try again later.") from e


class PullRequestWriter:
    """
    Write a change as one commit on a new branch, and open a pull request from it.

    :param repository: The repository.
    :param token: The caller's classic personal access token, from :func:`validate_token`.
    """

    def __init__(self, repository: ProjectRepository, token: str):
        self.repository = repository
        self.token = token
        self.trees: dict[str, GitTree] = {}

    def request(
        self,
        method: str,
        path: str,
        action: str,
        expected: int = 200,
        json: Optional[SmarterDictType] = None,
        not_found: Optional[str] = None,
    ) -> requests.Response:
        """
        Send one request to the repository's api, and return GitHub's response, if it succeeded.

        :param method: The HTTP method.
        :param path: The path after ``/repos/{owner}/{repo}``, e.g. ``/git/refs``.
        :param action: What the request does, for the error message, e.g. ``create the branch``.
        :param expected: The status of success.
        :param json: The request's JSON body, if any.
        :param not_found: What a 404 means, if not that the repository was not found.
        :returns: GitHub's response.
        :raises SmarterMCPServerToolError: If GitHub could not be reached, or refused the request.
        """
        response = github_request(method, f"/repos/{self.repository.full_name}{path}", self.token, json=json)
        if response.status_code != expected:
            logger.info(
                "%s.request() GitHub did not %s in %s: HTTP %s",
                logger_prefix,
                action,
                self.repository.full_name,
                response.status_code,
            )
            raise SmarterMCPServerToolError(explain_failure(response, self.repository, action, not_found=not_found))
        return response

    def default_branch(self) -> str:
        """Return the repository's default branch, e.g. ``main``."""
        response = self.request("GET", "", "read the repository")
        return parse(response, GitHubRepositoryInfo, "the repository").default_branch

    def branch_commit(self, branch: str) -> str:
        """Return the sha of a branch's latest commit."""
        response = self.request(
            "GET",
            f"/git/ref/heads/{branch}",
            f"read the branch {branch}",
            not_found=f"The branch {branch} was not found in {self.repository.full_name}.",
        )
        return parse(response, GitRef, f"the branch {branch}").object.sha

    def tree(self, sha: str) -> GitTree:
        """Return a tree, which is read once per pull request."""
        if sha not in self.trees:
            response = self.request("GET", f"/git/trees/{sha}", "read a folder")
            self.trees[sha] = parse(response, GitTree, "a folder")
        return self.trees[sha]

    def existing_entry(self, root_tree: str, path: str) -> Optional[GitTreeEntry]:
        """
        Return the tree entry of a path at the base commit, or None if it does not exist.

        :param root_tree: The sha of the base commit's tree.
        :param path: The path.
        :returns: The entry, whose mode says whether it is a file, an executable, a link or a folder.
        """
        tree_sha = root_tree
        folders, name = posixpath.split(path)
        for folder in folders.split("/") if folders else []:
            entry = next((e for e in self.tree(tree_sha).tree if e.path == folder), None)
            if entry is None or entry.type != "tree" or not entry.sha:
                return None
            tree_sha = entry.sha
        return next((e for e in self.tree(tree_sha).tree if e.path == name), None)

    def tree_entries(self, root_tree: str, files: list[PullRequestFile]) -> list[SmarterDictType]:
        """
        Return the entries of the new tree: each file's content and mode, or its deletion.

        :param root_tree: The sha of the base commit's tree.
        :param files: The changed files.
        :returns: The entries, for ``POST /git/trees``.
        :raises SmarterMCPServerToolError: If a deleted file does not exist, or a path is a
            folder or a symbolic link.
        """
        entries: list[SmarterDictType] = []
        for file in files:
            existing = self.existing_entry(root_tree, file.path)
            if existing is not None and existing.type != "blob":
                raise SmarterMCPServerToolError(f"{file.path} is a folder, not a file.")
            if existing is not None and existing.mode == SYMLINK_MODE:
                raise SmarterMCPServerToolError(f"{file.path} is a symbolic link, which this tool does not change.")
            if file.delete:
                if existing is None:
                    raise SmarterMCPServerToolError(f"{file.path} cannot be deleted: it does not exist.")
                entries.append({"path": file.path, "mode": existing.mode, "type": "blob", "sha": None})
            else:
                mode = existing.mode if existing is not None else FILE_MODE
                entries.append({"path": file.path, "mode": mode, "type": "blob", "content": file.content})
        return entries

    def write(
        self,
        branch: str,
        base: Optional[str],
        title: str,
        body: str,
        commit_message: str,
        files: list[PullRequestFile],
        author: Optional[GitHubCommitAuthor],
        draft: bool,
    ) -> GitHubPullRequest:
        """
        Write the commit on a new branch, and open the pull request.

        See :func:`create_pull_request`.

        :raises SmarterMCPServerToolError: If a step fails. If the branch was created, but the
            pull request was not, the error says so.
        """
        base = base or self.default_branch()
        base_sha = self.branch_commit(base)
        response = self.request("GET", f"/git/commits/{base_sha}", "read the base commit")
        base_commit = parse(response, GitCommit, "the base commit")
        entries = self.tree_entries(base_commit.tree.sha, files)
        response = self.request(
            "POST",
            "/git/trees",
            "write the changed files",
            expected=201,
            json={"base_tree": base_commit.tree.sha, "tree": entries},
        )
        tree = parse(response, GitObject, "the new tree")
        commit: SmarterDictType = {"message": commit_message, "tree": tree.sha, "parents": [base_sha]}
        if author is not None:
            # the author also commits: the change is entirely theirs.
            commit["author"] = author.model_dump()
            commit["committer"] = author.model_dump()
        response = self.request("POST", "/git/commits", "write the commit", expected=201, json=commit)
        new_commit = parse(response, GitObject, "the new commit")
        self.request(
            "POST",
            "/git/refs",
            f"create the branch {branch}",
            expected=201,
            json={"ref": f"refs/heads/{branch}", "sha": new_commit.sha},
        )
        logger.info("%s.write() created the branch %s in %s", logger_prefix, branch, self.repository.full_name)
        try:
            response = self.request(
                "POST",
                "/pulls",
                "open the pull request",
                expected=201,
                json={"title": title, "head": branch, "base": base, "body": body + PULL_REQUEST_FOOTER, "draft": draft},
            )
        except SmarterMCPServerToolError as e:
            raise SmarterMCPServerToolError(
                f"The branch {branch} was created, with the change, at {self.repository.github_url}/tree/{branch}, "
                f"but the pull request was not opened: {e.message} Do not call create_pull_request again with "
                "the same branch: open the pull request from the branch on github.com."
            ) from e
        try:
            data = response.json()
            pull_request = GitHubPullRequest.model_validate(
                {
                    **data,
                    "author": (data.get("user") or {}).get("login"),
                    "branch": branch,
                    "base": base,
                    "commit_sha": new_commit.sha,
                }
            )
        except (ValueError, AttributeError, ValidationError) as e:
            logger.warning("%s.write() GitHub's response is not a pull request: %s", logger_prefix, e)
            raise SmarterMCPServerToolError(
                f"GitHub opened a pull request from {branch} in {self.repository.full_name}, but its response could "
                f"not be read. See {self.repository.github_url}/pulls."
            ) from e
        logger.info("%s.write() opened %s", logger_prefix, pull_request.html_url)
        return pull_request


def create_pull_request(
    repository: ProjectRepository,
    branch: str,
    title: str,
    body: str,
    commit_message: str,
    files: list[PullRequestFile],
    token: Optional[SecretStr],
    base: Optional[str] = None,
    author: Optional[GitHubCommitAuthor] = None,
    draft: bool = False,
) -> GitHubPullRequest:
    """
    Open a pull request in a repository of The Smarter Project, as the owner of a GitHub token.

    The change is one commit, on a new branch from the latest commit of ``base``. Each file is
    given whole: its new content, or its deletion. A changed file keeps its mode, e.g. an
    executable stays executable.

    :param repository: The repository.
    :param branch: The new branch, e.g. ``claude/fix-plugin-timeout``. It must not exist.
    :param title: The pull request's title.
    :param body: The pull request's description, in Markdown. :data:`PULL_REQUEST_FOOTER` is appended.
    :param commit_message: The commit's message.
    :param files: The changed files.
    :param token: The caller's classic personal access token.
    :param base: The branch to merge into, and to branch from. Defaults to the repository's default branch.
    :param author: The commit's author and committer. Defaults to the token's owner.
    :param draft: Whether to open it as a draft.
    :returns: The new pull request.
    :raises SmarterMCPServerToolError: If the token is not a classic personal access token, the
        branch name or a file is not valid, the change holds a credential, or GitHub could not be
        reached, or refused a step, e.g. because the branch exists.
    """
    value = validate_token(token)
    validate_branch(branch)
    if base is not None:
        validate_branch(base)
    validate_files(files)
    refuse_secrets(value, title, body, commit_message, *[file.content or "" for file in files])
    return PullRequestWriter(repository, value).write(branch, base, title, body, commit_message, files, author, draft)


__all__ = [
    "GitHubCommitAuthor",
    "GitHubPullRequest",
    "PullRequestFile",
    "PullRequestWriter",
    "create_pull_request",
    "validate_branch",
    "validate_files",
]
