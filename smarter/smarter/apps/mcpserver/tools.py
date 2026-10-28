"""
The tools of the Smarter Project MCP server.

Each tool is a :class:`SmarterProjectTool`: a name, a description, a Pydantic model of its
arguments, from which its MCP ``inputSchema`` is generated, and :meth:`SmarterProjectTool.run`,
which returns its result as Markdown text for the LLM. Every tool is read-only.

- ``get_repository_overview``: what a repository contains, its layout, and its README.
- ``search_documentation``: ranked passages of the documentation.
- ``search_code``: ranked files of source code, with their matching lines.
- ``read_file``: a file, or a range of its lines, with line numbers.
- ``list_files``: the folders and files under a folder.
- ``search_blog``: ranked passages of the posts of the blog, blog.smarter.sh.
- ``read_blog_post``: a post of the blog, with line numbers.
- ``get_manifest_schema``: a resource kind's example manifest, and its fields.

A tool works on the repositories of its :class:`SmarterProjectScope`. The MCP server of
one repository serves the tools without a ``repository`` argument, and the MCP server of
all of the repositories adds one, whose values are the repositories' names. The blog's
tools have no ``repository`` argument, and only the MCP server of all of the repositories
serves them.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

import copy
import posixpath
from abc import ABC, abstractmethod
from typing import ClassVar, Optional, Sequence, cast

import mcp_types
import yaml
from cache_results import lazy_cache
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from smarter.apps.api.v1.contract.const import SAM_SCHEMA_SUFFIX
from smarter.common.const import VERSION
from smarter.lib import json, logging
from smarter.lib.cache.tool_results import cached_tool_call
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.typing import SmarterDictType

from . import manifests
from .caching import TOOL_CACHE_NAMESPACE, TOOL_RESULT_CACHE_TTL, index_generation
from .exceptions import SmarterMCPServerToolError
from .models import RepositoryFile, RepositoryFileKind, RepositoryIndex
from .repositories import (
    SMARTER_PROJECT_DOCS_LATEST_URL,
    ProjectBlog,
    ProjectRepository,
    ProjectSource,
    get_repository,
    project_blog,
)
from .search import SearchHit, search_files

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.MCPSERVER_LOGGING])

DEFAULT_SEARCH_LIMIT = 8
MAX_SEARCH_LIMIT = 20
MAX_READ_LINES = 400
"""The maximum number of lines that read_file returns at once."""
MAX_READ_CHARACTERS = 16000
"""The maximum length of read_file's result, below the MCPClient's limit for a tool result."""
MAX_LIST_ENTRIES = 300
MAX_README_CHARACTERS = 6000
README_NAMES = ("README.md", "README.rst", "readme.md", "README.txt", "README")
INDEX_QUEUE_TIMEOUT = 600
"""Seconds during which a repository that is not indexed is queued for indexing only once."""

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


class SmarterProjectScope(BaseModel):
    """
    The repositories that one Smarter Project MCP server serves.

    :param repository: The one repository of the server, or None for all of them.
    """

    model_config = ConfigDict(frozen=True)

    repository: Optional[ProjectRepository] = None
    repositories: tuple[ProjectRepository, ...]

    @property
    def is_single(self) -> bool:
        """Whether the server serves one repository."""
        return self.repository is not None

    @property
    def names(self) -> list[str]:
        """The names of the repositories."""
        return [repository.name for repository in self.repositories]

    def resolve(self, name: Optional[str], required: bool) -> Optional[ProjectRepository]:
        """
        Return the repository that a tool call names.

        :param name: The tool call's ``repository`` argument.
        :param required: Whether the tool needs one repository.
        :returns: The server's one repository, the named repository, or None for all of them.
        :raises SmarterMCPServerToolError: If the name is not one of the scope's repositories,
            or a required name is missing.
        """
        if self.repository is not None:
            return self.repository
        if not name:
            if required:
                raise SmarterMCPServerToolError(f"repository is required. It is one of: {', '.join(self.names)}.")
            return None
        repository = get_repository(name)
        if repository is None or repository.name not in self.names:
            raise SmarterMCPServerToolError(f"{name} is not a repository. It is one of: {', '.join(self.names)}.")
        return repository


def queue_indexing_key(name: str) -> str:
    """Return the cache key that remembers that a repository was queued for indexing."""
    return f"smarter.apps.mcpserver.tools.queue_indexing.{name}"


def queue_indexing(repository: ProjectSource) -> None:
    """
    Queue a repository, or the blog, that is not indexed for indexing, at most once every :data:`INDEX_QUEUE_TIMEOUT` seconds.

    :param repository: The repository, or the blog.
    """
    # pylint: disable=import-outside-toplevel
    from .tasks import index_blog, index_repository

    if lazy_cache.add(queue_indexing_key(repository.name), True, timeout=INDEX_QUEUE_TIMEOUT):
        if isinstance(repository, ProjectBlog):
            index_blog.delay()
        else:
            index_repository.delay(repository.name)


def ready_indexes(repositories: Sequence[ProjectSource]) -> dict[str, RepositoryIndex]:
    """
    Return the indexes of the repositories that are ready to search, and queue the others for indexing.

    :param repositories: The repositories, or the blog.
    :returns: The ready indexes, by repository name.
    """
    indexes = {
        index.repository: index
        for index in RepositoryIndex.objects.filter(repository__in=[r.name for r in repositories])
    }
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

    :param repository: The repository.
    :returns: Its index.
    :raises SmarterMCPServerToolError: If the repository is not indexed yet. It is then queued for indexing.
    """
    index = ready_indexes([repository]).get(repository.name)
    if index is None:
        raise SmarterMCPServerToolError(
            f"{repository.name} has not been indexed yet. Indexing has started: try again in a few minutes."
        )
    return index


def not_indexed_note(repositories: list[ProjectRepository], ready: dict[str, RepositoryIndex]) -> str:
    """Return a note that names the repositories that were not searched because they are not indexed yet."""
    missing = [repository.name for repository in repositories if repository.name not in ready]
    if not missing:
        return ""
    return f"\n\nNot searched, because they are still being indexed: {', '.join(missing)}. Try again in a few minutes."


def code_fence_language(path: str) -> str:
    """Return the Markdown code fence language of a file."""
    return CODE_FENCE_LANGUAGES.get(posixpath.splitext(path)[1].lower(), "text")


def simplify_schema(schema: SmarterDictType) -> SmarterDictType:
    """
    Simplify a Pydantic JSON schema for an LLM.

    Titles, the model's docstring and null defaults are removed, and an optional field's
    ``anyOf: [<type>, null]`` becomes its type.

    :param schema: The schema, from ``model_json_schema()``.
    :returns: The simplified schema.
    """
    schema = copy.deepcopy(schema)
    schema.pop("title", None)
    schema.pop("description", None)
    for name, prop in list(schema.get("properties", {}).items()):
        prop.pop("title", None)
        if "default" in prop and prop["default"] is None:
            prop.pop("default")
        variants = prop.get("anyOf")
        if variants and len(variants) == 2 and {"type": "null"} in variants:
            prop.pop("anyOf")
            prop.update(next(variant for variant in variants if variant != {"type": "null"}))
        schema["properties"][name] = prop
    return schema


class ToolArguments(BaseModel):
    """The arguments of every tool: ``repository``, which only the MCP server of all of the repositories offers."""

    model_config = ConfigDict(extra="forbid")

    repository: Optional[str] = Field(default=None, description="The repository.")


class SmarterProjectTool(ABC):
    """
    A tool of the Smarter Project MCP server.

    :param scope: The repositories of the MCP server.
    """

    name: ClassVar[str]
    title: ClassVar[str]
    description: ClassVar[str]
    arguments_model: ClassVar[type[ToolArguments]] = ToolArguments
    requires_repository: ClassVar[bool] = False
    """Whether a call to the MCP server of all of the repositories must name one."""
    uses_repository: ClassVar[bool] = True
    """Whether the tool takes a ``repository`` argument on the MCP server of all of the repositories."""
    project_wide: ClassVar[bool] = False
    """Whether only the MCP server of all of the repositories serves the tool."""

    def __init__(self, scope: SmarterProjectScope):
        self.scope = scope

    @classmethod
    def serves(cls, scope: SmarterProjectScope) -> bool:
        """Whether the MCP server of a scope serves the tool."""
        return not (cls.project_wide and scope.is_single)

    def input_schema(self) -> SmarterDictType:
        """
        Return the tool's MCP ``inputSchema``.

        :returns: A JSON schema of type object. The MCP server of one repository omits
            ``repository``, and that of all of them lists the repositories' names.
        """
        schema = simplify_schema(self.arguments_model.model_json_schema())
        properties = schema.setdefault("properties", {})
        if self.scope.is_single or not self.uses_repository:
            properties.pop("repository", None)
        else:
            properties["repository"] = {
                "type": "string",
                "enum": self.scope.names,
                "description": (
                    "The repository."
                    if self.requires_repository
                    else "The repository. Omit it to use all of the repositories."
                ),
            }
            if self.requires_repository:
                schema["required"] = [
                    "repository",
                    *[name for name in schema.get("required", []) if name != "repository"],
                ]
        schema["type"] = "object"
        schema["additionalProperties"] = False
        return schema

    def definition(self) -> mcp_types.Tool:
        """Return the tool, as tools/list lists it."""
        return mcp_types.Tool(
            name=self.name,
            title=self.title,
            description=self.description,
            input_schema=self.input_schema(),
            annotations=mcp_types.ToolAnnotations(
                title=self.title,
                read_only_hint=True,
                destructive_hint=False,
                idempotent_hint=True,
                open_world_hint=False,
            ),
        )

    def call(self, arguments: Optional[SmarterDictType]) -> str:
        """
        Validate a tool call's arguments, and run the tool.

        The result is cached for an hour, until an index changes. See
        :mod:`smarter.apps.mcpserver.caching`.

        :param arguments: The tool call's arguments.
        :returns: The result, as Markdown.
        :raises SmarterMCPServerToolError: If the arguments are not valid, or the tool fails.
        """
        arguments = dict(arguments or {})
        if self.scope.is_single or not self.uses_repository:
            arguments.pop("repository", None)
        try:
            validated = self.arguments_model.model_validate(arguments)
        except ValidationError as e:
            problems = "; ".join(
                f"{'.'.join(str(part) for part in error['loc']) or 'arguments'}: {error['msg']}" for error in e.errors()
            )
            raise SmarterMCPServerToolError(f"invalid arguments for {self.name}: {problems}") from e
        scope = self.scope.repository.name if self.scope.repository else "*"
        # the index generation changes whenever an index does, so new files are found at once.
        key = (str(VERSION.get("__version__", "0.0.0")), index_generation(), scope, self.name)
        result = cached_tool_call(
            TOOL_CACHE_NAMESPACE, key, validated, TOOL_RESULT_CACHE_TTL, lambda: self.run(validated)
        )
        return str(result.value)

    @abstractmethod
    def run(self, arguments: ToolArguments) -> str:
        """
        Run the tool.

        :param arguments: The validated arguments, an instance of :attr:`arguments_model`.
        :returns: The result, as Markdown.
        """


# -----------------------------------------------------------------------------
# get_repository_overview
# -----------------------------------------------------------------------------
class GetRepositoryOverviewTool(SmarterProjectTool):
    """What a repository contains, how it is laid out, and its README."""

    name = "get_repository_overview"
    title = "Repository overview"
    description = (
        "Describe a repository of The Smarter Project: what it contains, its GitHub url, its indexed "
        "commit, its top-level folders and files, and its README. Use it for questions about a repository "
        "as a whole, not to answer a specific question, which the search tools answer directly."
    )

    def run(self, arguments: ToolArguments) -> str:
        repository = self.scope.resolve(arguments.repository, required=False)
        if repository is None:
            return self.all_repositories()
        index = require_index(repository)
        files = RepositoryFile.objects.filter(index=index)
        documentation = files.filter(kind=RepositoryFileKind.DOCUMENTATION).count()
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
            f"{documentation} of documentation and {index.file_count - documentation} of code"
        )
        parts.append("\n## Top-level folders and files\n\n" + "\n".join(top_level))
        readme = files.filter(path__in=README_NAMES).order_by("path").values_list("path", "content").first()
        if readme:
            path, content = readme
            excerpt = content[:MAX_README_CHARACTERS]
            if len(content) > MAX_README_CHARACTERS:
                excerpt += f"\n\n[README truncated: read the rest with read_file, path {path}]"
            parts.append(f"\n## {path}\n\n{excerpt}")
        return "\n".join(parts)

    def all_repositories(self) -> str:
        """Return a table of every repository of the scope."""
        indexes = {index.repository: index for index in RepositoryIndex.objects.filter(repository__in=self.scope.names)}
        rows = ["| Repository | Contents | Indexed |", "| --- | --- | --- |"]
        for repository in self.scope.repositories:
            index = indexes.get(repository.name)
            if index is not None and index.is_ready:
                indexed = f"{(index.commit_sha or '')[:7]}, {index.file_count} files"
            else:
                indexed = "not yet"
                queue_indexing(repository)
            rows.append(f"| [{repository.name}]({repository.github_url}) | {repository.description} | {indexed} |")
        return (
            "# The Smarter Project's repositories\n\n"
            + "\n".join(rows)
            + f"\n\nThe documentation, {SMARTER_PROJECT_DOCS_LATEST_URL}, is built from the smarter "
            f"repository's docs/source. The blog, {project_blog().url}, is searched with search_blog. "
            "Name a repository to see its layout and README."
        )


# -----------------------------------------------------------------------------
# search_documentation, search_code
# -----------------------------------------------------------------------------
class SearchArguments(ToolArguments):
    """The arguments of search_documentation."""

    query: str = Field(
        min_length=1,
        max_length=500,
        description='Keywords, identifiers or "quoted phrases", e.g. custom domain verification.',
    )
    limit: int = Field(
        default=DEFAULT_SEARCH_LIMIT, ge=1, le=MAX_SEARCH_LIMIT, description="The maximum number of results."
    )


class SearchCodeArguments(SearchArguments):
    """The arguments of search_code."""

    path: Optional[str] = Field(
        default=None,
        max_length=512,
        description="Only search files under this folder, e.g. smarter/smarter/apps/llmclient.",
    )


class SearchTool(SmarterProjectTool):
    """The base class of the search tools."""

    kind: ClassVar[str]
    noun: ClassVar[str]

    def search(self, arguments: SearchArguments, path: Optional[str] = None) -> str:
        """Search the scope's repositories, and return the hits as Markdown."""
        repository = self.scope.resolve(arguments.repository, required=False)
        repositories = [repository] if repository else list(self.scope.repositories)
        ready = ready_indexes(repositories)
        if not ready:
            raise SmarterMCPServerToolError(
                f"{', '.join(r.name for r in repositories)} has not been indexed yet. "
                "Indexing has started: try again in a few minutes."
            )
        hits = search_files(
            [r for r in repositories if r.name in ready],
            arguments.query,
            kind=self.kind,
            path=path,
            limit=arguments.limit,
        )
        where = repository.name if repository else "The Smarter Project's repositories"
        if not hits:
            return (
                f'No {self.noun} of {where} matches "{arguments.query}". Try other keywords, an identifier, '
                "or the other search tool." + not_indexed_note(repositories, ready)
            )
        results = "\n\n".join(self.format_hit(number, hit) for number, hit in enumerate(hits, start=1))
        return (
            f'{len(hits)} results in the {self.noun} of {where}, for "{arguments.query}", best first. '
            f"Read a file with read_file to see more of it.\n\n{results}" + not_indexed_note(repositories, ready)
        )

    def format_hit(self, number: int, hit: SearchHit) -> str:
        """Return one hit, as Markdown."""
        heading = f"{number}. **{hit.title}** `{hit.path}`" if hit.title else f"{number}. `{hit.path}`"
        if not self.scope.is_single:
            heading += f" in {hit.repository}"
        links = []
        if hit.documentation_url:
            links.append(f"   Documentation: {hit.documentation_url}")
        links.append(f"   Source: {hit.url}")
        width = len(str(hit.lines[-1].number)) if hit.lines else 1
        excerpt = "\n".join(f"{line.number:>{width}}  {line.text}" for line in hit.lines)
        fence = code_fence_language(hit.path) if hit.kind == RepositoryFileKind.CODE else "text"
        return f"{heading}\n" + "\n".join(links) + f"\n\n```{fence}\n{excerpt}\n```"


class SearchDocumentationTool(SearchTool):
    """Search the documentation."""

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
        return self.search(cast(SearchArguments, arguments))


class SearchCodeTool(SearchTool):
    """Search the source code."""

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

    :param content: The file's content.
    :param start_line: The first line to read, from 1.
    :param end_line: The last line to read, or None to read as many as allowed.
    :returns: The lines.
    """
    lines = content.splitlines()
    total = len(lines)
    start = min(start_line, max(total, 1))
    end = min(end_line or start + MAX_READ_LINES - 1, start + MAX_READ_LINES - 1, total)
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


class ReadFileArguments(ToolArguments):
    """The arguments of read_file."""

    path: str = Field(min_length=1, max_length=512, description="The file's path in the repository, e.g. README.md.")
    start_line: int = Field(default=1, ge=1, description="The first line to read.")
    end_line: Optional[int] = Field(
        default=None, ge=1, description=f"The last line to read. At most {MAX_READ_LINES} lines are read at once."
    )


class ReadFileTool(SmarterProjectTool):
    """Read a file."""

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
        arguments = cast(ReadFileArguments, arguments)
        repository = cast(ProjectRepository, self.scope.resolve(arguments.repository, required=True))
        index = require_index(repository)
        path = arguments.path.strip().lstrip("/")
        row = RepositoryFile.objects.filter(index=index, path=path).values("content", "line_count").first()
        if row is None:
            raise SmarterMCPServerToolError(self.not_found(index, repository, path))
        lines = read_lines(row["content"], arguments.start_line, arguments.end_line)
        header = f"{repository.name}/{path}, lines {lines.start}-{lines.end} of {lines.total}\n{repository.file_url(index.commit_sha, path, lines.start, lines.end)}"
        documentation_url = repository.documentation_url(path)
        if documentation_url:
            header += f"\nPublished at {documentation_url}"
        footer = (
            f"\n\nThe file continues: call read_file with start_line={lines.end + 1}."
            if lines.end < lines.total
            else ""
        )
        return f"{header}\n\n```{code_fence_language(path)}\n{lines.text}\n```{footer}"

    def not_found(self, index: RepositoryIndex, repository: ProjectRepository, path: str) -> str:
        """Return an error message that suggests the files that the LLM may have meant."""
        basename = posixpath.basename(path)
        suggestions = list(
            RepositoryFile.objects.filter(index=index, path__iendswith="/" + basename)
            .order_by("path")
            .values_list("path", flat=True)[:8]
        )
        if not suggestions:
            suggestions = list(
                RepositoryFile.objects.filter(index=index, path__icontains=basename)
                .order_by("path")
                .values_list("path", flat=True)[:8]
            )
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
    """List a folder."""

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

        :param index: The repository's index.
        :param folder: The folder, or an empty string for the top level.
        :returns: The folders, then the files, each sorted by name.
        """
        prefix = folder.strip("/") + "/" if folder.strip("/") else ""
        folders: dict[str, int] = {}
        files: list[tuple[str, int]] = []
        for path, size in RepositoryFile.objects.filter(index=index, path__startswith=prefix).values_list(
            "path", "size"
        ):
            rest = path[len(prefix) :]
            if "/" in rest:
                name = rest.split("/", 1)[0]
                folders[name] = folders.get(name, 0) + 1
            else:
                files.append((rest, size))
        items = [f"- {name}/ ({count} files)" for name, count in sorted(folders.items())]
        items += [f"- {name} ({size} bytes)" for name, size in sorted(files)]
        if len(items) > MAX_LIST_ENTRIES:
            items = items[:MAX_LIST_ENTRIES] + [f"- ... and {len(items) - MAX_LIST_ENTRIES} more"]
        return items

    def run(self, arguments: ToolArguments) -> str:
        arguments = cast(ListFilesArguments, arguments)
        repository = cast(ProjectRepository, self.scope.resolve(arguments.repository, required=True))
        index = require_index(repository)
        folder = (arguments.path or "").strip().strip("/")
        items = self.entries(index, folder)
        if not items:
            raise SmarterMCPServerToolError(
                f"{folder} is not a folder of {repository.name}, or has no indexed files. "
                "Omit path for the top-level folder."
            )
        location = f"{repository.name}/{folder}" if folder else f"{repository.name} (top level)"
        return f"{location}\n{repository.github_url}/tree/{index.commit_sha}/{folder}\n\n" + "\n".join(items)


# -----------------------------------------------------------------------------
# search_blog, read_blog_post
# -----------------------------------------------------------------------------
def require_blog_index(blog: ProjectBlog) -> RepositoryIndex:
    """
    Return the blog's index.

    :param blog: The blog.
    :returns: Its index.
    :raises SmarterMCPServerToolError: If the blog is not indexed yet. It is then queued for indexing.
    """
    index = ready_indexes([blog]).get(blog.name)
    if index is None:
        raise SmarterMCPServerToolError(
            f"The blog, {blog.url}, has not been indexed yet. Indexing has started: try again in a few minutes."
        )
    return index


class SearchBlogTool(SmarterProjectTool):
    """Search the blog's posts."""

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
        arguments = cast(SearchArguments, arguments)
        blog = project_blog()
        require_blog_index(blog)
        hits = search_files([blog], arguments.query, kind=RepositoryFileKind.DOCUMENTATION, limit=arguments.limit)
        if not hits:
            return (
                f'No post of the blog, {blog.url}, matches "{arguments.query}". Try other keywords, or '
                "search_documentation."
            )
        results = "\n\n".join(self.format_hit(number, hit) for number, hit in enumerate(hits, start=1))
        return (
            f'{len(hits)} posts of the blog, {blog.url}, for "{arguments.query}", best first. '
            f"Read a post with read_blog_post to see more of it.\n\n{results}"
        )

    @staticmethod
    def format_hit(number: int, hit: SearchHit) -> str:
        """Return one hit, as Markdown."""
        width = len(str(hit.lines[-1].number)) if hit.lines else 1
        excerpt = "\n".join(f"{line.number:>{width}}  {line.text}" for line in hit.lines)
        return f"{number}. **{hit.title or hit.path}** `{hit.path}`\n   Post: {hit.url}\n\n```text\n{excerpt}\n```"


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
    """Read a post of the blog."""

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
        arguments = cast(ReadBlogPostArguments, arguments)
        blog = project_blog()
        index = require_blog_index(blog)
        path = blog.post_path(arguments.path)
        row = RepositoryFile.objects.filter(index=index, path=path).values("content").first()
        if row is None:
            slug = path.rsplit("/", 1)[-1]
            suggestions = list(
                RepositoryFile.objects.filter(index=index, path__icontains=slug)
                .order_by("-path")
                .values_list("path", flat=True)[:8]
            )
            message = f"{path} is not a post of the blog, {blog.url}."
            if suggestions and slug:
                message += " Did you mean: " + ", ".join(suggestions) + "?"
            else:
                message += " Use search_blog to find it."
            raise SmarterMCPServerToolError(message)
        lines = read_lines(row["content"], arguments.start_line, arguments.end_line)
        header = f"{blog.post_url(path)}, lines {lines.start}-{lines.end} of {lines.total}"
        footer = (
            f"\n\nThe post continues: call read_blog_post with start_line={lines.end + 1}."
            if lines.end < lines.total
            else ""
        )
        return f"{header}\n\n```markdown\n{lines.text}\n```{footer}"


# -----------------------------------------------------------------------------
# get_manifest_schema
# -----------------------------------------------------------------------------
class GetManifestSchemaArguments(ToolArguments):
    """The arguments of get_manifest_schema."""

    kind: Optional[str] = Field(
        default=None,
        max_length=64,
        description="The resource kind, e.g. LLMClient, Guardrail or MCPClient. Omit it to list the kinds.",
    )


class GetManifestSchemaTool(SmarterProjectTool):
    """A resource kind's example manifest, and the fields of its JSON Schema."""

    name = "get_manifest_schema"
    title = "Get manifest schema"
    description = (
        "Return a Smarter resource kind's example manifest, in YAML, and every field that its manifest may "
        "have: its path, type, whether it is required, its default and its description, from the JSON "
        "Schema that this platform validates manifests with. Use it before writing, fixing or explaining a "
        "manifest, rather than guessing its fields. Omit kind to list the kinds."
    )
    arguments_model = GetManifestSchemaArguments
    uses_repository = False

    def run(self, arguments: ToolArguments) -> str:
        arguments = cast(GetManifestSchemaArguments, arguments)
        kinds = manifests.manifest_kinds()
        if not arguments.kind:
            return (
                "# Smarter resource kinds\n\nEach kind's manifest is a YAML file with apiVersion, kind, metadata "
                "and spec. Call get_manifest_schema with one of these kinds for its example and fields:\n\n"
                + "\n".join(f"- {kind}" for kind in kinds)
            )
        kind = manifests.find_kind(arguments.kind)
        if kind is None:
            raise SmarterMCPServerToolError(
                f"{arguments.kind} is not a resource kind. It is one of: {', '.join(kinds)}."
            )
        schema = manifests.manifest_schema(kind)
        example = yaml.safe_dump(manifests.manifest_example(kind), sort_keys=False, allow_unicode=True).rstrip()
        schema_url = self.schema_url(kind)
        header = (
            f"# {kind} manifest\n\n{schema.get('description', '')} The example and fields are this platform's, "
            f"version {VERSION.get('__version__', '0.0.0')}. Apply a manifest with `smarter apply -f <file>.yaml`.\n"
            f"Full JSON Schema: {schema_url}\n\n## Example\n\n```yaml\n{example}\n```\n\n## Fields\n\n"
            "The read-only status, which the platform writes, is left out. `[]` is an item of a list, and "
            "`<key>` a key of a map.\n"
        )
        lines, characters, fields = [], len(header), manifests.manifest_fields(schema)
        for number, field in enumerate(fields):
            line = self.format_field(field)
            if characters + len(line) + 1 > MAX_READ_CHARACTERS:
                lines.append(f"\n[{len(fields) - number} more fields: see the full JSON Schema, {schema_url}]")
                break
            lines.append(line)
            characters += len(line) + 1
        return header + "\n".join(lines)

    @staticmethod
    def schema_url(kind: str) -> str:
        """Return the GitHub url of a kind's JSON Schema, in the smarter repository."""
        repository = get_repository("smarter") or ProjectRepository(
            name="smarter", title="the Smarter platform", description="The Smarter platform."
        )
        return repository.file_url(None, f"{manifests.SAM_SCHEMA_REPOSITORY_PATH}/{kind}{SAM_SCHEMA_SUFFIX}")

    @staticmethod
    def format_field(field: manifests.ManifestField) -> str:
        """Return one field, as a Markdown list item."""
        details = [field.type, "required" if field.required else "optional"]
        if field.default is not None:
            details.append(f"default {json.dumps(field.default)}")
        text = f"- `{field.path}` ({', '.join(details)})"
        return f"{text}: {field.description}" if field.description else text


TOOL_CLASSES: tuple[type[SmarterProjectTool], ...] = (
    GetRepositoryOverviewTool,
    SearchDocumentationTool,
    SearchCodeTool,
    ReadFileTool,
    ListFilesTool,
    GetManifestSchemaTool,
    SearchBlogTool,
    ReadBlogPostTool,
)
"""Every tool of the Smarter Project MCP server, in the order that tools/list lists them."""

__all__ = [
    "TOOL_CLASSES",
    "GetManifestSchemaTool",
    "GetRepositoryOverviewTool",
    "ListFilesTool",
    "ReadBlogPostTool",
    "ReadFileTool",
    "SearchBlogTool",
    "SearchCodeTool",
    "SearchDocumentationTool",
    "SmarterProjectScope",
    "SmarterProjectTool",
]
