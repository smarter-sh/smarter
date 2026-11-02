"""
The base class of the Smarter Project MCP server's tools, the scope that they work on, and the limits of their results.

Each tool is a :class:`SmarterProjectTool`: a name, a description, a Pydantic model of its
arguments, from which its MCP ``inputSchema`` is generated, and :meth:`SmarterProjectTool.run`,
which returns its result as Markdown text for the LLM. :meth:`SmarterProjectTool.call`
validates the arguments, and caches a read-only tool's result.

A tool works on the repositories of its :class:`SmarterProjectScope`. The MCP server of
one repository serves the tools without a ``repository`` argument, and the MCP server of
all of the repositories adds one, whose values are the repositories' names.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from abc import abstractmethod
from typing import ClassVar, Optional

from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError

from smarter.apps.mcpserver.caching import (
    TOOL_CACHE_NAMESPACE,
    TOOL_RESULT_CACHE_TTL,
    index_generation,
)
from smarter.apps.mcpserver.exceptions import SmarterMCPServerToolError
from smarter.apps.mcpserver.protocol.base import (
    MCPToolBase,
    invalid_arguments,
    simplify_schema,
)
from smarter.apps.mcpserver.repositories import ProjectRepository, get_repository
from smarter.common.const import VERSION
from smarter.lib.cache.tool_results import cached_tool_call
from smarter.lib.typing import SmarterDictType

DEFAULT_SEARCH_LIMIT = 8
"""The number of results that a search tool returns when the LLM does not give a ``limit``."""

MAX_SEARCH_LIMIT = 20
"""The most results that a search tool returns, which keeps a result within the LLM's context."""

MAX_READ_CHARACTERS = 16000
"""The maximum length of a tool's result that reads a file or a schema, below the MCPClient's limit for a tool result."""


class SmarterProjectScope(BaseModel):
    """
    The repositories that one Smarter Project MCP server serves.

    The server creates its scope once, and gives it to each of its tools, which call
    :meth:`resolve` to turn a call's ``repository`` argument into a repository. It is frozen,
    because the tools share it.

    :param repository: The one repository of the server, or None for all of them.
    :param repositories: The repositories that the server serves: ``(repository,)``, or every
        repository of The Smarter Project.
    """

    model_config = ConfigDict(frozen=True)

    repository: Optional[ProjectRepository] = None
    """The one repository of the server, or None for the server of all of them."""

    repositories: tuple[ProjectRepository, ...]
    """The repositories that the server serves, in their configured order."""

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
        choices = ", ".join(self.names)
        if not name:
            if required:
                raise SmarterMCPServerToolError(f"repository is required. It is one of: {choices}.")
            return None
        repository = get_repository(name)
        if repository is None:
            raise SmarterMCPServerToolError(f"{name} is not a repository. It is one of: {choices}.")
        if repository.name not in self.names:
            raise SmarterMCPServerToolError(f"{name} is not a repository. It is one of: {choices}.")
        return repository


class ToolArguments(BaseModel):
    """
    The arguments of every tool: ``repository``, which only the MCP server of all of the repositories offers.

    A tool's own arguments model subclasses it. Arguments that the model does not define are
    refused (``extra="forbid"``), so that a misspelled argument is reported to the LLM rather than
    ignored.
    """

    model_config = ConfigDict(extra="forbid")

    repository: Optional[str] = Field(default=None, description="The repository.")
    """
    The name of the repository to work on, e.g. ``smarter-cli``.

    :meth:`SmarterProjectTool.input_schema` replaces its schema with an ``enum`` of the scope's
    repositories, or removes it from the server of one repository.
    """


class SmarterProjectTool(MCPToolBase):
    """
    A tool of the Smarter Project MCP server.

    A subclass sets :attr:`name`, :attr:`title`, :attr:`description` and :attr:`arguments_model`,
    the class attributes that say which servers serve it and how it takes a repository, and
    implements :meth:`run`. :meth:`call` validates the arguments and caches a read-only tool's
    result, so :meth:`run` only does the work.

    :param scope: The repositories of the MCP server.
    :param github_token: The caller's GitHub token, from the request's ``Authorization: Bearer``
        header, or None. Only a tool that :attr:`requires_github_token` uses it.
    """

    name: ClassVar[str]
    """The tool's name, which the LLM calls it by, e.g. ``search_code``."""

    title: ClassVar[str]
    """The tool's human-readable name, which an MCP client may show."""

    description: ClassVar[str]
    """What the tool does, and when to call it.

    The LLM reads it to decide which tool to call.
    """

    arguments_model: ClassVar[type[ToolArguments]] = ToolArguments
    """The Pydantic model of the tool's arguments, a subclass of :class:`ToolArguments`."""

    requires_repository: ClassVar[bool] = False
    """Whether a call to the MCP server of all of the repositories must name one."""
    uses_repository: ClassVar[bool] = True
    """Whether the tool takes a ``repository`` argument on the MCP server of all of the repositories."""
    project_wide: ClassVar[bool] = False
    """Whether only the MCP server of all of the repositories serves the tool."""
    requires_github_token: ClassVar[bool] = False
    """Whether the tool is served only to a request that carries the caller's GitHub token."""
    cache_ttl: ClassVar[Optional[int]] = None
    """Seconds that a read-only tool's result is cached, or None for :data:`~smarter.apps.mcpserver.caching.TOOL_RESULT_CACHE_TTL`."""

    def __init__(self, scope: SmarterProjectScope, github_token: Optional[SecretStr] = None):
        """
        Keep the server's scope, and the caller's GitHub token.

        :param scope: The repositories of the MCP server.
        :param github_token: The caller's GitHub token, or None.
        """
        self.scope = scope
        self.github_token = github_token

    @classmethod
    def serves(cls, scope: SmarterProjectScope, has_github_token: bool = False) -> bool:
        """
        Whether the MCP server of a scope serves the tool.

        A tool that :attr:`requires_github_token` is served only to a request that carries one, and
        a :attr:`project_wide` tool only by the MCP server of all of the repositories.

        :param scope: The server's repositories.
        :param has_github_token: Whether the request carries the caller's GitHub token.
        :returns: True if the server lists the tool, and lets the LLM call it.
        """
        if cls.requires_github_token and not has_github_token:
            return False
        if cls.project_wide and scope.is_single:
            return False
        return True

    def input_schema(self) -> SmarterDictType:
        """
        Return the tool's MCP ``inputSchema``.

        :returns: A JSON schema of type object. The MCP server of one repository omits
            ``repository``, and that of all of them lists the repositories' names.
        """
        model_schema = self.arguments_model.model_json_schema()
        schema = simplify_schema(model_schema)
        properties = schema.setdefault("properties", {})
        if self.scope.is_single or not self.uses_repository:
            properties.pop("repository", None)
        else:
            if self.requires_repository:
                description = "The repository."
            else:
                description = "The repository. Omit it to use all of the repositories."
            properties["repository"] = {
                "type": "string",
                "enum": self.scope.names,
                "description": description,
            }
            if self.requires_repository:
                # "repository" first, then the tool's own required arguments, in their order.
                required = ["repository"]
                for name in schema.get("required", []):
                    if name != "repository":
                        required.append(name)
                schema["required"] = required
        schema["type"] = "object"
        schema["additionalProperties"] = False
        return schema

    def call(self, arguments: Optional[SmarterDictType]) -> str:
        """
        Validate a tool call's arguments, and run the tool.

        The server of one repository, and a tool that does not :attr:`uses_repository`, drop a
        ``repository`` argument, which their schema does not offer, rather than refuse it.

        A read-only tool's result is cached for an hour, or its :attr:`cache_ttl`, until an index
        changes. See :mod:`smarter.apps.mcpserver.caching`. The cache key is the platform's version,
        the index generation, the server's repository (``*`` for all of them), the tool's name and
        its validated arguments, so a new release or a new index never serves a stale result. An
        error is not cached. A tool that writes runs on every call.

        **Side effects:** reads, and on a miss writes, the Django cache, with
        :func:`~smarter.lib.cache.tool_results.cached_tool_call`.

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
            raise invalid_arguments(self.name, e) from e
        if not self.read_only:
            return self.run(validated)
        if self.scope.repository:
            scope = self.scope.repository.name
        else:
            scope = "*"
        version = str(VERSION.get("__version__", "0.0.0"))
        # the index generation changes whenever an index does, so new files are found at once.
        generation = index_generation()
        key = (version, generation, scope, self.name)
        if self.cache_ttl is None:
            timeout = TOOL_RESULT_CACHE_TTL
        else:
            timeout = self.cache_ttl

        def run_tool() -> str:
            return self.run(validated)

        result = cached_tool_call(TOOL_CACHE_NAMESPACE, key, validated, timeout, run_tool)
        text = str(result.value)
        return text

    @abstractmethod
    def run(self, arguments: ToolArguments) -> str:
        """
        Run the tool.

        :meth:`call` has already validated the arguments, and checked the cache.

        :param arguments: The validated arguments, an instance of :attr:`arguments_model`.
        :returns: The result, as Markdown.
        :raises SmarterMCPServerToolError: If the tool fails in a way that the LLM should be told
            about, e.g. a file that does not exist.
        """


__all__ = [
    "DEFAULT_SEARCH_LIMIT",
    "MAX_READ_CHARACTERS",
    "MAX_SEARCH_LIMIT",
    "SmarterProjectScope",
    "SmarterProjectTool",
    "ToolArguments",
    "simplify_schema",
]
