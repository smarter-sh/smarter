"""URL configuration for the plugin app."""

from django.urls import path, re_path

from smarter.common.utils import to_snake_case

from .const import namespace
from .views.detailview import PluginDetailView
from .views.listview.api import (
    PluginListApiCloneView,
    PluginListApiDeleteView,
    PluginListApiRenameView,
    PluginListApiView,
)
from .views.listview.view import PluginListView

app_name = namespace


class PluginReverseNames:
    """Reverse view names for the plugin app."""

    namespace = namespace
    listview = to_snake_case(PluginListView)
    detailview = to_snake_case(PluginDetailView)

    listview = to_snake_case(PluginListView)
    listview_api = to_snake_case(PluginListApiView)
    listview_api_all = to_snake_case(PluginListApiView) + "_all"
    listview_api_clone = to_snake_case(PluginListApiCloneView)
    listview_api_delete = to_snake_case(PluginListApiDeleteView)
    listview_api_rename = to_snake_case(PluginListApiRenameView)


urlpatterns = [
    path("", PluginListView.as_view(), name=PluginReverseNames.listview),
    path("react-integration/api/listview/", PluginListApiView.as_view(), name=PluginReverseNames.listview_api_all),
    re_path(
        r"^react-integration/api/listview/(?:(?P<ownership_filter>owned|shared|all)/)?$",
        PluginListApiView.as_view(),
        name=PluginReverseNames.listview_api,
    ),
    path(
        "react-integration/api/clone/<int:llm_client_id>/<str:new_name>/",
        PluginListApiCloneView.as_view(),
        name=PluginReverseNames.listview_api_clone,
    ),
    path(
        "react-integration/api/delete/<int:llm_client_id>/",
        PluginListApiDeleteView.as_view(),
        name=PluginReverseNames.listview_api_delete,
    ),
    path(
        "react-integration/api/rename/<int:llm_client_id>/<str:new_name>/",
        PluginListApiRenameView.as_view(),
        name=PluginReverseNames.listview_api_rename,
    ),
    path("plugins/<str:name>/", PluginDetailView.as_view(), name=PluginReverseNames.detailview),
]
