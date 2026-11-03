"""
Reading the index of The Smarter Project's repositories and blog: files, folders, posts and overviews.

The search service (:mod:`~smarter.apps.mcpserver.services.search`) finds what to read, and this
service reads it, from the copy that :mod:`~smarter.apps.mcpserver.services.indexing` keeps in the
database. GitHub is never asked.

- :func:`read_file`: a file of a repository, or a range of its lines, with line numbers.
- :func:`read_blog_post`: a post of the blog, or a range of its lines.
- :func:`list_files`: the folders and files directly in a folder of a repository.
- :func:`repository_overview`: what a repository contains, its top-level folders and files, and its README.
- :func:`repositories_state`: whether each repository is indexed, and at which commit.

Each function returns a Pydantic model, which the MCPServer's public tools
(:mod:`smarter.apps.mcpserver.protocol.tools.reading`) format as Markdown. A repository that is not
indexed yet is queued for indexing, and a file or post that does not exist raises
:class:`~smarter.apps.mcpserver.exceptions.SmarterMCPServerNotFoundError`, with the paths that the
caller may have meant.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

import posixpath
from datetime import datetime
from typing import Optional, Sequence

from pydantic import BaseModel, ConfigDict, Field

from smarter.apps.mcpserver.exceptions import SmarterMCPServerNotFoundError
from smarter.apps.mcpserver.models import (
    RepositoryFile,
    RepositoryFileKind,
    RepositoryIndex,
)
from smarter.apps.mcpserver.services.indexing.indexes import (
    queue_indexing,
    require_blog_index,
    require_index,
)
from smarter.apps.mcpserver.services.repositories import ProjectRepository, project_blog

MAX_READ_LINES = 400
"""The maximum number of lines of a file or post that are read at once."""

MAX_READ_CHARACTERS = 16000
"""
The maximum length of what is read at once, below the MCPClient's limit for a tool result.

The public tools also keep their results that read a schema or an issue within it.
"""

MAX_LIST_ENTRIES = 300
"""The maximum number of folders and files that a listing returns.

The rest are counted.
"""

MAX_README_CHARACTERS = 6000
"""The most characters of a README that an overview shows.

The rest is read with :func:`read_file`.
"""

README_NAMES = ("README.md", "README.rst", "readme.md", "README.txt", "README")
"""The names of a repository's top-level README, which an overview shows."""

MAX_SUGGESTIONS = 8
"""The most paths that a "not found" error suggests."""


# -----------------------------------------------------------------------------
# lines
# -----------------------------------------------------------------------------
class ReadLines(BaseModel):
    """The lines of a file that :func:`read_lines` selected."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    start: int = Field(description="The first line, from 1.")
    end: int = Field(description="The last line.")
    total: int = Field(description="The file's number of lines.")
    text: str = Field(description="The lines, each prefixed with its number.")

    @property
    def is_complete(self) -> bool:
        """Whether the last line of the file was read."""
        return self.end >= self.total


def read_lines(content: str, start_line: int, end_line: Optional[int]) -> ReadLines:
    """
    Return a range of a file's lines, with line numbers, within :data:`MAX_READ_LINES` and :data:`MAX_READ_CHARACTERS`.

    A start after the last line reads the last line. The range ends early, but always has at least
    one line, when its text would exceed :data:`MAX_READ_CHARACTERS`, so that the result fits in a
    tool result: the caller then reads on from ``end + 1``.

    :param content: The file's content.
    :param start_line: The first line to read, from 1.
    :param end_line: The last line to read, or None to read as many as allowed.
    :returns: The lines.
    """
    lines = content.splitlines()
    total = len(lines)
    start = min(start_line, max(total, 1))
    last_allowed = start + MAX_READ_LINES - 1
    requested_end = end_line
    if not requested_end:
        requested_end = last_allowed
    end = min(requested_end, last_allowed, total)
    width = len(str(end))
    selected: list[str] = []
    characters = 0
    for number in range(start, end + 1):
        text = f"{number:>{width}}  {lines[number - 1]}"
        characters += len(text) + 1
        if characters > MAX_READ_CHARACTERS and selected:
            end = number - 1
            break
        selected.append(text)
    joined = "\n".join(selected)
    read = ReadLines(start=start, end=end, total=total, text=joined)
    return read


def suggested_paths(index: RepositoryIndex, order_by: str, **path_filter: str) -> list[str]:
    """
    Return up to :data:`MAX_SUGGESTIONS` paths of an index's files that match a filter.

    **Side effects:** one database query.

    :param index: The index.
    :param order_by: The field to order the paths by, e.g. ``path`` or ``-path``.
    :param path_filter: The lookup to filter the files by, e.g. ``path__icontains="tasks.py"``.
    :returns: The paths.
    """
    files = RepositoryFile.objects.filter(index=index, **path_filter).order_by(order_by)
    paths = files.values_list("path", flat=True)[:MAX_SUGGESTIONS]
    return list(paths)


# -----------------------------------------------------------------------------
# files
# -----------------------------------------------------------------------------
class FileLines(BaseModel):
    """Lines of a file of a repository, as :func:`read_file` returns them, with where to find the file."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    repository: str = Field(description="The repository's name.")
    path: str = Field(description="The file's path in the repository.")
    lines: ReadLines = Field(description="The lines that were read.")
    github_url: str = Field(description="The file's GitHub url, at the indexed commit, highlighting the lines.")
    documentation_url: Optional[str] = Field(
        default=None, description="The file's published documentation page, if it is one."
    )


def file_not_found(index: RepositoryIndex, repository: ProjectRepository, path: str) -> SmarterMCPServerNotFoundError:
    """
    Return the error for a file that does not exist, with the files that the caller may have meant.

    The suggestions are the files with the same name, or else the files whose path contains it.

    **Side effects:** one or two database queries.

    :param index: The repository's index.
    :param repository: The repository.
    :param path: The path that was not found.
    :returns: The error, for the caller to raise.
    """
    basename = posixpath.basename(path)
    suggestions = suggested_paths(index, "path", path__iendswith="/" + basename)
    if not suggestions:
        suggestions = suggested_paths(index, "path", path__icontains=basename)
    message = f"{path} is not a file of {repository.name}, or is not indexed."
    if suggestions:
        message += " Did you mean: " + ", ".join(suggestions) + "?"
    error = SmarterMCPServerNotFoundError(message, suggestions)
    return error


def read_file(
    repository: ProjectRepository, path: str, start_line: int = 1, end_line: Optional[int] = None
) -> FileLines:
    """
    Read a file of a repository, or a range of its lines.

    **Side effects:** database queries, and, for a repository that is not indexed yet, a Celery task
    queued to index it.

    :param repository: The repository.
    :param path: The file's path in the repository, e.g. ``README.md``. A leading slash is ignored.
    :param start_line: The first line to read, from 1.
    :param end_line: The last line to read, or None to read as many as :func:`read_lines` allows.
    :returns: The lines, and the file's GitHub url and documentation page.
    :raises SmarterMCPServerServiceError: If the repository is not indexed yet.
    :raises SmarterMCPServerNotFoundError: If the repository has no such file.
    """
    index = require_index(repository)
    clean_path = path.strip().lstrip("/")
    files = RepositoryFile.objects.filter(index=index, path=clean_path)
    row = files.values("content").first()
    if row is None:
        raise file_not_found(index, repository, clean_path)
    lines = read_lines(row["content"], start_line, end_line)
    github_url = repository.file_url(index.commit_sha, clean_path, lines.start, lines.end)
    documentation_url = repository.documentation_url(clean_path)
    file_lines = FileLines(
        repository=repository.name,
        path=clean_path,
        lines=lines,
        github_url=github_url,
        documentation_url=documentation_url,
    )
    return file_lines


# -----------------------------------------------------------------------------
# folders
# -----------------------------------------------------------------------------
class FolderEntry(BaseModel):
    """A folder or a file directly in a folder of a repository."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(description="The folder's or file's name.")
    is_folder: bool = Field(description="Whether it is a folder.")
    files: int = Field(default=0, description="For a folder, the number of indexed files under it.")
    size: int = Field(default=0, description="For a file, its size in bytes.")


class FolderListing(BaseModel):
    """The folders and files directly in a folder of a repository, as :func:`list_files` returns them."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    repository: str = Field(description="The repository's name.")
    folder: str = Field(description="The folder, or an empty string for the top level.")
    github_url: str = Field(description="The folder's GitHub url, at the indexed commit.")
    entries: list[FolderEntry] = Field(description="The folders, then the files, each sorted by name.")
    hidden: int = Field(default=0, description=f"The entries left out, beyond the first {MAX_LIST_ENTRIES}.")


def folder_entries(index: RepositoryIndex, folder: str) -> tuple[list[FolderEntry], int]:
    """
    Return the folders and files directly in a folder of an index.

    Only indexed files are listed, so a folder of only binaries or vendored files does not appear.

    **Side effects:** one database query, of the paths and sizes of the files under the folder.

    :param index: The repository's index.
    :param folder: The folder, or an empty string for the top level.
    :returns: The folders, with the number of files under each, then the files, with their sizes,
        each sorted by name, at most :data:`MAX_LIST_ENTRIES`, and the number of entries left out.
    """
    folder = folder.strip("/")
    prefix = ""
    if folder:
        prefix = folder + "/"
    folder_counts: dict[str, int] = {}
    file_sizes: list[tuple[str, int]] = []
    files = RepositoryFile.objects.filter(index=index, path__startswith=prefix)
    rows = files.values_list("path", "size")
    for path, size in rows:
        rest = path[len(prefix) :]
        if "/" in rest:
            name = rest.split("/", 1)[0]
            folder_counts[name] = folder_counts.get(name, 0) + 1
        else:
            file_sizes.append((rest, size))

    entries = []
    for name, count in sorted(folder_counts.items()):
        entries.append(FolderEntry(name=name, is_folder=True, files=count))
    for name, size in sorted(file_sizes):
        entries.append(FolderEntry(name=name, is_folder=False, size=size))
    hidden = 0
    if len(entries) > MAX_LIST_ENTRIES:
        hidden = len(entries) - MAX_LIST_ENTRIES
        entries = entries[:MAX_LIST_ENTRIES]
    return entries, hidden


def list_files(repository: ProjectRepository, folder: Optional[str] = None) -> FolderListing:
    """
    List the folders and indexed files directly in a folder of a repository.

    **Side effects:** database queries, and, for a repository that is not indexed yet, a Celery task
    queued to index it.

    :param repository: The repository.
    :param folder: The folder, e.g. ``smarter/smarter/apps``, or None for the top level.
    :returns: The folder's entries and GitHub url.
    :raises SmarterMCPServerServiceError: If the repository is not indexed yet.
    :raises SmarterMCPServerNotFoundError: If the folder has no indexed files.
    """
    index = require_index(repository)
    clean_folder = ""
    if folder:
        clean_folder = folder.strip().strip("/")
    entries, hidden = folder_entries(index, clean_folder)
    if not entries:
        message = f"{clean_folder} is not a folder of {repository.name}, or has no indexed files."
        raise SmarterMCPServerNotFoundError(message, [])
    github_url = f"{repository.github_url}/tree/{index.commit_sha}/{clean_folder}"
    listing = FolderListing(
        repository=repository.name,
        folder=clean_folder,
        github_url=github_url,
        entries=entries,
        hidden=hidden,
    )
    return listing


# -----------------------------------------------------------------------------
# repositories
# -----------------------------------------------------------------------------
class RepositoryOverview(BaseModel):
    """What a repository contains, as :func:`repository_overview` returns it."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    repository: ProjectRepository = Field(description="The repository.")
    commit_sha: str = Field(description="The indexed commit.")
    indexed_at: datetime = Field(description="When the repository was indexed.")
    file_count: int = Field(description="The number of indexed files.")
    documentation_files: int = Field(description="The number of indexed files of documentation.")
    code_files: int = Field(description="The number of indexed files of code.")
    top_level: list[FolderEntry] = Field(description="The top-level folders and files.")
    top_level_hidden: int = Field(default=0, description="The top-level entries left out.")
    readme_path: Optional[str] = Field(default=None, description="The path of the top-level README, if any.")
    readme: str = Field(default="", description=f"The README's first {MAX_README_CHARACTERS} characters.")
    readme_truncated: bool = Field(default=False, description="Whether the README is longer than what is shown.")


def repository_overview(repository: ProjectRepository) -> RepositoryOverview:
    """
    Describe a repository: its indexed commit, its numbers of files, its top-level folders and files, and its README.

    **Side effects:** database queries, and, for a repository that is not indexed yet, a Celery task
    queued to index it.

    :param repository: The repository.
    :returns: The overview.
    :raises SmarterMCPServerServiceError: If the repository is not indexed yet.
    """
    index = require_index(repository)
    files = RepositoryFile.objects.filter(index=index)
    documentation_files = files.filter(kind=RepositoryFileKind.DOCUMENTATION).count()
    code_files = index.file_count - documentation_files
    top_level, top_level_hidden = folder_entries(index, "")

    readme_path = None
    readme = ""
    readme_truncated = False
    readmes = files.filter(path__in=README_NAMES).order_by("path")
    readme_row = readmes.values_list("path", "content").first()
    if readme_row:
        readme_path, content = readme_row
        readme = content[:MAX_README_CHARACTERS]
        readme_truncated = len(content) > MAX_README_CHARACTERS

    overview = RepositoryOverview(
        repository=repository,
        commit_sha=index.commit_sha or "",
        indexed_at=index.indexed_at,
        file_count=index.file_count,
        documentation_files=documentation_files,
        code_files=code_files,
        top_level=top_level,
        top_level_hidden=top_level_hidden,
        readme_path=readme_path,
        readme=readme,
        readme_truncated=readme_truncated,
    )
    return overview


class RepositoryState(BaseModel):
    """Whether a repository is indexed, and at which commit, as :func:`repositories_state` returns it."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    repository: ProjectRepository = Field(description="The repository.")
    is_indexed: bool = Field(description="Whether its index is ready to read.")
    commit_sha: str = Field(default="", description="The indexed commit, or an empty string.")
    file_count: int = Field(default=0, description="The number of indexed files.")


def repositories_state(repositories: Sequence[ProjectRepository]) -> list[RepositoryState]:
    """
    Return whether each repository is indexed, and queue those that are not for indexing.

    **Side effects:** one database query, and a Celery task queued for each repository that is not
    indexed yet (see :func:`~smarter.apps.mcpserver.services.indexing.indexes.queue_indexing`).

    :param repositories: The repositories, in the order to return them.
    :returns: One state per repository, in the same order.
    """
    names = [repository.name for repository in repositories]
    indexes = {}
    for index in RepositoryIndex.objects.filter(repository__in=names):
        indexes[index.repository] = index

    states = []
    for repository in repositories:
        index = indexes.get(repository.name)
        if index is not None and index.is_ready:
            state = RepositoryState(
                repository=repository,
                is_indexed=True,
                commit_sha=index.commit_sha or "",
                file_count=index.file_count,
            )
        else:
            queue_indexing(repository)
            state = RepositoryState(repository=repository, is_indexed=False)
        states.append(state)
    return states


# -----------------------------------------------------------------------------
# the blog
# -----------------------------------------------------------------------------
class PostLines(BaseModel):
    """Lines of a post of the blog, as :func:`read_blog_post` returns them."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    path: str = Field(description="The post's path, e.g. 2026/10/26/release-smarter-api-v0-6.")
    url: str = Field(description="The post's url.")
    lines: ReadLines = Field(description="The lines that were read.")


def read_blog_post(path: str, start_line: int = 1, end_line: Optional[int] = None) -> PostLines:
    """
    Read a post of the blog, or a range of its lines, by its path or its url.

    **Side effects:** database queries, and, if the blog is not indexed yet, a Celery task queued to
    index it.

    :param path: The post's path, e.g. ``2026/10/26/release-smarter-api-v0-6``, or its url.
    :param start_line: The first line to read, from 1.
    :param end_line: The last line to read, or None to read as many as :func:`read_lines` allows.
    :returns: The lines, and the post's url.
    :raises SmarterMCPServerServiceError: If the blog is not indexed yet.
    :raises SmarterMCPServerNotFoundError: If the blog has no such post. The error suggests the
        posts with the same slug.
    """
    blog = project_blog()
    index = require_blog_index(blog)
    post_path = blog.post_path(path)
    posts = RepositoryFile.objects.filter(index=index, path=post_path)
    row = posts.values("content").first()
    if row is None:
        slug = post_path.rsplit("/", 1)[-1]
        suggestions = []
        if slug:
            suggestions = suggested_paths(index, "-path", path__icontains=slug)
        message = f"{post_path} is not a post of the blog, {blog.url}."
        if suggestions:
            message += " Did you mean: " + ", ".join(suggestions) + "?"
        raise SmarterMCPServerNotFoundError(message, suggestions)
    lines = read_lines(row["content"], start_line, end_line)
    post_lines = PostLines(path=post_path, url=blog.post_url(post_path), lines=lines)
    return post_lines


__all__ = [
    "MAX_LIST_ENTRIES",
    "MAX_READ_CHARACTERS",
    "MAX_READ_LINES",
    "MAX_README_CHARACTERS",
    "FileLines",
    "FolderEntry",
    "FolderListing",
    "PostLines",
    "ReadLines",
    "RepositoryOverview",
    "RepositoryState",
    "folder_entries",
    "list_files",
    "read_blog_post",
    "read_file",
    "read_lines",
    "repositories_state",
    "repository_overview",
    "suggested_paths",
]
