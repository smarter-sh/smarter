"""
URL configuration of the MCPServer app: the endpoints of its MCP servers.

These are mounted at ``/api/v1/mcp/``, in the ``api:v1:mcpserver`` namespace:

- ``smarter-project/``: the Smarter Project MCP server, over every repository and the blog.
- ``smarter-project/<repository>/``: the same server, over one repository, e.g. ``smarter-cli``.
- ``smarter-operations/``: the Smarter Operations MCP server, for the platform's staff.

See :mod:`smarter.apps.mcpserver.protocol.views`.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from django.urls import path

from smarter.common.utils import to_snake_case

from .const import namespace
from .protocol.views import SmarterOperationsMCPServerView, SmarterProjectMCPServerView

app_name = namespace
"""The app's url namespace, ``mcpserver``."""


class MCPServerReverseNames:
    """
    Reverse view names of the MCPServer app.

    Each name is :func:`~smarter.common.utils.to_snake_case` of its view class's name, so that
    it changes with the view. Reverse them with :attr:`namespace`.

    Example
    -------
    .. code-block:: python

        from django.urls import reverse
        url = reverse(f"{MCPServerReverseNames.namespace}:{MCPServerReverseNames.repository}", kwargs={"repository": "smarter-cli"})
    """

    #: The app's full namespace, under the api's.
    namespace = "api:v1:mcpserver"

    #: The Smarter Project MCP server, over every repository.
    smarter_project = to_snake_case(SmarterProjectMCPServerView.__name__)

    #: The Smarter Project MCP server, over one repository, whose name is the ``repository`` kwarg.
    repository = to_snake_case(SmarterProjectMCPServerView.__name__) + "_repository"

    #: The Smarter Operations MCP server.
    smarter_operations = to_snake_case(SmarterOperationsMCPServerView.__name__)


urlpatterns = [
    path("smarter-project/", SmarterProjectMCPServerView.as_view(), name=MCPServerReverseNames.smarter_project),
    path(
        "smarter-project/<str:repository>/",
        SmarterProjectMCPServerView.as_view(),
        name=MCPServerReverseNames.repository,
    ),
    path(
        "smarter-operations/",
        SmarterOperationsMCPServerView.as_view(),
        name=MCPServerReverseNames.smarter_operations,
    ),
]
"""The MCP servers' endpoints."""
