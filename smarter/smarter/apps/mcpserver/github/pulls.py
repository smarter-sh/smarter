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
    author_login,
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
"""The longest branch name, in characters, that :func:`validate_branch` accepts."""

MAX_PATH_LENGTH = 300
"""The longest file path, in characters, that a pull request may change."""

MAX_FILES = 20
"""The most files that one pull request may change, so that a change stays small enough to review."""

MAX_FILE_LENGTH = 200000
"""The longest file, in characters, that a pull request may write."""

MAX_COMMIT_MESSAGE_LENGTH = 10000
"""The longest commit message, in characters, that the ``create_pull_request`` tool accepts."""

BRANCH_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")
"""A branch name: letters, digits, ``.``, ``_``, ``-`` and ``/``, starting with a letter or digit."""

PROTECTED_FOLDERS = (".github/", ".git/")
"""Folders whose files a pull request never changes.

A change to ``.github/`` needs the ``workflow`` scope, and a workflow may run with the
repository's secrets. ``.git/`` is git's own folder, which is never part of a commit.
"""

FILE_MODE = "100644"
"""The git mode of an ordinary file, which a new file gets."""

EXECUTABLE_MODE = "100755"
"""The git mode of an executable file, which a changed executable keeps."""

SYMLINK_MODE = "120000"
"""The git mode of a symbolic link, which this module never changes."""


class GitHubCommitAuthor(BaseModel):
    """
    The author of a commit, as git records it: a name and an email address.

    It is an argument of the ``create_pull_request`` tool. When it is given, it is both the
    commit's author and its committer, e.g. ``Claude <noreply@anthropic.com>``. When it is
    omitted, GitHub records the token's owner. ``extra="forbid"`` refuses any other field, so
    that a misspelt argument is reported to the LLM rather than ignored.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(min_length=1, max_length=100, description="The author's name, e.g. Claude.")
    email: str = Field(
        min_length=3,
        max_length=254,
        pattern=r"^[^@\s]+@[^@\s]+$",
        description="The author's email address, e.g. noreply@anthropic.com.",
    )


class PullRequestFile(BaseModel):
    """
    One file that a pull request changes: its whole new content, or its deletion.

    It is an argument of the ``create_pull_request`` tool. Exactly one of ``content`` and
    ``delete`` must be given, which :func:`validate_files` checks. A file is given whole, not as a
    diff, because GitHub's api writes whole files.
    """

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
    """
    One entry of a git tree, with the fields that :func:`create_pull_request` reads.

    An entry is a file, a symbolic link or a folder. Its mode tells a pull request whether a
    changed file is executable, and whether a path may be changed at all.
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    path: str
    """The entry's name in its folder, e.g. ``models.py``, not its whole path."""

    mode: str
    """The entry's git mode, e.g. :data:`FILE_MODE`, :data:`EXECUTABLE_MODE` or :data:`SYMLINK_MODE`."""

    type: str
    """``blob`` for a file or a symbolic link, ``tree`` for a folder, or ``commit`` for a submodule."""

    sha: Optional[str] = None
    """The sha of the entry's content, or None if GitHub did not give one."""


class GitTree(BaseModel):
    """
    A git tree, i.e. one folder, as ``GET /repos/{owner}/{repo}/git/trees/{sha}`` returns it.

    It is read without ``recursive``, so it lists only the folder's own entries.
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    sha: str
    """The tree's sha."""

    tree: list[GitTreeEntry] = Field(default_factory=list)
    """The folder's files, links and subfolders."""


class GitObject(BaseModel):
    """
    A git object that GitHub returns: a ref's target, a commit or a tree, by its sha.

    Only the sha is read, e.g. of the new tree, to put in the new commit.
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    sha: str
    """The object's sha."""


class GitRef(BaseModel):
    """
    A branch, as ``GET /repos/{owner}/{repo}/git/ref/heads/{branch}`` returns it.

    Its ``object`` is the branch's latest commit, which the new branch starts from.
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    object: GitObject
    """The commit that the branch points to."""


class GitCommit(BaseModel):
    """
    A commit, as ``GET /repos/{owner}/{repo}/git/commits/{sha}`` returns it.

    The base commit's tree is the starting point of the new tree.
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    sha: str
    """The commit's sha."""

    tree: GitObject
    """The commit's root tree, i.e. the repository's top folder at that commit."""


class GitHubRepositoryInfo(BaseModel):
    """
    A repository, as ``GET /repos/{owner}/{repo}`` returns it, with the field that is read.

    It is read only when a pull request does not name its base branch.
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    default_branch: str
    """The repository's default branch, e.g. ``main``."""


class GitHubPullRequest(BaseModel):
    """
    A pull request that GitHub created, with the fields that the ``create_pull_request`` tool reports.

    :meth:`PullRequestWriter.write` builds it from GitHub's ``201 Created`` response, plus the
    ``author``, ``branch``, ``base`` and ``commit_sha`` that it knows. GitHub's response has many
    more fields, which are ignored.
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
"""The Pydantic model that :func:`parse` returns, so that its callers get the precise type."""


def _is_valid_branch(name: str) -> bool:
    """
    Return whether git and GitHub accept a branch name.

    It is a subset of git's ``check-ref-format`` rules, stricter where that is simpler: only the
    characters of :data:`BRANCH_PATTERN`, no ``..``, ``//`` or ``/.``, and no trailing ``/``,
    ``.`` or ``.lock``.

    :param name: The branch name.
    :returns: Whether the name is valid.
    """
    if len(name) > MAX_BRANCH_LENGTH:
        return False
    if not BRANCH_PATTERN.match(name):
        return False
    if ".." in name:
        return False
    if "//" in name:
        return False
    if "/." in name:
        return False
    if name.endswith(("/", ".", ".lock")):
        return False
    return True


def validate_branch(name: str) -> str:
    """
    Return a branch name, if git and GitHub accept it.

    It is checked before anything is sent to GitHub, so that the LLM gets a clear explanation,
    rather than GitHub's, and so that a name cannot change the path of an api request.

    :param name: The branch name, e.g. ``claude/fix-plugin-timeout``.
    :returns: The name.
    :raises SmarterMCPServerToolError: If git would refuse the name.
    """
    if not _is_valid_branch(name):
        raise SmarterMCPServerToolError(
            f"{name!r} is not a valid branch name. Use letters, digits, '-', '_', '.' and '/', "
            f"e.g. claude/fix-plugin-timeout, at most {MAX_BRANCH_LENGTH} characters."
        )
    return name


def _is_relative_path(path: str) -> bool:
    """
    Return whether a path is a plain relative path in the repository.

    A plain relative path does not start with ``/``, uses ``/`` rather than ``\\``, and has no
    empty, ``.`` or ``..`` part, so that it cannot point outside the repository, nor name the
    same file in two ways.

    :param path: The path, e.g. ``docs/source/index.rst``.
    :returns: Whether the path is a plain relative path.
    """
    if path.startswith("/"):
        return False
    if "\\" in path:
        return False
    for part in path.split("/"):
        if part in ("", ".", ".."):
            return False
    return True


def validate_files(files: list[PullRequestFile]) -> list[PullRequestFile]:
    """
    Return a pull request's files, if they are a change that the tool may write.

    They are checked before anything is sent to GitHub. Whether a file exists, and whether it is
    a folder or a symbolic link, is checked later, against the base commit, by
    :meth:`PullRequestWriter.tree_entries`.

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
        if not _is_relative_path(path):
            raise SmarterMCPServerToolError(
                f"{path!r} is not a path in the repository. Use a relative path, e.g. docs/source/index.rst."
            )
        if path.startswith(PROTECTED_FOLDERS):
            top_folder = path.split("/")[0]
            raise SmarterMCPServerToolError(
                f"{path} is under {top_folder}/, which this tool never changes: describe the change in the "
                "pull request instead."
            )
        if path in seen:
            raise SmarterMCPServerToolError(f"{path} is listed twice.")
        seen.add(path)
        has_content = file.content is not None
        if file.delete == has_content:
            raise SmarterMCPServerToolError(f"{path}: give either its whole new content, or delete: true.")
    return files


def parse(response: requests.Response, model: type[Model], what: str) -> Model:
    """
    Return GitHub's JSON response as a model.

    Every step of :class:`PullRequestWriter` reads GitHub's response with it, so that a response
    that is not what was expected is logged once, and explained the same way.

    :param response: GitHub's successful response.
    :param model: The model of the response.
    :param what: What the response is, for the error message, e.g. ``the base branch``.
    :returns: The model.
    :raises SmarterMCPServerToolError: If the response is not what was expected.
    """
    try:
        data = response.json()
        result = model.model_validate(data)
    except (ValueError, ValidationError) as e:
        logger.warning("%s.parse() GitHub's response for %s could not be read: %s", logger_prefix, what, e)
        raise SmarterMCPServerToolError(f"GitHub's response for {what} could not be read. Try again later.") from e
    return result


class PullRequestWriter:
    """
    Write a change as one commit on a new branch, and open a pull request from it.

    One writer opens one pull request: :func:`create_pull_request` makes it, after checking the
    token, the branch names, the files and the text, and calls :meth:`write`, which takes the
    steps that the module's docstring lists. Each step is one request to GitHub's api, with the
    caller's token, through :meth:`request`, which turns a refusal into an explanation for the
    LLM. The folders that the change touches are read once each, and kept in :attr:`trees`.

    The token is kept only for the writer's lifetime, and is never logged.

    :param repository: The repository.
    :param token: The caller's classic personal access token, from
        :func:`~smarter.apps.mcpserver.github.client.validate_token`.
    """

    def __init__(self, repository: ProjectRepository, token: str):
        self.repository = repository
        """The repository that the pull request is opened in."""

        self.token = token
        """The caller's classic personal access token, which every request is sent with."""

        self.trees: dict[str, GitTree] = {}
        """The folders read so far, by their sha, so that each is read once."""

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

        Side effects: one request to GitHub (see
        :func:`~smarter.apps.mcpserver.github.client.github_request`), which writes when
        ``method`` is ``POST``. A refusal is logged with its status.

        :param method: The HTTP method.
        :param path: The path after ``/repos/{owner}/{repo}``, e.g. ``/git/refs``.
        :param action: What the request does, for the error message, e.g. ``create the branch``.
        :param expected: The status of success.
        :param json: The request's JSON body, if any.
        :param not_found: What a 404 means, if not that the repository was not found.
        :returns: GitHub's response.
        :raises SmarterMCPServerToolError: If GitHub could not be reached, or refused the request.
        """
        full_path = f"/repos/{self.repository.full_name}{path}"
        response = github_request(method, full_path, self.token, json=json)
        if response.status_code != expected:
            logger.info(
                "%s.request() GitHub did not %s in %s: HTTP %s",
                logger_prefix,
                action,
                self.repository.full_name,
                response.status_code,
            )
            reason = explain_failure(response, self.repository, action, not_found=not_found)
            raise SmarterMCPServerToolError(reason)
        return response

    def default_branch(self) -> str:
        """
        Return the repository's default branch, e.g. ``main``.

        Side effects: one ``GET /repos/{owner}/{repo}`` request to GitHub.

        :returns: The default branch's name.
        :raises SmarterMCPServerToolError: If GitHub could not be reached, refused the request, or
            its response could not be read.
        """
        response = self.request("GET", "", "read the repository")
        info = parse(response, GitHubRepositoryInfo, "the repository")
        return info.default_branch

    def branch_commit(self, branch: str) -> str:
        """
        Return the sha of a branch's latest commit, which the new branch starts from.

        Side effects: one ``GET /repos/{owner}/{repo}/git/ref/heads/{branch}`` request to GitHub.

        :param branch: The branch's name, e.g. ``main``.
        :returns: The commit's sha.
        :raises SmarterMCPServerToolError: If the branch was not found, GitHub could not be reached
            or refused the request, or its response could not be read.
        """
        response = self.request(
            "GET",
            f"/git/ref/heads/{branch}",
            f"read the branch {branch}",
            not_found=f"The branch {branch} was not found in {self.repository.full_name}.",
        )
        ref = parse(response, GitRef, f"the branch {branch}")
        return ref.object.sha

    def tree(self, sha: str) -> GitTree:
        """
        Return a tree, i.e. one folder, which is read once per pull request.

        Side effects: the first time that a sha is asked for, one
        ``GET /repos/{owner}/{repo}/git/trees/{sha}`` request to GitHub. The tree is then kept in
        :attr:`trees`, because several changed files may share a folder.

        :param sha: The tree's sha.
        :returns: The tree.
        :raises SmarterMCPServerToolError: If GitHub could not be reached or refused the request,
            or its response could not be read.
        """
        if sha not in self.trees:
            response = self.request("GET", f"/git/trees/{sha}", "read a folder")
            self.trees[sha] = parse(response, GitTree, "a folder")
        return self.trees[sha]

    def _find_entry(self, tree_sha: str, name: str) -> Optional[GitTreeEntry]:
        """
        Return the entry of a folder that has a name, or None if there is none.

        :param tree_sha: The folder's sha.
        :param name: The entry's name, e.g. ``models.py``.
        :returns: The first entry with the name, or None.
        :raises SmarterMCPServerToolError: If the folder could not be read (see :meth:`tree`).
        """
        folder = self.tree(tree_sha)
        for entry in folder.tree:
            if entry.path == name:
                return entry
        return None

    def existing_entry(self, root_tree: str, path: str) -> Optional[GitTreeEntry]:
        """
        Return the tree entry of a path at the base commit, or None if it does not exist.

        It walks from the root folder down the path's folders, one tree at a time, rather than
        reading the whole repository's tree recursively, which may be large.

        Side effects: one ``GET`` request to GitHub for each folder on the path that has not
        been read yet (see :meth:`tree`).

        :param root_tree: The sha of the base commit's tree.
        :param path: The path, e.g. ``smarter/smarter/apps/plugin/models.py``.
        :returns: The entry, whose mode says whether it is a file, an executable, a link or a
            folder, or None if the path, or one of its folders, does not exist.
        :raises SmarterMCPServerToolError: If a folder could not be read.
        """
        tree_sha = root_tree
        folders, name = posixpath.split(path)
        folder_names: list[str] = []
        if folders:
            folder_names = folders.split("/")
        for folder_name in folder_names:
            entry = self._find_entry(tree_sha, folder_name)
            if entry is None:
                return None
            if entry.type != "tree":
                return None
            if not entry.sha:
                return None
            tree_sha = entry.sha
        file_entry = self._find_entry(tree_sha, name)
        return file_entry

    def tree_entries(self, root_tree: str, files: list[PullRequestFile]) -> list[SmarterDictType]:
        """
        Return the entries of the new tree: each file's content and mode, or its deletion.

        Each file is compared with the base commit, so that a changed file keeps its mode, e.g.
        an executable stays executable, a new file is an ordinary file, and a folder or a
        symbolic link is never overwritten. A deletion is an entry whose ``sha`` is None.

        Side effects: ``GET`` requests to GitHub for the folders on the files' paths (see
        :meth:`existing_entry`).

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
                deletion: SmarterDictType = {
                    "path": file.path,
                    "mode": existing.mode,
                    "type": "blob",
                    "sha": None,
                }
                entries.append(deletion)
            else:
                mode = FILE_MODE
                if existing is not None:
                    mode = existing.mode
                change: SmarterDictType = {
                    "path": file.path,
                    "mode": mode,
                    "type": "blob",
                    "content": file.content,
                }
                entries.append(change)
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

        It takes the steps that the module's docstring lists, in order. The arguments were
        already checked by :func:`create_pull_request`, which documents them.

        Side effects: ``GET`` requests to GitHub for the base branch, its commit and the changed
        files' folders, then ``POST`` requests that write a tree, a commit, a new branch and the
        pull request, which notifies the repository's watchers. The new branch and the pull
        request's url are logged. Nothing is cached.

        :param branch: The new branch.
        :param base: The branch to merge into, or None for the repository's default branch.
        :param title: The pull request's title.
        :param body: The pull request's description. :data:`PULL_REQUEST_FOOTER` is appended.
        :param commit_message: The commit's message.
        :param files: The changed files.
        :param author: The commit's author and committer, or None for the token's owner.
        :param draft: Whether to open the pull request as a draft.
        :returns: The new pull request.
        :raises SmarterMCPServerToolError: If a step fails. If the branch was created, but the
            pull request was not, the error says so, so that the LLM does not create it again.
        """
        if not base:
            base = self.default_branch()
        base_sha = self.branch_commit(base)
        response = self.request("GET", f"/git/commits/{base_sha}", "read the base commit")
        base_commit = parse(response, GitCommit, "the base commit")
        base_tree_sha = base_commit.tree.sha
        entries = self.tree_entries(base_tree_sha, files)
        new_tree_request: SmarterDictType = {"base_tree": base_tree_sha, "tree": entries}
        response = self.request("POST", "/git/trees", "write the changed files", expected=201, json=new_tree_request)
        tree = parse(response, GitObject, "the new tree")
        commit: SmarterDictType = {
            "message": commit_message,
            "tree": tree.sha,
            "parents": [base_sha],
        }
        if author is not None:
            # the author also commits: the change is entirely theirs.
            commit["author"] = author.model_dump()
            commit["committer"] = author.model_dump()
        response = self.request("POST", "/git/commits", "write the commit", expected=201, json=commit)
        new_commit = parse(response, GitObject, "the new commit")
        new_branch: SmarterDictType = {"ref": f"refs/heads/{branch}", "sha": new_commit.sha}
        self.request("POST", "/git/refs", f"create the branch {branch}", expected=201, json=new_branch)
        logger.info("%s.write() created the branch %s in %s", logger_prefix, branch, self.repository.full_name)
        new_pull_request: SmarterDictType = {
            "title": title,
            "head": branch,
            "base": base,
            "body": body + PULL_REQUEST_FOOTER,
            "draft": draft,
        }
        try:
            response = self.request("POST", "/pulls", "open the pull request", expected=201, json=new_pull_request)
        except SmarterMCPServerToolError as e:
            raise SmarterMCPServerToolError(
                f"The branch {branch} was created, with the change, at {self.repository.github_url}/tree/{branch}, "
                f"but the pull request was not opened: {e.message} Do not call create_pull_request again with "
                "the same branch: open the pull request from the branch on github.com."
            ) from e
        try:
            data = response.json()
            description = {**data}
            description["author"] = author_login(data)
            description["branch"] = branch
            description["base"] = base
            description["commit_sha"] = new_commit.sha
            pull_request = GitHubPullRequest.model_validate(description)
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

    Everything that can be checked without GitHub is checked first: the token
    (:func:`~smarter.apps.mcpserver.github.client.validate_token`), the branch names, the files,
    and the text and file contents for credentials
    (:func:`~smarter.apps.mcpserver.github.client.refuse_secrets`), because the pull request is
    public. Then :meth:`PullRequestWriter.write` takes the steps that the module's docstring
    lists.

    Side effects: the requests to GitHub of :meth:`PullRequestWriter.write`, which create a new
    branch and a public pull request, as the caller. Nothing is cached: every call writes.

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
    contents: list[str] = []
    for file in files:
        if file.content is None:
            contents.append("")
        else:
            contents.append(file.content)
    refuse_secrets(value, title, body, commit_message, *contents)
    writer = PullRequestWriter(repository, value)
    pull_request = writer.write(branch, base, title, body, commit_message, files, author, draft)
    return pull_request


__all__ = [
    "GitHubCommitAuthor",
    "GitHubPullRequest",
    "PullRequestFile",
    "PullRequestWriter",
    "create_pull_request",
    "validate_branch",
    "validate_files",
]
