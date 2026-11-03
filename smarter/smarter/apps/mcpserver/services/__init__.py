"""
The services of the MCPServer app: what it can do, for the rest of the platform.

The services know nothing of the Model Context Protocol. The MCPServer's tools
(:mod:`smarter.apps.mcpserver.protocol.tools`) are thin adapters of them, and any other part of
the platform, e.g. the web console, a management command or another app, can call them too.
Import them from this package, which names the app's capabilities, rather than from its modules.

**The Smarter Project's repositories, documentation and blog**, from the platform's own index of them:

- :mod:`~smarter.apps.mcpserver.services.repositories`: the repositories and the blog that are indexed.
- :mod:`~smarter.apps.mcpserver.services.indexing`: indexes them from GitHub and from WordPress,
  every hour, and queues one that is not indexed yet.
- :mod:`~smarter.apps.mcpserver.services.search`: searches their documentation, code and posts.
- :mod:`~smarter.apps.mcpserver.services.reading`: reads a file, a folder, a post, or a
  repository's overview.
- :mod:`~smarter.apps.mcpserver.services.manifests`: the JSON Schema and example manifest of each
  resource kind, and the platform's own validation of a manifest.
- :mod:`~smarter.apps.mcpserver.services.github`: searches and reads GitHub issues, and opens
  issues and pull requests as the caller.

**This platform's operations**, for its staff:

- :mod:`~smarter.apps.mcpserver.services.status`: the platform's health now, and the cluster as
  the cloud provider sees it.
- :mod:`~smarter.apps.mcpserver.services.logs`: the last 72 hours of the pod logs.
- :mod:`~smarter.apps.mcpserver.services.helpdesk`: one user's account and problems, and the
  check of a reply to them.
- :mod:`~smarter.apps.mcpserver.services.acting_user`: who is chatting with an LLMClient, signed by
  the platform for its own staff-only endpoint. The prompt api and the MCPClient app use it.

A service raises :class:`~smarter.apps.mcpserver.exceptions.SmarterMCPServerServiceError`, or its
subclass :class:`~smarter.apps.mcpserver.exceptions.SmarterMCPServerNotFoundError`, with a message
written for the caller.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from smarter.apps.mcpserver.exceptions import (
    SmarterMCPServerNotFoundError,
    SmarterMCPServerServiceError,
)
from smarter.apps.mcpserver.services.acting_user import (
    ACTING_USER_HEADER,
    acting_user,
    acting_user_headers,
    current_acting_user,
    is_staff_endpoint_url,
    staff_endpoint_url,
    verify_acting_user,
)
from smarter.apps.mcpserver.services.helpdesk.replies import check_reply
from smarter.apps.mcpserver.services.helpdesk.users import support_snapshot
from smarter.apps.mcpserver.services.indexing.blog import index_blog
from smarter.apps.mcpserver.services.indexing.github import index_repository
from smarter.apps.mcpserver.services.logs import log_errors, log_sources, search_logs
from smarter.apps.mcpserver.services.manifests import validate_manifest_text
from smarter.apps.mcpserver.services.reading import (
    list_files,
    read_blog_post,
    read_file,
    repositories_state,
    repository_overview,
)
from smarter.apps.mcpserver.services.repositories import (
    get_repository,
    project_blog,
    project_repositories,
)
from smarter.apps.mcpserver.services.search import (
    search_blog,
    search_code,
    search_documentation,
)
from smarter.apps.mcpserver.services.status.report import eks_status, platform_status

__all__ = [
    "ACTING_USER_HEADER",
    "SmarterMCPServerNotFoundError",
    "SmarterMCPServerServiceError",
    "acting_user",
    "acting_user_headers",
    "check_reply",
    "current_acting_user",
    "eks_status",
    "get_repository",
    "index_blog",
    "index_repository",
    "is_staff_endpoint_url",
    "list_files",
    "log_errors",
    "log_sources",
    "platform_status",
    "project_blog",
    "project_repositories",
    "read_blog_post",
    "read_file",
    "repositories_state",
    "repository_overview",
    "search_blog",
    "search_code",
    "search_documentation",
    "search_logs",
    "staff_endpoint_url",
    "support_snapshot",
    "validate_manifest_text",
    "verify_acting_user",
]
