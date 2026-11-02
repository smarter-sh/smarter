"""
The tools that answer from the index of the repositories and the blog.

The Smarter Project MCP server offers these tools to an LLM, which calls them to answer questions
about The Smarter Project from its own copy of the repositories' files and the blog's posts. The
copy is made by :mod:`smarter.apps.mcpserver.index.indexer` and
:mod:`smarter.apps.mcpserver.index.blog`, and searched by :mod:`smarter.apps.mcpserver.index.search`:

- ``get_repository_overview``: what a repository contains, its layout, and its README.
- ``search_documentation``: ranked passages of the documentation.
- ``search_code``: ranked files of source code, with their matching lines.
- ``read_file``: a file, or a range of its lines, with line numbers.
- ``list_files``: the folders and files under a folder.
- ``search_blog``: ranked passages of the posts of the blog, blog.smarter.sh.
- ``read_blog_post``: a post of the blog, with line numbers.

The blog's tools have no ``repository`` argument, and only the MCP server of all of the
repositories serves them. A tool that is called on a repository that is not indexed yet
says so, and queues the repository for indexing, with a Celery task. Every tool is read-only,
so :meth:`~smarter.apps.mcpserver.protocol.tools.SmarterProjectTool.call` caches its results until
an index changes.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

import posixpath
from typing import ClassVar, Optional, Sequence, cast

from cache_results import lazy_cache
from pydantic import BaseModel, ConfigDict, Field

from smarter.apps.mcpserver.exceptions import SmarterMCPServerToolError
from smarter.apps.mcpserver.index.search import SearchHit, SearchLine, search_files
from smarter.apps.mcpserver.models import (
    RepositoryFile,
    RepositoryFileKind,
    RepositoryIndex,
)
from smarter.apps.mcpserver.protocol.tools import (
    DEFAULT_SEARCH_LIMIT,
    MAX_READ_CHARACTERS,
    MAX_SEARCH_LIMIT,
    SmarterProjectTool,
    ToolArguments,
)
from smarter.apps.mcpserver.repositories import (
    SMARTER_PROJECT_DOCS_LATEST_URL,
    ProjectBlog,
    ProjectRepository,
    ProjectSource,
    project_blog,
)

MAX_READ_LINES = 400
"""The maximum number of lines that read_file and read_blog_post return at once."""

MAX_LIST_ENTRIES = 300
"""The maximum number of folders and files that list_files returns.

The rest are counted.
"""

MAX_README_CHARACTERS = 6000
"""The most characters of a README that get_repository_overview shows.

The rest is read with read_file.
"""

README_NAMES = ("README.md", "README.rst", "readme.md", "README.txt", "README")
"""The names of a repository's top-level README, which get_repository_overview shows."""

INDEX_QUEUE_TIMEOUT = 600
"""Seconds during which a repository that is not indexed is queued for indexing only once."""

MAX_SUGGESTIONS = 8
"""The most paths that a "not found" error suggests."""

CODE_FENCE_LANGUAGES = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".js": "javascript",
    ".jsx": "jsx",
    ".go": "go",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".sh": "bash",
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
    ".tf": "hcl",
    ".hcl": "hcl",
    ".sql": "sql",
    ".rst": "rst",
    ".md": "markdown",
}
"""The language of a Markdown code fence, by file extension, so that a client highlights the code.

Others are ``text``.
"""


def queue_indexing_key(name: str) -> str:
    """
    Return the cache key that remembers that a repository was queued for indexing.

    :param name: The repository's name, or the blog's.
    :returns: The key.
    """
    return f"smarter.apps.mcpserver.index.tools.queue_indexing.{name}"


def queue_indexing(repository: ProjectSource) -> None:
    """
    Queue a repository, or the blog, that is not indexed for indexing, at most once every :data:`INDEX_QUEUE_TIMEOUT` seconds.

    Many tool calls may find the same repository not indexed while it is being indexed, so a cache
    key, added only if it is missing, makes sure that only the first of them queues a task.

    Side effects: a cache write, and, if the key was not there, a Celery task queued:
    :func:`smarter.apps.mcpserver.tasks.index_blog` or :func:`smarter.apps.mcpserver.tasks.index_repository`.

    :param repository: The repository, or the blog.
    """
    # pylint: disable=import-outside-toplevel
    from smarter.apps.mcpserver.tasks import index_blog, index_repository

    key = queue_indexing_key(repository.name)
    is_first = lazy_cache.add(key, True, timeout=INDEX_QUEUE_TIMEOUT)
    if not is_first:
        return
    if isinstance(repository, ProjectBlog):
        index_blog.delay()
    else:
        index_repository.delay(repository.name)


def ready_indexes(repositories: Sequence[ProjectSource]) -> dict[str, RepositoryIndex]:
    """
    Return the indexes of the repositories that are ready to search, and queue the others for indexing.

    Side effects: one database query, and :func:`queue_indexing` for each repository that is not ready.

    :param repositories: The repositories, or the blog.
    :returns: The ready indexes, by repository name.
    """
    names = [repository.name for repository in repositories]
    indexes = {}
    for index in RepositoryIndex.objects.filter(repository__in=names):
        indexes[index.repository] = index

    ready = {}
    for repository in repositories:
        index = indexes.get(repository.name)
        if index is not None and index.is_ready:
            ready[repository.name] = index
        else:
            queue_indexing(repository)
    return ready


def require_index(repository: ProjectRepository) -> RepositoryIndex:
    """
    Return a repository's index.

    Side effects: see :func:`ready_indexes`.

    :param repository: The repository.
    :returns: Its index.
    :raises SmarterMCPServerToolError: If the repository is not indexed yet. It is then queued for indexing.
    """
    ready = ready_indexes([repository])
    index = ready.get(repository.name)
    if index is None:
        raise SmarterMCPServerToolError(
            f"{repository.name} has not been indexed yet. Indexing has started: try again in a few minutes."
        )
    return index


def not_indexed_note(repositories: list[ProjectRepository], ready: dict[str, RepositoryIndex]) -> str:
    """
    Return a note that names the repositories that were not searched because they are not indexed yet.

    :param repositories: The repositories that the search was asked to search.
    :param ready: The indexes that were ready, by repository name, from :func:`ready_indexes`.
    :returns: The note, which starts with a blank line, or an empty string if every repository was searched.
    """
    missing = []
    for repository in repositories:
        if repository.name not in ready:
            missing.append(repository.name)
    if not missing:
        return ""
    names = ", ".join(missing)
    return f"\n\nNot searched, because they are still being indexed: {names}. Try again in a few minutes."


def code_fence_language(path: str) -> str:
    """
    Return the Markdown code fence language of a file.

    :param path: The file's path.
    :returns: The language, from :data:`CODE_FENCE_LANGUAGES`, or ``text``.
    """
    extension = posixpath.splitext(path)[1].lower()
    return CODE_FENCE_LANGUAGES.get(extension, "text")


def numbered_excerpt(lines: list[SearchLine]) -> str:
    """
    Return a hit's lines, each after its line number, right-aligned, for a code block.

    :param lines: The hit's lines.
    :returns: The lines, e.g. `` 9  text`` and ``10  text``.
    """
    width = 1
    if lines:
        width = len(str(lines[-1].number))
    numbered = [f"{line.number:>{width}}  {line.text}" for line in lines]
    return "\n".join(numbered)


def suggested_paths(index: RepositoryIndex, order_by: str, **path_filter: str) -> list[str]:
    """
    Return up to :data:`MAX_SUGGESTIONS` paths of an index's files that match a filter.

    Side effects: one database query.

    :param index: The index.
    :param order_by: The field to order the paths by, e.g. ``path`` or ``-path``.
    :param path_filter: The lookup to filter the files by, e.g. ``path__icontains="tasks.py"``.
    :returns: The paths.
    """
    files = RepositoryFile.objects.filter(index=index, **path_filter).order_by(order_by)
    paths = files.values_list("path", flat=True)[:MAX_SUGGESTIONS]
    return list(paths)


# -----------------------------------------------------------------------------
# get_repository_overview
# -----------------------------------------------------------------------------
class GetRepositoryOverviewTool(SmarterProjectTool):
    """
    The ``get_repository_overview`` tool: what a repository contains, how it is laid out, and its README.

    Without a repository, it lists every repository of the server, with whether each is indexed.
    """

    name = "get_repository_overview"
    title = "Repository overview"
    description = (
        "Describe a repository of The Smarter Project: what it contains, its GitHub url, its indexed "
        "commit, its top-level folders and files, and its README. Use it for questions about a repository "
        "as a whole, not to answer a specific question, which the search tools answer directly."
    )

    def run(self, arguments: ToolArguments) -> str:
        """
        Describe the named repository, or list them all if none is named.

        Side effects: database queries, and, for a repository that is not indexed yet, a Celery task
        queued to index it (see :func:`queue_indexing`).

        :param arguments: The validated arguments.
        :returns: The overview, as Markdown.
        :raises SmarterMCPServerToolError: If the repository is not one of the server's, or is not indexed yet.
        """
        repository = self.scope.resolve(arguments.repository, required=False)
        if repository is None:
            return self.all_repositories()
        index = require_index(repository)
        files = RepositoryFile.objects.filter(index=index)
        documentation = files.filter(kind=RepositoryFileKind.DOCUMENTATION).count()
        code = index.file_count - documentation
        top_level = ListFilesTool(self.scope).entries(index, "")

        parts = [
            f"# {repository.name}: {repository.title}",
            repository.description,
            f"- GitHub: {repository.github_url}",
        ]
        if repository.docs_url:
            parts.append(f"- Published documentation: {repository.docs_url}, built from {repository.docs_root}/")
        parts.append(
            f"- Indexed commit: {index.commit_sha} of {repository.ref}, "
            f"{index.indexed_at:%Y-%m-%d %H:%M} UTC: {index.file_count} files, "
            f"{documentation} of documentation and {code} of code"
        )
        parts.append("\n## Top-level folders and files\n\n" + "\n".join(top_level))

        readmes = files.filter(path__in=README_NAMES).order_by("path")
        readme = readmes.values_list("path", "content").first()
        if readme:
            path, content = readme
            excerpt = content[:MAX_README_CHARACTERS]
            if len(content) > MAX_README_CHARACTERS:
                excerpt += f"\n\n[README truncated: read the rest with read_file, path {path}]"
            parts.append(f"\n## {path}\n\n{excerpt}")
        return "\n".join(parts)

    def all_repositories(self) -> str:
        """
        Return a table of every repository of the scope, with whether each one is indexed.

        Side effects: one database query, and a Celery task queued for each repository that is not
        indexed yet (see :func:`queue_indexing`).

        :returns: The table, as Markdown, and where the documentation and the blog are.
        """
        indexes = {}
        for index in RepositoryIndex.objects.filter(repository__in=self.scope.names):
            indexes[index.repository] = index

        rows = ["| Repository | Contents | Indexed |", "| --- | --- | --- |"]
        for repository in self.scope.repositories:
            index = indexes.get(repository.name)
            if index is not None and index.is_ready:
                commit_sha = index.commit_sha or ""
                indexed = f"{commit_sha[:7]}, {index.file_count} files"
            else:
                indexed = "not yet"
                queue_indexing(repository)
            rows.append(f"| [{repository.name}]({repository.github_url}) | {repository.description} | {indexed} |")

        table = "\n".join(rows)
        overview = (
            "# The Smarter Project's repositories\n\n"
            + table
            + f"\n\nThe documentation, {SMARTER_PROJECT_DOCS_LATEST_URL}, is built from the smarter "
            f"repository's docs/source. The blog, {project_blog().url}, is searched with search_blog. "
            "Name a repository to see its layout and README."
        )
        return overview


# -----------------------------------------------------------------------------
# search_documentation, search_code
# -----------------------------------------------------------------------------
class SearchArguments(ToolArguments):
    """The arguments of search_documentation and search_blog, and the base of those of search_code."""

    query: str = Field(
        min_length=1,
        max_length=500,
        description='Keywords, identifiers or "quoted phrases", e.g. custom domain verification.',
    )
    limit: int = Field(
        default=DEFAULT_SEARCH_LIMIT, ge=1, le=MAX_SEARCH_LIMIT, description="The maximum number of results."
    )


class SearchCodeArguments(SearchArguments):
    """The arguments of search_code: those of search_documentation, and a folder to search under."""

    path: Optional[str] = Field(
        default=None,
        max_length=512,
        description="Only search files under this folder, e.g. smarter/smarter/apps/llmclient.",
    )


class SearchTool(SmarterProjectTool):
    """
    The base class of the search tools of the repositories, ``search_documentation`` and ``search_code``.

    A subclass sets which kind of file it searches, and the noun that its results call them.
    """

    kind: ClassVar[str]
    """The kind of file that the tool searches, a :class:`~smarter.apps.mcpserver.models.RepositoryFileKind`."""

    noun: ClassVar[str]
    """What the tool's results call the files, e.g. ``documentation`` or ``code``."""

    def search(self, arguments: SearchArguments, path: Optional[str] = None) -> str:
        """
        Search the scope's repositories, and return the hits as Markdown.

        The named repository is searched, or else every repository of the scope. A repository that is
        not indexed yet is queued for indexing, and named in a note after the results.

        Side effects: database queries, and Celery tasks queued (see :func:`ready_indexes`).

        :param arguments: The validated arguments.
        :param path: Only search files under this folder, or None to search them all.
        :returns: The hits, best first, as Markdown, or a message that nothing matches.
        :raises SmarterMCPServerToolError: If the repository is not one of the server's, or no repository
            to search is indexed yet.
        """
        repository = self.scope.resolve(arguments.repository, required=False)
        if repository:
            repositories = [repository]
            where = repository.name
        else:
            repositories = list(self.scope.repositories)
            where = "The Smarter Project's repositories"
        ready = ready_indexes(repositories)
        if not ready:
            names = ", ".join(r.name for r in repositories)
            raise SmarterMCPServerToolError(
                f"{names} has not been indexed yet. Indexing has started: try again in a few minutes."
            )
        searchable = [r for r in repositories if r.name in ready]
        hits = search_files(
            searchable,
            arguments.query,
            kind=self.kind,
            path=path,
            limit=arguments.limit,
        )
        note = not_indexed_note(repositories, ready)
        if not hits:
            message = (
                f'No {self.noun} of {where} matches "{arguments.query}". Try other keywords, an identifier, '
                "or the other search tool." + note
            )
            return message
        formatted_hits = [self.format_hit(number, hit) for number, hit in enumerate(hits, start=1)]
        results = "\n\n".join(formatted_hits)
        answer = (
            f'{len(hits)} results in the {self.noun} of {where}, for "{arguments.query}", best first. '
            f"Read a file with read_file to see more of it.\n\n{results}" + note
        )
        return answer

    def format_hit(self, number: int, hit: SearchHit) -> str:
        """
        Return one hit, as Markdown: a numbered heading, its links, and its lines in a code block.

        :param number: The hit's rank, from 1.
        :param hit: The hit.
        :returns: The Markdown. The heading names the repository on the server of all of them.
        """
        if hit.title:
            heading = f"{number}. **{hit.title}** `{hit.path}`"
        else:
            heading = f"{number}. `{hit.path}`"
        if not self.scope.is_single:
            heading += f" in {hit.repository}"
        links = []
        if hit.documentation_url:
            links.append(f"   Documentation: {hit.documentation_url}")
        links.append(f"   Source: {hit.url}")
        excerpt = numbered_excerpt(hit.lines)
        fence = "text"
        if hit.kind == RepositoryFileKind.CODE:
            fence = code_fence_language(hit.path)
        markdown = f"{heading}\n" + "\n".join(links) + f"\n\n```{fence}\n{excerpt}\n```"
        return markdown


class SearchDocumentationTool(SearchTool):
    """The ``search_documentation`` tool: ranked passages of the repositories' documentation."""

    name = "search_documentation"
    title = "Search documentation"
    description = (
        "Search the documentation of The Smarter Project: the Sphinx documentation published at "
        "docs.smarter.sh, READMEs, and other reStructuredText and Markdown files. Returns the best "
        "passages, with links to the published page and to the source. Use it for concepts, features, "
        "configuration, installation and how-to questions."
    )
    arguments_model = SearchArguments
    kind = RepositoryFileKind.DOCUMENTATION
    noun = "documentation"

    def run(self, arguments: ToolArguments) -> str:
        """
        Search the documentation (see :meth:`SearchTool.search`).

        :param arguments: The validated arguments, a :class:`SearchArguments`.
        :returns: The hits, as Markdown.
        """
        return self.search(cast(SearchArguments, arguments))


class SearchCodeTool(SearchTool):
    """The ``search_code`` tool: ranked files of the repositories' source code, with their matching lines."""

    name = "search_code"
    title = "Search code"
    description = (
        "Search the source code and configuration of The Smarter Project: Python, TypeScript, Go, YAML "
        "manifests, Helm charts, Terraform and more. Returns the best files, with their matching lines "
        "and GitHub links. Use it for how something is implemented, and to find a class, function, "
        "setting or manifest field by name."
    )
    arguments_model = SearchCodeArguments
    kind = RepositoryFileKind.CODE
    noun = "code"

    def run(self, arguments: ToolArguments) -> str:
        """
        Search the code, under the folder that the arguments name, if any (see :meth:`SearchTool.search`).

        :param arguments: The validated arguments, a :class:`SearchCodeArguments`.
        :returns: The hits, as Markdown.
        """
        search_arguments = cast(SearchCodeArguments, arguments)
        return self.search(search_arguments, path=search_arguments.path)


# -----------------------------------------------------------------------------
# read_file
# -----------------------------------------------------------------------------
class ReadLines(BaseModel):
    """The lines of a file that :func:`read_lines` selected."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    start: int = Field(description="The first line, from 1.")
    end: int = Field(description="The last line.")
    total: int = Field(description="The file's number of lines.")
    text: str = Field(description="The lines, each prefixed with its number.")


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
    return ReadLines(start=start, end=end, total=total, text="\n".join(selected))


def continuation(tool_name: str, noun: str, lines: ReadLines) -> str:
    """
    Return the note that tells the LLM how to read the rest of a file or post.

    :param tool_name: The tool that reads on, e.g. ``read_file``.
    :param noun: What is read, e.g. ``file`` or ``post``.
    :param lines: The lines that were read.
    :returns: The note, which starts with a blank line, or an empty string if the last line was read.
    """
    if lines.end >= lines.total:
        return ""
    next_line = lines.end + 1
    return f"\n\nThe {noun} continues: call {tool_name} with start_line={next_line}."


class ReadFileArguments(ToolArguments):
    """The arguments of read_file."""

    path: str = Field(min_length=1, max_length=512, description="The file's path in the repository, e.g. README.md.")
    start_line: int = Field(default=1, ge=1, description="The first line to read.")
    end_line: Optional[int] = Field(
        default=None, ge=1, description=f"The last line to read. At most {MAX_READ_LINES} lines are read at once."
    )


class ReadFileTool(SmarterProjectTool):
    """The ``read_file`` tool: a file of a repository, or a range of its lines, with line numbers."""

    name = "read_file"
    title = "Read file"
    description = (
        "Read a file of a repository of The Smarter Project, with line numbers, from the paths that the "
        f"search tools and list_files return. Long files are read {MAX_READ_LINES} lines at a time: use "
        "start_line and end_line to read more."
    )
    arguments_model = ReadFileArguments
    requires_repository = True

    def run(self, arguments: ToolArguments) -> str:
        """
        Read the lines of the file that the arguments name.

        The result starts with the file's GitHub url at the indexed commit, and its published
        documentation page, if it is one.

        Side effects: database queries, and, for a repository that is not indexed yet, a Celery task
        queued to index it.

        :param arguments: The validated arguments, a :class:`ReadFileArguments`.
        :returns: The lines, in a code block, as Markdown.
        :raises SmarterMCPServerToolError: If the repository is not indexed yet, or has no such file.
            The error suggests files with a similar path.
        """
        arguments = cast(ReadFileArguments, arguments)
        repository = cast(ProjectRepository, self.scope.resolve(arguments.repository, required=True))
        index = require_index(repository)
        path = arguments.path.strip().lstrip("/")
        row = RepositoryFile.objects.filter(index=index, path=path).values("content", "line_count").first()
        if row is None:
            raise SmarterMCPServerToolError(self.not_found(index, repository, path))
        lines = read_lines(row["content"], arguments.start_line, arguments.end_line)
        github_url = repository.file_url(index.commit_sha, path, lines.start, lines.end)
        header = f"{repository.name}/{path}, lines {lines.start}-{lines.end} of {lines.total}\n{github_url}"
        documentation_url = repository.documentation_url(path)
        if documentation_url:
            header += f"\nPublished at {documentation_url}"
        footer = continuation("read_file", "file", lines)
        language = code_fence_language(path)
        return f"{header}\n\n```{language}\n{lines.text}\n```{footer}"

    def not_found(self, index: RepositoryIndex, repository: ProjectRepository, path: str) -> str:
        """
        Return an error message that suggests the files that the LLM may have meant.

        The suggestions are the files with the same name, or else the files whose path contains it.

        Side effects: one or two database queries.

        :param index: The repository's index.
        :param repository: The repository.
        :param path: The path that was not found.
        :returns: The message.
        """
        basename = posixpath.basename(path)
        suggestions = suggested_paths(index, "path", path__iendswith="/" + basename)
        if not suggestions:
            suggestions = suggested_paths(index, "path", path__icontains=basename)
        message = f"{path} is not a file of {repository.name}, or is not indexed."
        if suggestions:
            message += " Did you mean: " + ", ".join(suggestions) + "?"
        else:
            message += " Use list_files or search_code to find it."
        return message


# -----------------------------------------------------------------------------
# list_files
# -----------------------------------------------------------------------------
class ListFilesArguments(ToolArguments):
    """The arguments of list_files."""

    path: Optional[str] = Field(
        default=None,
        max_length=512,
        description="The folder, e.g. smarter/smarter/apps. Omit it for the repository's top-level folder.",
    )


class ListFilesTool(SmarterProjectTool):
    """
    The ``list_files`` tool: the folders and indexed files directly in a folder of a repository.

    Only indexed files are listed, so a folder of only binaries or vendored files does not appear.
    """

    name = "list_files"
    title = "List files"
    description = (
        "List the folders and indexed files in a folder of a repository of The Smarter Project, with the "
        "number of files in each folder. Use it to explore a repository's layout."
    )
    arguments_model = ListFilesArguments
    requires_repository = True

    def entries(self, index: RepositoryIndex, folder: str) -> list[str]:
        """
        Return the folders and files directly in a folder, as Markdown list items.

        Side effects: one database query, of the paths and sizes of the files under the folder.

        :param index: The repository's index.
        :param folder: The folder, or an empty string for the top level.
        :returns: The folders, with the number of files under each, then the files, with their sizes,
            each sorted by name, at most :data:`MAX_LIST_ENTRIES`, and a last item that counts the rest.
        """
        folder = folder.strip("/")
        prefix = ""
        if folder:
            prefix = folder + "/"
        folders: dict[str, int] = {}
        files: list[tuple[str, int]] = []
        rows = RepositoryFile.objects.filter(index=index, path__startswith=prefix).values_list("path", "size")
        for path, size in rows:
            rest = path[len(prefix) :]
            if "/" in rest:
                name = rest.split("/", 1)[0]
                folders[name] = folders.get(name, 0) + 1
            else:
                files.append((rest, size))

        items = []
        for name, count in sorted(folders.items()):
            items.append(f"- {name}/ ({count} files)")
        for name, size in sorted(files):
            items.append(f"- {name} ({size} bytes)")
        if len(items) > MAX_LIST_ENTRIES:
            hidden = len(items) - MAX_LIST_ENTRIES
            items = items[:MAX_LIST_ENTRIES]
            items.append(f"- ... and {hidden} more")
        return items

    def run(self, arguments: ToolArguments) -> str:
        """
        List the folder that the arguments name, or the top-level folder.

        Side effects: database queries, and, for a repository that is not indexed yet, a Celery task
        queued to index it.

        :param arguments: The validated arguments, a :class:`ListFilesArguments`.
        :returns: The folder's name, its GitHub url, and its entries, as Markdown.
        :raises SmarterMCPServerToolError: If the repository is not indexed yet, or the folder has no
            indexed files.
        """
        arguments = cast(ListFilesArguments, arguments)
        repository = cast(ProjectRepository, self.scope.resolve(arguments.repository, required=True))
        index = require_index(repository)
        folder = ""
        if arguments.path:
            folder = arguments.path.strip().strip("/")
        items = self.entries(index, folder)
        if not items:
            raise SmarterMCPServerToolError(
                f"{folder} is not a folder of {repository.name}, or has no indexed files. "
                "Omit path for the top-level folder."
            )
        if folder:
            location = f"{repository.name}/{folder}"
        else:
            location = f"{repository.name} (top level)"
        github_url = f"{repository.github_url}/tree/{index.commit_sha}/{folder}"
        listing = "\n".join(items)
        return f"{location}\n{github_url}\n\n{listing}"


# -----------------------------------------------------------------------------
# search_blog, read_blog_post
# -----------------------------------------------------------------------------
def require_blog_index(blog: ProjectBlog) -> RepositoryIndex:
    """
    Return the blog's index.

    Side effects: see :func:`ready_indexes`.

    :param blog: The blog.
    :returns: Its index.
    :raises SmarterMCPServerToolError: If the blog is not indexed yet. It is then queued for indexing.
    """
    ready = ready_indexes([blog])
    index = ready.get(blog.name)
    if index is None:
        raise SmarterMCPServerToolError(
            f"The blog, {blog.url}, has not been indexed yet. Indexing has started: try again in a few minutes."
        )
    return index


class SearchBlogTool(SmarterProjectTool):
    """The ``search_blog`` tool: ranked passages of the blog's posts, with links to them."""

    name = "search_blog"
    title = "Search blog"
    description = (
        "Search the posts of The Smarter Project's blog, blog.smarter.sh: release announcements, with what "
        "changed in each version and how to upgrade, and articles about how and why Smarter was built, e.g. "
        "its security, logging, testing, caching and use of AI coding agents. Returns the best passages, with "
        "links to the posts. Use it, together with search_documentation, for why and how questions, design "
        "decisions, what changed in a release, and the project's history."
    )
    arguments_model = SearchArguments
    uses_repository = False
    project_wide = True

    def run(self, arguments: ToolArguments) -> str:
        """
        Search the blog's posts.

        Side effects: database queries, and, if the blog is not indexed yet, a Celery task queued to
        index it.

        :param arguments: The validated arguments, a :class:`SearchArguments`.
        :returns: The hits, best first, as Markdown, or a message that nothing matches.
        :raises SmarterMCPServerToolError: If the blog is not indexed yet.
        """
        arguments = cast(SearchArguments, arguments)
        blog = project_blog()
        require_blog_index(blog)
        hits = search_files([blog], arguments.query, kind=RepositoryFileKind.DOCUMENTATION, limit=arguments.limit)
        if not hits:
            message = (
                f'No post of the blog, {blog.url}, matches "{arguments.query}". Try other keywords, or '
                "search_documentation."
            )
            return message
        formatted_hits = [self.format_hit(number, hit) for number, hit in enumerate(hits, start=1)]
        results = "\n\n".join(formatted_hits)
        answer = (
            f'{len(hits)} posts of the blog, {blog.url}, for "{arguments.query}", best first. '
            f"Read a post with read_blog_post to see more of it.\n\n{results}"
        )
        return answer

    @staticmethod
    def format_hit(number: int, hit: SearchHit) -> str:
        """
        Return one hit, as Markdown: a numbered heading, the post's url, and its passage in a code block.

        :param number: The hit's rank, from 1.
        :param hit: The hit.
        :returns: The Markdown.
        """
        excerpt = numbered_excerpt(hit.lines)
        heading = hit.title
        if not heading:
            heading = hit.path
        return f"{number}. **{heading}** `{hit.path}`\n   Post: {hit.url}\n\n```text\n{excerpt}\n```"


class ReadBlogPostArguments(ToolArguments):
    """The arguments of read_blog_post."""

    path: str = Field(
        min_length=1,
        max_length=512,
        description="The post's path, e.g. 2026/10/26/release-smarter-api-v0-6, or its url.",
    )
    start_line: int = Field(default=1, ge=1, description="The first line to read.")
    end_line: Optional[int] = Field(
        default=None, ge=1, description=f"The last line to read. At most {MAX_READ_LINES} lines are read at once."
    )


class ReadBlogPostTool(SmarterProjectTool):
    """The ``read_blog_post`` tool: a post of the blog, or a range of its lines, as text with line numbers."""

    name = "read_blog_post"
    title = "Read blog post"
    description = (
        "Read a post of The Smarter Project's blog, blog.smarter.sh, as text with line numbers, from the "
        f"paths or urls that search_blog returns. Long posts are read {MAX_READ_LINES} lines at a time: use "
        "start_line and end_line to read more."
    )
    arguments_model = ReadBlogPostArguments
    uses_repository = False
    project_wide = True

    def run(self, arguments: ToolArguments) -> str:
        """
        Read the lines of the post that the arguments name, by its path or its url.

        Side effects: database queries, and, if the blog is not indexed yet, a Celery task queued to
        index it.

        :param arguments: The validated arguments, a :class:`ReadBlogPostArguments`.
        :returns: The post's url, and its lines in a code block, as Markdown.
        :raises SmarterMCPServerToolError: If the blog is not indexed yet, or has no such post. The error
            suggests posts with the same slug.
        """
        arguments = cast(ReadBlogPostArguments, arguments)
        blog = project_blog()
        index = require_blog_index(blog)
        path = blog.post_path(arguments.path)
        row = RepositoryFile.objects.filter(index=index, path=path).values("content").first()
        if row is None:
            raise SmarterMCPServerToolError(self.not_found(index, blog, path))
        lines = read_lines(row["content"], arguments.start_line, arguments.end_line)
        header = f"{blog.post_url(path)}, lines {lines.start}-{lines.end} of {lines.total}"
        footer = continuation("read_blog_post", "post", lines)
        return f"{header}\n\n```markdown\n{lines.text}\n```{footer}"

    @staticmethod
    def not_found(index: RepositoryIndex, blog: ProjectBlog, path: str) -> str:
        """
        Return an error message that suggests the posts that the LLM may have meant: those with the same slug.

        Side effects: one database query.

        :param index: The blog's index.
        :param blog: The blog.
        :param path: The path that was not found.
        :returns: The message.
        """
        slug = path.rsplit("/", 1)[-1]
        suggestions = suggested_paths(index, "-path", path__icontains=slug)
        message = f"{path} is not a post of the blog, {blog.url}."
        if suggestions and slug:
            message += " Did you mean: " + ", ".join(suggestions) + "?"
        else:
            message += " Use search_blog to find it."
        return message


__all__ = [
    "GetRepositoryOverviewTool",
    "ListFilesTool",
    "ReadBlogPostTool",
    "ReadFileTool",
    "SearchBlogTool",
    "SearchCodeTool",
    "SearchDocumentationTool",
    "queue_indexing_key",
]
