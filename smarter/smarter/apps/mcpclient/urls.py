"""
Django URL patterns for the mcpclient app's web console pages.

- ``/mcpclient/``
- ``/mcpclient/mcpclients/<hashed_id>/``

The MCPClient api is at ``/api/v1/mcpclients/`` (:mod:`smarter.apps.mcpclient.api.v1.urls`), and the
endpoints that the console's React apps call are at ``/api/web/mcpclient/``
(:mod:`smarter.apps.mcpclient.api.web.urls`).
"""

from django.urls import path

from smarter.apps.mcpclient.views.detailview import MCPClientDetailView
from smarter.apps.mcpclient.views.listview.view import MCPClientListView
from smarter.common.utils import to_snake_case

from .const import namespace

app_name = namespace


class MCPClientReverseNames:
    """
    Reverse view names for the MCPClient app's console pages.

    The endpoints that the list page's React app calls are in the web console's api:
    see :class:`smarter.apps.mcpclient.api.web.urls.MCPClientApiWebReverseNames`.
    """

    namespace = namespace

    detailview = to_snake_case(MCPClientDetailView.__name__)
    listview = to_snake_case(MCPClientListView.__name__)


urlpatterns = [
    path("mcpclients/<str:hashed_id>/", MCPClientDetailView.as_view(), name=MCPClientReverseNames.detailview),
    path("", MCPClientListView.as_view(), name=MCPClientReverseNames.listview),
]
