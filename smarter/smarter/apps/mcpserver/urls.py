"""
URL configuration of the MCPServer app.

These are mounted at ``/api/v1/mcp/``. See :mod:`smarter.apps.mcpserver.views`.
"""

from django.urls import path

from smarter.common.utils import to_snake_case

from .const import namespace
from .views import SmarterProjectMCPServerView

app_name = namespace


class MCPServerReverseNames:
    """
    Reverse view names of the MCPServer app.

    Example
    -------
    .. code-block:: python

        from django.urls import reverse
        url = reverse(f"{MCPServerReverseNames.namespace}:{MCPServerReverseNames.repository}", kwargs={"repository": "smarter-cli"})
    """

    namespace = "api:v1:mcpserver"

    smarter_project = to_snake_case(SmarterProjectMCPServerView.__name__)
    repository = to_snake_case(SmarterProjectMCPServerView.__name__) + "_repository"


urlpatterns = [
    path("smarter-project/", SmarterProjectMCPServerView.as_view(), name=MCPServerReverseNames.smarter_project),
    path(
        "smarter-project/<str:repository>/",
        SmarterProjectMCPServerView.as_view(),
        name=MCPServerReverseNames.repository,
    ),
]
