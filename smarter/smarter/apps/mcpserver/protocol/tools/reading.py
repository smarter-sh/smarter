"""
The public tools that read the index: ``get_repository_overview``, ``read_file``, ``list_files`` and ``read_blog_post``.

Each tool validates its arguments, calls :mod:`smarter.apps.mcpserver.services.reading`, and formats
what it returns as Markdown. They are served at the MCPServer's public endpoint
(:mod:`smarter.apps.mcpserver.protocol.public`). ``read_blog_post`` has no ``repository`` argument,
and only the endpoint of every repository serves it. Every tool is read-only, so
:meth:`~smarter.apps.mcpserver.protocol.tools.public.PublicTool.call` caches its results until an
index changes.

A file, folder or post that does not exist is a tool error that suggests what the LLM may have
meant, or else which tool finds it.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from typing import Optional, cast

from pydantic import Field

from smarter.apps.mcpserver.exceptions import (
    SmarterMCPServerNotFoundError,
    SmarterMCPServerToolError,
)
from smarter.apps.mcpserver.protocol.tools.markdown import code_fence_language
from smarter.apps.mcpserver.protocol.tools.public import PublicTool, PublicToolArguments
from smarter.apps.mcpserver.services.reading import (
    MAX_READ_LINES,
    FolderEntry,
    ReadLines,
    list_files,
    read_blog_post,
    read_file,
    repositories_state,
    repository_overview,
)
from smarter.apps.mcpserver.services.repositories import (
    SMARTER_PROJECT_DOCS_ROOT_URL,
    ProjectRepository,
    project_blog,
)


def continuation(tool_name: str, noun: str, lines: ReadLines) -> str:
    """
    Return the note that tells the LLM how to read the rest of a file or post.

    :param tool_name: The tool that reads on, e.g. ``read_file``.
    :param noun: What is read, e.g. ``file`` or ``post``.
    :param lines: The lines that were read.
    :returns: The note, which starts with a blank line, or an empty string if the last line was read.
    """
    if lines.is_complete:
        return ""
    next_line = lines.end + 1
    note = f"\n\nThe {noun} continues: call {tool_name} with start_line={next_line}."
    return note


def not_found(error: SmarterMCPServerNotFoundError, hint: str) -> SmarterMCPServerToolError:
    """
    Return the tool error for something that does not exist, with a hint when there is nothing to suggest.

    :param error: The service's error, whose message names what was not found, and suggests what
        the LLM may have meant.
    :param hint: What to do when there are no suggestions, e.g. ``Use search_blog to find it.``
    :returns: The tool error, for the caller to raise ``from error``.
    """
    message = error.message
    if not error.suggestions:
        message += f" {hint}"
    tool_error = SmarterMCPServerToolError(message)
    return tool_error


def entry_items(entries: list[FolderEntry], hidden: int) -> list[str]:
    """
    Return the folders and files of a listing as Markdown list items.

    :param entries: The folders and files.
    :param hidden: The number of entries left out.
    :returns: One item per entry, the folders with their number of files and the files with their
        sizes, and a last item that counts the entries left out, if any.
    """
    items = []
    for entry in entries:
        if entry.is_folder:
            items.append(f"- {entry.name}/ ({entry.files} files)")
        else:
            items.append(f"- {entry.name} ({entry.size} bytes)")
    if hidden:
        items.append(f"- ... and {hidden} more")
    return items


# -----------------------------------------------------------------------------
# get_repository_overview
# -----------------------------------------------------------------------------
class GetRepositoryOverviewTool(PublicTool):
    """
    The ``get_repository_overview`` tool: what a repository contains, how it is laid out, and its README.

    Without a repository, it lists every repository of the endpoint, with whether each is indexed.
    """

    name = "get_repository_overview"
    title = "Repository overview"
    description = (
        "Describe a repository of The Smarter Project: what it contains, its GitHub url, its indexed "
        "commit, its top-level folders and files, and its README. Use it for questions about a repository "
        "as a whole, not to answer a specific question, which the search tools answer directly."
    )

    def run(self, arguments: PublicToolArguments) -> str:
        """
        Describe the named repository, with :func:`~smarter.apps.mcpserver.services.reading.repository_overview`, or list them all if none is named.

        **Side effects:** database queries, and, for a repository that is not indexed yet, a Celery task
        queued to index it.

        :param arguments: The validated arguments.
        :returns: The overview, as Markdown.
        :raises SmarterMCPServerToolError: If the repository is not one of the endpoint's.
        :raises SmarterMCPServerServiceError: If the repository is not indexed yet.
        """
        repository = self.scope.resolve(arguments.repository, required=False)
        if repository is None:
            return self.all_repositories()
        overview = repository_overview(repository)
        indexed_at = f"{overview.indexed_at:%Y-%m-%d %H:%M}"
        top_level = entry_items(overview.top_level, overview.top_level_hidden)

        parts = [
            f"# {repository.name}: {repository.title}",
            repository.description,
            f"- GitHub: {repository.github_url}",
        ]
        if repository.docs_url:
            parts.append(f"- Published documentation: {repository.docs_url}, built from {repository.docs_root}/")
        parts.append(
            f"- Indexed commit: {overview.commit_sha} of {repository.ref}, "
            f"{indexed_at} UTC: {overview.file_count} files, "
            f"{overview.documentation_files} of documentation and {overview.code_files} of code"
        )
        parts.append("\n## Top-level folders and files\n\n" + "\n".join(top_level))
        if overview.readme_path:
            excerpt = overview.readme
            if overview.readme_truncated:
                excerpt += f"\n\n[README truncated: read the rest with read_file, path {overview.readme_path}]"
            parts.append(f"\n## {overview.readme_path}\n\n{excerpt}")
        text = "\n".join(parts)
        return text

    def all_repositories(self) -> str:
        """
        Return a table of every repository of the scope, with whether each one is indexed.

        **Side effects:** see :func:`~smarter.apps.mcpserver.services.reading.repositories_state`.

        :returns: The table, as Markdown, and where the documentation and the blog are.
        """
        states = repositories_state(self.scope.repositories)
        rows = ["| Repository | Contents | Indexed |", "| --- | --- | --- |"]
        for state in states:
            repository = state.repository
            if state.is_indexed:
                indexed = f"{state.commit_sha[:7]}, {state.file_count} files"
            else:
                indexed = "not yet"
            rows.append(f"| [{repository.name}]({repository.github_url}) | {repository.description} | {indexed} |")

        table = "\n".join(rows)
        blog_url = project_blog().url
        overview = (
            "# The Smarter Project's repositories\n\n"
            + table
            + f"\n\nThe documentation, {SMARTER_PROJECT_DOCS_ROOT_URL}, is built from the smarter "
            f"repository's docs/source. The blog, {blog_url}, is searched with search_blog. "
            "Name a repository to see its layout and README."
        )
        return overview


# -----------------------------------------------------------------------------
# read_file
# -----------------------------------------------------------------------------
class ReadFileArguments(PublicToolArguments):
    """The arguments of read_file."""

    path: str = Field(min_length=1, max_length=512, description="The file's path in the repository, e.g. README.md.")
    start_line: int = Field(default=1, ge=1, description="The first line to read.")
    end_line: Optional[int] = Field(
        default=None, ge=1, description=f"The last line to read. At most {MAX_READ_LINES} lines are read at once."
    )


class ReadFileTool(PublicTool):
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

    def run(self, arguments: PublicToolArguments) -> str:
        """
        Read the lines of the file that the arguments name, with :func:`~smarter.apps.mcpserver.services.reading.read_file`.

        The result starts with the file's GitHub url at the indexed commit, and its published
        documentation page, if it is one.

        **Side effects:** database queries, and, for a repository that is not indexed yet, a Celery task
        queued to index it.

        :param arguments: The validated arguments, a :class:`ReadFileArguments`.
        :returns: The lines, in a code block, as Markdown.
        :raises SmarterMCPServerToolError: If the repository has no such file. The error suggests files
            with a similar path.
        :raises SmarterMCPServerServiceError: If the repository is not indexed yet.
        """
        read_arguments = cast(ReadFileArguments, arguments)
        repository = cast(ProjectRepository, self.scope.resolve(read_arguments.repository, required=True))
        try:
            file_lines = read_file(repository, read_arguments.path, read_arguments.start_line, read_arguments.end_line)
        except SmarterMCPServerNotFoundError as e:
            raise not_found(e, "Use list_files or search_code to find it.") from e
        lines = file_lines.lines
        header = f"{repository.name}/{file_lines.path}, lines {lines.start}-{lines.end} of {lines.total}\n{file_lines.github_url}"
        if file_lines.documentation_url:
            header += f"\nPublished at {file_lines.documentation_url}"
        footer = continuation("read_file", "file", lines)
        language = code_fence_language(file_lines.path)
        text = f"{header}\n\n```{language}\n{lines.text}\n```{footer}"
        return text


# -----------------------------------------------------------------------------
# list_files
# -----------------------------------------------------------------------------
class ListFilesArguments(PublicToolArguments):
    """The arguments of list_files."""

    path: Optional[str] = Field(
        default=None,
        max_length=512,
        description="The folder, e.g. smarter/smarter/apps. Omit it for the repository's top-level folder.",
    )


class ListFilesTool(PublicTool):
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

    def run(self, arguments: PublicToolArguments) -> str:
        """
        List the folder that the arguments name, or the top-level folder, with :func:`~smarter.apps.mcpserver.services.reading.list_files`.

        **Side effects:** database queries, and, for a repository that is not indexed yet, a Celery task
        queued to index it.

        :param arguments: The validated arguments, a :class:`ListFilesArguments`.
        :returns: The folder's name, its GitHub url, and its entries, as Markdown.
        :raises SmarterMCPServerToolError: If the folder has no indexed files.
        :raises SmarterMCPServerServiceError: If the repository is not indexed yet.
        """
        list_arguments = cast(ListFilesArguments, arguments)
        repository = cast(ProjectRepository, self.scope.resolve(list_arguments.repository, required=True))
        try:
            listing = list_files(repository, list_arguments.path)
        except SmarterMCPServerNotFoundError as e:
            raise not_found(e, "Omit path for the top-level folder.") from e
        if listing.folder:
            location = f"{repository.name}/{listing.folder}"
        else:
            location = f"{repository.name} (top level)"
        items = entry_items(listing.entries, listing.hidden)
        text = "\n".join(items)
        result = f"{location}\n{listing.github_url}\n\n{text}"
        return result


# -----------------------------------------------------------------------------
# read_blog_post
# -----------------------------------------------------------------------------
class ReadBlogPostArguments(PublicToolArguments):
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


class ReadBlogPostTool(PublicTool):
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

    def run(self, arguments: PublicToolArguments) -> str:
        """
        Read the lines of the post that the arguments name, by its path or its url, with :func:`~smarter.apps.mcpserver.services.reading.read_blog_post`.

        **Side effects:** database queries, and, if the blog is not indexed yet, a Celery task queued to
        index it.

        :param arguments: The validated arguments, a :class:`ReadBlogPostArguments`.
        :returns: The post's url, and its lines in a code block, as Markdown.
        :raises SmarterMCPServerToolError: If the blog has no such post. The error suggests posts with
            the same slug.
        :raises SmarterMCPServerServiceError: If the blog is not indexed yet.
        """
        read_arguments = cast(ReadBlogPostArguments, arguments)
        try:
            post = read_blog_post(read_arguments.path, read_arguments.start_line, read_arguments.end_line)
        except SmarterMCPServerNotFoundError as e:
            raise not_found(e, "Use search_blog to find it.") from e
        lines = post.lines
        header = f"{post.url}, lines {lines.start}-{lines.end} of {lines.total}"
        footer = continuation("read_blog_post", "post", lines)
        text = f"{header}\n\n```markdown\n{lines.text}\n```{footer}"
        return text


__all__ = [
    "GetRepositoryOverviewTool",
    "ListFilesTool",
    "ReadBlogPostTool",
    "ReadFileTool",
]
