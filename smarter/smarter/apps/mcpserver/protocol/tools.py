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

import copy
from abc import ABC, abstractmethod
from typing import ClassVar, Optional

import mcp_types
from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError

from smarter.apps.mcpserver.caching import (
    TOOL_CACHE_NAMESPACE,
    TOOL_RESULT_CACHE_TTL,
    index_generation,
)
from smarter.apps.mcpserver.exceptions import SmarterMCPServerToolError
from smarter.apps.mcpserver.repositories import ProjectRepository, get_repository

DEFAULT_SEARCH_LIMIT = 8
MAX_SEARCH_LIMIT = 20
MAX_READ_CHARACTERS = 16000
"""The maximum length of a tool's result that reads a file or a schema, below the MCPClient's limit for a tool result."""
from smarter.common.const import VERSION
from smarter.lib.cache.tool_results import cached_tool_call
from smarter.lib.typing import SmarterDictType


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
    :param github_token: The caller's GitHub token, from the request's ``Authorization: Bearer``
        header, or None. Only a tool that :attr:`requires_github_token` uses it.
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
    read_only: ClassVar[bool] = True
    """Whether the tool only reads.

    A tool that writes is annotated so, and its results are never cached.
    """
    requires_github_token: ClassVar[bool] = False
    """Whether the tool is served only to a request that carries the caller's GitHub token."""
    open_world: ClassVar[bool] = False
    """Whether the tool reaches beyond the index, e.g. to GitHub, rather than the platform's own data."""
    cache_ttl: ClassVar[Optional[int]] = None
    """Seconds that a read-only tool's result is cached, or None for :data:`~smarter.apps.mcpserver.caching.TOOL_RESULT_CACHE_TTL`."""

    def __init__(self, scope: SmarterProjectScope, github_token: Optional[SecretStr] = None):
        self.scope = scope
        self.github_token = github_token

    @classmethod
    def serves(cls, scope: SmarterProjectScope, has_github_token: bool = False) -> bool:
        """
        Whether the MCP server of a scope serves the tool.

        :param scope: The server's repositories.
        :param has_github_token: Whether the request carries the caller's GitHub token.
        """
        if cls.requires_github_token and not has_github_token:
            return False
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
                read_only_hint=self.read_only,
                destructive_hint=False,
                idempotent_hint=self.read_only,
                open_world_hint=self.open_world,
            ),
        )

    def call(self, arguments: Optional[SmarterDictType]) -> str:
        """
        Validate a tool call's arguments, and run the tool.

        A read-only tool's result is cached for an hour, or its :attr:`cache_ttl`, until an index
        changes. See :mod:`smarter.apps.mcpserver.caching`. A tool that writes runs on every call.

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
        if not self.read_only:
            return self.run(validated)
        scope = self.scope.repository.name if self.scope.repository else "*"
        # the index generation changes whenever an index does, so new files are found at once.
        key = (str(VERSION.get("__version__", "0.0.0")), index_generation(), scope, self.name)
        timeout = TOOL_RESULT_CACHE_TTL if self.cache_ttl is None else self.cache_ttl
        result = cached_tool_call(TOOL_CACHE_NAMESPACE, key, validated, timeout, lambda: self.run(validated))
        return str(result.value)

    @abstractmethod
    def run(self, arguments: ToolArguments) -> str:
        """
        Run the tool.

        :param arguments: The validated arguments, an instance of :attr:`arguments_model`.
        :returns: The result, as Markdown.
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
