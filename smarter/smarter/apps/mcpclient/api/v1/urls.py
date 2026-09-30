"""
URL configuration for the MCPClient app API.

These are mounted at ``/api/v1/mcpclients/``. See :mod:`smarter.apps.mcpclient.api.v1.views.views`.
"""

from django.urls import path

from smarter.common.utils import to_snake_case

from .const import namespace
from .views.views import (
    MCPClientListView,
    MCPClientRefreshView,
    MCPClientToolCallView,
    MCPClientToolsView,
    MCPClientView,
)

app_name = namespace
BY_ID = "_by_id"
BY_HASHED_ID = "_by_hashed_id"


class MCPClientApiV1ReverseViews:
    """
    Reverse view names for the MCPClient api.

    Each MCPClient view is available by the MCPClient's hashed id, and by its id.

    Example
    -------
    .. code-block:: python

        from django.urls import reverse
        url = reverse(
            f"{MCPClientApiV1ReverseViews.namespace}:{MCPClientApiV1ReverseViews.tools_by_hashed_id}",
            kwargs={"hashed_id": mcpclient.hashed_id},
        )
    """

    namespace = "api:v1:mcpclient"

    list_view = to_snake_case(MCPClientListView.__name__)

    mcpclient_by_hashed_id = to_snake_case(MCPClientView.__name__) + BY_HASHED_ID
    tools_by_hashed_id = to_snake_case(MCPClientToolsView.__name__) + BY_HASHED_ID
    refresh_by_hashed_id = to_snake_case(MCPClientRefreshView.__name__) + BY_HASHED_ID
    tool_call_by_hashed_id = to_snake_case(MCPClientToolCallView.__name__) + BY_HASHED_ID

    mcpclient_by_id = to_snake_case(MCPClientView.__name__) + BY_ID
    tools_by_id = to_snake_case(MCPClientToolsView.__name__) + BY_ID
    refresh_by_id = to_snake_case(MCPClientRefreshView.__name__) + BY_ID
    tool_call_by_id = to_snake_case(MCPClientToolCallView.__name__) + BY_ID


urlpatterns = [
    path("", MCPClientListView.as_view(), name=MCPClientApiV1ReverseViews.list_view),
    # by mcpclient_id
    path("<int:mcpclient_id>/", MCPClientView.as_view(), name=MCPClientApiV1ReverseViews.mcpclient_by_id),
    path("<int:mcpclient_id>/tools/", MCPClientToolsView.as_view(), name=MCPClientApiV1ReverseViews.tools_by_id),
    path("<int:mcpclient_id>/refresh/", MCPClientRefreshView.as_view(), name=MCPClientApiV1ReverseViews.refresh_by_id),
    path(
        "<int:mcpclient_id>/tools/<str:tool_name>/",
        MCPClientToolCallView.as_view(),
        name=MCPClientApiV1ReverseViews.tool_call_by_id,
    ),
    # by hashed_id
    path("<str:hashed_id>/", MCPClientView.as_view(), name=MCPClientApiV1ReverseViews.mcpclient_by_hashed_id),
    path("<str:hashed_id>/tools/", MCPClientToolsView.as_view(), name=MCPClientApiV1ReverseViews.tools_by_hashed_id),
    path(
        "<str:hashed_id>/refresh/",
        MCPClientRefreshView.as_view(),
        name=MCPClientApiV1ReverseViews.refresh_by_hashed_id,
    ),
    path(
        "<str:hashed_id>/tools/<str:tool_name>/",
        MCPClientToolCallView.as_view(),
        name=MCPClientApiV1ReverseViews.tool_call_by_hashed_id,
    ),
]
