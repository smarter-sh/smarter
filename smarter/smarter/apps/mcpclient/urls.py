"""
Django URL patterns for the mcpclient app.

how we got here:
 - /mcpclients/api/v1/
"""

from django.urls import include, path, re_path

from smarter.apps.mcpclient.views.detailview import MCPClientDetailView
from smarter.apps.mcpclient.views.listview.api import (
    MCPClientListApiCloneView,
    MCPClientListApiDeleteView,
    MCPClientListApiRenameView,
    MCPClientListApiView,
)
from smarter.apps.mcpclient.views.listview.view import MCPClientListView
from smarter.common.utils import to_snake_case

from .api.const import namespace as api_namespace
from .const import namespace

app_name = namespace


class MCPClientReverseNames:
    """
    Holds named URL patterns for the account dashboard.

    This class provides constants for all named URL patterns used in the account dashboard views.
    """

    namespace = namespace

    listview = to_snake_case(MCPClientListApiView.__name__)
    detailview = to_snake_case(MCPClientDetailView.__name__)

    listview = to_snake_case(MCPClientListView.__name__)
    listview_api = to_snake_case(MCPClientListApiView.__name__)
    listview_api_all = to_snake_case(MCPClientListApiView.__name__) + "_all"
    listview_api_clone = to_snake_case(MCPClientListApiCloneView.__name__)
    listview_api_delete = to_snake_case(MCPClientListApiDeleteView.__name__)
    listview_api_rename = to_snake_case(MCPClientListApiRenameView.__name__)


urlpatterns = [
    path("api/", include("smarter.apps.mcpclient.api.urls", namespace=api_namespace)),
    path("mcpclients/<str:hashed_id>/", MCPClientDetailView.as_view(), name=MCPClientReverseNames.detailview),
    path("", MCPClientListView.as_view(), name=MCPClientReverseNames.listview),
    path(
        "react-integration/api/listview/", MCPClientListApiView.as_view(), name=MCPClientReverseNames.listview_api_all
    ),
    re_path(
        r"^react-integration/api/listview/(?:(?P<ownership_filter>owned|shared|all)/)?$",
        MCPClientListApiView.as_view(),
        name=MCPClientReverseNames.listview_api,
    ),
    path(
        "react-integration/api/clone/<int:llm_client_id>/<str:new_name>/",
        MCPClientListApiCloneView.as_view(),
        name=MCPClientReverseNames.listview_api_clone,
    ),
    path(
        "react-integration/api/delete/<int:llm_client_id>/",
        MCPClientListApiDeleteView.as_view(),
        name=MCPClientReverseNames.listview_api_delete,
    ),
    path(
        "react-integration/api/rename/<int:llm_client_id>/<str:new_name>/",
        MCPClientListApiRenameView.as_view(),
        name=MCPClientReverseNames.listview_api_rename,
    ),
]
