"""
The MCP tools that a prompt offers the LLM.

:class:`MCPToolkit` turns an LLMClient's MCPClients into what an OpenAI-compatible chat
completion needs:

- **tools**: one function tool per MCP server tool that the MCPClient allows, named
  ``mcp<id>_<tool name>``, with the server's description and input schema. If the
  MCPClient allows resources, and the server has any, a ``mcp<id>_read_resource`` tool
  reads them.
- **instructions**: the servers' instructions, for the system prompt.
- **tool calls**: :meth:`MCPToolkit.call` runs a tool call on the right server, and
  returns the result as text for the LLM. Errors are returned to the LLM as text, so
  that it can recover, rather than failing the prompt.

An MCP server that cannot be reached is skipped, and reported in :attr:`MCPToolkit.errors`,
so that one unavailable server does not fail the prompt.

.. note::

    **Experimental.** The MCPClient was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

import hashlib
import re
from dataclasses import dataclass
from typing import Any, Optional

from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .caching import get_cached_catalog
from .connection import (
    MAX_INSTRUCTIONS_CHARACTERS,
    MCPServerConnection,
    MCPToolInfo,
    is_tool_allowed,
    truncate,
)
from .exceptions import SmarterMCPClientException
from .models import MCPClient
from .signals import (
    mcpclient_resource_read,
    mcpclient_tool_called,
    mcpclient_tool_failed,
    mcpclient_tool_responded,
)

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.MCPCLIENT_LOGGING])

FUNCTION_NAME_PATTERN = re.compile(r"[^A-Za-z0-9_-]")
MAX_FUNCTION_NAME_LENGTH = 64
"""The maximum length of an OpenAI function name."""
MAX_DESCRIPTION_LENGTH = 1024
"""The maximum length of a tool description offered to the LLM."""
READ_RESOURCE = "read_resource"
TOOL = "tool"


@dataclass(frozen=True)
class MCPFunction:
    """A function tool offered to the LLM, and what it calls."""

    name: str
    mcpclient: MCPClient
    kind: str
    tool_name: Optional[str] = None


def input_schema(tool: MCPToolInfo) -> dict[str, Any]:
    """
    Return a tool's input schema as OpenAI function parameters.

    :param tool: The tool.
    :returns: A JSON schema of type object.
    """
    schema = {key: value for key, value in (tool.input_schema or {}).items() if key != "$schema"}
    schema["type"] = "object"
    schema.setdefault("properties", {})
    return schema


class MCPToolkit:
    """
    The MCP tools, instructions and tool call dispatch of one prompt.

    :param mcpclients: The LLMClient's active MCPClients, in order of priority.

    **Example usage**::

        toolkit = MCPToolkit(LLMClientMCPClients.mcpclients_for(llmclient)).load()
        tools.extend(toolkit.tools)
        ...
        if toolkit.is_mcp_function(tool_call.function.name):
            content = toolkit.call(tool_call.function.name, arguments)
    """

    def __init__(self, mcpclients: list[MCPClient]):
        self.mcpclients = mcpclients
        self.tools: list[dict[str, Any]] = []
        self.functions: dict[str, MCPFunction] = {}
        self.instructions: dict[str, str] = {}
        self.errors: dict[str, str] = {}
        self.connected: list[MCPClient] = []

    @property
    def formatted_class_name(self) -> str:
        """The class name, for logging."""
        return logging.formatted_text(f"{__name__}.{self.__class__.__name__}")

    def function_name(self, mcpclient: MCPClient, name: str) -> str:
        """
        Return a unique OpenAI function name for one of an MCPClient's tools.

        The name is ``mcp<id>_<name>``, with characters that OpenAI does not allow replaced
        by underscores, and at most 64 characters long. If two tools would have the same
        name, a short hash of the tool's name is appended.

        :param mcpclient: The MCPClient.
        :param name: The name of the tool, as the server reports it.
        :returns: The function name.
        """
        candidate = f"mcp{mcpclient.id}_{FUNCTION_NAME_PATTERN.sub('_', name)}"[:MAX_FUNCTION_NAME_LENGTH]
        if candidate in self.functions:
            suffix = "_" + hashlib.sha256(name.encode()).hexdigest()[:6]
            candidate = candidate[: MAX_FUNCTION_NAME_LENGTH - len(suffix)] + suffix
        return candidate

    def add_function(self, function: MCPFunction, description: str, parameters: dict[str, Any]) -> None:
        """Add a function tool, and remember what it calls."""
        self.functions[function.name] = function
        self.tools.append(
            {
                "type": "function",
                "function": {
                    "name": function.name,
                    "description": truncate(description, MAX_DESCRIPTION_LENGTH),
                    "parameters": parameters,
                },
            }
        )

    def load(self) -> "MCPToolkit":
        """
        Fetch each MCPClient's catalog, from the cache if possible, and build its tools.

        :returns: This toolkit.
        """
        for mcpclient in self.mcpclients:
            try:
                catalog = get_cached_catalog(mcpclient)
            except SmarterMCPClientException as e:
                self.errors[mcpclient.name] = e.message
                logger.warning("%s.load() skipping MCPClient %s: %s", self.formatted_class_name, mcpclient.name, e)
                continue
            self.connected.append(mcpclient)
            for tool in catalog.tools:
                if not is_tool_allowed(mcpclient, tool.name):
                    continue
                function = MCPFunction(
                    name=self.function_name(mcpclient, tool.name), mcpclient=mcpclient, kind=TOOL, tool_name=tool.name
                )
                label = tool.title or tool.name
                description = f"{label}, from the {mcpclient.name} MCP server. {tool.description}".strip()
                self.add_function(function, description, input_schema(tool))
            if catalog.has_resources and mcpclient.allowed_resources:
                function = MCPFunction(
                    name=self.function_name(mcpclient, READ_RESOURCE), mcpclient=mcpclient, kind=READ_RESOURCE
                )
                patterns = ", ".join(mcpclient.allowed_resources)
                description = (
                    f"Read a resource from the {mcpclient.name} MCP server, by its URI. "
                    f"Resource URIs must match one of: {patterns}"
                )
                parameters = {
                    "type": "object",
                    "properties": {"uri": {"type": "string", "description": "The URI of the resource."}},
                    "required": ["uri"],
                }
                self.add_function(function, description, parameters)
            if mcpclient.include_instructions and catalog.instructions:
                self.instructions[mcpclient.name] = truncate(catalog.instructions.strip(), MAX_INSTRUCTIONS_CHARACTERS)
        return self

    def system_prompt(self) -> Optional[str]:
        """
        Return the MCP servers' instructions, for the system prompt.

        :returns: The instructions, or None if no server has any.
        """
        if not self.instructions:
            return None
        sections = [
            f'Instructions from the "{name}" MCP server, whose tools are named mcp<n>_...:\n{instructions}'
            for name, instructions in self.instructions.items()
        ]
        return "\n\n".join(sections)

    def is_mcp_function(self, function_name: str) -> bool:
        """Return whether a function name is one of this toolkit's tools."""
        return function_name in self.functions

    def mcpclient_for(self, function_name: str) -> Optional[MCPClient]:
        """Return the MCPClient of one of this toolkit's tools."""
        function = self.functions.get(function_name)
        return function.mcpclient if function else None

    def call(self, function_name: str, arguments: Optional[dict[str, Any]] = None) -> str:
        """
        Run a tool call, and return its result as text for the LLM.

        Errors, including an unreachable server and errors that the tool reports, are
        returned as text that begins with ``Error:``, so that the LLM can recover.

        :param function_name: The function name that the LLM called.
        :param arguments: The function's arguments.
        :returns: The result, or a description of the error.
        """
        function = self.functions.get(function_name)
        if function is None:
            return f"Error: {function_name} is not an MCP tool."
        mcpclient = function.mcpclient
        arguments = arguments if isinstance(arguments, dict) else {}
        connection = MCPServerConnection(mcpclient)
        target = function.tool_name or READ_RESOURCE
        mcpclient_tool_called.send(sender=self.__class__, mcpclient=mcpclient, tool_name=target, arguments=arguments)
        try:
            if function.kind == READ_RESOURCE:
                uri = str(arguments.get("uri", ""))
                text = connection.read_resource(uri)
                mcpclient_resource_read.send(sender=self.__class__, mcpclient=mcpclient, uri=uri, characters=len(text))
            else:
                result = connection.call_tool(function.tool_name or "", arguments)
                text = f"Error: {result.text}" if result.is_error else result.text
                mcpclient_tool_responded.send(
                    sender=self.__class__,
                    mcpclient=mcpclient,
                    tool_name=target,
                    is_error=result.is_error,
                    characters=len(text),
                )
        except SmarterMCPClientException as e:
            mcpclient_tool_failed.send(sender=self.__class__, mcpclient=mcpclient, tool_name=target, error=e.message)
            return f"Error: {e.message}"
        return text or "(the tool returned no content)"


__all__ = ["MCPFunction", "MCPToolkit"]
