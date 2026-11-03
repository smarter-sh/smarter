"""
The MCPServer's two sets of tools, one for each of its endpoints, in the order that ``tools/list`` lists them.

- :data:`PUBLIC_TOOL_CLASSES`: the public tools, served at ``/api/v1/mcp/smarter-project/`` by
  :class:`~smarter.apps.mcpserver.protocol.public.PublicEndpoint`. They read The Smarter Project's
  repositories, documentation, blog and manifest schemas, and its GitHub issues, and, with the
  caller's GitHub token, report issues and propose fixes.
- :data:`STAFF_TOOL_CLASSES`: the staff-only tools, served at ``/api/v1/mcp/smarter-operations/`` by
  :class:`~smarter.apps.mcpserver.protocol.staff.StaffEndpoint`. They read this platform's health,
  its pod logs and its users' accounts, for its staff.

Each tool is a thin adapter of a service of :mod:`smarter.apps.mcpserver.services`, in
:mod:`smarter.apps.mcpserver.protocol.tools`. Smarter's built-in MCPClients ``smarter_project``
and ``smarter_operations`` connect to one endpoint each, and choose which of its tools their
LLMClients may call (``allowedTools``).

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from smarter.apps.mcpserver.protocol.tools.github import (
    CloseIssueTool,
    CommentOnIssueTool,
    CreateIssueTool,
    CreatePullRequestTool,
    ReadIssueTool,
    SearchIssuesTool,
)
from smarter.apps.mcpserver.protocol.tools.helpdesk import (
    CheckReplyTool,
    UserSupportSnapshotTool,
)
from smarter.apps.mcpserver.protocol.tools.logs import (
    ListLogSourcesTool,
    SearchLogsTool,
    SummarizeLogErrorsTool,
)
from smarter.apps.mcpserver.protocol.tools.manifests import (
    GetManifestSchemaTool,
    ValidateManifestTool,
)
from smarter.apps.mcpserver.protocol.tools.public import PublicTool
from smarter.apps.mcpserver.protocol.tools.reading import (
    GetRepositoryOverviewTool,
    ListFilesTool,
    ReadBlogPostTool,
    ReadFileTool,
)
from smarter.apps.mcpserver.protocol.tools.search import (
    SearchBlogTool,
    SearchCodeTool,
    SearchDocumentationTool,
)
from smarter.apps.mcpserver.protocol.tools.staff import StaffTool
from smarter.apps.mcpserver.protocol.tools.status import (
    EksStatusTool,
    PlatformStatusTool,
)

PUBLIC_TOOL_CLASSES: tuple[type[PublicTool], ...] = (
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
    ReadIssueTool,
    CreateIssueTool,
    CommentOnIssueTool,
    CloseIssueTool,
    CreatePullRequestTool,
)
"""
Every public tool, in the order that tools/list lists them.

:class:`~smarter.apps.mcpserver.protocol.public.PublicEndpoint` creates one of each that its scope
serves (see :meth:`~smarter.apps.mcpserver.protocol.tools.public.PublicTool.serves`). The order
puts the tools that an LLM should try first, the overview and the searches, before the tools that
read one item, and the tools that write to GitHub last.
"""

STAFF_TOOL_CLASSES: tuple[type[StaffTool], ...] = (
    PlatformStatusTool,
    EksStatusTool,
    SummarizeLogErrorsTool,
    SearchLogsTool,
    ListLogSourcesTool,
    UserSupportSnapshotTool,
    CheckReplyTool,
)
"""
Every staff-only tool, in the order that tools/list lists them.

The order follows a help desk investigation: the platform's health first, then its logs, then one
user's account, and last the check of the reply to that user.
"""

__all__ = ["PUBLIC_TOOL_CLASSES", "STAFF_TOOL_CLASSES"]
