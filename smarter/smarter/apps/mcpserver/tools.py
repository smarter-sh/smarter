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

A tool works on the repositories of its :class:`SmarterProjectScope`. The MCP server of
one repository serves the tools without a ``repository`` argument, and the MCP server of
all of the repositories adds one, whose values are the repositories' names.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

import copy
import posixpath
from abc import ABC, abstractmethod
from typing import ClassVar, Optional, cast

import mcp_types
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from smarter.lib import logging
from smarter.lib.cache import lazy_cache
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.typing import SmarterDictType

from .exceptions import SmarterMCPServerToolError
from .models import RepositoryFile, RepositoryFileKind, RepositoryIndex
from .repositories import (
    SMARTER_PROJECT_DOCS_LATEST_URL,
    ProjectRepository,
    get_repository,
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


def queue_indexing(repository: ProjectRepository) -> None:
    """
    Queue a repository that is not indexed for indexing, at most once every :data:`INDEX_QUEUE_TIMEOUT` seconds.

    :param repository: The repository.
    """
    # pylint: disable=import-outside-toplevel
    from .tasks import index_repository

    if lazy_cache.add(queue_indexing_key(repository.name), True, timeout=INDEX_QUEUE_TIMEOUT):
        index_repository.delay(repository.name)


def ready_indexes(repositories: list[ProjectRepository]) -> dict[str, RepositoryIndex]:
    """
    Return the indexes of the repositories that are ready to search, and queue the others for indexing.

    :param repositories: The repositories.
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

    def __init__(self, scope: SmarterProjectScope):
        self.scope = scope

    def input_schema(self) -> SmarterDictType:
        """
        Return the tool's MCP ``inputSchema``.

        :returns: A JSON schema of type object. The MCP server of one repository omits
            ``repository``, and that of all of them lists the repositories' names.
        """
        schema = simplify_schema(self.arguments_model.model_json_schema())
        properties = schema.setdefault("properties", {})
        if self.scope.is_single:
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

        :param arguments: The tool call's arguments.
        :returns: The result, as Markdown.
        :raises SmarterMCPServerToolError: If the arguments are not valid, or the tool fails.
        """
        arguments = dict(arguments or {})
        if self.scope.is_single:
            arguments.pop("repository", None)
        try:
            validated = self.arguments_model.model_validate(arguments)
        except ValidationError as e:
            problems = "; ".join(
                f"{'.'.join(str(part) for part in error['loc']) or 'arguments'}: {error['msg']}" for error in e.errors()
            )
            raise SmarterMCPServerToolError(f"invalid arguments for {self.name}: {problems}") from e
        return self.run(validated)

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
            "repository's docs/source. Name a repository to see its layout and README."
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
        lines = row["content"].splitlines()
        total = len(lines)
        start = min(arguments.start_line, max(total, 1))
        end = min(arguments.end_line or start + MAX_READ_LINES - 1, start + MAX_READ_LINES - 1, total)
        width = len(str(end))
        selected, characters = [], 0
        for number in range(start, end + 1):
            text = f"{number:>{width}}  {lines[number - 1]}"
            characters += len(text) + 1
            if characters > MAX_READ_CHARACTERS and selected:
                end = number - 1
                break
            selected.append(text)
        header = f"{repository.name}/{path}, lines {start}-{end} of {total}\n{repository.file_url(index.commit_sha, path, start, end)}"
        documentation_url = repository.documentation_url(path)
        if documentation_url:
            header += f"\nPublished at {documentation_url}"
        body = "\n".join(selected)
        footer = f"\n\nThe file continues: call read_file with start_line={end + 1}." if end < total else ""
        return f"{header}\n\n```{code_fence_language(path)}\n{body}\n```{footer}"

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


TOOL_CLASSES: tuple[type[SmarterProjectTool], ...] = (
    GetRepositoryOverviewTool,
    SearchDocumentationTool,
    SearchCodeTool,
    ReadFileTool,
    ListFilesTool,
)
"""Every tool of the Smarter Project MCP server, in the order that tools/list lists them."""

__all__ = [
    "TOOL_CLASSES",
    "GetRepositoryOverviewTool",
    "ListFilesTool",
    "ReadFileTool",
    "SearchCodeTool",
    "SearchDocumentationTool",
    "SmarterProjectScope",
    "SmarterProjectTool",
]
