"""URL configuration for the connection app."""

from django.urls import path, re_path

from smarter.apps.connection.views.detailview import (
    ApiConnectionDetailView,
    SqlConnectionDetailView,
)
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

    listview = to_snake_case(ConnectionListApiView.__name__)
    sql_detailview = to_snake_case(SqlConnectionDetailView.__name__)
    api_detailview = to_snake_case(ApiConnectionDetailView.__name__)

    listview = to_snake_case(ConnectionListView.__name__)
    listview_api = to_snake_case(ConnectionListApiView.__name__)
    listview_api_all = to_snake_case(ConnectionListApiView.__name__) + "_all"
    listview_api_clone = to_snake_case(ConnectionListApiCloneView.__name__)
    listview_api_delete = to_snake_case(ConnectionListApiDeleteView.__name__)
    listview_api_rename = to_snake_case(ConnectionListApiRenameView.__name__)


urlpatterns = [
    path("", ConnectionListView.as_view(), name=ConnectionReverseNames.listview),
    path(
        "connections/sql-connection/<str:hashed_id>/",
        SqlConnectionDetailView.as_view(),
        name=ConnectionReverseNames.sql_detailview,
    ),
    path(
        "connections/api-connection/<str:hashed_id>/",
        ApiConnectionDetailView.as_view(),
        name=ConnectionReverseNames.api_detailview,
    ),
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
