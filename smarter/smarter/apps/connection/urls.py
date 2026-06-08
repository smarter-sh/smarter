"""URL configuration for the connection app."""

from django.urls import path, re_path

from smarter.apps.connection.views.detailview import ConnectionDetailView
from smarter.apps.connection.views.listview.api import (
    ConnectionListApiCloneView,
    ConnectionListApiDeleteView,
    ConnectionListApiRenameView,
    ConnectionListApiView,
)
from smarter.apps.connection.views.listview.view import ConnectionListView
from smarter.common.utils import to_snake_case

from .const import namespace

app_name = namespace


class ConnectionReverseNames:
    """Reverse view names for the connection app."""

    namespace = namespace

    listview = to_snake_case(ConnectionListApiView)
    detailview = to_snake_case(ConnectionDetailView)

    listview = to_snake_case(ConnectionListView)
    listview_api = to_snake_case(ConnectionListApiView)
    listview_api_all = to_snake_case(ConnectionListApiView) + "_all"
    listview_api_clone = to_snake_case(ConnectionListApiCloneView)
    listview_api_delete = to_snake_case(ConnectionListApiDeleteView)
    listview_api_rename = to_snake_case(ConnectionListApiRenameView)


urlpatterns = [
    path("", ConnectionListView.as_view(), name=ConnectionReverseNames.listview),
    path("connections/<str:kind>/<str:name>/", ConnectionDetailView.as_view(), name=ConnectionReverseNames.detailview),
    path("connections/<int:connection_id>/", ConnectionDetailView.as_view(), name=ConnectionReverseNames.detailview),
    path(
        "react-integration/api/listview/", ConnectionListApiView.as_view(), name=ConnectionReverseNames.listview_api_all
    ),
    re_path(
        r"^react-integration/api/listview/(?:(?P<ownership_filter>owned|shared|all)/)?$",
        ConnectionListApiView.as_view(),
        name=ConnectionReverseNames.listview_api,
    ),
    path(
        "react-integration/api/clone/<int:llm_client_id>/<str:new_name>/",
        ConnectionListApiCloneView.as_view(),
        name=ConnectionReverseNames.listview_api_clone,
    ),
    path(
        "react-integration/api/delete/<int:llm_client_id>/",
        ConnectionListApiDeleteView.as_view(),
        name=ConnectionReverseNames.listview_api_delete,
    ),
    path(
        "react-integration/api/rename/<int:llm_client_id>/<str:new_name>/",
        ConnectionListApiRenameView.as_view(),
        name=ConnectionReverseNames.listview_api_rename,
    ),
]
