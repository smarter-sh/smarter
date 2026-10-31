"""
The tools of the Smarter Project MCP server: :data:`TOOL_CLASSES`, in the order that ``tools/list`` lists them.

Each feature's tools are in its own package, beside the code that they call:

- :mod:`smarter.apps.mcpserver.index.tools`: the repositories and the blog, from the index.
- :mod:`smarter.apps.mcpserver.manifests.tools`: the platform's manifests.
- :mod:`smarter.apps.mcpserver.github.tools`: the GitHub issues.

Their base class is :class:`smarter.apps.mcpserver.protocol.tools.SmarterProjectTool`.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from smarter.apps.mcpserver.github.tools import (
    CommentOnIssueTool,
    CreateIssueTool,
    SearchIssuesTool,
)
from smarter.apps.mcpserver.index.tools import (
    GetRepositoryOverviewTool,
    ListFilesTool,
    ReadBlogPostTool,
    ReadFileTool,
    SearchBlogTool,
    SearchCodeTool,
    SearchDocumentationTool,
)
from smarter.apps.mcpserver.manifests.tools import (
    GetManifestSchemaTool,
    ValidateManifestTool,
)
from smarter.apps.mcpserver.protocol.tools import SmarterProjectTool

TOOL_CLASSES: tuple[type[SmarterProjectTool], ...] = (
    GetRepositoryOverviewTool,
    SearchDocumentationTool,
    SearchCodeTool,
    ReadFileTool,
    ListFilesTool,
    GetManifestSchemaTool,
    ValidateManifestTool,
    SearchBlogTool,
    ReadBlogPostTool,
    SearchIssuesTool,
    CreateIssueTool,
    CommentOnIssueTool,
)
"""Every tool of the Smarter Project MCP server, in the order that tools/list lists them."""

__all__ = ["TOOL_CLASSES"]
