"""
URL configuration of the MCPServer app: the endpoints of the MCP server.

The MCPServer serves its tools at two endpoints, mounted at ``/api/v1/mcp/``, in the
``api:v1:mcpserver`` namespace:

- ``smarter-project/``: the public tools, over every repository of The Smarter Project and its blog.
- ``smarter-project/<repository>/``: the public tools, over one repository, e.g. ``smarter-cli``.
- ``smarter-operations/``: the staff-only tools, for the platform's staff.

See :mod:`smarter.apps.mcpserver.protocol.views`.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from django.urls import path

from smarter.common.utils import to_snake_case

from .const import namespace
from .protocol.views import PublicEndpointView, StaffEndpointView

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
        url = reverse(f"{MCPServerReverseNames.namespace}:{MCPServerReverseNames.public_repository}", kwargs={"repository": "smarter-cli"})
    """

    #: The app's full namespace, under the api's.
    namespace = "api:v1:mcpserver"

    #: The endpoint of the public tools, over every repository.
    public = to_snake_case(PublicEndpointView.__name__)

    #: The endpoint of the public tools, over one repository, whose name is the ``repository`` kwarg.
    public_repository = to_snake_case(PublicEndpointView.__name__) + "_repository"

    #: The endpoint of the staff-only tools.
    staff = to_snake_case(StaffEndpointView.__name__)


urlpatterns = [
    path("smarter-project/", PublicEndpointView.as_view(), name=MCPServerReverseNames.public),
    path(
        "smarter-project/<str:repository>/",
        PublicEndpointView.as_view(),
        name=MCPServerReverseNames.public_repository,
    ),
    path(
        "smarter-operations/",
        StaffEndpointView.as_view(),
        name=MCPServerReverseNames.staff,
    ),
]
"""The MCPServer's endpoints."""
